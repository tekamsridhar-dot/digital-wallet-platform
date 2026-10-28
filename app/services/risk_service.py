from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.services.notification_service import create_notification
from app.models import (
    AuditLog,
    Role,
    SuspiciousTransaction,
    Transaction,
    User,
    Wallet,
)
from app.core.risk_config import (
    HIGH_AMOUNT_THRESHOLD,
    VELOCITY_WINDOW_MINUTES,
    MAX_TRANSFERS_IN_WINDOW,
    MAX_TRANSACTIONS_IN_WINDOW,
    RECENT_WALLET_FREEZE_HOURS,
)
from app.models import (
    AuditLog,
    SuspiciousTransaction,
    Transaction,
    User,
    Wallet,
)


STAFF_ROLES = {"Super Admin", "Admin", "Support Agent"}

TRANSFER_TYPES = {"TRANSFER_OUT", "TRANSFER_DEBIT"}


def evaluate_transaction_risk(
    db: Session,
    transaction: Transaction,
) -> dict:
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(
        minutes=VELOCITY_WINDOW_MINUTES
    )

    amount = Decimal(str(transaction.amount))
    reasons = []
    score = 0

    # Rule 1: High transaction amount.
    if amount >= HIGH_AMOUNT_THRESHOLD:
        reasons.append("TRANSACTION_AMOUNT_EXCEEDS_THRESHOLD")
        score += 40

    # Rule 2: Frequent outgoing transfers.
    if transaction.transaction_type in TRANSFER_TYPES:
        recent_transfers = db.scalar(
            select(func.count())
            .select_from(Transaction)
            .where(
                Transaction.wallet_id == transaction.wallet_id,
                Transaction.transaction_type.in_(TRANSFER_TYPES),
                Transaction.created_at >= window_start,
                Transaction.id != transaction.id,
            )
        ) or 0

        if recent_transfers >= MAX_TRANSFERS_IN_WINDOW:
            reasons.append("HIGH_TRANSFER_FREQUENCY")
            score += 30

    # Rule 3: Unusual overall transaction frequency.
    recent_transactions = db.scalar(
        select(func.count())
        .select_from(Transaction)
        .where(
            Transaction.wallet_id == transaction.wallet_id,
            Transaction.created_at >= window_start,
            Transaction.id != transaction.id,
        )
    ) or 0

    if recent_transactions >= MAX_TRANSACTIONS_IN_WINDOW:
        reasons.append("UNUSUAL_TRANSACTION_FREQUENCY")
        score += 20

    # Rule 4: Wallet frozen recently.
    freeze_start = now - timedelta(
        hours=RECENT_WALLET_FREEZE_HOURS
    )

    recent_freeze = db.scalar(
        select(AuditLog.id)
        .where(
            AuditLog.entity_type == "wallet",
            AuditLog.entity_id == transaction.wallet_id,
            AuditLog.action == "Wallet Frozen",
            AuditLog.created_at >= freeze_start,
        )
        .limit(1)
    )

    if recent_freeze is not None:
        reasons.append("WALLET_RECENTLY_FROZEN")
        score += 30

    # Rule 5: A transaction's daily-limit rule must use your
    # actual configured transaction-limit model and business logic.
    # Do not hardcode a separate limit here that conflicts with
    # the withdrawal/transfer services.

    risk_status = "REVIEW_REQUIRED" if reasons else "NORMAL"

    if reasons:
        admin_users = db.scalars(
        select(User)
        .join(Role, User.role_id == Role.id)
        .where(Role.name.in_({"Super Admin", "Admin"}))
    ).all()

    for admin_user in admin_users:
        create_notification(
            db=db,
            user_id=admin_user.id,
            title="Suspicious Transaction Detected",
            message=(
                f"Transaction {transaction.id} requires review. "
                f"Risk score: {min(score, 100)}. "
                f"Reasons: {', '.join(reasons)}"
            ),
        )

    return {
    "risk_status": risk_status,
    "risk_score": min(score, 100),
    "reasons": reasons,}

def record_risk_assessment(
    db: Session,
    transaction: Transaction,
):
    assessment = evaluate_transaction_risk(db, transaction)

    if not assessment["reasons"]:
        return None

    alert = SuspiciousTransaction(
        transaction_id=transaction.id,
        wallet_id=transaction.wallet_id,
        risk_status=assessment["risk_status"],
        reason=", ".join(assessment["reasons"]),
        risk_score=assessment["risk_score"],
        created_at=datetime.now(timezone.utc),
    )

    db.add(alert)
    db.flush()

    return alert


def list_suspicious_transactions(db: Session):
    return (
        db.query(SuspiciousTransaction)
        .filter(
            SuspiciousTransaction.risk_status.in_(
                ["REVIEW_REQUIRED", "BLOCKED"]
            )
        )
        .order_by(
            SuspiciousTransaction.created_at.desc()
        )
        .all()
    )


def review_suspicious_transaction(
    db: Session,
    suspicious_id: int,
    reviewer: User,
    decision: str,
    notes: str | None = None,
):
    if reviewer.role.name not in STAFF_ROLES:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to review suspicious transactions",
        )

    allowed_decisions = {
        "NORMAL",
        "REVIEW_REQUIRED",
        "BLOCKED",
    }

    if decision not in allowed_decisions:
        raise HTTPException(
            status_code=422,
            detail="Invalid risk decision",
        )

    try:
        alert = db.scalar(
            select(SuspiciousTransaction)
            .where(SuspiciousTransaction.id == suspicious_id)
            .with_for_update()
        )

        if alert is None:
            raise HTTPException(
                status_code=404,
                detail="Suspicious transaction not found",
            )

        transaction = db.scalar(
            select(Transaction)
            .where(
                Transaction.id == alert.transaction_id
            )
            .with_for_update()
        )

        if transaction is None:
            raise HTTPException(
                status_code=404,
                detail="Transaction not found",
            )

        # Do not pretend that an already completed transaction
        # was blocked. A completed transaction needs a separate
        # reversal or refund workflow.
        if decision == "BLOCKED" and transaction.status not in {
            "PENDING",
            "PROCESSING",
        }:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Only pending or processing transactions "
                    "can be blocked through this review endpoint"
                ),
            )

        if decision == "BLOCKED":
            transaction.status = "BLOCKED"

        alert.risk_status = decision
        alert.reviewed_by = reviewer.id
        alert.reviewed_at = datetime.now(timezone.utc)
        alert.review_notes = notes

        db.commit()
        db.refresh(alert)
        return alert

    except Exception:
        db.rollback()
        raise