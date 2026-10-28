from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database import get_db
from app.models import AuditLog, User
from app.schemas.audit import AuditLogResponse


router = APIRouter(
    prefix="/api/admin/audit-logs",
    tags=["Audit Logs"],
)

AUDIT_ROLES = {"Super Admin", "Admin"}

def require_audit_access(user: User):
    if user.role.name not in AUDIT_ROLES:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to view audit logs",
        )

@router.get("", response_model=list[AuditLogResponse])
def get_audit_logs(
    action: str | None = None,
    entity_type: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_audit_access(current_user)
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=422,
            detail="start_date cannot be after end_date",
        )

    query = db.query(AuditLog)

    if action:
        query = query.filter(AuditLog.action == action)

    if entity_type:
        query = query.filter(
            AuditLog.entity_type == entity_type
        )

    if start_date:
        start = datetime.combine(
            start_date,
            time.min,
            tzinfo=timezone.utc,
        )
        query = query.filter(AuditLog.created_at >= start)

    if end_date:
        end = datetime.combine(
            end_date + timedelta(days=1),
            time.min,
            tzinfo=timezone.utc,
        )
        query = query.filter(AuditLog.created_at < end)

    return (
        query
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )