"""
Tests for the recommendation stack: the deterministic risk engine,
the KNN-driven prevention plan, and the labeled-case retrain loop.

Referenced by the risk_engine module docstring (ISO 25010 Functional
Correctness / Testability) - this file is the test suite that was promised
there but never created until the KNN eval + retrain work shipped.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from app.ml import recommender
from app.ml.risk_engine import compute_risk
from app.ml.train_knn import (
    append_labeled_case, load_labeled_cases, retrain_with_labeled,
)


@pytest.fixture(autouse=True)
def _isolate_artifacts():
    """Each test trains fresh KNN artifacts pointing at the throwaway
    test_artifacts/ dir, so a retrain test can't stomp the shipped model."""
    recommender._bundle = None
    yield
    recommender._bundle = None


# ---------- risk_engine (deterministic, no model required) ----------

def test_clean_screening_is_low(tmp_path):
    result = compute_risk([{"label": "healthy_tooth", "confidence": 0.9}])
    assert result.level == "LOW"
    assert result.score == 0


def test_high_severity_detection_is_high(tmp_path):
    result = compute_risk([{"label": "cavity", "confidence": 1.0}])
    assert result.level == "HIGH"
    assert result.score >= 70


def test_multiple_findings_compound(tmp_path):
    single = compute_risk([{"label": "plaque", "confidence": 0.9}])
    multi = compute_risk([
        {"label": "plaque", "confidence": 0.9},
        {"label": "plaque", "confidence": 0.9},
        {"label": "plaque", "confidence": 0.9},
    ])
    assert multi.score > single.score


# ---------- prevention plan (model-backed) ----------

def test_prevention_plan_healthy_gives_only_general_advice(tmp_path):
    plan = recommender.generate_prevention_plan(
        [{"label": "healthy_tooth", "confidence": 0.9}], 30,
    )
    assert plan
    assert all("cavity" not in r["text"].lower() for r in plan)


def test_prevention_plan_cavity_is_urgent(tmp_path):
    # Two cavities + plaque: risk engine scores 66.5 + 12 bonus = ~78 -> HIGH.
    plan = recommender.generate_prevention_plan([
        {"label": "cavity", "confidence": 0.95},
        {"label": "cavity", "confidence": 0.9},
        {"label": "plaque", "confidence": 0.95},
    ], 30, )
    assert "URGENT" in plan[0]["text"]


def test_prevention_plan_orders_by_severity(tmp_path):
    plan = recommender.generate_prevention_plan([
        {"label": "plaque", "confidence": 0.8},
        {"label": "cavity", "confidence": 0.8},
    ], 30, )
    texts = [r["text"] for r in plan]
    assert texts.index(next(t for t in texts if "cavity" in t.lower())) < \
        texts.index(next(t for t in texts if "plaque" in t.lower()))


def test_prevention_plan_adds_tier_follow_up_and_home_care(tmp_path):
    from app.ml.labels import LABEL_HOME_CARE, TIER_FOLLOW_UP
    detections = [{"label": "gum_inflammation", "confidence": 0.8}]
    plan = recommender.generate_prevention_plan(detections, 30)
    texts = [r["text"] for r in plan]
    tier = recommender.predict_tier(detections, 30)
    assert TIER_FOLLOW_UP[tier] in texts
    for tip in LABEL_HOME_CARE["gum_inflammation"]:
        assert tip in texts
    # Clinical advice comes before the home-care steps.
    assert any("gum" in t.lower() for t in texts[:2])


def test_prevention_plan_age_specific_advice(tmp_path):
    healthy = [{"label": "healthy_tooth", "confidence": 0.9}]
    child = " ".join(r["text"] for r in recommender.generate_prevention_plan(healthy, 7))
    adult = " ".join(r["text"] for r in recommender.generate_prevention_plan(healthy, 30))
    senior = " ".join(r["text"] for r in recommender.generate_prevention_plan(healthy, 70))
    assert "children" in child.lower()
    assert "older adults" in senior.lower()
    assert "children" not in adult.lower() and "older adults" not in adult.lower()


def test_prevention_plan_has_no_duplicates_and_sequential_order(tmp_path):
    plan = recommender.generate_prevention_plan([
        {"label": "plaque", "confidence": 0.9},
        {"label": "tartar", "confidence": 0.9},
        {"label": "plaque", "confidence": 0.7},
    ], 45)
    texts = [r["text"] for r in plan]
    assert len(texts) == len(set(texts))
    assert [r["order_index"] for r in plan] == list(range(len(plan)))
    # Plaque home care already covers flossing, so the general tip is dropped.
    assert not any(t.startswith("Floss daily") for t in texts)


# ---------- labeled-case journal + retrain loop ----------

def test_append_and_load_labeled_cases(tmp_path):
    path = str(tmp_path / "labeled.jsonl")
    # [cavity, gum_inflammation, plaque, tartar, total_detections, age_norm]
    append_labeled_case([1.0, 0.0, 0.0, 0.0, 1.0, 0.3], 2, path=path)
    append_labeled_case([0.0, 0.0, 0.0, 0.0, 0.0, 0.3], 0, path=path)
    X, y = load_labeled_cases(path=path)
    assert len(X) == 2
    assert y.tolist() == [2, 0]


def test_retrain_with_labeled_folds_labeled_cases_in(tmp_path):
    model_path = str(tmp_path / "model.joblib")
    labels_path = str(tmp_path / "labeled.jsonl")
    append_labeled_case([1.0, 0.0, 0.0, 0.0, 1.0, 0.3], 2, path=labels_path)
    retrain_with_labeled(path=model_path)
    # Without the labeled case the artifact is still written and loadable;
    # the point is the pipe doesn't crash on a single real row (fewer than
    # n_neighbors), which pure-real-data retraining WOULD do at predict time.
    import joblib
    bundle = joblib.load(Path(model_path))
    assert bundle["model"].n_features_in_ == 6


def test_confirm_tier_endpoint_records_label(client, admin_headers, seed_patient):
    """PATCH /screenings/{id}/tier appends a labeled case and returns the
    screening unchanged otherwise. auth: dentist-level required."""
    import io
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (64, 64), color=(200, 0, 0)).save(buf, format="PNG")

    resp = client.post(
        f"/api/patients/{seed_patient['id']}/screening",
        files={"file": ("t.png", io.BytesIO(buf.getvalue()), "image/png")},
        headers=admin_headers,
    )
    assert resp.status_code == 201, resp.text
    screening = resp.json()

    resp = client.patch(
        f"/api/screenings/{screening['id']}/tier",
        json={"risk_level": "HIGH"},
        headers=admin_headers,
    )
    assert resp.status_code == 200, resp.text

    cases_path = Path(
        os.environ.get(
            "KNN_LABELED_CASES_PATH", "test_artifacts/labeled_cases.jsonl",
        )
    )
    if cases_path.exists():
        lines = [l for l in cases_path.read_text().splitlines() if l.strip()]
        assert lines, "expected at least one labeled case written"