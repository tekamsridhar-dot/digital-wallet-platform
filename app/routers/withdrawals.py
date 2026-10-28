from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.security import get_current_user
from app.models import User
from app.schemas.withdrawal import (WithdrawalCreate,WithdrawalResponse,)
from app.services.withdrawal_service import ( create_withdrawal, list_withdrawals, get_withdrawal)

router = APIRouter(tags=["Withdrawals"])

@router.post( "/api/wallets/{wallet_id}/withdrawals", 
             response_model=WithdrawalResponse,
               status_code=status.HTTP_201_CREATED)
def create_withdrawal_endpoint(
    wallet_id: int,
    payload: WithdrawalCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),):
    return create_withdrawal( db, wallet_id, payload.amount, current_user)

@router.get( "/api/withdrawals", response_model=list[WithdrawalResponse],)
def list_withdrawals_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),):
    return list_withdrawals(db, current_user)

@router.get( "/api/withdrawals/{withdrawal_id}", response_model=WithdrawalResponse,)
def get_withdrawal_endpoint(
    withdrawal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),):
    return get_withdrawal(db, withdrawal_id, current_user)
