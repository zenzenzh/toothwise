"""
Converts a list of detections into a single clinical risk score (0-100)
and a categorical risk level (LOW / MEDIUM / HIGH), matching the
"RISK LEVEL: HIGH - Score: 100/100" panel in the UI.

The scoring rule is intentionally simple and auditable (a requirement for
capstone defenses): it is the confidence-weighted maximum severity across
all detections, boosted slightly for each additional finding. Being
rule-based rather than a black box also makes it easy to unit test
(see tests/test_recommender.py) — part of the ISO 25010
"Functional Suitability - Functional Correctness" and
"Maintainability - Testability" story.
"""
from dataclasses import dataclass

from app.ml.labels import SEVERITY_WEIGHT


@dataclass
class RiskResult:
    score: int
    level: str  # "LOW" | "MEDIUM" | "HIGH"


def compute_risk(detections: list[dict]) -> RiskResult:
    """
    detections: list of {"label": str, "confidence": float, ...}
    """
    non_healthy = [d for d in detections if d["label"] != "healthy_tooth"]

    if not non_healthy:
        return RiskResult(score=0, level="LOW")

    weighted_scores = [
        SEVERITY_WEIGHT.get(d["label"], 30) * d["confidence"] for d in non_healthy
    ]
    base = max(weighted_scores)

    # Multiple concerning findings compound the risk (capped contribution).
    extra_findings_bonus = min(len(non_healthy) - 1, 5) * 6

    score = round(min(base + extra_findings_bonus, 100))

    if score >= 70:
        level = "HIGH"
    elif score >= 35:
        level = "MEDIUM"
    else:
        level = "LOW"

    return RiskResult(score=score, level=level)
