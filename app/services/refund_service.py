from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4
from app.core.exceptions import AppException
from app.services.notification_service import create_notification
from fastapi import HTTPException
from sqlalchemy import func, select
from app.services.audit_service import record_audit_log
from sqlalchemy.orm import Session

from app.models import (User,Wallet,WalletBalance,Transaction,TransactionLedger,Refund,)

STAFF_ROLES = {"Super Admin", "Admin", "Support Agent"}
REFUNDABLE_TYPES = {"WITHDRAWAL", "TRANSFER_OUT"}
RESERVED_STATUSES = { "REQUESTED", "UNDER_REVIEW", "APPROVED", "COMPLETED",}


def request_refund(
    db: Session,
    transaction_id: int,
    amount: Decimal,
    reason: str,
    user: User,
):
    if amount <= 0 or amount.as_tuple().exponent < -2:
        raise HTTPException(
            status_code=422,
            detail="Refund amount must be positive with at most two decimal places",
        )

    try:
        transaction = db.scalar(
            select(Transaction)
            .where(Transaction.id == transaction_id)
            .with_for_update()
        )

        if not transaction:
            raise HTTPException(
                status_code=404,
                detail="Original transaction not found",
            )

        wallet = db.scalar(
            select(Wallet)
            .where(Wallet.id == transaction.wallet_id)
            .with_for_update()
        )

        if not wallet:
            raise HTTPException(
                status_code=404,
                detail="Original wallet not found",
            )

        if user.role.name not in STAFF_ROLES and wallet.user_id != user.id:
            raise HTTPException(
                status_code=403,
                detail="You cannot request a refund for this transaction",
            )

        if transaction.status != "COMPLETED":
            raise HTTPException(
                status_code=409,
                detail="Only completed transactions can be refunded",
            )

        if transaction.transaction_type not in REFUNDABLE_TYPES:
            raise HTTPException(
                status_code=409,
                detail="This transaction type is not refundable",
            )

        if wallet.status == "CLOSED":
            raise AppException(status_code=409,code="WALLET_CLOSED",message="This wallet is closed.",)

        if amount > transaction.amount:
            raise HTTPException(
                status_code=409,
                detail="Refund exceeds the original transaction amount",
            )

        reserved_total = db.scalar(
            select(func.coalesce(func.sum(Refund.amount), 0)).where(
                Refund.transaction_id == transaction_id,
                Refund.status.in_(RESERVED_STATUSES),
            )
        )
        reserved_total = Decimal(str(reserved_total or 0))

        if reserved_total + amount > transaction.amount:
            raise HTTPException(
                status_code=409,
                detail="Refund requests exceed the refundable amount",
            )

        refund = Refund(
            transaction_id=transaction.id,
            wallet_id=transaction.wallet_id,
            amount=amount,
            status="REQUESTED",
            reason=reason,
            created_by=user.id,
            reference_number=f"REF-{uuid4().hex}",
            created_at=datetime.now(timezone.utc),
        )

        db.add(refund)
        db.flush()  # Generates refund.id before audit logging

        create_notification(
            db=db,
            user_id=wallet.user_id,
            title="Refund Request Submitted",
            message=(
                f"Your refund request for {transaction.currency} "
                f"{refund.amount} has been submitted for review."
            ),
        )

        record_audit_log(
            db=db,
            user_id=user.id,
            action="Refund Requested",
            entity_type="refund",
            entity_id=refund.id,
            details={
                "amount": str(refund.amount),
                "status": "REQUESTED",
                "transaction_id": transaction.id,
            },
        )

        db.commit()
        db.refresh(refund)
        return refund

    except Exception:
        db.rollback()
        raise



def list_refunds(db: Session, user: User):
    query = db.query(Refund).join(
        Transaction,Refund.transaction_id == Transaction.id,).join( 
            Wallet, Transaction.wallet_id == Wallet.id,)
    if user.role.name not in STAFF_ROLES:
        query = query.filter(Wallet.user_id == user.id)
    return query.order_by(Refund.created_at.desc()).all()

