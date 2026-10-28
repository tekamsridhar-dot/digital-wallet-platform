import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy import func
from app.database import SessionLocal
from app.models import (Transaction,Wallet,WalletBalance,SuspiciousTransaction)
from app.services.risk_service import record_risk_assessment

logger = logging.getLogger(__name__)

def scan_suspicious_transactions():
    """Assess recent completed transactions for suspicious patterns."""
    db = SessionLocal()
    try:
        since = datetime.now(timezone.utc) - timedelta(hours=24)
        transactions = (
            db.query(Transaction)
            .filter(
                Transaction.created_at >= since,
                Transaction.status == "COMPLETED",
            )
            .order_by(Transaction.created_at.asc())
            .all()
        )
        assessed = 0
        for transaction in transactions:
            existing_alert = (
                db.query(SuspiciousTransaction.id)
                .filter(
                    SuspiciousTransaction.transaction_id
                    == transaction.id
                )
                .first()
            )
            if existing_alert:
                continue
            alert = record_risk_assessment(db, transaction)
            if alert:
                assessed += 1
        db.commit()
        logger.info(
            "Suspicious transaction scan completed; alerts created: %s",
            assessed,
        )
    except Exception:
        db.rollback()
        logger.exception("Suspicious transaction scan failed")
        raise
    finally:
        db.close()

def generate_daily_wallet_summary():
    """Log basic wallet and balance totals for operational reporting."""
    db = SessionLocal()
    try:
        wallet_count = (
            db.query(func.count(Wallet.id))
            .filter(Wallet.status == "ACTIVE")
            .scalar()
            or 0
        )
        total_available_balance = (
            db.query(
                func.coalesce(
                    func.sum(WalletBalance.available_balance),
                    0,
                )
            )
            .scalar()
        )
        logger.info(
            "Daily wallet summary: active_wallets=%s, "
            "total_available_balance=%s",
            wallet_count,
            total_available_balance,
        )
    except Exception:
        logger.exception("Daily wallet summary failed")
        raise
    finally:
        db.close()

def generate_daily_transaction_report():
    """Log counts and amounts grouped by transaction status."""
    db = SessionLocal()
    try:
        today = datetime.now(timezone.utc).date()
        start = datetime.combine(
            today,
            datetime.min.time(),
            tzinfo=timezone.utc,
        )
        end = start + timedelta(days=1)
        rows = (
            db.query(
                Transaction.status,
                func.count(Transaction.id),
                func.coalesce(func.sum(Transaction.amount), 0),
            )
            .filter(
                Transaction.created_at >= start,
                Transaction.created_at < end,
            )
            .group_by(Transaction.status)
            .all()
        )
        for status, count, amount in rows:
            logger.info(
                "Daily transaction report: date=%s status=%s "
                "count=%s amount=%s",
                today,
                status,
                count,
                amount,
            )
    except Exception:
        logger.exception("Daily transaction report failed")
        raise
    finally:
        db.close()

def cleanup_stale_pending_transactions():
    db = SessionLocal()
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        stale_count = (
            db.query(func.count(Transaction.id))
            .filter(
                Transaction.status.in_(["PENDING", "PROCESSING"]),
                Transaction.created_at < cutoff,
            )
            .scalar()
            or 0
        )
        if stale_count:
            logger.warning(
                "Found %s stale transactions requiring reconciliation",
                stale_count,
            )
        else:
            logger.info("No stale pending transactions found")
    except Exception:
        logger.exception("Pending transaction cleanup scan failed")
        raise
    finally:
        db.close()