import hashlib
import json
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models import IdempotencyKey

def make_request_hash(payload: dict) -> str:
    canonical_json = json.dumps(payload,sort_keys=True,separators=(",", ":"),default=str,)
    return hashlib.sha256( canonical_json.encode("utf-8") ).hexdigest()

def find_idempotency_record(
    db: Session,
    user_id: int,
    key: str,
    endpoint: str,
    request_hash: str,):
    record = (
        db.query(IdempotencyKey) .filter(
            IdempotencyKey.user_id == user_id,
            IdempotencyKey.key == key,
            IdempotencyKey.endpoint == endpoint,) .first())
    if record is None:
        return None
    if record.request_hash != request_hash:
        raise HTTPException( status_code=409,
                             detail=("This Idempotency-Key was already used with a different request"))
    # A committed record should have a saved response.
    if record.response_status is None or record.response_body is None:
        raise HTTPException( status_code=409,
                             detail="A request with this key is still being processed",)
    return record

def save_idempotency_record(
    db: Session,
    user_id: int,
    key: str,
    endpoint: str,
    request_hash: str,
    response_status: int,
    response_body: dict,):
    record = IdempotencyKey(
        user_id=user_id,
        key=key,
        endpoint=endpoint,
        request_hash=request_hash,
        response_status=response_status,
        response_body=response_body )
    db.add(record)
    db.flush()
    return record

def reserve_idempotency_key(
    db: Session,
    user_id: int,
    key: str,
    endpoint: str,
    request_hash: str,):
    record = IdempotencyKey(
        user_id=user_id,
        key=key,
        endpoint=endpoint,
        request_hash=request_hash,
        response_status=None,
        response_body=None)
    db.add(record)
    db.flush()  # Detect duplicate keys before processing money.
    return record

def complete_idempotency_key(
    record: IdempotencyKey,
    response_status: int,
    response_body: dict,):
    record.response_status = response_status
    record.response_body = response_body