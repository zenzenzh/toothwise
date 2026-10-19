"""
Recommendation engine: given a fused detection set, decides a severity
tier via the trained KNN model, then composes a prevention plan by
layering (all text lives in app.ml.labels):
  1. An urgent banner if the tier is HIGH.
  2. Label-specific clinical advice for each distinct concerning finding
     (most severe first) - RECOMMENDATIONS.
  3. Tier follow-up: when to return, or what to do until the visit -
     TIER_FOLLOW_UP.
  4. Home-care steps per finding - LABEL_HOME_CARE.
  5. Age-specific advice for children and older adults - AGE_ADVICE.
  6. General oral-hygiene advice not already covered.

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
    TIER_FOLLOW_UP, LABEL_HOME_CARE, age_advice,
)
from app.ml.train_knn import (
    FEATURE_LABELS, train_and_save, retrain_with_labeled,
)

settings = get_settings()

_lock = Lock()
_bundle = None  # {"model": KNeighborsClassifier, "feature_labels": [...]}

TIER_NAMES = {0: "LOW", 1: "MEDIUM", 2: "HIGH"}


def _retrain_if_journal_newer(path: Path) -> bool:
    """If clinician-confirmed cases were written after the artifact was
    trained, fold them in. The journal is the source of truth, so a boot
    after any lost retrain converges by comparing mtimes. Cheap (one stat
    each) and runs only once per process under _lock."""
    global _bundle
    journal = Path(settings.KNN_LABELED_CASES_PATH)
    if not journal.exists():
        return False
    if path.exists() and path.stat().st_mtime >= journal.stat().st_mtime:
        return False
    retrain_with_labeled(str(path))
    _bundle = joblib.load(path)
    return True


def _ensure_trained() -> dict:
    global _bundle
    with _lock:
        if _bundle is not None:
            return _bundle
        path = Path(settings.KNN_MODEL_PATH)
        if _retrain_if_journal_newer(path):
            return _bundle
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


def retrain_from_labeled() -> dict:
    """Fold every clinician-confirmed tier into the model and swap the cache."""
    global _bundle
    with _lock:
        path = Path(settings.KNN_MODEL_PATH)
        retrain_with_labeled(str(path))
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
    """Returns an ordered list of {text, priority, order_index} dicts.

    Sections, in order (the KNN tier drives the banner and the follow-up):
      1. Urgent banner (HIGH tier only).
      2. Clinical advice per finding, most severe first.
      3. Tier follow-up: when to come back, or what to do until the visit.
      4. Home-care steps per finding, most severe first.
      5. Age-specific advice (children, older adults).
      6. General hygiene advice not already covered above.
    """
    tier = predict_tier(detections, patient_age)

    distinct_labels = sorted(
        {d["label"] for d in detections if d["label"] != "healthy_tooth"},
        key=lambda l: SEVERITY_WEIGHT.get(l, 0),
        reverse=True,
    )

    plan: list[dict] = []
    seen: set[str] = set()

    def add(text: str | None, priority: int = 0) -> None:
        if not text or text in seen:
            return
        seen.add(text)
        plan.append({"text": text, "priority": priority, "order_index": len(plan)})

    if tier == "HIGH":
        add("URGENT: Please visit CodiSmile Dental Clinic immediately "
            "for professional evaluation.", priority=1)

    for label in distinct_labels:
        add(RECOMMENDATIONS.get(label),
            priority=1 if SEVERITY_WEIGHT.get(label, 0) >= 70 else 0)

    if not distinct_labels:
        add(RECOMMENDATIONS["healthy_tooth"])

    add(TIER_FOLLOW_UP.get(tier), priority=1 if tier == "HIGH" else 0)

    for label in distinct_labels:
        for tip in LABEL_HOME_CARE.get(label, []):
            add(tip)

    for tip in age_advice(patient_age):
        add(tip)

    for text in GENERAL_RECOMMENDATIONS:
        # The plaque home-care steps already cover daily flossing.
        if "plaque" in distinct_labels and text.startswith("Floss"):
            continue
        add(text)

    return plan