def get_refund(db: Session, refund_id: int, user: User):
    refund = db.get(Refund, refund_id)
    if not refund:
        raise HTTPException( status_code=404,
                             detail="Refund not found",)
    transaction = db.get(Transaction, refund.transaction_id)
    wallet = db.get(Wallet, transaction.wallet_id)
    if ( user.role.name not in STAFF_ROLES
        and wallet.user_id != user.id ):
        raise HTTPException( status_code=403,
                             detail="Access denied",)
    return refund

def approve_refund(
    db: Session,
    refund_id: int,
    reviewer: User,
    review_reason: str | None = None,):
    if reviewer.role.name not in STAFF_ROLES:
        raise HTTPException(status_code=403,
                             detail="Only authorized staff can approve refunds",)
    try:
        refund = db.scalar(select(Refund).where(Refund.id == refund_id).with_for_update())
        if not refund:
            raise HTTPException( status_code=404,
                                detail="Refund not found",)
        if refund.status not in {"REQUESTED", "UNDER_REVIEW"}:
            raise HTTPException( status_code=409,
                                 detail=f"Cannot approve a refund in {refund.status} status",)
        transaction = db.scalar(select(Transaction) 
                                .where(Transaction.id == refund.transaction_id)
                                .with_for_update())
        if not transaction or transaction.status != "COMPLETED":
            raise HTTPException(status_code=409,
                                detail="Original transaction is not eligible for refund",)
        wallet = db.scalar(select(Wallet) .where(Wallet.id == transaction.wallet_id) .with_for_update())
        if not wallet or wallet.status == "CLOSED":
            raise HTTPException( status_code=409,
                                 detail="Refunds are not allowed for closed wallets",)
        balance = db.scalar( select(WalletBalance).where(WalletBalance.wallet_id == wallet.id).with_for_update())
        if not balance:
            raise HTTPException(status_code=409,
                                detail="Wallet balance record is missing",)
        # Recheck the aggregate at approval time.
        other_refunds = db.scalar(
            select(func.coalesce(func.sum(Refund.amount), 0))
            .where(
                Refund.transaction_id == transaction.id,
                Refund.id != refund.id,
                Refund.status.in_(RESERVED_STATUSES),))
        other_refunds = Decimal(str(other_refunds or 0))
        if other_refunds + refund.amount > transaction.amount:
            raise HTTPException(status_code=409,
                                detail="Refund exceeds the remaining refundable amount",)
        balance_before = balance.available_balance
        balance_after = balance_before + refund.amount
        now = datetime.now(timezone.utc)
        # APPROVED is the decision; COMPLETED means wallet credit succeeded.
        refund.status = "APPROVED"
        refund.reviewed_by = reviewer.id
        refund.review_reason = review_reason
        balance.available_balance = balance_after
        db.add(Transaction(
                wallet_id=wallet.id,
                transaction_type="REFUND",
                amount=refund.amount,
                currency=transaction.currency,
                status="COMPLETED",
                reference_entity="refund",
                reference_id=refund.id,
                description="Refund credited to wallet",
                created_at=now,))
        db.add(TransactionLedger(
                wallet_id=wallet.id,
                transaction_type="REFUND",
                amount=refund.amount,
                balance_before=balance_before,
                balance_after=balance_after,
                reference_entity="refund",
                reference_id=refund.id,
                description="Approved refund",
                created_by=reviewer.id,
                created_at=now,))
        refund.status = "COMPLETED"
        refund.completed_at = now
        db.commit()
        db.refresh(refund)
        return refund
    except Exception:
        db.rollback()
        raise

def reject_refund(
    db: Session,
    refund_id: int,
    reviewer: User,
    review_reason: str | None = None,):
    if reviewer.role.name not in STAFF_ROLES:
        raise HTTPException(status_code=403,
                            detail="Only authorized staff can reject refunds",)
    try:
        refund = db.scalar(select(Refund).where(Refund.id == refund_id).with_for_update())
        if not refund:
            raise HTTPException(status_code=404,
                                detail="Refund not found",)
        if refund.status not in {"REQUESTED", "UNDER_REVIEW"}:
            raise HTTPException(status_code=409,
                                detail=f"Cannot reject a refund in {refund.status} status",)
        refund.status = "REJECTED"
        refund.reviewed_by = reviewer.id
        refund.review_reason = review_reason
        db.commit()
        db.refresh(refund)
        return refund
    except Exception:
        db.rollback()
        raise