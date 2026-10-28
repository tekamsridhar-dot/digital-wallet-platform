from fastapi import APIRouter, Depends, status,Header
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.security import get_current_user
from app.models import User
from app.schemas.transfer import TransferCreate, TransferResponse
from app.services.transfer_service import (create_transfer,list_transfers,get_transfer,)

router = APIRouter(tags=["Transfers"])

@router.post(
    "/api/transfers",
    response_model=TransferResponse,
    status_code=status.HTTP_201_CREATED)
def create_transfer_endpoint(
    payload: TransferCreate,
    idempotency_key: str = Header( ...,
        alias="Idempotency-Key",
        min_length=8,
        max_length=255,),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),):
    return create_transfer(
        db,
        payload,
        current_user,
        idempotency_key=idempotency_key,)

@router.get("/api/transfers", response_model=list[TransferResponse])
def list_transfers_endpoint(db: Session = Depends(get_db), current_user: User = Depends(get_current_user),):
    return list_transfers(db, current_user)

@router.get( "/api/transfers/{transfer_id}", response_model=TransferResponse,)
def get_transfer_endpoint(
    transfer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),):
    return get_transfer(db, transfer_id, current_user)