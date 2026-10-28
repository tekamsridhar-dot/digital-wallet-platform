from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

class TransferCreate(BaseModel):
    sender_wallet_id: int = Field(gt=0)
    receiver_wallet_id: int = Field(gt=0)
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)

class TransferResponse(BaseModel):
    id: int
    sender_wallet_id: int
    receiver_wallet_id: int
    amount: Decimal
    currency: str
    status: str
    reference: str
    created_at: datetime
    completed_at: datetime | None

    model_config = ConfigDict(from_attributes=True)