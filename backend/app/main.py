import logging
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import inspect, text
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import get_settings
from app.database import Base, engine, SessionLocal
from app import models
from app.rate_limit import limiter
from app.routers import auth, dentists, patients, screenings, dashboard, audit, health, chatbot
from app.security import hash_password
from app.utils.names import split_name

settings = get_settings()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("toothwise")

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="AI-powered dental screening and recommendation API for "
                 "CodiSmile Dental Clinic.",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    """
    Baseline security headers. CSP is intentionally NOT set here - a
    correct Content-Security-Policy needs to enumerate every script/style/
    connect-src the frontend actually uses, and is best owned by whatever
    serves the built frontend in production (nginx/reverse proxy), not
    hardcoded into the API. Same for Strict-Transport-Security, which
    should only be sent over an actual HTTPS deployment - sending it over
    plain HTTP in local dev would be actively wrong.
    """
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
    # Every response from this API carries clinical/personal data or an
    # auth-gated result, so none of it should be written to disk cache by
    # the browser, a shared proxy, or a CDN. This is a second, independent
    # layer against the same bfcache/back-button exposure the frontend
    # guards against in App.jsx - this one closes off HTTP-level caching
    # (proxies, disk cache) rather than the in-memory page snapshot.
    response.headers["Cache-Control"] = "no-store"
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """
    Safety net for anything that escapes individual route handlers'
    try/except blocks. Never leak a traceback, SQL text, or file paths to
    the client - log the full detail server-side (where it's useful for
    debugging) and return a generic message (where it isn't a
    reconnaissance gift to an attacker).
    """
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected error occurred. Please try again."},
    )


def _ensure_new_columns():
    """
    Poor-man's migration for columns added after the first `create_all`.

    `Base.metadata.create_all` only creates tables that don't exist yet -
    it never alters an existing table, so a dev DB created before the
    first/middle/last-name split and the sex->gender rename needs these
    columns added by hand. Runs on every startup and is a no-op once the
    columns already exist, so it's safe to leave in place permanently.
    """
    inspector = inspect(engine)
    plan = {
        "dentists": [
            ("first_name", "VARCHAR(60)"),
            ("middle_name", "VARCHAR(60)"),
            ("last_name", "VARCHAR(60)"),
        ],
        "patients": [
            ("first_name", "VARCHAR(60)"),
            ("middle_name", "VARCHAR(60)"),
            ("last_name", "VARCHAR(60)"),
            ("gender", "VARCHAR(10)"),
        ],
    }
    with engine.begin() as conn:
        for table, columns in plan.items():
            if table not in inspector.get_table_names():
                continue
            existing = {c["name"] for c in inspector.get_columns(table)}
            for column_name, column_type in columns:
                if column_name in existing:
                    continue
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column_name} {column_type}"))
                logger.info("Added missing column %s.%s", table, column_name)


def _backfill_name_parts():
    """
    Best-effort split of any legacy `full_name`-only row into
    first/middle/last, so PatientOut/DentistOut (which now require
    first_name and last_name) don't break on rows created before this
    migration. full_name itself is left untouched - nothing already
    displayed anywhere changes.
    """
    with engine.begin() as conn:
        for table in ("patients", "dentists"):
            rows = conn.execute(
                text(f"SELECT id, full_name FROM {table} WHERE first_name IS NULL OR first_name = ''")
            ).fetchall()
            for row in rows:
                tokens = (row.full_name or "").split()
                if not tokens:
                    continue
                if len(tokens) == 1:
                    first, middle, last = tokens[0], None, tokens[0]
                else:
                    first, middle, last = tokens[0], (" ".join(tokens[1:-1]) or None), tokens[-1]
                conn.execute(
                    text(f"UPDATE {table} SET first_name = :f, middle_name = :m, last_name = :l WHERE id = :id"),
                    {"f": first, "m": middle, "l": last, "id": row.id},
                )
            if rows:
                logger.info("Backfilled name parts for %s legacy %s row(s).", len(rows), table)


@app.on_event("startup")
def on_startup():
    Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)

    # Functional Suitability: schema is created automatically so `docker
    # compose up` gives a working system with zero manual DB steps.
    Base.metadata.create_all(bind=engine)
    _ensure_new_columns()
    _backfill_name_parts()
    logger.info("Database tables ensured.")

    db = SessionLocal()
    try:
        seed_values = (
            settings.SEED_ADMIN_EMAIL.strip(),
            settings.SEED_ADMIN_PASSWORD,
            settings.SEED_ADMIN_NAME.strip(),
            settings.SEED_ADMIN_LICENSE.strip(),
        )
        if db.query(models.Dentist).count() == 0 and all(seed_values):
            seed_first, seed_middle, seed_last = split_name(settings.SEED_ADMIN_NAME.strip())
            admin = models.Dentist(
                full_name=settings.SEED_ADMIN_NAME.strip(),
                first_name=seed_first,
                middle_name=seed_middle,
                last_name=seed_last,
                email=settings.SEED_ADMIN_EMAIL.strip().lower(),
                hashed_password=hash_password(settings.SEED_ADMIN_PASSWORD),
                role=models.DentistRole.admin,
                license_no=settings.SEED_ADMIN_LICENSE.strip(),
            )
            db.add(admin)
            db.commit()
            logger.info("Seeded admin account from environment configuration.")
        elif db.query(models.Dentist).count() == 0:
            logger.warning("No staff account exists. Set SEED_ADMIN_* values or create an account with the seed script.")
    finally:
        db.close()

    # Warm up the detector + recommender once at boot rather than on the
    # first request, so the first screening a dentist runs isn't slow.
    from app.ml.yolo_detector import get_detector
    from app.ml.recommender import _ensure_trained

    detector = get_detector()
    logger.info(
        "Detector ready (yolov8_mock=%s, yolov12_mock=%s).",
        detector.v8_mock, detector.v12_mock,
    )
    # Log each real model's own embedded class names (not our canonical
    # list) so a training-time label mismatch shows up immediately in the
    # startup log instead of silently producing unmapped detection labels
    # later. See app/ml/labels.py::normalize_label / LABEL_ALIASES.
    if not detector.v8_mock:
        logger.info("YOLOv8 model classes: %s", list(detector.model_v8.names.values()))
    if not detector.v12_mock:
        logger.info("YOLOv12 model classes: %s", list(detector.model_v12.names.values()))
    _ensure_trained()
    logger.info("KNN recommender ready.")


app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(dentists.router, prefix=settings.API_V1_PREFIX)
app.include_router(patients.router, prefix=settings.API_V1_PREFIX)
app.include_router(screenings.router, prefix=settings.API_V1_PREFIX)
app.include_router(dashboard.router, prefix=settings.API_V1_PREFIX)
app.include_router(audit.router, prefix=settings.API_V1_PREFIX)
app.include_router(health.router, prefix=settings.API_V1_PREFIX)
app.include_router(chatbot.router, prefix=settings.API_V1_PREFIX)
