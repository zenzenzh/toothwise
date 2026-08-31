"""Tests for auth endpoints — login, register, token scoping."""
import pytest


class TestLogin:
    def test_login_success(self, client, seed_admin):
        resp = client.post("/api/auth/login", json={
            "email": "admin@codismile.com",
            "password": seed_admin,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["dentist"]["email"] == "admin@codismile.com"

    def test_login_wrong_password(self, client, seed_admin):
        resp = client.post("/api/auth/login", json={
            "email": "admin@codismile.com",
            "password": "wrongpassword",
        })
        assert resp.status_code == 401

    def test_login_nonexistent_email(self, client, seed_admin):
        resp = client.post("/api/auth/login", json={
            "email": "nobody@example.com",
            "password": "anything",
        })
        assert resp.status_code == 401

    def test_me_endpoint(self, client, admin_headers):
        resp = client.get("/api/auth/me", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["email"] == "admin@codismile.com"

    def test_me_without_token(self, client):
        resp = client.get("/api/auth/me")
        assert resp.status_code in (401, 403)


class TestPatientRegistration:
    def test_register_success(self, client):
        resp = client.post("/api/auth/patient/register", json={
            "first_name": "Test",
            "last_name": "Patient",
            "email": "patient@test.com",
            "password": "Secure123!",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert "access_token" in data
        assert data["patient"]["email"] == "patient@test.com"

    def test_register_duplicate_email(self, client):
        payload = {
            "first_name": "Test",
            "last_name": "Patient",
            "email": "dup@test.com",
            "password": "Secure123!",
        }
        client.post("/api/auth/patient/register", json=payload)
        resp = client.post("/api/auth/patient/register", json=payload)
        assert resp.status_code == 400

    def test_patient_login(self, client):
        client.post("/api/auth/patient/register", json={
            "first_name": "Login",
            "last_name": "Test",
            "email": "logintest@test.com",
            "password": "MyPass123!",
        })
        resp = client.post("/api/auth/patient/login", json={
            "email": "logintest@test.com",
            "password": "MyPass123!",
        })
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_patient_login_wrong_password(self, client):
        client.post("/api/auth/patient/register", json={
            "first_name": "P",
            "last_name": "Patient",
            "email": "pw@test.com",
            "password": "MyPass123!",
        })
        resp = client.post("/api/auth/patient/login", json={
            "email": "pw@test.com",
            "password": "wrong",
        })
        assert resp.status_code == 401


class TestTokenScoping:
    """A staff (dentist) token must not work on patient endpoints and
    vice versa — this is enforced by scope in the JWT."""

    def test_dentist_token_cannot_access_patient_me(self, client, admin_headers):
        resp = client.get("/api/auth/patient/me", headers=admin_headers)
        assert resp.status_code in (401, 403)

    def test_patient_token_cannot_access_dentist_me(self, client):
        client.post("/api/auth/patient/register", json={
            "first_name": "PT",
            "last_name": "User",
            "email": "scope@test.com",
            "password": "Pass1234!",
        })
        login = client.post("/api/auth/patient/login", json={
            "email": "scope@test.com",
            "password": "Pass1234!",
        })
        patient_token = login.json()["access_token"]
        resp = client.get("/api/auth/me", headers={
            "Authorization": f"Bearer {patient_token}"
        })
        assert resp.status_code in (401, 403)

