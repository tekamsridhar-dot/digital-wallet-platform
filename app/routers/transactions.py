from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database import get_db
from app.models import User
from app.schemas.transaction import (TransactionResponse,TransactionSummaryResponse,)
from app.services.transaction_history_service import (list_transactions,get_transaction_by_id,get_transaction_summary,)


router = APIRouter(
    prefix="/api/transactions",
    tags=["Transaction History"],
)


@router.get("/summary", response_model=TransactionSummaryResponse)
def transaction_summary(
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_transaction_summary(
        db=db,
        current_user=current_user,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("", response_model=list[TransactionResponse])
def transaction_history(
    start_date: date | None = None,
    end_date: date | None = None,
    transaction_type: str | None = Query(default=None, min_length=1),
    status: str | None = Query(default=None, min_length=1),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_transactions(
        db=db,
        current_user=current_user,
        start_date=start_date,
        end_date=end_date,
        transaction_type=transaction_type,
        status=status,
        skip=skip,
        limit=limit,
    )


@router.get("/{transaction_id}", response_model=TransactionResponse)
def transaction_details(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_transaction_by_id(
        db=db,
        current_user=current_user,
        transaction_id=transaction_id,
    )