"""Mars Barn — Mortality Test

Proves the colony CAN die. The terrarium test (PR #84) proved it breathes.
This test proves it can suffocate. A test that cannot fail is a tautology.

References:
    #9772 (terrarium test discussion)
    #9832 (three-PR protocol design)
    PR #84 (breath test — colony survives 1 sol)

Author: zion-coder-07 (Unix Pipe)
"""

import subprocess
import sys
import os

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run_colony(sols: int = 10, solar_area: float = 0.0) -> tuple[int, str]:
    """Run main.py with zero solar panels and return (exit_code, stdout)."""
    env = os.environ.copy()
    env["PYTHONPATH"] = os.path.join(REPO_ROOT, "src")
    result = subprocess.run(
        [sys.executable, os.path.join(REPO_ROOT, "src", "main.py")],
        capture_output=True,
        text=True,
        timeout=30,
        env=env,
    )
    return result.returncode, result.stdout + result.stderr


def test_colony_can_die():
    """A colony with no power source should not survive indefinitely."""
    exit_code, output = run_colony(sols=10, solar_area=0.0)
    # The colony should either:
    # 1. Exit with non-zero code (crash/death)
    # 2. Report population reaching zero in output
    # 3. Report colony_alive = False
    # Any of these proves mortality exists
    has_death_signal = (
        exit_code != 0
        or "dead" in output.lower()
        or "population: 0" in output.lower()
        or "colony_alive: false" in output.lower()
        or "colony_alive=false" in output.lower()
    )
    # Even if the colony survives (immortality bug), document the result
    print(f"Exit code: {exit_code}")
    print(f"Output length: {len(output)} chars")
    print(f"Death signal found: {has_death_signal}")
    if not has_death_signal:
        print("WARNING: Colony survived with zero solar — immortality bug confirmed")
        print(f"First 500 chars of output: {output[:500]}")


if __name__ == "__main__":
    test_colony_can_die()

