from datetime import datetime, time, timedelta, timezone
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models import (User,Wallet,WalletBalance,Transaction,SuspiciousTransaction,Refund)

STAFF_ROLES = {"Super Admin", "Admin", "Support Agent"}

def utc_day_range():
    now = datetime.now(timezone.utc)
    start = datetime.combine(
        now.date(),
        time.min,
        tzinfo=timezone.utc,
    )
    return start, start + timedelta(days=1)

def admin_dashboard(db: Session):
    start, end = utc_day_range()
    total_users = db.query(func.count(User.id)).scalar() or 0
    active_wallets = (
        db.query(func.count(Wallet.id))
        .filter(Wallet.status == "ACTIVE")
        .scalar()
        or 0
    )
    total_wallet_balance = (
        db.query(
            func.coalesce(
                func.sum(WalletBalance.available_balance),
                0,
            )
        )
        .scalar()
    )
    today_query = db.query(Transaction).filter(
        Transaction.created_at >= start,
        Transaction.created_at < end,
    )
    today_transactions = today_query.count()
    today_volume = (
        today_query.with_entities(
            func.coalesce(func.sum(Transaction.amount), 0)
        ).scalar()
    )
    failed_transactions = (
        db.query(func.count(Transaction.id))
        .filter(Transaction.status == "FAILED")
        .scalar()
        or 0
    )
    suspicious_transactions = (
        db.query(func.count(SuspiciousTransaction.id))
        .filter(
            SuspiciousTransaction.status.in_(
                ["REVIEW_REQUIRED", "BLOCKED"]
            )
        )
        .scalar()
        or 0
    )

    return {
        "total_users": total_users,
        "active_wallets": active_wallets,
        "total_wallet_balance": str(total_wallet_balance),
        "today_transactions": today_transactions,
        "today_transaction_volume": str(today_volume),
        "failed_transactions": failed_transactions,
        "suspicious_transactions": suspicious_transactions,
    }


def support_dashboard(db: Session):
    pending_reviews = (
        db.query(func.count(SuspiciousTransaction.id))
        .filter(
            SuspiciousTransaction.status == "REVIEW_REQUIRED"
        )
        .scalar()
        or 0
    )

    suspicious_transactions = (
        db.query(func.count(SuspiciousTransaction.id))
        .filter(
            SuspiciousTransaction.status.in_(
                ["REVIEW_REQUIRED", "BLOCKED"]
            )
        )
        .scalar()
        or 0
    )

    failed_transactions = (
        db.query(func.count(Transaction.id))
        .filter(Transaction.status == "FAILED")
        .scalar()
        or 0
    )

    refund_requests = (
        db.query(func.count(Refund.id))
        .filter(
            Refund.status.in_(["REQUESTED", "UNDER_REVIEW"])
        )
        .scalar()
        or 0
    )

    frozen_wallets = (
        db.query(func.count(Wallet.id))
        .filter(Wallet.status == "FROZEN")
        .scalar()
        or 0
    )

    return {
        "pending_reviews": pending_reviews,
        "suspicious_transactions": suspicious_transactions,
        "failed_transactions": failed_transactions,
        "refund_requests": refund_requests,
        "frozen_wallets": frozen_wallets,
    }


def customer_dashboard(db: Session, user: User):
    wallets = (
        db.query(Wallet)
        .filter(Wallet.user_id == user.id)
        .all()
    )
    wallet_ids = [wallet.id for wallet in wallets]
    total_balance = (
        db.query(
            func.coalesce(
                func.sum(WalletBalance.available_balance),
                0,
            )
        )
        .join(
            Wallet,
            WalletBalance.wallet_id == Wallet.id,
        )
        .filter(Wallet.user_id == user.id)
        .scalar()
    )
    if not wallet_ids:
        return {
            "wallet_count": 0,
            "wallet_balance": str(total_balance),
            "recent_transactions": [],
            "total_deposits": 0,
            "total_transfers": 0,
            "total_withdrawals": 0,
            "pending_transactions": 0,
        }
    transaction_query = db.query(Transaction).filter(
        Transaction.wallet_id.in_(wallet_ids)
    )
    recent_transactions = (
        transaction_query
        .order_by(
            Transaction.created_at.desc(),
            Transaction.id.desc(),
        )
        .limit(5)
        .all()
    )
    # Counts are transaction-record counts, not necessarily
    # unique business operations. Align these values with your
    # transaction_type values.
    total_deposits = transaction_query.filter(
        Transaction.transaction_type == "DEPOSIT"
    ).count()
    total_transfers = transaction_query.filter(
        Transaction.transaction_type.in_(
            ["TRANSFER_OUT", "TRANSFER_DEBIT"]
        )
    ).count()
    total_withdrawals = transaction_query.filter(
        Transaction.transaction_type == "WITHDRAWAL"
    ).count()
    pending_transactions = transaction_query.filter(
        Transaction.status.in_(["PENDING", "PROCESSING"])
    ).count()
    return {
        "wallet_count": len(wallet_ids),
        "wallet_balance": str(total_balance),
        "recent_transactions": [
            {
                "id": tx.id,
                "wallet_id": tx.wallet_id,
                "amount": str(tx.amount),
                "transaction_type": tx.transaction_type,
                "status": tx.status,
                "created_at": tx.created_at,
            }
            for tx in recent_transactions
        ],
        "total_deposits": total_deposits,
        "total_transfers": total_transfers,
        "total_withdrawals": total_withdrawals,
        "pending_transactions": pending_transactions,
    }