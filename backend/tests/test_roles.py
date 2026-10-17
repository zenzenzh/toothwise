"""Role-based access-control tests for the three-role staff model.

    dentist       = administrator, full access
    receptionist  = front desk (patient directory only, no clinical data)
    assistant     = clinical support (screenings, no clinical notes/tier)

The permission matrix enforced here is documented in the user manual (7.3)
and in the Chapter III/IV requirements tables.
"""
import io

import pytest
from PIL import Image


def _png():
    buf = io.BytesIO()
    Image.new("RGB", (64, 64), color=(10, 20, 30)).save(buf, format="PNG")
    return buf.getvalue()


class TestReceptionistAccess:
    """Receptionists manage patients but must be kept out of clinical data."""

    def test_can_manage_patients(self, client, receptionist_headers):
        resp = client.post("/api/patients", json={
            "first_name": "Rina", "last_name": "Reception",
        }, headers=receptionist_headers)
        assert resp.status_code == 201
        pid = resp.json()["id"]
        assert client.get("/api/patients", headers=receptionist_headers).status_code == 200
        assert client.get(f"/api/patients/{pid}", headers=receptionist_headers).status_code == 200
        assert client.put(
            f"/api/patients/{pid}", json={"address": "Manila"},
            headers=receptionist_headers,
        ).status_code == 200

    def test_cannot_delete_patient(self, client, receptionist_headers, seed_patient):
        resp = client.delete(
            f"/api/patients/{seed_patient['id']}", headers=receptionist_headers,
        )
        assert resp.status_code == 403

    def test_cannot_view_screening_history(self, client, receptionist_headers, seed_screening, seed_patient):
        resp = client.get(
            f"/api/patients/{seed_patient['id']}/screenings", headers=receptionist_headers,
        )
        assert resp.status_code == 403

    def test_cannot_create_screening(self, client, receptionist_headers, seed_patient):
        resp = client.post(
            f"/api/patients/{seed_patient['id']}/screening",
            files={"file": ("t.png", io.BytesIO(_png()), "image/png")},
            headers=receptionist_headers,
        )
        assert resp.status_code == 403

    def test_cannot_view_audit_log_or_manage_staff(self, client, receptionist_headers):
        assert client.get("/api/audit-logs", headers=receptionist_headers).status_code == 403
        assert client.get("/api/dentists", headers=receptionist_headers).status_code == 403


class TestAssistantAccess:
    """Assistants run screenings but cannot perform licensed clinical acts."""

    def test_can_create_and_view_screening(self, client, assistant_headers, seed_patient):
        resp = client.post(
            f"/api/patients/{seed_patient['id']}/screening",
            files={"file": ("t.png", io.BytesIO(_png()), "image/png")},
            headers=assistant_headers,
        )
        assert resp.status_code == 201
        sid = resp.json()["id"]
        assert client.get(f"/api/screenings/{sid}", headers=assistant_headers).status_code == 200
        assert client.get(f"/api/screenings/{sid}/image", headers=assistant_headers).status_code == 200

    def test_cannot_add_clinical_note(self, client, assistant_headers, seed_screening):
        resp = client.post(
            f"/api/screenings/{seed_screening['id']}/notes",
            json={"body": "note"}, headers=assistant_headers,
        )
        assert resp.status_code == 403

    def test_cannot_confirm_tier(self, client, assistant_headers, seed_screening):
        resp = client.patch(
            f"/api/screenings/{seed_screening['id']}/tier",
            json={"risk_level": "LOW"}, headers=assistant_headers,
        )
        assert resp.status_code == 403

    def test_cannot_delete_screening(self, client, assistant_headers, seed_screening):
        resp = client.delete(
            f"/api/screenings/{seed_screening['id']}", headers=assistant_headers,
        )
        assert resp.status_code == 403

    def test_cannot_manage_staff_or_audit(self, client, assistant_headers):
        assert client.get("/api/dentists", headers=assistant_headers).status_code == 403
        assert client.get("/api/audit-logs", headers=assistant_headers).status_code == 403


class TestDentistAccess:
    """The dentist is the administrator and keeps full access."""

    def test_dentist_has_full_access(self, client, admin_headers, seed_screening):
        assert client.get("/api/dentists", headers=admin_headers).status_code == 200
        assert client.get("/api/audit-logs", headers=admin_headers).status_code == 200
        resp = client.post(
            f"/api/screenings/{seed_screening['id']}/notes",
            json={"body": "Clinical note"}, headers=admin_headers,
        )
        assert resp.status_code == 201
        resp = client.patch(
            f"/api/screenings/{seed_screening['id']}/tier",
            json={"risk_level": "LOW"}, headers=admin_headers,
        )
        assert resp.status_code == 200
