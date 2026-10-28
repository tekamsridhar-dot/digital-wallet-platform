from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class TransactionResponse(BaseModel):
    id: int
    wallet_id: int
    amount: Decimal
    transaction_type: str
    status: str
    currency: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TransactionTypeSummary(BaseModel):
    transaction_type: str
    transaction_count: int
    total_amount: Decimal


class TransactionSummaryResponse(BaseModel):
    total_transactions: int
    total_amount: Decimal
    by_type: list[TransactionTypeSummary]