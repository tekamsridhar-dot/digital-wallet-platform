from datetime import datetime, time, timedelta, timezone
from decimal import Decimal
from uuid import uuid4
from app.core.exceptions import AppException
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.services.notification_service import create_notification

from app.models import (Wallet,WalletBalance,Withdrawal,Transaction,TransactionLedger,User,)

DAILY_WITHDRAWAL_LIMIT = Decimal("10000.00")
MAX_DAILY_WITHDRAWALS = 5

def create_withdrawal(
    db: Session,
    wallet_id: int,
    amount: Decimal,
    user: User,):
    if amount <= 0 or amount.as_tuple().exponent < -2:
        raise HTTPException(status_code=422,
                            detail="Amount must be positive with at most two decimal places",)
    try:
        # Lock wallet first to serialize withdrawals on this wallet.
        wallet = db.scalar(select(Wallet).where(Wallet.id == wallet_id) .with_for_update())
        if not wallet:
            raise HTTPException(status_code=404, 
                                detail="Wallet not found")
        if (wallet.user_id != user.id and user.role.name not in {"Super Admin", "Admin"}):
            raise HTTPException(status_code=403, 
                                detail="Access denied")
        if wallet.status != "ACTIVE":
            raise HTTPException(status_code=409,
                                detail="Only active wallets can make withdrawals",)
        if wallet.currency != "INR":
            raise HTTPException(status_code=400,
                                detail="This withdrawal service currently supports INR only",)
        balance = db.scalar(select(WalletBalance)
                            .where(WalletBalance.wallet_id == wallet_id)
                            .with_for_update())
        if not balance:
            raise HTTPException(status_code=409,
                                 detail="Wallet balance record is missing",)
        now = datetime.now(timezone.utc)
        day_start = datetime.combine( now.date(), time.min, tzinfo=timezone.utc)
        # Count and sum completed withdrawals for this wallet today.
        daily_stats = db.query(
            func.count(Withdrawal.id),
            func.coalesce(func.sum(Withdrawal.amount), 0),
        ).filter(
            Withdrawal.wallet_id == wallet_id,
            Withdrawal.status == "COMPLETED",
            Withdrawal.created_at >= day_start,
            Withdrawal.created_at < day_start + timedelta(days=1),
        ).one()
        withdrawal_count = daily_stats[0]
        withdrawn_today = Decimal(str(daily_stats[1]))
        if withdrawal_count >= MAX_DAILY_WITHDRAWALS:
            raise HTTPException(status_code=409,
                                 detail="Daily withdrawal count limit exceeded",)
        if withdrawn_today + amount > DAILY_WITHDRAWAL_LIMIT:
            raise HTTPException( status_code=409,
                                 detail="Daily withdrawal amount limit exceeded",)
        
        if balance.available_balance < amount:
            raise AppException(status_code=400,
                               code="INSUFFICIENT_BALANCE",
                               message="Insufficient wallet balance.")
        balance_before = balance.available_balance
        balance_after = balance_before - amount
        withdrawal = Withdrawal(
            wallet_id=wallet.id,
            amount=amount,
            currency=wallet.currency,
            status="COMPLETED",
            reference_number=f"WDR-{uuid4().hex}",
            created_at=now,
            completed_at=now,)
        db.add(withdrawal)
        db.flush()
        balance.available_balance = balance_after
        transaction = Transaction(
            wallet_id=wallet.id,
            transaction_type="WITHDRAWAL",
            amount=amount,
            currency=wallet.currency,
            status="COMPLETED",
            reference_entity="withdrawal",
            reference_id=withdrawal.id,
            description="Simulated wallet withdrawal",
            created_at=now,)
        db.add(transaction)
        db.flush()
        ledger_entry = TransactionLedger(
            wallet_id=wallet.id,
            transaction_type="WITHDRAWAL",
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            reference_entity="withdrawal",
            reference_id=withdrawal.id,
            description="Simulated wallet withdrawal",
            created_by=user.id,
            created_at=now)
        db.add(ledger_entry)
        create_notification(db=db,
                            user_id=wallet.user_id,
                            title="Withdrawal Completed",
                            message=f"Your withdrawal of ₹{withdrawal.amount} was completed.",)
        db.commit()
        db.refresh(withdrawal)
        return withdrawal
    except Exception:
        db.rollback()
        raise

def list_withdrawals(db: Session, user: User):
    query = (db.query(Withdrawal) .join(Wallet, Withdrawal.wallet_id == Wallet.id))
    if user.role.name not in {"Super Admin", "Admin"}:
        query = query.filter(Wallet.user_id == user.id)
    return query.order_by(Withdrawal.created_at.desc()).all()

def get_withdrawal(db: Session, withdrawal_id: int, user: User):
    withdrawal = db.get(Withdrawal, withdrawal_id)
    if not withdrawal:
        raise HTTPException(status_code=404,
                             detail="Withdrawal not found",)
    wallet = db.get(Wallet, withdrawal.wallet_id)
    if ( user.role.name not in {"Super Admin", "Admin"}
        and wallet.user_id != user.id):
        raise HTTPException(status_code=403, detail="Access denied")
    return withdrawal
