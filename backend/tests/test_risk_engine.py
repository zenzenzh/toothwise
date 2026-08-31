"""Tests for app.ml.risk_engine — deterministic risk scoring."""
from app.ml.risk_engine import compute_risk


class TestComputeRisk:
    def test_empty_detections(self):
        result = compute_risk([])
        assert result.score == 0
        assert result.level == "LOW"

    def test_only_healthy(self):
        result = compute_risk([{"label": "healthy_tooth", "confidence": 0.9}])
        assert result.score == 0
        assert result.level == "LOW"

    def test_single_low_severity(self):
        # plaque severity=25, confidence=0.8 → 25*0.8 = 20
        result = compute_risk([{"label": "plaque", "confidence": 0.8}])
        assert result.score == 20
        assert result.level == "LOW"

    def test_single_medium_severity(self):
        # cavity severity=70, confidence=0.8 → 70*0.8 = 56
        result = compute_risk([{"label": "cavity", "confidence": 0.8}])
        assert result.score == 56
        assert result.level == "MEDIUM"

    def test_single_high_severity(self):
        # cavity severity=70, confidence=1.0 → 70*1.0 = 70
        result = compute_risk([{"label": "cavity", "confidence": 1.0}])
        assert result.score == 70
        assert result.level == "HIGH"

    def test_multiple_findings_compound(self):
        # Two moderate findings: tartar(35)*0.8=28, gum_inflammation(45)*0.8=36
        # Base = max(28, 36) = 36, bonus = min(2-1, 5)*6 = 6, total = 42
        detections = [
            {"label": "tartar", "confidence": 0.8},
            {"label": "gum_inflammation", "confidence": 0.8},
        ]
        result = compute_risk(detections)
        assert result.score == 42
        assert result.level == "MEDIUM"

    def test_many_findings_bonus_capped(self):
        # 7 non-healthy findings, bonus = min(7-1, 5)*6 = 30
        detections = [{"label": "plaque", "confidence": 0.5}] * 7
        result = compute_risk(detections)
        # base = 25*0.5 = 12.5, bonus = min(6,5)*6 = 30, total = 42.5
        # round() is banker's rounding → 42
        assert result.score == 42
        assert result.level == "MEDIUM"

    def test_score_never_exceeds_100(self):
        detections = [{"label": "cavity", "confidence": 1.0}] * 10
        result = compute_risk(detections)
        assert result.score <= 100


    def test_level_boundaries(self):
        # Exactly at boundary: score 70 → HIGH
        # cavity(70)*1.0 = 70
        r1 = compute_risk([{"label": "cavity", "confidence": 1.0}])
        assert r1.level == "HIGH"

        # Just below HIGH: cavity(70)*0.95 = 66.5
        r2 = compute_risk([{"label": "cavity", "confidence": 0.95}])
        assert r2.level == "MEDIUM"
