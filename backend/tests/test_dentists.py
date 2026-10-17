"""Tests for staff CRUD — critically, privilege-escalation guards.

Under the three-role model the ``dentist`` role IS the administrator; the
limited staff roles are ``receptionist`` and ``assistant``.  The escalation
tests therefore act as a receptionist (a non-administrator) to prove that a
limited account cannot grant itself administrator access or manage staff.
"""
import pytest


class TestStaffCRUD:
    def test_list_staff(self, client, admin_headers, seed_receptionist):
        resp = client.get("/api/dentists", headers=admin_headers)
        assert resp.status_code == 200
        emails = [d["email"] for d in resp.json()]
        assert "admin@codismile.com" in emails
        assert "receptionist@test.com" in emails

    def test_get_staff(self, client, admin_headers, seed_receptionist):
        resp = client.get(f"/api/dentists/{seed_receptionist['id']}", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["email"] == "receptionist@test.com"

    def test_create_receptionist(self, client, admin_headers):
        resp = client.post("/api/dentists", json={
            "first_name": "New",
            "last_name": "Reception",
            "email": "new@codismile.com",
            "password": "NewPass123!",
            "role": "receptionist",
        }, headers=admin_headers)
        assert resp.status_code == 201
        assert resp.json()["email"] == "new@codismile.com"
        assert resp.json()["role"] == "receptionist"

    def test_create_staff_duplicate_email(self, client, admin_headers, seed_receptionist):
        resp = client.post("/api/dentists", json={
            "first_name": "Dup",
            "last_name": "Reception",
            "email": "receptionist@test.com",
            "password": "Pass123!",
        }, headers=admin_headers)
        assert resp.status_code == 409

    def test_delete_staff(self, client, admin_headers, seed_receptionist):
        resp = client.delete(f"/api/dentists/{seed_receptionist['id']}", headers=admin_headers)
        assert resp.status_code == 204

    def test_admin_cannot_delete_self(self, client, admin_headers):
        # Get the administrator's own ID
        me = client.get("/api/auth/me", headers=admin_headers).json()
        resp = client.delete(f"/api/dentists/{me['id']}", headers=admin_headers)
        assert resp.status_code == 400


class TestPrivilegeEscalation:
    """A receptionist (non-administrator) must not be able to grant itself
    administrator access or change protected fields."""

    def test_receptionist_cannot_change_own_role(self, client, receptionist_headers, seed_receptionist):
        resp = client.put(
            f"/api/dentists/{seed_receptionist['id']}",
            json={"role": "dentist"},
            headers=receptionist_headers,
        )
        assert resp.status_code == 403

    def test_receptionist_cannot_change_own_email(self, client, receptionist_headers, seed_receptionist):
        resp = client.put(
            f"/api/dentists/{seed_receptionist['id']}",
            json={"email": "hacked@evil.com"},
            headers=receptionist_headers,
        )
        assert resp.status_code == 403

    def test_receptionist_cannot_deactivate_themselves(self, client, receptionist_headers, seed_receptionist):
        resp = client.put(
            f"/api/dentists/{seed_receptionist['id']}",
            json={"is_active": False},
            headers=receptionist_headers,
        )
        assert resp.status_code == 403

    def test_receptionist_can_update_own_name(self, client, receptionist_headers, seed_receptionist):
        resp = client.put(
            f"/api/dentists/{seed_receptionist['id']}",
            json={"first_name": "Updated", "last_name": "Name"},
            headers=receptionist_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["first_name"] == "Updated"
        assert resp.json()["last_name"] == "Name"

    def test_receptionist_cannot_list_staff(self, client, receptionist_headers):
        # Staff management is dentist/administrator-only.
        resp = client.get("/api/dentists", headers=receptionist_headers)
        assert resp.status_code == 403

    def test_admin_can_change_staff_role(self, client, admin_headers, seed_receptionist):
        resp = client.put(
            f"/api/dentists/{seed_receptionist['id']}",
            json={"role": "assistant"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["role"] == "assistant"


class TestPasswordReset:
    def test_admin_can_reset_password(self, client, admin_headers, seed_receptionist):
        resp = client.put(
            f"/api/dentists/{seed_receptionist['id']}/password",
            json={"new_password": "ResetPass123!"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        # Verify new password works
        login = client.post("/api/auth/login", json={
            "email": seed_receptionist["email"],
            "password": "ResetPass123!",
        })
        assert login.status_code == 200

    def test_limited_staff_cannot_reset_password(self, client, receptionist_headers, seed_receptionist):
        resp = client.put(
            f"/api/dentists/{seed_receptionist['id']}/password",
            json={"new_password": "HackedPass!"},
            headers=receptionist_headers,
        )
        assert resp.status_code == 403  # dentist/administrator-only
