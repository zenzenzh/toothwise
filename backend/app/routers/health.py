from fastapi import APIRouter
from sqlalchemy import text

from app.config import get_settings
from app.database import engine
from app import schemas

router = APIRouter(tags=["health"])


@router.get("/health", response_model=schemas.HealthOut)
def health_check():
    """
    No auth required - intended for uptime monitors / load balancers /
    Windows Task Scheduler pre-flight checks, not for clinical data.
    Never raises; always returns 200 with a status field, since a 500 here
    would itself trip most external monitors' "service down" alerting
    even when the real problem is just the DB being briefly unreachable.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return schemas.HealthOut(
            status="ok", database="connected",
            detection_enabled=get_settings().DETECTION_ENABLED,
        )
    except Exception:
        return schemas.HealthOut(
            status="degraded", database="unreachable",
            detection_enabled=get_settings().DETECTION_ENABLED,
        )
