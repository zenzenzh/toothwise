"""
Trains the K-Nearest-Neighbors model that powers the recommendation
engine's severity-tier classification.

Cold-start problem: on day one there is no clinician-labeled outcome data
to train on. We bootstrap the KNN with a large synthetic dataset generated
from the same clinical severity weights used by the deterministic risk
engine (app/ml/risk_engine.py). This gives the KNN a sensible starting
decision boundary that already reflects dental domain knowledge, while
keeping the door open to add real labeled cases later: every
clinician-confirmed tier is appended to a JSONL journal
(append_labeled_case / load_labeled_cases) and folded into the model by
retrain_with_labeled(), which always keeps the synthetic base so KNN never
sees fewer rows than n_neighbors.

Feature vector per sample (order matters, see FEATURE_LABELS):
  [count*meanConfidence for each non-healthy label]  -> 7 features
  + total_detection_count                             -> 1 feature
  + patient_age / 100 (normalized)                     -> 1 feature
Target: severity tier -> 0 = LOW, 1 = MEDIUM, 2 = HIGH
"""
from __future__ import annotations

import json
import random
from pathlib import Path

import joblib
import numpy as np
from sklearn.neighbors import KNeighborsClassifier

from app.config import get_settings
from app.ml.labels import LABELS, SEVERITY_WEIGHT

settings = get_settings()

FEATURE_LABELS = [l for l in LABELS if l != "healthy_tooth"] + [
    "total_detections", "patient_age_norm",
]


def _tier_from_score(score: int) -> int:
    if score >= 70:
        return 2  # HIGH
    if score >= 35:
        return 1  # MEDIUM
    return 0  # LOW


def _synthesize_dataset(n_samples: int = 4000, seed: int = 42):
    rng = random.Random(seed)
    non_healthy = [l for l in LABELS if l != "healthy_tooth"]

    X, y = [], []
    for _ in range(n_samples):
        n_findings = rng.choices([0, 1, 2, 3, 4, 5], weights=[15, 25, 25, 18, 10, 7])[0]
        findings = [rng.choice(non_healthy) for _ in range(n_findings)]
        age = rng.randint(5, 85)

        feature_row = []
        weighted_scores = []
        for label in non_healthy:
            count = findings.count(label)
            mean_conf = rng.uniform(0.4, 0.95) if count else 0.0
            feature_row.append(count * mean_conf)
            if count:
                weighted_scores.append(SEVERITY_WEIGHT[label] * mean_conf)

        feature_row.append(len(findings))
        feature_row.append(age / 100.0)

        base = max(weighted_scores) if weighted_scores else 0
        bonus = min(max(len(findings) - 1, 0), 5) * 6
        score = min(base + bonus, 100)

        X.append(feature_row)
        y.append(_tier_from_score(score))

    return np.array(X), np.array(y)


def train_and_save(path: str | None = None) -> str:
    X, y = _synthesize_dataset()
    model = KNeighborsClassifier(n_neighbors=settings.KNN_NEIGHBORS, weights="distance")
    model.fit(X, y)

    out_path = Path(path or settings.KNN_MODEL_PATH)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "feature_labels": FEATURE_LABELS}, out_path)
    return str(out_path)


def append_labeled_case(features: list[float], tier: int,
                        path: str | None = None) -> str:
    """Append one clinician-confirmed case to the labeled-data journal."""
    out_path = Path(path or settings.KNN_LABELED_CASES_PATH)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"features": features, "tier": tier}) + "\n")
    return str(out_path)


def load_labeled_cases(path: str | None = None) -> tuple[np.ndarray, np.ndarray]:
    """Read every clinician-confirmed case written by append_labeled_case."""
    in_path = Path(path or settings.KNN_LABELED_CASES_PATH)
    X, y = [], []
    if in_path.exists():
        for line in in_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            X.append(row["features"])
            y.append(row["tier"])
    if not X:
        return np.empty((0, len(FEATURE_LABELS))), np.empty((0,), dtype=int)
    return np.array(X, dtype=float), np.array(y, dtype=int)


def retrain_with_labeled(path: str | None = None) -> str:
    """
    Retrain on the bootstrap synthetic data PLUS every clinician-confirmed
    case. Real rows alone crash KNN at predict time once fewer than
    n_neighbors exist, so synthetic data is always kept as the base.
    """
    X, y = _synthesize_dataset()
    X_real, y_real = load_labeled_cases()
    if len(X_real):
        X = np.vstack([X, X_real])
        y = np.concatenate([y, y_real])

    model = KNeighborsClassifier(n_neighbors=settings.KNN_NEIGHBORS, weights="distance")
    model.fit(X, y)

    out_path = Path(path or settings.KNN_MODEL_PATH)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "feature_labels": FEATURE_LABELS}, out_path)
    return str(out_path)


if __name__ == "__main__":
    saved_to = train_and_save()
    print(f"KNN recommender trained on synthetic bootstrap data -> {saved_to}")
