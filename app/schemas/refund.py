from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

class RefundCreate(BaseModel):
    transaction_id: int = Field(gt=0)
    amount: Decimal = Field(
        gt=0,
        max_digits=18,
        decimal_places=2,
    )
    reason: str = Field(min_length=3, max_length=500)


class RefundResponse(BaseModel):
    id: int
    transaction_id: int
    amount: Decimal
    status: str
    reason: str
    reference_number: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RefundDecision(BaseModel):
    reason: str | None = Field(default=None, max_length=500)