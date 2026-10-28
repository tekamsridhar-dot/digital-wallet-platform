from decimal import Decimal

# Example values; adjust to your business requirements.
HIGH_AMOUNT_THRESHOLD = Decimal("10000.00")

VELOCITY_WINDOW_MINUTES = 10
MAX_TRANSFERS_IN_WINDOW = 5
MAX_TRANSACTIONS_IN_WINDOW = 10

RECENT_WALLET_FREEZE_HOURS = 24