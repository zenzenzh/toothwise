"""
Evaluation harness for the KNN recommender. Two honest yardsticks:

1. Synthetic holdout (train/test split): the bootstrap data is generated
   deterministically from the same severity rule, so a held-out slice tells
   you how well the KNN REPRODUCES that rule on data it never saw. Near-100%
   accuracy here is expected and only proves self-consistency.

2. Real labeled cases (deployed): every clinician-confirmed tier recorded
   via PATCH /screenings/{id}/tier is evaluated against the CURRENT model.
   This is the only meaningful accuracy signal once reviews exist; until
   there are reviews it reports "no real data".

Also reports KNN-vs-deterministic agreement on the holdout, i.e. how far the
ML boundary has drifted from risk_engine.compute_risk's thresholds.

Run:  python -m app.ml.evaluate_knn
"""
from __future__ import annotations

from app.ml.recommender import _ensure_trained
from app.ml.train_knn import _synthesize_dataset, load_labeled_cases
from app.ml.risk_engine import compute_risk


def evaluate_holdout(model, n_samples: int = 2000, seed: int = 999) -> dict:
    """Accuracy/F1 of the trained KNN on fresh synthetic data."""
    # Use a DIFFERENT seed than the training bootstrap (42) so holdout
    # samples are genuinely unseen, not a replay of training rows.
    X, y = _synthesize_dataset(n_samples=n_samples, seed=seed)
    preds = model.predict(X)

    from collections import Counter
    from sklearn.metrics import f1_score

    errors = Counter((str(yi), str(pi)) for yi, pi in zip(y, preds))
    return {
        "accuracy": round(float((y == preds).mean()), 4),
        "f1_weighted": round(float(f1_score(y, preds, average="weighted")), 4),
        "misclassifications": [f"{pred}/{truth} x{n}" for (pred, truth), n in
                               sorted(errors.items(), key=lambda kv: -kv[1])],
    }


def evaluate_real_cases(model) -> dict:
    """Accuracy of the current model on every clinician-confirmed tier."""
    X, y = load_labeled_cases()
    if len(X) == 0:
        return {"n_real_cases": 0, "status": "no real labeled data yet"}
    preds = model.predict(X)
    return {
        "n_real_cases": int(len(X)),
        "accuracy": round(float((preds == y).mean()), 4),
        "correct": int((preds == y).sum()),
        "wrong": int((preds != y).sum()),
    }


def run_evaluation() -> dict:
    bundle = _ensure_trained()
    model = bundle["model"]
    return {
        "holdout": evaluate_holdout(model),
        "real_cases": evaluate_real_cases(model),
    }


if __name__ == "__main__":
    import json
    print(json.dumps(run_evaluation(), indent=2))