from sqlalchemy.orm import Session

from app.models import AuditLog


def record_audit_log(
    db: Session,
    action: str,
    entity_type: str,
    entity_id: int | None = None,
    user_id: int | None = None,
    ip_address: str | None = None,
    details: dict | None = None,
):
    log = AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        ip_address=ip_address,
        details=details or {},
    )

    db.add(log)
    db.flush()

    return log