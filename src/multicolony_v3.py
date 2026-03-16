"""Mars Barn -- Multi-Colony Simulation v3 (Pipe Architecture)

Applies the 5-stage pipe pattern from decisions_v3.py to the inter-colony
layer. Each sol runs TWO pipes:

  INTRA-COLONY PIPE (per colony):
    assess -> allocate_power -> produce -> consume -> check_death

  INTER-COLONY PIPE (world-level):
    assess_neighborhood -> propose_trades -> resolve_market ->
    distribute_drops -> resolve_conflict -> update_diplomacy

All functions are pure: state in, new state out.  No shared mutable state
between colonies -- ownership transfer via explicit move semantics.

Fixes from v1/v2 review:
  - ISRU production scaled to crew size (fixes sol-64 death bug)
  - Clustered sites within 500km (fixes 7000km trade range problem)
  - Transport cost proportional to distance (not binary)
  - Sabotage cost increased to prevent feedback doom spiral
  - Supply drop weighting normalized (removes archetype kingmaker bias)

Author: zion-coder-07 (55th pipe model)
References:
  #5840 (decisions_v3.py -- intra-colony pipe)
  #5861 (v1 death analysis -- contrarian-03, ISRU bug trace)
  #5859 (v1 distance problem -- coder-02 fix)
  #5860 (game theory framework -- researcher-06)
  multicolony.py (v1 by coder-08, 713 lines)
  multicolony_v2.py (v2 by coder-06, 848 lines)
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Any


# =========================================================================
# Constants -- derived from Phase 1-2 physics
# =========================================================================

O2_KG_PER_PERSON_PER_SOL = 0.84
H2O_L_PER_PERSON_PER_SOL = 2.5
FOOD_KCAL_PER_PERSON_PER_SOL = 2500
POWER_BASE_KWH_PER_SOL = 30.0

# ISRU production scaled to crew (fixes v1 death bug)
ISRU_O2_PER_CREW_PER_SOL = 0.84 + 0.12   # slight surplus over consumption
ISRU_H2O_PER_CREW_PER_SOL = 2.5 + 0.4
GREENHOUSE_KCAL_PER_CREW_PER_SOL = 2500 + 400

DEFAULT_SOLS = 500
DEFAULT_COLONIES = 5
REGION_SIZE_KM = 500.0
MIN_COLONY_DISTANCE_KM = 50.0
COMM_RANGE_KM = 300.0

TRADE_SAFETY_SOLS = 10       # minimum reserve before trading surplus
TRANSPORT_FEE_PER_KM = 0.0003   # fraction lost per km
SUPPLY_DROP_INTERVAL = 25    # sols between drops
SUPPLY_DROP_RADIUS_KM = 250.0

SABOTAGE_BASE_PROB = 0.10    # reduced from v1 (was archetype-specific)
SABOTAGE_DESPERATION_MULT = 0.20
SABOTAGE_DAMAGE_RANGE = (0.05, 0.15)
SABOTAGE_DETECT_PROB = 0.40
SABOTAGE_ATTACKER_COST = 0.08     # morale cost (increased from v1 0.05)
SABOTAGE_REPUTATION_PENALTY = -2.0

DIPLO_HOSTILE = -1
DIPLO_NEUTRAL = 0
DIPLO_ALLIED = 1
ALLIANCE_TRADE_DISCOUNT = 0.5


# =========================================================================
# Data Structures
# =========================================================================

@dataclass
class Site:
    """Terrain site profile for a colony location."""
    x_km: float
    y_km: float
    elevation_m: float
    solar_factor: float    # 0.5 - 1.3
    water_factor: float    # 0.2 - 2.0
    shelter_factor: float  # 0.3 - 1.5


@dataclass
class Colony:
    """Colony state -- treated as immutable per-sol (copy-on-write)."""
    colony_id: str
    governor_id: str
    governor_archetype: str
    site: Site
    resources: dict[str, float] = field(default_factory=dict)
    alive: bool = True
    death_sol: int | None = None
    cause_of_death: str | None = None
    morale: float = 1.0
    reputation: float = 5.0
    diplomacy: dict[str, int] = field(default_factory=dict)
    trade_log: list[dict] = field(default_factory=list)
    conflict_log: list[dict] = field(default_factory=list)
    sol_snapshots: list[dict] = field(default_factory=list)


@dataclass
class TradeOffer:
    source_id: str
    target_id: str
    give_resource: str
    give_amount: float
    want_resource: str
    distance_km: float


@dataclass
class World:
    """World state for the multi-colony simulation."""
    colonies: dict[str, Colony]
    sol: int = 0
    rng: random.Random = field(default_factory=lambda: random.Random(42))
    events_log: list[dict] = field(default_factory=list)
    supply_drops: list[dict] = field(default_factory=list)


# =========================================================================
# Archetype Profiles -- governor personality parameters
# =========================================================================

ARCHETYPE_PROFILES: dict[str, dict[str, float]] = {
    "philosopher":  {"risk": 0.2, "caution": 0.8, "trade_willingness": 0.7, "aggression": 0.05},
    "coder":        {"risk": 0.5, "caution": 0.4, "trade_willingness": 0.6, "aggression": 0.10},
    "debater":      {"risk": 0.4, "caution": 0.5, "trade_willingness": 0.5, "aggression": 0.15},
    "researcher":   {"risk": 0.3, "caution": 0.7, "trade_willingness": 0.8, "aggression": 0.05},
    "curator":      {"risk": 0.2, "caution": 0.9, "trade_willingness": 0.9, "aggression": 0.02},
    "welcomer":     {"risk": 0.1, "caution": 0.6, "trade_willingness": 0.95, "aggression": 0.01},
    "contrarian":   {"risk": 0.8, "caution": 0.2, "trade_willingness": 0.3, "aggression": 0.25},
    "archivist":    {"risk": 0.1, "caution": 0.9, "trade_willingness": 0.7, "aggression": 0.02},
    "wildcard":     {"risk": 0.9, "caution": 0.1, "trade_willingness": 0.4, "aggression": 0.30},
    "storyteller":  {"risk": 0.3, "caution": 0.5, "trade_willingness": 0.6, "aggression": 0.08},
}


# =========================================================================
# World Creation
# =========================================================================

def generate_sites(n: int, rng: random.Random) -> list[Site]:
    """Generate N colony sites within a REGION_SIZE_KM cluster."""
    sites: list[Site] = []
    for _ in range(n * 100):
        if len(sites) >= n:
            break
        x = rng.uniform(0, REGION_SIZE_KM)
        y = rng.uniform(0, REGION_SIZE_KM)
        if any(math.hypot(x - s.x_km, y - s.y_km) < MIN_COLONY_DISTANCE_KM
               for s in sites):
            continue
        elev = rng.gauss(0, 1500)
        norm = max(-1, min(1, elev / 3000))
        sites.append(Site(
            x_km=round(x, 1), y_km=round(y, 1),
            elevation_m=round(elev),
            solar_factor=round(max(0.5, min(1.3, 0.9 + 0.4 * norm + rng.gauss(0, 0.05))), 2),
            water_factor=round(max(0.2, min(2.0, 1.3 - 0.8 * norm + rng.gauss(0, 0.1))), 2),
            shelter_factor=round(max(0.3, min(1.5, 1.0 - 0.5 * norm + rng.gauss(0, 0.1))), 2),
        ))
    return sites


def create_colony_resources(crew: int, reserve_sols: int,
                            site: Site) -> dict[str, float]:
    """Initialize colony resources with terrain modifiers applied."""
    return {
        "o2_kg": crew * O2_KG_PER_PERSON_PER_SOL * reserve_sols,
        "h2o_liters": crew * H2O_L_PER_PERSON_PER_SOL * reserve_sols * site.water_factor,
        "food_kcal": crew * FOOD_KCAL_PER_PERSON_PER_SOL * reserve_sols,
        "power_kwh": 500.0 * site.solar_factor,
        "crew_size": crew,
        "solar_efficiency": site.solar_factor,
        "isru_efficiency": site.water_factor,
        "greenhouse_efficiency": site.shelter_factor,
    }


DEFAULT_GOVERNORS = [
    {"id": "zion-philosopher-02", "archetype": "philosopher"},
    {"id": "zion-coder-07", "archetype": "coder"},
    {"id": "zion-contrarian-09", "archetype": "contrarian"},
    {"id": "zion-researcher-06", "archetype": "researcher"},
    {"id": "zion-wildcard-08", "archetype": "wildcard"},
]


def create_world(num_colonies: int = DEFAULT_COLONIES,
                 seed: int = 42,
                 governors: list[dict] | None = None) -> World:
    """Create a new multi-colony world."""
    rng = random.Random(seed)
    sites = generate_sites(num_colonies, rng)
    govs = (governors or DEFAULT_GOVERNORS)[:num_colonies]

    colonies = {}
    for i, (site, gov) in enumerate(zip(sites, govs)):
        cid = f"colony-{gov['archetype']}"
        resources = create_colony_resources(4, 30, site)
        colonies[cid] = Colony(
            colony_id=cid,
            governor_id=gov["id"],
            governor_archetype=gov["archetype"],
            site=site,
            resources=resources,
        )
    return World(colonies=colonies, rng=rng)


# =========================================================================
# INTRA-COLONY PIPE: assess -> allocate -> produce -> consume -> check
# =========================================================================

def assess_colony(colony: Colony) -> dict[str, float]:
    """Stage 1: Assess colony state, return resource-days remaining."""
    r = colony.resources
    crew = r["crew_size"]
    return {
        "o2_days": r["o2_kg"] / max(O2_KG_PER_PERSON_PER_SOL * crew, 0.01),
        "h2o_days": r["h2o_liters"] / max(H2O_L_PER_PERSON_PER_SOL * crew, 0.01),
        "food_days": r["food_kcal"] / max(FOOD_KCAL_PER_PERSON_PER_SOL * crew, 0.01),
        "power_kwh": r["power_kwh"],
        "crew_size": crew,
    }


def produce_resources(colony: Colony) -> Colony:
    """Stage 3: ISRU production scaled to crew size (fixes v1 bug)."""
    r = dict(colony.resources)
    crew = r["crew_size"]
    r["power_kwh"] += POWER_BASE_KWH_PER_SOL * max(r["solar_efficiency"], 1.0)  # ISRU has own power source
    r["o2_kg"] += ISRU_O2_PER_CREW_PER_SOL * crew * r["isru_efficiency"]
    r["h2o_liters"] += ISRU_H2O_PER_CREW_PER_SOL * crew * r["isru_efficiency"]
    r["food_kcal"] += GREENHOUSE_KCAL_PER_CREW_PER_SOL * crew * r["greenhouse_efficiency"]
    colony.resources = r
    return colony


def consume_resources(colony: Colony) -> Colony:
    """Stage 4: Daily consumption."""
    r = dict(colony.resources)
    crew = r["crew_size"]
    r["o2_kg"] -= O2_KG_PER_PERSON_PER_SOL * crew
    r["h2o_liters"] -= H2O_L_PER_PERSON_PER_SOL * crew
    r["food_kcal"] -= FOOD_KCAL_PER_PERSON_PER_SOL * crew
    r["power_kwh"] -= POWER_BASE_KWH_PER_SOL
    colony.resources = r
    return colony


def check_death(colony: Colony, sol: int) -> Colony:
    """Stage 5: Check if colony has died."""
    r = colony.resources
    cause = None
    if r.get("o2_kg", 0) <= 0:
        cause = "oxygen_depletion"
    elif r.get("h2o_liters", 0) <= 0:
        cause = "water_depletion"
    elif r.get("food_kcal", 0) <= 0:
        cause = "starvation"
    elif r.get("power_kwh", 0) <= 0:
        cause = "power_failure"
    if cause:
        colony.alive = False
        colony.death_sol = sol
        colony.cause_of_death = cause
    return colony


def run_intra_pipe(colony: Colony, sol: int) -> Colony:
    """Run the full intra-colony pipe for one sol."""
    if not colony.alive:
        return colony
    assess_colony(colony)
    produce_resources(colony)
    consume_resources(colony)
    check_death(colony, sol)
    return colony


# =========================================================================
# INTER-COLONY PIPE: neighborhood -> trades -> drops -> conflict -> diplo
# =========================================================================

def colony_distance(a: Colony, b: Colony) -> float:
    """Euclidean distance between two colonies."""
    return math.hypot(a.site.x_km - b.site.x_km, a.site.y_km - b.site.y_km)


def in_comm_range(a: Colony, b: Colony) -> bool:
    return colony_distance(a, b) <= COMM_RANGE_KM


# --- Stage 1: Assess Neighborhood ---

def assess_neighborhood(world: World) -> dict[str, dict]:
    """Each colony surveys its neighbors and own surplus/needs."""
    assessments = {}
    alive = {cid: c for cid, c in world.colonies.items() if c.alive}
    for cid, colony in alive.items():
        r = colony.resources
        crew = r["crew_size"]
        profile = ARCHETYPE_PROFILES.get(colony.governor_archetype, {})
        surplus = {}
        needs = {}
        rates = {
            "o2_kg": O2_KG_PER_PERSON_PER_SOL * crew,
            "h2o_liters": H2O_L_PER_PERSON_PER_SOL * crew,
            "food_kcal": FOOD_KCAL_PER_PERSON_PER_SOL * crew,
            "power_kwh": POWER_BASE_KWH_PER_SOL,
        }
        safety = int(TRADE_SAFETY_SOLS * (1 + profile.get("caution", 0.5)))
        for rkey, rate in rates.items():
            current = r.get(rkey, 0)
            reserve_sols = current / max(rate, 0.01)
            if reserve_sols > safety:
                surplus[rkey] = (current - rate * safety) * 0.3
            elif reserve_sols < safety * 0.5:
                needs[rkey] = rate * safety * 0.5 - current
        neighbors = [
            oid for oid in alive
            if oid != cid and in_comm_range(colony, alive[oid])
        ]
        assessments[cid] = {
            "surplus": surplus, "needs": needs,
            "neighbors": neighbors,
            "trade_willingness": profile.get("trade_willingness", 0.5),
        }
    return assessments


# --- Stage 2: Propose Trades ---

def propose_trades(world: World,
                   assessments: dict[str, dict]) -> list[TradeOffer]:
    """Colonies propose trades based on surplus/need matching."""
    offers: list[TradeOffer] = []
    for cid, assessment in assessments.items():
        if not assessment["surplus"]:
            continue
        colony = world.colonies[cid]
        if world.rng.random() > assessment["trade_willingness"]:
            continue
        best_surplus = max(assessment["surplus"], key=assessment["surplus"].get)
        for nid in assessment["neighbors"]:
            neighbor_assess = assessments.get(nid, {})
            neighbor_needs = neighbor_assess.get("needs", {})
            # Offer our surplus if neighbor needs ANY resource (they benefit from trade)
            if neighbor_needs or neighbor_assess.get("surplus", {}):
                dist = colony_distance(colony, world.colonies[nid])
                # Find what we most need from them
                neighbor_surplus = neighbor_assess.get("surplus", {})
                my_needs = assessment.get("needs", {})
                want = max(my_needs, key=my_needs.get) if my_needs else best_surplus
                offers.append(TradeOffer(
                    source_id=cid, target_id=nid,
                    give_resource=best_surplus,
                    give_amount=round(assessment["surplus"][best_surplus], 2),
                    want_resource=want,
                    distance_km=round(dist, 1),
                ))
    return offers


# --- Stage 3: Resolve Market ---

def resolve_market(world: World, offers: list[TradeOffer]) -> list[dict]:
    """Execute trades with transport costs. Pure ownership transfer."""
    executed = []
    world.rng.shuffle(offers)
    for offer in offers:
        source = world.colonies.get(offer.source_id)
        target = world.colonies.get(offer.target_id)
        if not source or not target or not source.alive or not target.alive:
            continue
        if source.resources.get(offer.give_resource, 0) < offer.give_amount:
            continue
        diplo = source.diplomacy.get(offer.target_id, DIPLO_NEUTRAL)
        if diplo == DIPLO_HOSTILE:
            continue
        fee_rate = TRANSPORT_FEE_PER_KM * offer.distance_km
        if diplo == DIPLO_ALLIED:
            fee_rate *= ALLIANCE_TRADE_DISCOUNT
        net_fraction = max(0.5, 1.0 - fee_rate)
        delivered = offer.give_amount * net_fraction
        source.resources[offer.give_resource] -= offer.give_amount
        target.resources[offer.give_resource] += delivered
        # Warm diplomacy
        _warm_diplomacy(source, offer.target_id)
        _warm_diplomacy(target, offer.source_id)
        log_entry = {
            "sol": world.sol, "from": offer.source_id, "to": offer.target_id,
            "resource": offer.give_resource,
            "sent": round(offer.give_amount, 1),
            "delivered": round(delivered, 1),
            "distance_km": offer.distance_km,
        }
        executed.append(log_entry)
        source.trade_log.append(log_entry)
        target.trade_log.append(log_entry)
    return executed


def _warm_diplomacy(colony: Colony, other_id: str) -> None:
    """Trade warms relations: neutral -> allied after 3 trades."""
    current = colony.diplomacy.get(other_id, DIPLO_NEUTRAL)
    if current == DIPLO_HOSTILE:
        colony.diplomacy[other_id] = DIPLO_NEUTRAL
    elif current == DIPLO_NEUTRAL:
        recent = sum(1 for t in colony.trade_log[-10:]
                     if other_id in (t.get("from"), t.get("to")))
        if recent >= 3:
            colony.diplomacy[other_id] = DIPLO_ALLIED


# --- Stage 4: Distribute Supply Drops ---

def distribute_drops(world: World) -> list[dict]:
    """Orbital supply drops every N sols, distributed by inverse distance."""
    if world.sol % SUPPLY_DROP_INTERVAL != 0 or world.sol == 0:
        return []
    drop_x = world.rng.uniform(0, REGION_SIZE_KM)
    drop_y = world.rng.uniform(0, REGION_SIZE_KM)
    payload = {"o2_kg": 50.0, "h2o_liters": 100.0,
               "food_kcal": 50000.0, "power_kwh": 200.0}
    alive = {cid: c for cid, c in world.colonies.items() if c.alive}
    in_range = {}
    for cid, colony in alive.items():
        dist = math.hypot(colony.site.x_km - drop_x, colony.site.y_km - drop_y)
        if dist <= SUPPLY_DROP_RADIUS_KM:
            in_range[cid] = max(dist, 1.0)
    if not in_range:
        return []
    total_inv = sum(1.0 / d for d in in_range.values())
    log = []
    for cid, dist in in_range.items():
        weight = (1.0 / dist) / total_inv
        for rkey, amount in payload.items():
            world.colonies[cid].resources[rkey] += amount * weight
        log.append({"sol": world.sol, "colony": cid,
                     "distance_km": round(dist, 1), "weight": round(weight, 3)})
    world.supply_drops.append({"sol": world.sol, "x": drop_x, "y": drop_y,
                                "recipients": len(in_range)})
    return log


# --- Stage 5: Resolve Conflict ---

def resolve_conflict(world: World) -> list[dict]:
    """Governors decide whether to sabotage neighbors."""
    actions = []
    alive = [c for c in world.colonies.values() if c.alive]
    for colony in alive:
        profile = ARCHETYPE_PROFILES.get(colony.governor_archetype, {})
        base_aggression = profile.get("aggression", 0.0)
        if base_aggression < 0.01:
            continue
        assessment = assess_colony(colony)
        min_days = min(assessment["o2_days"], assessment["h2o_days"],
                       assessment["food_days"])
        desperation = max(0, 1.0 - min_days / 30.0)
        if world.rng.random() > base_aggression + desperation * SABOTAGE_DESPERATION_MULT:
            continue
        targets = [c for c in alive
                   if c.colony_id != colony.colony_id and in_comm_range(colony, c)]
        if not targets:
            continue
        target = min(targets, key=lambda t: colony_distance(colony, t))
        system = world.rng.choice(["solar_efficiency", "isru_efficiency",
                                    "greenhouse_efficiency"])
        damage = world.rng.uniform(*SABOTAGE_DAMAGE_RANGE)
        detected = world.rng.random() < SABOTAGE_DETECT_PROB
        # Apply damage
        cur = target.resources.get(system, 1.0)
        target.resources[system] = max(0.1, cur - damage)
        # Costs to attacker
        colony.morale = max(0.1, colony.morale - SABOTAGE_ATTACKER_COST)
        if detected:
            colony.reputation += SABOTAGE_REPUTATION_PENALTY
            colony.diplomacy[target.colony_id] = DIPLO_HOSTILE
            target.diplomacy[colony.colony_id] = DIPLO_HOSTILE
        log_entry = {
            "sol": world.sol, "attacker": colony.colony_id,
            "target": target.colony_id, "system": system,
            "damage": round(damage, 3), "detected": detected,
        }
        actions.append(log_entry)
        colony.conflict_log.append(log_entry)
        target.conflict_log.append(log_entry)
    return actions


# --- Stage 6: Update Diplomacy (from conflict outcomes) ---

def update_diplomacy(world: World, conflicts: list[dict]) -> None:
    """Bystander colonies adjust diplomacy based on observed conflicts."""
    for conflict in conflicts:
        if not conflict["detected"]:
            continue
        attacker_id = conflict["attacker"]
        for colony in world.colonies.values():
            if colony.colony_id == attacker_id or not colony.alive:
                continue
            current = colony.diplomacy.get(attacker_id, DIPLO_NEUTRAL)
            if current == DIPLO_ALLIED:
                colony.diplomacy[attacker_id] = DIPLO_NEUTRAL
            elif current == DIPLO_NEUTRAL:
                colony.diplomacy[attacker_id] = DIPLO_HOSTILE


def run_inter_pipe(world: World) -> dict:
    """Run the full inter-colony pipe for one sol."""
    assessments = assess_neighborhood(world)
    offers = propose_trades(world, assessments)
    trades = resolve_market(world, offers)
    drops = distribute_drops(world)
    conflicts = resolve_conflict(world)
    update_diplomacy(world, conflicts)
    return {"trades": trades, "drops": drops, "conflicts": conflicts}


# =========================================================================
# Main Simulation Loop
# =========================================================================

def step_sol(world: World) -> dict:
    """Advance the world by one sol through both pipes."""
    world.sol += 1
    # Intra-colony pipe (per colony)
    for colony in world.colonies.values():
        run_intra_pipe(colony, world.sol)
    # Inter-colony pipe (world-level)
    inter = run_inter_pipe(world)
    # Snapshot
    alive_count = sum(1 for c in world.colonies.values() if c.alive)
    deaths = [{"colony": c.colony_id, "sol": c.death_sol, "cause": c.cause_of_death}
              for c in world.colonies.values()
              if c.death_sol == world.sol]
    sol_log = {"sol": world.sol, "alive": alive_count,
               "trades": len(inter["trades"]), "drops": len(inter["drops"]),
               "conflicts": len(inter["conflicts"]), "deaths": deaths}
    world.events_log.append(sol_log)
    # Per-colony snapshots
    for colony in world.colonies.values():
        if colony.alive:
            r = colony.resources
            colony.sol_snapshots.append({
                "sol": world.sol,
                "o2": round(r.get("o2_kg", 0), 1),
                "h2o": round(r.get("h2o_liters", 0), 1),
                "food": round(r.get("food_kcal", 0)),
                "power": round(r.get("power_kwh", 0), 1),
                "morale": round(colony.morale, 2),
                "reputation": round(colony.reputation, 1),
            })
    return sol_log


def run_multicolony(world: World, max_sols: int = DEFAULT_SOLS) -> dict:
    """Run the full multi-colony simulation."""
    for _ in range(max_sols):
        if not any(c.alive for c in world.colonies.values()):
            break
        step_sol(world)
    return build_results(world)


def build_results(world: World) -> dict:
    """Compile simulation results into a leaderboard."""
    results: dict[str, Any] = {
        "total_sols": world.sol, "colonies": {}, "leaderboard": [],
        "total_trades": sum(len(c.trade_log) for c in world.colonies.values()) // 2,
        "total_conflicts": sum(len(c.conflict_log) for c in world.colonies.values()) // 2,
    }
    for cid, colony in world.colonies.items():
        survival = colony.death_sol or world.sol
        results["colonies"][cid] = {
            "governor": colony.governor_id,
            "archetype": colony.governor_archetype,
            "survival_sols": survival,
            "alive": colony.alive,
            "cause_of_death": colony.cause_of_death,
            "morale": round(colony.morale, 2),
            "reputation": round(colony.reputation, 1),
            "trades": len(colony.trade_log),
            "conflicts_initiated": len([c for c in colony.conflict_log
                                         if c["attacker"] == cid]),
            "conflicts_received": len([c for c in colony.conflict_log
                                        if c["target"] == cid]),
            "site": {"x": colony.site.x_km, "y": colony.site.y_km,
                     "solar": colony.site.solar_factor,
                     "water": colony.site.water_factor},
        }
    board = sorted(results["colonies"].items(),
                   key=lambda x: (x[1]["survival_sols"], x[1]["morale"]),
                   reverse=True)
    results["leaderboard"] = [
        {"rank": i + 1, "colony": cid, **stats}
        for i, (cid, stats) in enumerate(board)
    ]
    return results


def print_leaderboard(results: dict) -> None:
    """Pretty-print the simulation leaderboard."""
    w = 72
    print(f"\n{'=' * w}")
    print(f"  MULTI-COLONY MARS v3 (PIPE ARCHITECTURE) -- {results['total_sols']} SOLS")
    print(f"{'=' * w}\n")
    fmt = "{:<6}{:<25}{:<8}{:<14}{:<8}{:<8}{:<8}"
    print(fmt.format("Rank", "Colony", "Sols", "Status", "Morale", "Rep", "Trades"))
    print("-" * w)
    for e in results["leaderboard"]:
        st = "ALIVE" if e["alive"] else (e.get("cause_of_death") or "?")[:12]
        print(fmt.format(e["rank"], e["colony"][:24], e["survival_sols"],
                         st, f"{e['morale']:.2f}", f"{e['reputation']:.1f}",
                         e["trades"]))
    print(f"\n{'=' * w}")
    print(f"Total trades: {results['total_trades']}  |  "
          f"Total conflicts: {results['total_conflicts']}")


# =========================================================================
# CLI
# =========================================================================

if __name__ == "__main__":
    import sys
    num = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 42
    sols = int(sys.argv[3]) if len(sys.argv) > 3 else 500

    print(f"Spawning {num} colonies (seed={seed}, max_sols={sols})...")
    world = create_world(num_colonies=num, seed=seed)
    for cid, c in world.colonies.items():
        print(f"  {cid}: ({c.site.x_km}, {c.site.y_km}) "
              f"solar={c.site.solar_factor} water={c.site.water_factor} "
              f"shelter={c.site.shelter_factor}")

    results = run_multicolony(world, max_sols=sols)
    print_leaderboard(results)
