"""
Recommendation engine: given a fused detection set, decides a severity
tier via the trained KNN model, then composes a prevention plan by
layering:
  1. An urgent banner if the tier is HIGH.
  2. Label-specific clinical advice for each distinct concerning finding
     (most severe first), pulled from app.ml.labels.RECOMMENDATIONS.
  3. General oral-hygiene advice.

This hybrid "ML picks the tier, templates compose the language" design
keeps the output clinically readable (a dentist can trust every sentence)
while still satisfying the requirement that the recommendation system be
KNN-driven rather than purely if/else.
"""
from __future__ import annotations

from pathlib import Path
from threading import Lock

import joblib
import numpy as np

from app.config import get_settings
from app.ml.labels import (
    LABELS, SEVERITY_WEIGHT, RECOMMENDATIONS, GENERAL_RECOMMENDATIONS,
)
from app.ml.train_knn import FEATURE_LABELS, train_and_save

settings = get_settings()

_lock = Lock()
_bundle = None  # {"model": KNeighborsClassifier, "feature_labels": [...]}

TIER_NAMES = {0: "LOW", 1: "MEDIUM", 2: "HIGH"}


def _ensure_trained() -> dict:
    global _bundle
    with _lock:
        if _bundle is not None:
            return _bundle
        path = Path(settings.KNN_MODEL_PATH)
        if path.exists():
            try:
                loaded = joblib.load(path)
                expected_features = len(FEATURE_LABELS)
                model = loaded.get("model") if isinstance(loaded, dict) else None
                if model is not None and getattr(model, "n_features_in_", None) == expected_features:
                    _bundle = loaded
                    return _bundle
            except Exception:
                pass
        train_and_save(str(path))
        _bundle = joblib.load(path)
        return _bundle



def build_feature_vector(detections: list[dict], patient_age: int | None) -> list[float]:
    non_healthy_labels = [l for l in LABELS if l != "healthy_tooth"]
    counts = {l: [] for l in non_healthy_labels}
    for d in detections:
        if d["label"] in counts:
            counts[d["label"]].append(d["confidence"])

    row = []
    for label in non_healthy_labels:
        confs = counts[label]
        row.append(len(confs) * (sum(confs) / len(confs)) if confs else 0.0)

    total = sum(len(v) for v in counts.values())
    row.append(total)
    row.append((patient_age or 30) / 100.0)
    return row


def predict_tier(detections: list[dict], patient_age: int | None) -> str:
    non_healthy = [d for d in detections if d["label"] != "healthy_tooth"]
    if not non_healthy:
        return "LOW"

    bundle = _ensure_trained()
    features = np.array([build_feature_vector(detections, patient_age)])
    tier_id = int(bundle["model"].predict(features)[0])
    return TIER_NAMES[tier_id]


def generate_prevention_plan(detections: list[dict], patient_age: int | None) -> list[dict]:
    """Returns an ordered list of {text, priority} dicts for the UI."""
    tier = predict_tier(detections, patient_age)

    distinct_labels = sorted(
        {d["label"] for d in detections if d["label"] != "healthy_tooth"},
        key=lambda l: SEVERITY_WEIGHT.get(l, 0),
        reverse=True,
    )

    plan: list[dict] = []
    order = 0

    if tier == "HIGH":
        plan.append({
            "text": "URGENT: Please visit CodiSmile Dental Clinic immediately "
                    "for professional evaluation.",
            "priority": 1,
            "order_index": order,
        })
        order += 1

    for label in distinct_labels:
        text = RECOMMENDATIONS.get(label)
        if not text:
            continue
        plan.append({
            "text": text,
            "priority": 1 if SEVERITY_WEIGHT.get(label, 0) >= 70 else 0,
            "order_index": order,
        })
        order += 1

    if not distinct_labels:
        plan.append({
            "text": RECOMMENDATIONS["healthy_tooth"],
            "priority": 0,
            "order_index": order,
        })
        order += 1

    for text in GENERAL_RECOMMENDATIONS:
        plan.append({"text": text, "priority": 0, "order_index": order})
        order += 1

    return plan
