from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models import Wallet, WalletBalance, User
from app.services.audit_service import record_audit_log
from app.core.exceptions import AppException

def create_wallet(db: Session, user: User, currency: str):
    wallet = Wallet(
        user_id=user.id,
        currency=currency,
        status="ACTIVE")
    try:
        db.add(wallet)
        db.flush()
        # Every new wallet starts with zero available and pending balance.
        balance = WalletBalance(
            wallet_id=wallet.id,
            available_balance=0,
            pending_balance=0)
        db.add(balance)
        db.commit()
        db.refresh(wallet)
        return wallet
    except Exception:
        db.rollback()
        raise

def list_wallets(db: Session, user: User):
    query = db.query(Wallet)
    # Customers can only see their own wallets.
    if user.role.name == "Customer":
        query = query.filter(Wallet.user_id == user.id)
    return query.order_by(Wallet.created_at.desc()).all()

def get_wallet(db: Session, wallet_id: int, user: User):
    wallet = db.query(Wallet).filter(Wallet.id == wallet_id).first()
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    if user.role.name == "Customer" and wallet.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return wallet

def get_wallet_balance(db: Session, wallet_id: int, user: User):
    wallet = get_wallet(db, wallet_id, user)
    balance = (db.query(WalletBalance).filter(WalletBalance.wallet_id == wallet.id).first())
    if not balance:
        raise HTTPException(status_code=404,
                            detail="Wallet balance not found",)
    return {
        "wallet_id": wallet.id,
        "currency": wallet.currency,
        "available_balance": balance.available_balance,
        "pending_balance": balance.pending_balance,}


def change_wallet_status(
    db: Session,
    wallet_id: int,
    user: User,
    action: str,
):
    allowed_roles = {"Super Admin", "Admin", "Support Agent"}

    if user.role.name not in allowed_roles:
        raise HTTPException(
            status_code=403,
            detail="You are not allowed to change wallet status",
        )

    wallet = (
        db.query(Wallet)
        .filter(Wallet.id == wallet_id)
        .with_for_update()
        .first()
    )

    if not wallet:
        raise HTTPException(
            status_code=404,
            detail="Wallet not found",
        )

    if action == "freeze":
        if wallet.status != "ACTIVE":
            raise HTTPException(
                status_code=409,
                detail="Only active wallets can be frozen",
            )
        new_status = "FROZEN"
        audit_action = "Wallet Frozen"

    elif action == "unfreeze":
        
        if wallet.status == "FROZEN":
            raise AppException(status_code=409,
                               code="WALLET_FROZEN",
                               message="Transactions are not allowed on a frozen wallet.",)
        new_status = "ACTIVE"
        audit_action = "Wallet Unfrozen"

    else:
        raise HTTPException(
            status_code=400,
            detail="Invalid action",
        )

    try:
        wallet.status = new_status

        record_audit_log(
            db=db,
            user_id=user.id,
            action=audit_action,
            entity_type="wallet",
            entity_id=wallet.id,
            details={"new_status": new_status},
        )

        db.commit()
        db.refresh(wallet)
        return wallet

    except Exception:
        db.rollback()
        raise
