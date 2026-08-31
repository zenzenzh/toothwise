"""Tests for patient CRUD endpoints."""


class TestPatientCRUD:
    def test_create_patient(self, client, admin_headers):
        resp = client.post("/api/patients", json={
            "first_name": "Maria",
            "last_name": "Clara",
            "birthdate": "1995-03-20",
            "gender": "Female",
            "contact_number": "09181234567",
            "address": "Ermita, Manila",
        }, headers=admin_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["full_name"] == "Maria Clara"
        assert data["gender"] == "Female"

    def test_create_patient_with_null_optionals(self, client, admin_headers):
        """Empty optional fields sent as null should be accepted."""
        resp = client.post("/api/patients", json={
            "first_name": "Minimal",
            "last_name": "Patient",
            "birthdate": None,
            "gender": None,
            "contact_number": None,
            "address": None,
        }, headers=admin_headers)
        assert resp.status_code == 201

    def test_list_patients(self, client, admin_headers, seed_patient):
        resp = client.get("/api/patients", headers=admin_headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_search_patients(self, client, admin_headers, seed_patient):
        resp = client.get("/api/patients?search=Juan", headers=admin_headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_get_patient(self, client, admin_headers, seed_patient):
        resp = client.get(f"/api/patients/{seed_patient['id']}", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["full_name"] == "Juan Dela Cruz"

    def test_update_patient(self, client, admin_headers, seed_patient):
        resp = client.put(
            f"/api/patients/{seed_patient['id']}",
            json={"first_name": "Juan Pedro", "middle_name": None, "last_name": "Cruz"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["full_name"] == "Juan Pedro Cruz"



    def test_delete_patient(self, client, admin_headers, seed_patient):
        resp = client.delete(f"/api/patients/{seed_patient['id']}", headers=admin_headers)
        assert resp.status_code == 204

    def test_get_nonexistent_patient(self, client, admin_headers):
        resp = client.get("/api/patients/99999", headers=admin_headers)
        assert resp.status_code == 404


class TestPatientScreenings:
    def test_list_patient_screenings(self, client, admin_headers, seed_screening, seed_patient):
        resp = client.get(
            f"/api/patients/{seed_patient['id']}/screenings",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_risk_trend(self, client, admin_headers, seed_screening, seed_patient):
        resp = client.get(
            f"/api/patients/{seed_patient['id']}/risk-trend",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
