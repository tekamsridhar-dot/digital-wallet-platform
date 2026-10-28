from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.security import get_current_user
from app.models import User
from app.schemas.refund import (
    RefundCreate,
    RefundResponse,
    RefundDecision,
)
from app.services.refund_service import (
    request_refund,
    list_refunds,
    get_refund,
    approve_refund,
    reject_refund,
)

router = APIRouter(prefix="/api/refunds", tags=["Refunds"])


@router.post(
    "",
    response_model=RefundResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_refund(
    payload: RefundCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return request_refund(
        db,
        payload.transaction_id,
        payload.amount,
        payload.reason,
        current_user,
    )


@router.get("", response_model=list[RefundResponse])
def get_refunds(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_refunds(db, current_user)


@router.get("/{refund_id}", response_model=RefundResponse)
def get_refund_by_id(
    refund_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_refund(db, refund_id, current_user)


@router.post("/{refund_id}/approve", response_model=RefundResponse)
def approve_refund_endpoint(
    refund_id: int,
    payload: RefundDecision,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return approve_refund(
        db,
        refund_id,
        current_user,
        payload.reason,
    )


@router.post("/{refund_id}/reject", response_model=RefundResponse)
def reject_refund_endpoint(
    refund_id: int,
    payload: RefundDecision,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return reject_refund(
        db,
        refund_id,
        current_user,
        payload.reason,
    )