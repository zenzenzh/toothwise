"""Tests for screening endpoints — creation with mock model, retrieval, comparison."""
import io
from PIL import Image


def _make_test_png():
    buf = io.BytesIO()
    img = Image.new("RGB", (64, 64), color=(255, 0, 0))
    img.save(buf, format="PNG")
    return buf.getvalue()


class TestScreeningCRUD:
    def test_create_screening(self, client, admin_headers, seed_patient):
        png_bytes = _make_test_png()
        resp = client.post(
            f"/api/patients/{seed_patient['id']}/screening",
            files={"file": ("test.png", io.BytesIO(png_bytes), "image/png")},
            headers=admin_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "risk_level" in data
        assert "risk_score" in data
        assert data["risk_level"] in ("LOW", "MEDIUM", "HIGH")
        assert 0 <= data["risk_score"] <= 100

    def test_get_screening(self, client, admin_headers, seed_screening):
        resp = client.get(
            f"/api/screenings/{seed_screening['id']}",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == seed_screening["id"]

    def test_screening_has_fused_detections(self, client, admin_headers, seed_screening):
        resp = client.get(
            f"/api/screenings/{seed_screening['id']}",
            headers=admin_headers,
        )
        data = resp.json()
        detections = data.get("detections", [])
        fused = [d for d in detections if d["detection_set"] == "fused"]
        assert len(fused) > 0

    def test_screening_has_recommendations(self, client, admin_headers, seed_screening):
        resp = client.get(
            f"/api/screenings/{seed_screening['id']}",
            headers=admin_headers,
        )
        recs = resp.json().get("recommendations", [])
        assert len(recs) > 0
        assert all("text" in r for r in recs)

    def test_delete_screening(self, client, admin_headers, seed_screening):
        resp = client.delete(
            f"/api/screenings/{seed_screening['id']}",
            headers=admin_headers,
        )
        assert resp.status_code == 204

    def test_model_comparison(self, client, admin_headers, seed_screening):
        resp = client.get(
            f"/api/screenings/{seed_screening['id']}/compare",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "yolov8" in data
        assert "yolov12" in data
        assert "fused_count" in data
        assert "agreement_count" in data

    def test_add_clinical_note(self, client, admin_headers, seed_screening):
        resp = client.post(
            f"/api/screenings/{seed_screening['id']}/notes",
            json={"body": "Mild gingivitis observed"},
            headers=admin_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["body"] == "Mild gingivitis observed"


class TestScreeningSecurity:
    def test_unauthenticated_screening_access(self, client):
        resp = client.get("/api/screenings/1")
        assert resp.status_code in (401, 403)

    def test_screening_for_nonexistent_patient(self, client, admin_headers):
        png_bytes = _make_test_png()
        resp = client.post(
            "/api/patients/99999/screening",
            files={"file": ("test.png", io.BytesIO(png_bytes), "image/png")},
            headers=admin_headers,
        )
        assert resp.status_code == 404

