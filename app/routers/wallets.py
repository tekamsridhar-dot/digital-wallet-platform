from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.database import get_db
from app.core.security import get_current_user
from app.models import User
from app.schemas.wallet import (WalletCreate,WalletResponse,
                                WalletBalanceResponse,WalletStatusUpdate,)
from app.services.wallet_service import (create_wallet,list_wallets,
                                         get_wallet,get_wallet_balance,change_wallet_status)

router = APIRouter(prefix="/api/wallets", tags=["Wallets"])

@router.post("",response_model=WalletResponse,status_code=status.HTTP_201_CREATED,)
def create_wallet_endpoint(
    payload: WalletCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)):
    return create_wallet(db, current_user, payload.currency)

@router.get("", response_model=list[WalletResponse])
def list_wallets_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)):
    return list_wallets(db, current_user)

@router.get("/{wallet_id}", response_model=WalletResponse)
def get_wallet_endpoint(
    wallet_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)):
    return get_wallet(db, wallet_id, current_user)

@router.get("/{wallet_id}/balance",response_model=WalletBalanceResponse)
def get_wallet_balance_endpoint(
    wallet_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)):
    return get_wallet_balance(db, wallet_id, current_user)

@router.post("/{wallet_id}/freeze", response_model=WalletResponse)
def freeze_wallet_endpoint(
    wallet_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)):
    return change_wallet_status(db, wallet_id, current_user, "freeze")

@router.post("/{wallet_id}/unfreeze", response_model=WalletResponse)
def unfreeze_wallet_endpoint(
    wallet_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)):
    return change_wallet_status(db, wallet_id, current_user, "unfreeze")

@router.patch("/{wallet_id}", response_model=WalletResponse)
def update_wallet_endpoint(
    wallet_id: int,
    payload: WalletStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)):
    # General status changes are restricted to administrators.
    if current_user.role.name not in {"Super Admin", "Admin"}:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Administrator access required")
    wallet = get_wallet(db, wallet_id, current_user)
    allowed_transitions = {
        "ACTIVE": {"FROZEN", "SUSPENDED"},
        "FROZEN": {"ACTIVE", "SUSPENDED"},
        "SUSPENDED": {"ACTIVE", "FROZEN", "CLOSED"},
        "CLOSED": set()}
    if payload.status not in allowed_transitions[wallet.status]:
        from fastapi import HTTPException
        raise HTTPException(status_code=409,
                            detail=f"Invalid wallet status transition: {wallet.status} ->{payload.status}")
    wallet = db.scalar(
        select(type(wallet))
        .where(type(wallet).id == wallet_id)
        .with_for_update()
    )
    try:
        wallet.status = payload.status
        db.commit()
        db.refresh(wallet)
        return wallet
    except Exception:
        db.rollback()
        raise
