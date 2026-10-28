from datetime import datetime
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

class WalletCreate(BaseModel):
    currency: Literal["INR", "USD", "EUR"] = "INR"

class WalletResponse(BaseModel):
    id: int
    user_id: int
    currency: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class WalletBalanceResponse(BaseModel):
    wallet_id: int
    currency: str
    available_balance: Decimal
    pending_balance: Decimal

class WalletStatusUpdate(BaseModel):
    status: Literal["ACTIVE", "FROZEN", "SUSPENDED", "CLOSED"]
