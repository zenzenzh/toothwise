"""
Shared test fixtures for the Toothwise backend.

The key trick: DATABASE_URL and USE_MOCK_MODEL are set BEFORE the app
modules are imported, so the ``lru_cache``-d ``get_settings()`` picks up
the test values.  This means the app's own ``engine`` and
``Base.metadata.create_all()`` target a throwaway SQLite database instead
of requiring a running PostgreSQL instance.

Usage::

    pytest                   # run all tests
    pytest tests/test_auth.py -v
"""
from __future__ import annotations

import os
import sys
import shutil

# ---- Must run BEFORE any ``app.*`` import so get_settings() caches test values ----
os.environ.setdefault("DATABASE_URL", "sqlite:///test.db")
os.environ.setdefault("USE_MOCK_MODEL", "true")
os.environ.setdefault("UPLOAD_DIR", "test_uploads")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("SEED_ADMIN_EMAIL", "admin@codismile.com")
os.environ.setdefault("SEED_ADMIN_PASSWORD", "CodiSmile@2025")
os.environ.setdefault("SEED_ADMIN_NAME", "Test Admin")
os.environ.setdefault("SEED_ADMIN_LICENSE", "TEST-001")
os.environ.setdefault("KNN_MODEL_PATH", "test_artifacts/knn_recommender.joblib")
os.environ.setdefault("KNN_LABELED_CASES_PATH", "test_artifacts/labeled_cases.jsonl")
# ---- end env setup ----

import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine, SessionLocal, get_db
from app import models
from app.security import hash_password
from app.rate_limit import limiter
from app.main import app

# Disable slowapi rate limiting during automated test runs
limiter.enabled = False


@pytest.fixture(autouse=True)
def _setup_and_teardown_db():
    """Create all tables before each test, drop them after."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    # Clean up test uploads and test-trained KNN artifacts
    for dirname in ("test_uploads", "test_artifacts"):
        path = os.path.join(os.getcwd(), dirname)
        if os.path.isdir(path):
            shutil.rmtree(path, ignore_errors=True)
    from app.ml import recommender
    recommender._bundle = None


@pytest.fixture()
def db():
    """Yield a fresh SQLAlchemy session for direct ORM testing."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client():
    """FastAPI TestClient wired to the test SQLite database."""
    def _override_get_db():
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def seed_admin(client):
    """Ensure the full-access dentist/administrator exists and return the
    plain-text password so callers can log in.  The app's startup event
    already seeds this account, so we only insert if it's missing.

    Under the three-role model `dentist` IS the administrator role."""
    password = "CodiSmile@2025"
    session = SessionLocal()
    try:
        existing = session.query(models.Dentist).filter(
            models.Dentist.email == "admin@codismile.com"
        ).first()
        if not existing:
            admin = models.Dentist(
                full_name="Test Admin",
                first_name="Test",
                last_name="Admin",
                email="admin@codismile.com",
                hashed_password=hash_password(password),
                role=models.DentistRole.dentist,
                license_no="TEST-001",
            )
            session.add(admin)
            session.commit()
    finally:
        session.close()
    return password


@pytest.fixture()
def admin_token(client, seed_admin):
    """Log in as the seeded dentist/administrator and return the JWT."""
    resp = client.post("/api/auth/login", json={
        "email": "admin@codismile.com",
        "password": seed_admin,
    })
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()["access_token"]


@pytest.fixture()
def admin_headers(admin_token):
    """Authorization headers dict for the dentist/administrator account."""
    return {"Authorization": f"Bearer {admin_token}"}


def _seed_staff(role, email, password):
    """Insert one limited staff account and return its login details."""
    session = SessionLocal()
    try:
        staff = models.Dentist(
            full_name=f"Test {role.value.title()}",
            first_name="Test",
            last_name=role.value.title(),
            email=email,
            hashed_password=hash_password(password),
            role=role,
        )
        session.add(staff)
        session.commit()
        session.refresh(staff)
        staff_id = staff.id
    finally:
        session.close()
    return {"email": email, "password": password, "id": staff_id}


def _login(client, account):
    resp = client.post("/api/auth/login", json={
        "email": account["email"],
        "password": account["password"],
    })
    assert resp.status_code == 200, f"Staff login failed: {resp.text}"
    return resp.json()["access_token"]


@pytest.fixture()
def seed_receptionist(client, seed_admin):
    """A front-desk receptionist (limited staff role)."""
    return _seed_staff(models.DentistRole.receptionist, "receptionist@test.com", "Reception123!")


@pytest.fixture()
def receptionist_token(client, seed_receptionist):
    return _login(client, seed_receptionist)


@pytest.fixture()
def receptionist_headers(receptionist_token):
    return {"Authorization": f"Bearer {receptionist_token}"}


@pytest.fixture()
def seed_assistant(client, seed_admin):
    """A dental assistant (clinical staff role)."""
    return _seed_staff(models.DentistRole.assistant, "assistant@test.com", "Assistant123!")


@pytest.fixture()
def assistant_token(client, seed_assistant):
    return _login(client, seed_assistant)


@pytest.fixture()
def assistant_headers(assistant_token):
    return {"Authorization": f"Bearer {assistant_token}"}


@pytest.fixture()
def seed_patient(client, admin_headers):
    """Create a test patient via the API and return the response dict."""
    resp = client.post("/api/patients", json={
        "first_name": "Juan",
        "middle_name": "Dela",
        "last_name": "Cruz",
        "birthdate": "1990-05-15",
        "gender": "Male",
        "contact_number": "09171234567",
        "address": "Manila, Philippines",
    }, headers=admin_headers)
    assert resp.status_code == 201, f"Patient creation failed: {resp.text}"
    return resp.json()


@pytest.fixture()
def seed_screening(client, admin_headers, seed_patient):
    """Create a screening for the seeded patient using the mock model."""
    import io
    from PIL import Image
    buf = io.BytesIO()
    img = Image.new("RGB", (64, 64), color=(0, 128, 255))
    img.save(buf, format="PNG")
    png_bytes = buf.getvalue()

    resp = client.post(
        f"/api/patients/{seed_patient['id']}/screening",
        files={"file": ("test.png", io.BytesIO(png_bytes), "image/png")},
        headers=admin_headers,
    )
    assert resp.status_code == 201, f"Screening creation failed: {resp.text}"
    return resp.json()

