"""Tests for dentist CRUD — critically, privilege escalation guards."""
import pytest


class TestDentistCRUD:
    def test_list_dentists(self, client, admin_headers, seed_dentist):
        resp = client.get("/api/dentists", headers=admin_headers)
        assert resp.status_code == 200
        emails = [d["email"] for d in resp.json()]
        assert "admin@codismile.com" in emails
        assert "dentist@test.com" in emails

    def test_get_dentist(self, client, admin_headers, seed_dentist):
        resp = client.get(f"/api/dentists/{seed_dentist['id']}", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["email"] == "dentist@test.com"

    def test_create_dentist(self, client, admin_headers):
        resp = client.post("/api/dentists", json={
            "first_name": "New",
            "last_name": "Doctor",
            "email": "new@codismile.com",
            "password": "NewPass123!",
            "role": "dentist",
        }, headers=admin_headers)
        assert resp.status_code == 201
        assert resp.json()["email"] == "new@codismile.com"

    def test_create_dentist_duplicate_email(self, client, admin_headers, seed_dentist):
        resp = client.post("/api/dentists", json={
            "first_name": "Dup",
            "last_name": "Dentist",
            "email": "dentist@test.com",
            "password": "Pass123!",
        }, headers=admin_headers)
        assert resp.status_code == 409

    def test_delete_dentist(self, client, admin_headers, seed_dentist):
        resp = client.delete(f"/api/dentists/{seed_dentist['id']}", headers=admin_headers)
        assert resp.status_code == 204

    def test_dentist_cannot_delete_self(self, client, admin_headers):
        # Get the admin's own ID
        me = client.get("/api/auth/me", headers=admin_headers).json()
        resp = client.delete(f"/api/dentists/{me['id']}", headers=admin_headers)
        assert resp.status_code == 400


class TestPrivilegeEscalation:
    """Verify that a non-admin dentist cannot self-promote to admin."""

    def test_dentist_cannot_change_own_role(self, client, dentist_headers, seed_dentist):
        resp = client.put(
            f"/api/dentists/{seed_dentist['id']}",
            json={"role": "admin"},
            headers=dentist_headers,
        )
        assert resp.status_code == 403

    def test_dentist_cannot_change_own_email(self, client, dentist_headers, seed_dentist):
        resp = client.put(
            f"/api/dentists/{seed_dentist['id']}",
            json={"email": "hacked@evil.com"},
            headers=dentist_headers,
        )
        assert resp.status_code == 403

    def test_dentist_cannot_deactivate_themselves(self, client, dentist_headers, seed_dentist):
        resp = client.put(
            f"/api/dentists/{seed_dentist['id']}",
            json={"is_active": False},
            headers=dentist_headers,
        )
        assert resp.status_code == 403

    def test_dentist_can_update_own_name(self, client, dentist_headers, seed_dentist):
        resp = client.put(
            f"/api/dentists/{seed_dentist['id']}",
            json={"first_name": "Updated", "last_name": "Name"},
            headers=dentist_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["first_name"] == "Updated"
        assert resp.json()["last_name"] == "Name"


    def test_dentist_can_update_own_license(self, client, dentist_headers, seed_dentist):
        resp = client.put(
            f"/api/dentists/{seed_dentist['id']}",
            json={"license_no": "NEW-LICENSE-001"},
            headers=dentist_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["license_no"] == "NEW-LICENSE-001"

    def test_admin_can_change_dentist_role(self, client, admin_headers, seed_dentist):
        resp = client.put(
            f"/api/dentists/{seed_dentist['id']}",
            json={"role": "admin"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["role"] == "admin"


class TestPasswordReset:
    def test_admin_can_reset_password(self, client, admin_headers, seed_dentist):
        resp = client.put(
            f"/api/dentists/{seed_dentist['id']}/password",
            json={"new_password": "ResetPass123!"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        # Verify new password works
        login = client.post("/api/auth/login", json={
            "email": seed_dentist["email"],
            "password": "ResetPass123!",
        })
        assert login.status_code == 200

    def test_dentist_cannot_reset_own_password_via_reset_endpoint(self, client, dentist_headers, seed_dentist):
        resp = client.put(
            f"/api/dentists/{seed_dentist['id']}/password",
            json={"new_password": "HackedPass!"},
            headers=dentist_headers,
        )
        assert resp.status_code == 403  # require_admin blocks it
