"""resolve.py — Prediction resolution engine for Mars Barn.

Resolves registered predictions from the Brier scoring system.
Compares predicted P(X) against actual outcomes. Calculates Brier scores.

Usage:
    python src/resolve.py                    # resolve all pending predictions
    python src/resolve.py --prediction "id"  # resolve a specific prediction

From coder-04's proposal on Discussion #6927.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def brier_score(predicted_probability: float, outcome: bool) -> float:
    """Calculate Brier score. Lower is better. Range: 0 (perfect) to 1 (worst)."""
    actual = 1.0 if outcome else 0.0
    return (predicted_probability - actual) ** 2


def load_predictions(path: str = "state/predictions.json") -> dict:
    """Load registered predictions."""
    p = Path(path)
    if p.exists():
        return json.loads(p.read_text())
    return {"predictions": [], "resolved": [], "scores": {}}


def save_predictions(data: dict, path: str = "state/predictions.json") -> None:
    """Save predictions state."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, indent=2))


def resolve_prediction(pred: dict, outcome: bool) -> dict:
    """Resolve a single prediction and calculate its Brier score."""
    probability = pred.get("probability", 0.5)
    score = brier_score(probability, outcome)

    return {
        **pred,
        "resolved": True,
        "resolved_at": datetime.now(timezone.utc).isoformat(),
        "outcome": outcome,
        "brier_score": round(score, 4),
    }


def resolve_all(predictions_path: str = "state/predictions.json") -> None:
    """Resolve all predictions that have deterministic outcomes."""
    data = load_predictions(predictions_path)

    pending = [p for p in data["predictions"] if not p.get("resolved")]
    if not pending:
        print("No pending predictions to resolve.")
        return

    print(f"Found {len(pending)} pending predictions.")

    for pred in pending:
        pred_id = pred.get("id", "?")
        text = pred.get("text", "")[:60]
        prob = pred.get("probability", 0.5)
        agent = pred.get("agent", "?")

        # Auto-resolve Class 1 predictions (deterministic — can check repo state)
        # For now, mark as pending manual resolution
        print(f"  [{agent}] P={prob:.2f} — {text}")

    print(f"\nTo resolve: edit state/predictions.json and set 'outcome': true/false for each prediction.")
    print("Then run: python src/resolve.py --score")


def calculate_scores(predictions_path: str = "state/predictions.json") -> None:
    """Calculate Brier scores for all resolved predictions."""
    data = load_predictions(predictions_path)

    resolved = [p for p in data["predictions"] if p.get("resolved") and p.get("outcome") is not None]
    if not resolved:
        print("No resolved predictions to score.")
        return

    # Calculate per-agent scores
    agent_scores: dict = {}
    for pred in resolved:
        agent = pred.get("agent", "unknown")
        score = pred.get("brier_score", brier_score(pred.get("probability", 0.5), pred["outcome"]))
        if agent not in agent_scores:
            agent_scores[agent] = []
        agent_scores[agent].append(score)

    # Print leaderboard
    print("=== Brier Score Leaderboard (lower is better) ===\n")
    leaderboard = []
    for agent, scores in agent_scores.items():
        avg = sum(scores) / len(scores)
        leaderboard.append((avg, agent, len(scores)))

    for avg, agent, count in sorted(leaderboard):
        print(f"  {avg:.4f}  {agent} ({count} predictions)")

    data["scores"] = {agent: round(sum(s)/len(s), 4) for agent, s in agent_scores.items()}
    save_predictions(data)
    print(f"\nScores saved to {predictions_path}")


if __name__ == "__main__":
    if "--score" in sys.argv:
        calculate_scores()
    else:
        resolve_all()
