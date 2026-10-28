from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Transaction, Wallet


STAFF_ROLES = {"Super Admin", "Admin", "Support Agent"}


def get_transaction_query(
    db: Session,
    current_user,
):
    query = (
        db.query(Transaction)
        .join(
            Wallet,
            Wallet.id == Transaction.wallet_id,
        )
    )

    # Customers can only access transactions for their own wallets.
    # Authorized staff can view transactions across wallets.
    if current_user.role.name not in STAFF_ROLES:
        query = query.filter(
            Wallet.user_id == current_user.id
        )

    return query


def list_transactions(
    db: Session,
    current_user,
    start_date: date | None = None,
    end_date: date | None = None,
    transaction_type: str | None = None,
    status: str | None = None,
    skip: int = 0,
    limit: int = 20,
):
    query = get_transaction_query(db, current_user)

    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=422,
            detail="start_date cannot be after end_date",
        )

    if start_date:
        start_datetime = datetime.combine(
            start_date,
            time.min,
            tzinfo=timezone.utc,
        )
        query = query.filter(
            Transaction.created_at >= start_datetime
        )

    if end_date:
        # Include the entire end date.
        end_datetime = datetime.combine(
            end_date + timedelta(days=1),
            time.min,
            tzinfo=timezone.utc,
        )
        query = query.filter(
            Transaction.created_at < end_datetime
        )

    if transaction_type:
        query = query.filter(
            Transaction.transaction_type == transaction_type.upper()
        )

    if status:
        query = query.filter(
            Transaction.status == status.upper()
        )

    return (
        query
        .order_by(
            Transaction.created_at.desc(),
            Transaction.id.desc(),
        )
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_transaction_by_id(
    db: Session,
    current_user,
    transaction_id: int,
):
    transaction = (
        get_transaction_query(db, current_user)
        .filter(Transaction.id == transaction_id)
        .first()
    )

    if transaction is None:
        raise HTTPException(
            status_code=404,
            detail="Transaction not found",
        )

    return transaction


def get_transaction_summary(
    db: Session,
    current_user,
    start_date: date | None = None,
    end_date: date | None = None,
):
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=422,
            detail="start_date cannot be after end_date",
        )

    query = get_transaction_query(db, current_user)

    if start_date:
        start_datetime = datetime.combine(
            start_date,
            time.min,
            tzinfo=timezone.utc,
        )
        query = query.filter(
            Transaction.created_at >= start_datetime
        )

    if end_date:
        end_datetime = datetime.combine(
            end_date + timedelta(days=1),
            time.min,
            tzinfo=timezone.utc,
        )
        query = query.filter(
            Transaction.created_at < end_datetime
        )

    total_transactions = query.count()

    total_amount = (
        query.with_entities(
            func.coalesce(
                func.sum(Transaction.amount),
                0,
            )
        ).scalar()
    )

    grouped_rows = (
        query.with_entities(
            Transaction.transaction_type,
            func.count(Transaction.id),
            func.coalesce(func.sum(Transaction.amount), 0),
        )
        .group_by(Transaction.transaction_type)
        .all()
    )

    return {
        "total_transactions": total_transactions,
        "total_amount": Decimal(str(total_amount)),
        "by_type": [
            {
                "transaction_type": transaction_type,
                "transaction_count": count,
                "total_amount": Decimal(str(amount)),
            }
            for transaction_type, count, amount in grouped_rows
        ],
    }