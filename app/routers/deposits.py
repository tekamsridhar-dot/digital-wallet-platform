from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from fastapi import Request

from app.database import get_db
from app.core.security import get_current_user
from app.models import User
from app.schemas.deposit import DepositCreate, DepositResponse
from app.services.deposit_service import (create_deposit,list_deposits,get_deposit)

router = APIRouter(tags=["Deposits"])

@router.post("/api/wallets/{wallet_id}/deposits",
             response_model=DepositResponse,
             status_code=status.HTTP_201_CREATED,)
def create_deposit_endpoint(
    wallet_id: int,
    payload: DepositCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)):
    return create_deposit(db, wallet_id, payload.amount, current_user)


@router.get("/api/deposits", response_model=list[DepositResponse])
def list_deposits_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)):
    return list_deposits(db, current_user)

@router.get("/api/deposits/{deposit_id}",
            response_model=DepositResponse,)
def deposit_endpoint(
    payload: DepositCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ip_address = (
        request.client.host
        if request.client is not None
        else None
    )

    return create_deposit(
        db=db,
        wallet_id=payload.wallet_id,
        amount=payload.amount,
        user=current_user,
        ip_address=ip_address,
    )