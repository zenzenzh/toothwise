"""
Lightweight audit-trail helper. Call log_action() from any router after a
sensitive write succeeds (login, patient/dentist/screening CRUD, password
resets). Writes are fire-and-forget within the same DB session/transaction
the caller is already using - no extra commit, so a failed audit write
can't be the reason a legitimate action rolls back, and a successful
action always has its audit row committed together with it.
"""
from sqlalchemy.orm import Session

from app import models


def log_action(
    db: Session,
    actor: models.Dentist | None,
    action: str,
    entity_type: str | None = None,
    entity_id: int | None = None,
    details: str | None = None,
    actor_label: str | None = None,
) -> None:
    """
    actor_label covers actors that aren't a Dentist row - e.g. a patient
    acting on their own account (self-registration, self-booking) - so the
    audit trail still records who did it even though actor_dentist_id has
    nothing to point to. Ignored if actor is set.
    """
    entry = models.AuditLog(
        actor_dentist_id=actor.id if actor else None,
        actor_email=actor.email if actor else actor_label,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
    )
    db.add(entry)
    # Intentionally no db.commit() here - the caller's own commit (for the
    # patient/dentist/screening write that triggered this) persists this
    # row too, keeping the action and its audit entry atomic.
