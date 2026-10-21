"""Tests for remember-me tokens, forgot/reset password and change password."""
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlparse

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


def _reset_token_from(resp):
    url = resp.json()["dev_reset_url"]
    assert url, "dev reset link should be returned when SMTP is not configured"
    return parse_qs(urlparse(url).query)["token"][0]


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


class TestForgotPassword:
    def test_unknown_email_gets_same_message(self, client, seed_admin):
        known = client.post("/api/auth/forgot-password", json={"email": "admin@codismile.com"})
        unknown = client.post("/api/auth/forgot-password", json={"email": "nobody@test.com"})
        assert known.status_code == unknown.status_code == 200
        assert known.json()["message"] == unknown.json()["message"]
        assert unknown.json()["dev_reset_url"] is None

    def test_staff_reset_flow_is_single_use(self, client, seed_admin):
        token = _reset_token_from(client.post("/api/auth/forgot-password", json={"email": "admin@codismile.com"}))
        resp = client.post("/api/auth/reset-password", json={"token": token, "new_password": "NewPass123!"})
        assert resp.status_code == 200
        # Old password no longer works, new one does.
        assert client.post("/api/auth/login", json={"email": "admin@codismile.com", "password": seed_admin}).status_code == 401
        assert client.post("/api/auth/login", json={"email": "admin@codismile.com", "password": "NewPass123!"}).status_code == 200
        # The same link can't be used twice.
        again = client.post("/api/auth/reset-password", json={"token": token, "new_password": "Another123!"})
        assert again.status_code == 400

    def test_patient_reset_flow(self, client):
        _register_patient(client)
        token = _reset_token_from(client.post("/api/auth/patient/forgot-password", json={"email": "pp@test.com"}))
        resp = client.post("/api/auth/patient/reset-password", json={"token": token, "new_password": "NewPass123!"})
        assert resp.status_code == 200
        login = client.post("/api/auth/patient/login", json={"email": "pp@test.com", "password": "NewPass123!"})
        assert login.status_code == 200

    def test_staff_token_cannot_reset_patient(self, client, seed_admin):
        token = _reset_token_from(client.post("/api/auth/forgot-password", json={"email": "admin@codismile.com"}))
        resp = client.post("/api/auth/patient/reset-password", json={"token": token, "new_password": "NewPass123!"})
        assert resp.status_code == 400

    def test_reset_token_cannot_call_api(self, client, seed_admin):
        token = _reset_token_from(client.post("/api/auth/forgot-password", json={"email": "admin@codismile.com"}))
        resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401

    def test_garbage_token_rejected(self, client):
        resp = client.post("/api/auth/reset-password", json={"token": "nope", "new_password": "NewPass123!"})
        assert resp.status_code == 400


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
