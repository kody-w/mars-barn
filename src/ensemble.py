"""Mars Barn — Ensemble Runner

Run the simulation with multiple random seeds and report statistics.
Answers: "What percentage of parameter sets survive N sols?"

Author: zion-researcher-05 (Methodology Maven)
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import run_simulation


def run_ensemble(
    num_runs: int = 50,
    num_sols: int = 100,
    latitude: float = -4.5,
) -> dict:
    """Run simulation with different seeds and aggregate results."""
    results = []
    
    for i in range(num_runs):
        result = run_simulation(
            num_sols=num_sols, latitude=latitude,
            seed=i, verbose=False,
        )
        results.append(result["summary"])
        
        if (i + 1) % 10 == 0:
            print(f"  Completed {i + 1}/{num_runs} runs...")
    
    # Aggregate
    temps = [r["final_temp_c"] for r in results]
    energies = [r["stored_energy_kwh"] for r in results]
    events = [r["events_survived"] for r in results]
    survived = sum(1 for r in results if r["stored_energy_kwh"] > 0)
    
    return {
        "runs": num_runs,
        "sols_per_run": num_sols,
        "survival_rate": round(survived / num_runs * 100, 1),
        "temp_min_c": round(min(temps), 1),
        "temp_max_c": round(max(temps), 1),
        "temp_mean_c": round(sum(temps) / len(temps), 1),
        "energy_min_kwh": round(min(energies), 1),
        "energy_max_kwh": round(max(energies), 1),
        "energy_mean_kwh": round(sum(energies) / len(energies), 1),
        "events_mean": round(sum(events) / len(events), 1),
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Mars Barn Ensemble Runner")
    parser.add_argument("--runs", type=int, default=20, help="Number of runs")
    parser.add_argument("--sols", type=int, default=50, help="Sols per run")
    args = parser.parse_args()
    
    print(f"Running {args.runs} simulations ({args.sols} sols each)...")
    report = run_ensemble(num_runs=args.runs, num_sols=args.sols)
    
    print(f"\n{'='*50}")
    print(f"  ENSEMBLE RESULTS ({report['runs']} runs, {report['sols_per_run']} sols)")
    print(f"  Survival rate: {report['survival_rate']}%")
    print(f"  Final temp: {report['temp_min_c']}°C to {report['temp_max_c']}°C (mean {report['temp_mean_c']}°C)")
    print(f"  Energy reserves: {report['energy_min_kwh']} to {report['energy_max_kwh']} kWh (mean {report['energy_mean_kwh']})")
    print(f"  Events per run: {report['events_mean']} (mean)")
    print(f"{'='*50}")
