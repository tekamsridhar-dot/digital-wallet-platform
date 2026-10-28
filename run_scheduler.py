import logging
from apscheduler.schedulers.blocking import BlockingScheduler
from app.tasks.scheduled_jobs import (
    scan_suspicious_transactions,
    generate_daily_wallet_summary,
    generate_daily_transaction_report,
    cleanup_stale_pending_transactions,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

scheduler = BlockingScheduler(timezone="UTC")

# Scan recent completed transactions every hour.
scheduler.add_job(
    scan_suspicious_transactions,
    trigger="interval",
    hours=1,
    id="suspicious_transaction_scan",
    max_instances=1,
    coalesce=True,
)

# Check for stale pending transactions every hour.
scheduler.add_job(
    cleanup_stale_pending_transactions,
    trigger="interval",
    hours=1,
    id="pending_transaction_cleanup",
    max_instances=1,
    coalesce=True,
)

# Generate the daily wallet summary at 00:05 UTC.
scheduler.add_job(
    generate_daily_wallet_summary,
    trigger="cron",
    hour=0,
    minute=5,
    id="daily_wallet_summary",
    max_instances=1,
    coalesce=True,
)

# Generate the daily transaction report at 00:10 UTC.
scheduler.add_job(
    generate_daily_transaction_report,
    trigger="cron",
    hour=0,
    minute=10,
    id="daily_transaction_report",
    max_instances=1,
    coalesce=True,
)

if __name__ == "__main__":
    logging.info("Starting digital wallet scheduler")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logging.info("Stopping digital wallet scheduler")