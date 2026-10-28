from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database import get_db
from app.models import User
from app.services.risk_service import (
    list_suspicious_transactions,
    review_suspicious_transaction,
)


router = APIRouter(
    prefix="/api/admin/suspicious-transactions",
    tags=["Suspicious Transactions"],
)

STAFF_ROLES = {"Super Admin", "Admin", "Support Agent"}


class RiskReviewRequest(BaseModel):
    decision: Literal[
        "NORMAL",
        "REVIEW_REQUIRED",
        "BLOCKED",
    ]
    notes: str | None = Field(default=None, max_length=500)


def require_risk_staff(current_user: User):
    if current_user.role.name not in STAFF_ROLES:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to review suspicious transactions",
        )


@router.get("")
def get_suspicious_transactions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_risk_staff(current_user)
    return list_suspicious_transactions(db)


@router.patch("/{suspicious_id}/review")
def review_suspicious(
    suspicious_id: int,
    payload: RiskReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return review_suspicious_transaction(
        db=db,
        suspicious_id=suspicious_id,
        reviewer=current_user,
        decision=payload.decision,
        notes=payload.notes,
    )