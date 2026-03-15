def colony_alive(state: dict) -> bool:
    """Return True if the colony is still viable.

    A colony dies when any critical resource hits zero
    or a failure cascade exhausts its death timer.
    """
    resources = state.get("resources", {})
    cascade = state.get("failure_cascade", {})

    if resources.get("o2_kg", 0) <= 0:
        return False
    if resources.get("h2o_liters", 0) <= 0:
        return False
    if resources.get("food_kcal", 0) <= 0:
        return False
    if resources.get("power_kwh", 0) <= 0 and not cascade.get("power_recovery_possible", True):
        return False
    if cascade.get("sols_since_thermal_failure", 0) >= FAILURE_THRESHOLDS["cascade_death_sols"]:
        return False

    return True
