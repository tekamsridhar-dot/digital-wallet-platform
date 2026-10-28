from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4
from app.services.risk_service import record_risk_assessment
from fastapi import HTTPException
from app.services.audit_service import record_audit_log
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.services.notification_service import create_notification

from app.models import (Wallet,WalletBalance,Deposit,Transaction,TransactionLedger,User)


def create_deposit(
    db: Session,
    wallet_id: int,
    amount: Decimal,
    user: User,
    ip_address: str | None = None,
):
    if amount <= 0 or amount.as_tuple().exponent < -2:
        raise HTTPException(
            status_code=422,
            detail="Amount must be positive with at most two decimal places",
        )

    try:
        # Lock the wallet
        wallet = db.scalar(
            select(Wallet)
            .where(Wallet.id == wallet_id)
            .with_for_update()
        )

        if not wallet:
            raise HTTPException(status_code=404, detail="Wallet not found")

        if (
            wallet.user_id != user.id
            and user.role.name not in {"Super Admin", "Admin"}
        ):
            raise HTTPException(status_code=403, detail="Access denied")

        if wallet.status != "ACTIVE":
            raise HTTPException(
                status_code=409,
                detail="Only active wallets can receive deposits",
            )

        # Lock the balance
        balance = db.scalar(
            select(WalletBalance)
            .where(WalletBalance.wallet_id == wallet_id)
            .with_for_update()
        )

        if not balance:
            raise HTTPException(
                status_code=409,
                detail="Wallet balance record is missing",
            )

        if wallet.currency != "INR":
            raise HTTPException(
                status_code=400,
                detail="This simulated deposit service currently supports INR only",
            )

        now = datetime.now(timezone.utc)
        balance_before = balance.available_balance
        balance_after = balance_before + amount

        deposit = Deposit(
            wallet_id=wallet.id,
            amount=amount,
            currency=wallet.currency,
            status="COMPLETED",
            reference_number=f"DEP-{uuid4().hex}",
            created_at=now,
            completed_at=now,
        )

        db.add(deposit)
        db.flush()  # Generate deposit.id

        record_audit_log(
            db=db,
            user_id=user.id,
            action="Deposit Created",
            entity_type="deposit",
            entity_id=deposit.id,
            details={
                "amount": str(deposit.amount),
                "status": deposit.status,
            },
        )

        # Update wallet balance
        balance.available_balance = balance_after

        transaction = Transaction(
            wallet_id=wallet.id,
            transaction_type="DEPOSIT",
            amount=amount,
            currency=wallet.currency,
            status="COMPLETED",
            reference_entity="deposit",
            reference_id=deposit.id,
            description="Simulated wallet deposit",
            created_at=now,
        )

        db.add(transaction)
        db.flush()

        # Record risk assessment
        record_risk_assessment(db, transaction)

        ledger_entry = TransactionLedger(
            wallet_id=wallet.id,
            transaction_type="DEPOSIT",
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            reference_entity="deposit",
            reference_id=deposit.id,
            description="Simulated wallet deposit",
            created_by=user.id,
            created_at=now,
        )

        db.add(ledger_entry)

        create_notification(
            db=db,
            user_id=wallet.user_id,
            title="Deposit Completed",
            message=(
                f"Your deposit of {deposit.currency} "
                f"{deposit.amount} was completed."
            ),
        )
        record_audit_log(
    db=db,
    user_id=user.id,
    action="Deposit Created",
    entity_type="deposit",
    entity_id=deposit.id,
    details={
        "amount": str(deposit.amount),
        "status": deposit.status,
        "ip_address": ip_address,},)
        db.commit()
        db.refresh(deposit)

        return deposit

    except Exception:
        db.rollback()
        raise


def list_deposits(db: Session, user: User):
    query = db.query(Deposit).join(Wallet, Deposit.wallet_id == Wallet.id)
    if user.role.name not in {"Super Admin", "Admin"}:
        query = query.filter(Wallet.user_id == user.id)
    return query.order_by(Deposit.created_at.desc()).all()

def get_deposit(db: Session, deposit_id: int, user: User):
    deposit = db.get(Deposit, deposit_id)
    if not deposit:
        raise HTTPException(status_code=404, detail="Deposit not found")
    wallet = db.get(Wallet, deposit.wallet_id)
    if (user.role.name not in {"Super Admin", "Admin"}
        and wallet.user_id != user.id):
        raise HTTPException(status_code=403, detail="Access denied")
    return deposit
