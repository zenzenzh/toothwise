"""Tests for remember-me tokens, email-free forgot password and change password."""
from datetime import datetime, timezone

from jose import jwt

from app.config import get_settings

settings = get_settings()


def _token_lifetime_hours(token):
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    return (exp - datetime.now(timezone.utc)).total_seconds() / 3600


def _register_patient(client, email="pp@test.com", password="Secure123!"):
    resp = client.post("/api/auth/patient/register", json={
        "first_name": "Pat", "last_name": "Ient", "email": email, "password": password,
    })
    assert resp.status_code == 201
    return resp.json()["access_token"]


class TestRememberMe:
    def test_staff_remember_me_gives_long_token(self, client, seed_admin):
        short = client.post("/api/auth/login", json={"email": "admin@codismile.com", "password": seed_admin})
        long = client.post("/api/auth/login", json={
            "email": "admin@codismile.com", "password": seed_admin, "remember_me": True,
        })
        assert _token_lifetime_hours(short.json()["access_token"]) <= 12.1
        assert _token_lifetime_hours(long.json()["access_token"]) > 24 * 29

    def test_patient_remember_me_gives_long_token(self, client):
        _register_patient(client)
        resp = client.post("/api/auth/patient/login", json={
            "email": "pp@test.com", "password": "Secure123!", "remember_me": True,
        })
        assert resp.status_code == 200
        assert _token_lifetime_hours(resp.json()["access_token"]) > 24 * 29


BAD_DETAILS = "The details you entered do not match our records."


def _register_full_patient(client):
    resp = client.post("/api/auth/patient/register", json={
        "first_name": "Ana", "last_name": "Cruz", "email": "ana@test.com", "password": "OldPass123!",
        "contact_number": "09171234567", "birthdate": "1995-04-12",
    })
    assert resp.status_code == 201


class TestForgotPassword:
    def test_patient_reset_with_matching_details(self, client):
        _register_full_patient(client)
        resp = client.post("/api/auth/patient/forgot-password", json={
            "email": "ANA@test.com", "birthdate": "1995-04-12",
            "contact_number": "+63 917 123 4567", "new_password": "NewPass123!",
        })
        assert resp.status_code == 200
        assert client.post("/api/auth/patient/login", json={"email": "ana@test.com", "password": "NewPass123!"}).status_code == 200
        assert client.post("/api/auth/patient/login", json={"email": "ana@test.com", "password": "OldPass123!"}).status_code == 401

    def test_patient_wrong_birthdate_rejected(self, client):
        _register_full_patient(client)
        resp = client.post("/api/auth/patient/forgot-password", json={
            "email": "ana@test.com", "birthdate": "1995-04-13",
            "contact_number": "09171234567", "new_password": "NewPass123!",
        })
        assert resp.status_code == 400
        assert resp.json()["detail"] == BAD_DETAILS

    def test_patient_wrong_phone_rejected(self, client):
        _register_full_patient(client)
        resp = client.post("/api/auth/patient/forgot-password", json={
            "email": "ana@test.com", "birthdate": "1995-04-12",
            "contact_number": "09179999999", "new_password": "NewPass123!",
        })
        assert resp.status_code == 400

    def test_patient_without_details_on_file_rejected(self, client):
        _register_patient(client)  # no birthdate or phone on this account
        resp = client.post("/api/auth/patient/forgot-password", json={
            "email": "pp@test.com", "birthdate": "1995-04-12",
            "contact_number": "09171234567", "new_password": "NewPass123!",
        })
        assert resp.status_code == 400

    def test_unknown_email_gets_same_message(self, client, seed_admin):
        resp = client.post("/api/auth/patient/forgot-password", json={
            "email": "nobody@test.com", "birthdate": "1995-04-12",
            "contact_number": "09171234567", "new_password": "NewPass123!",
        })
        assert resp.status_code == 400
        assert resp.json()["detail"] == BAD_DETAILS

    def test_weak_new_password_rejected(self, client):
        _register_full_patient(client)
        resp = client.post("/api/auth/patient/forgot-password", json={
            "email": "ana@test.com", "birthdate": "1995-04-12",
            "contact_number": "09171234567", "new_password": "short",
        })
        assert resp.status_code == 422

    def test_staff_reset_with_license(self, client, seed_admin):
        resp = client.post("/api/auth/forgot-password", json={
            "email": "admin@codismile.com", "license_no": " test-001 ", "new_password": "NewPass123!",
        })
        assert resp.status_code == 200
        assert client.post("/api/auth/login", json={"email": "admin@codismile.com", "password": seed_admin}).status_code == 401
        assert client.post("/api/auth/login", json={"email": "admin@codismile.com", "password": "NewPass123!"}).status_code == 200

    def test_staff_wrong_license_rejected(self, client, seed_admin):
        resp = client.post("/api/auth/forgot-password", json={
            "email": "admin@codismile.com", "license_no": "WRONG", "new_password": "NewPass123!",
        })
        assert resp.status_code == 400
        assert resp.json()["detail"] == BAD_DETAILS
        assert client.post("/api/auth/login", json={"email": "admin@codismile.com", "password": seed_admin}).status_code == 200


class TestChangePassword:
    def test_staff_change_password(self, client, admin_headers, seed_admin):
        resp = client.post("/api/auth/change-password", headers=admin_headers, json={
            "current_password": seed_admin, "new_password": "Changed123!",
        })
        assert resp.status_code == 200
        assert client.post("/api/auth/login", json={"email": "admin@codismile.com", "password": "Changed123!"}).status_code == 200

    def test_staff_wrong_current_password(self, client, admin_headers):
        resp = client.post("/api/auth/change-password", headers=admin_headers, json={
            "current_password": "wrong", "new_password": "Changed123!",
        })
        assert resp.status_code == 400

    def test_same_password_rejected(self, client, admin_headers, seed_admin):
        resp = client.post("/api/auth/change-password", headers=admin_headers, json={
            "current_password": seed_admin, "new_password": seed_admin,
        })
        assert resp.status_code == 400

    def test_patient_change_password(self, client):
        token = _register_patient(client)
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.post("/api/auth/patient/change-password", headers=headers, json={
            "current_password": "Secure123!", "new_password": "Changed123!",
        })
        assert resp.status_code == 200
        assert client.post("/api/auth/patient/login", json={"email": "pp@test.com", "password": "Changed123!"}).status_code == 200

    def test_change_password_requires_login(self, client):
        resp = client.post("/api/auth/change-password", json={
            "current_password": "x", "new_password": "Changed123!",
        })
        assert resp.status_code == 401
