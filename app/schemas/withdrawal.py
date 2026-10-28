from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

class WithdrawalCreate(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)

class WithdrawalResponse(BaseModel):
    id: int
    wallet_id: int
    amount: Decimal
    currency: str
    status: str
    reference_number: str
    created_at: datetime
    completed_at: datetime | None

    model_config = ConfigDict(from_attributes=True)