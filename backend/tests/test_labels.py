"""Tests for app.ml.labels — label normalization, severity weights, aliases."""
from app.ml.labels import (
    LABELS, LABEL_TO_ID, ID_TO_LABEL, SEVERITY_WEIGHT, LABEL_ALIASES,
    normalize_label,
)


class TestNormalizeLabel:
    def test_exact_match(self):
        assert normalize_label("cavity") == "cavity"
        assert normalize_label("healthy_tooth") == "healthy_tooth"

    def test_alias_caries(self):
        assert normalize_label("caries") == "cavity"
        assert normalize_label("tooth decay") == "cavity"

    def test_alias_gingivitis(self):
        assert normalize_label("gingivitis") == "gum_inflammation"

    def test_alias_calculus(self):
        assert normalize_label("calculus") == "tartar"

    def test_alias_tartar_buildup(self):
        assert normalize_label("tartar buildup") == "tartar"

    def test_unknown_label_passthrough(self):
        # Unknown labels get lowercased + underscored but not dropped
        result = normalize_label("Some Weird Label")
        assert result == "some_weird_label"

    def test_whitespace_handling(self):
        assert normalize_label("  cavity  ") == "cavity"


class TestLabelConstants:
    def test_all_labels_have_severity(self):
        for label in LABELS:
            assert label in SEVERITY_WEIGHT, f"Missing severity for {label}"

    def test_healthy_tooth_zero_severity(self):
        assert SEVERITY_WEIGHT["healthy_tooth"] == 0

    def test_label_id_roundtrip(self):
        for label in LABELS:
            assert ID_TO_LABEL[LABEL_TO_ID[label]] == label

    def test_label_count(self):
        assert len(LABELS) == 5

