from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.security import require_admin

router = APIRouter(prefix="/audit-logs", tags=["audit"])


@router.get("", response_model=list[schemas.AuditLogOut])
def list_audit_logs(
    action: str | None = None,
    entity_type: str | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    _: models.Dentist = Depends(require_admin),
):
    """Admin-only. Most recent entries first, capped at 500 per request."""
    query = db.query(models.AuditLog)
    if action:
        query = query.filter(models.AuditLog.action == action)
    if entity_type:
        query = query.filter(models.AuditLog.entity_type == entity_type)
    limit = max(1, min(limit, 500))
    return (
        query.order_by(models.AuditLog.created_at.desc())
        .limit(limit)
        .all()
    )
