"""
Single source of truth for the detection class list.

Reduced to the 5 most common findings from an initial 8-label set (dropped:
tooth_discoloration, cracked_tooth, missing_tooth) per consultation
feedback - cavity, gum inflammation, plaque, and tartar cover the great
majority of real screening findings, with healthy_tooth as the baseline
"no issue" class.

IMPORTANT: this list must match the class order the YOLO weights were
actually trained on. Editing LABELS here does NOT retroactively relabel an
already-trained checkpoint - if YOLOV8_WEIGHTS_PATH / YOLOV12_WEIGHTS_PATH
still point at weights trained on the old 8-class set, class indices will
no longer line up and detections will be mislabeled. To apply this label
set for real:
  1. Re-export/relabel the training dataset down to these 5 classes.
  2. Retrain YOLOv8 and YOLOv12 and point the weights paths at the new
     checkpoints.
  3. Delete app/ml/artifacts/knn_recommender.joblib so it retrains against
     the new label set on next boot (see train_knn.py).
No other application code needs to change - everything downstream reads
from here.
"""

LABELS: list[str] = [
    "healthy_tooth",
    "cavity",
    "gum_inflammation",
    "plaque",
    "tartar",
]

LABEL_TO_ID = {label: idx for idx, label in enumerate(LABELS)}
ID_TO_LABEL = {idx: label for idx, label in enumerate(LABELS)}

# Relative clinical severity per detected label, used by the risk engine.
# 0 = no risk contribution, 100 = maximum single-detection severity.
SEVERITY_WEIGHT: dict[str, int] = {
    "healthy_tooth": 0,
    "plaque": 25,
    "tartar": 35,
    "gum_inflammation": 45,
    "cavity": 70,
}

# Display color per label for the frontend bounding-box overlay (hex).
LABEL_COLOR: dict[str, str] = {
    "healthy_tooth": "#639922",
    "plaque": "#EF9F27",
    "tartar": "#BA7517",
    "gum_inflammation": "#D4537E",
    "cavity": "#E24B4A",
}

# Base clinical advice per label. The KNN recommender picks a severity
# tier (see recommender.py) and layers these onto the tier's general advice.
RECOMMENDATIONS: dict[str, str] = {
    "cavity": "Visit CodiSmile Dental Clinic for cavity treatment as soon "
              "as possible.",
    "gum_inflammation": "Gum inflammation detected - a professional cleaning "
                         "and gum assessment is recommended.",
    "plaque": "Improve plaque control with thorough brushing and daily "
              "flossing; a professional cleaning is advised.",
    "tartar": "Tartar buildup detected - schedule a professional scaling "
              "and polishing session.",
    "healthy_tooth": "No issues detected on this tooth - keep up your "
                      "current oral hygiene routine.",
}

# Public dental datasets and different annotation tools rarely use our
# exact label spelling. Rather than force every dataset to be relabeled,
# raw class names coming out of a trained checkpoint are normalized
# through this map before anything else in the app sees them. Extend this
# whenever you plug in a new dataset with different naming.
LABEL_ALIASES: dict[str, str] = {
    "healthy": "healthy_tooth",
    "health": "healthy_tooth",
    "normal": "healthy_tooth",
    "normal tooth": "healthy_tooth",
    "caries": "cavity",
    "decay": "cavity",
    "tooth-decay": "cavity",
    "tooth decay": "cavity",
    "decayed tooth": "cavity",
    "decaycavity": "cavity",
    "cavities": "cavity",
    "gingivitis": "gum_inflammation",
    "gingiva": "gum_inflammation",
    "gum disease": "gum_inflammation",
    "calculus": "tartar",
    "tartar buildup": "tartar",
}


def normalize_label(raw_label: str) -> str:
    """Maps a raw class name from any trained checkpoint onto our canonical
    label set. Falls back to the lowercased raw name if there's no known
    mapping, so unexpected classes are still visible (and easy to spot)
    rather than silently dropped."""
    key = raw_label.strip().lower().replace(" ", "_")
    if key in LABELS:
        return key
    alias_key = raw_label.strip().lower()
    return LABEL_ALIASES.get(alias_key, key)


GENERAL_RECOMMENDATIONS = [
    "Brush your teeth at least twice a day using fluoride toothpaste.",
    "Avoid sugary foods and drinks, especially between meals.",
    "Floss daily to remove plaque between teeth.",
    "Visit your dentist for a routine checkup every 6 months.",
]
