from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4
from fastapi import HTTPException
from sqlalchemy import select, or_
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.services.notification_service import create_notification
from app.services.audit_service import record_audit_log

from app.schemas.transfer import TransferResponse
from app.services.idempotency_service import ( make_request_hash, find_idempotency_record, 
                                              reserve_idempotency_key, complete_idempotency_key)
from app.models import (Wallet,WalletBalance, Transfer, Transaction, TransactionLedger, User)


def create_transfer(
    db: Session,
    payload,
    user: User,
    idempotency_key: str,):
    endpoint = "/api/transfers"
    request_data = payload.model_dump(mode="json")
    request_hash = make_request_hash(request_data)

    # Check for a previously completed request first.
    existing = find_idempotency_record(
        db, user.id, idempotency_key, endpoint, request_hash
    )
    if existing:
        return existing.response_body

    try:
        # Reserve the key inside the same transaction as the transfer.
        idempotency_record = reserve_idempotency_key(
            db, user.id, idempotency_key, endpoint, request_hash
        )

        sender_id = payload.sender_wallet_id
        receiver_id = payload.receiver_wallet_id
        amount = payload.amount

        if sender_id == receiver_id:
            raise HTTPException(
                status_code=400,
                detail="Sender and receiver wallets must be different",
            )

        if amount <= 0 or amount.as_tuple().exponent < -2:
            raise HTTPException(
                status_code=422,
                detail="Amount must be positive with at most two decimal places",
            )

        wallets = db.scalars(
            select(Wallet)
            .where(Wallet.id.in_([sender_id, receiver_id]))
            .order_by(Wallet.id)
            .with_for_update()
        ).all()

        wallet_map = {wallet.id: wallet for wallet in wallets}
        sender = wallet_map.get(sender_id)
        receiver = wallet_map.get(receiver_id)

        if not sender or not receiver:
            raise HTTPException(
                status_code=404,
                detail="Sender or receiver wallet not found",
            )

        if (
            user.role.name not in {"Super Admin", "Admin"}
            and sender.user_id != user.id
        ):
            raise HTTPException(
                status_code=403,
                detail="You cannot transfer from another user's wallet",
            )

        if sender.status != "ACTIVE" or receiver.status != "ACTIVE":
            raise HTTPException(
                status_code=409,
                detail="Both wallets must be active",
            )

        if sender.currency != receiver.currency:
            raise HTTPException(
                status_code=400,
                detail="Both wallets must use the same currency",
            )

        balances = db.scalars(
            select(WalletBalance)
            .where(WalletBalance.wallet_id.in_([sender_id, receiver_id]))
            .order_by(WalletBalance.wallet_id)
            .with_for_update()
        ).all()

        balance_map = {b.wallet_id: b for b in balances}
        sender_balance = balance_map.get(sender_id)
        receiver_balance = balance_map.get(receiver_id)

        if not sender_balance or not receiver_balance:
            raise HTTPException(
                status_code=409,
                detail="Sender or receiver balance record is missing",
            )

        if sender_balance.available_balance < amount:
            raise HTTPException(
                status_code=409,
                detail="Insufficient wallet balance",
            )

        sender_before = sender_balance.available_balance
        receiver_before = receiver_balance.available_balance
        sender_after = sender_before - amount
        receiver_after = receiver_before + amount
        now = datetime.now(timezone.utc)
        reference = f"TRF-{uuid4().hex}"

        transfer = Transfer(
            sender_wallet_id=sender_id,
            receiver_wallet_id=receiver_id,
            amount=amount,
            currency=sender.currency,
            status="COMPLETED",
            reference=reference,
            created_at=now,
            completed_at=now,
        )
        db.add(transfer)
        db.flush()

        sender_balance.available_balance = sender_after
        receiver_balance.available_balance = receiver_after

        db.add_all([
            Transaction(
                wallet_id=sender_id,
                transaction_type="TRANSFER_OUT",
                amount=amount,
                currency=sender.currency,
                status="COMPLETED",
                reference_entity="transfer",
                reference_id=transfer.id,
                description=f"Transfer sent to wallet {receiver_id}",
                created_at=now,
            ),
            Transaction(
                wallet_id=receiver_id,
                transaction_type="TRANSFER_IN",
                amount=amount,
                currency=receiver.currency,
                status="COMPLETED",
                reference_entity="transfer",
                reference_id=transfer.id,
                description=f"Transfer received from wallet {sender_id}",
                created_at=now,
            ),
            TransactionLedger(
                wallet_id=sender_id,
                transaction_type="TRANSFER_OUT",
                amount=amount,
                balance_before=sender_before,
                balance_after=sender_after,
                reference_entity="transfer",
                reference_id=transfer.id,
                description=f"Transfer sent to wallet {receiver_id}",
                created_by=user.id,
                created_at=now,
            ),
            TransactionLedger(
                wallet_id=receiver_id,
                transaction_type="TRANSFER_IN",
                amount=amount,
                balance_before=receiver_before,
                balance_after=receiver_after,
                reference_entity="transfer",
                reference_id=transfer.id,
                description=f"Transfer received from wallet {sender_id}",
                created_by=user.id,
                created_at=now,
            ),
        ])
        create_notification(db=db,
                            user_id=sender.wallet.user_id,
                            title="Transfer Sent",
                            message=f"Your transfer of ₹{transfer.amount} was completed.",)
        create_notification(db=db,user_id=receiver.wallet.user_id,
                            title="Money Received",
                            message=f"You received ₹{transfer.amount}.",)
        record_audit_log(
    db=db,
    user_id=user.id,
    action="Transfer Completed",
    entity_type="transfer",
    entity_id=transfer.id,
    details={
        "amount": str(transfer.amount),
        "status": "COMPLETED",},)
        response_body = TransferResponse.model_validate(
            transfer
        ).model_dump(mode="json")

        complete_idempotency_key(
            idempotency_record, 201, response_body
        )
        

        db.commit()
        db.refresh(transfer)
        return transfer

    except IntegrityError:
        db.rollback()
        # A concurrent request may have reserved this key.
        existing = find_idempotency_record(
            db, user.id, idempotency_key, endpoint, request_hash
        )
        if existing:
            return existing.response_body

        raise HTTPException(
            status_code=409,
            detail="Idempotency key conflict; retry with the same key",
        )
    except Exception:
        db.rollback()
        raise


def list_transfers(db: Session, user: User):
    query = db.query(Transfer)
    if user.role.name not in {"Super Admin", "Admin"}:
        query = query.join(
            Wallet,
            or_(
                Transfer.sender_wallet_id == Wallet.id,
                Transfer.receiver_wallet_id == Wallet.id,
            ),
        ).filter(Wallet.user_id == user.id)
    return query.distinct().order_by(
    Transfer.created_at.desc()).all()

def get_transfer(db: Session, transfer_id: int, user: User):
    transfer = db.get(Transfer, transfer_id)
    if not transfer:
        raise HTTPException(status_code=404, detail="Transfer not found")
    if user.role.name not in {"Super Admin", "Admin"}:
        sender = db.get(Wallet, transfer.sender_wallet_id)
        receiver = db.get(Wallet, transfer.receiver_wallet_id)
        if (sender.user_id != user.id and receiver.user_id != user.id):
            raise HTTPException(status_code=403, detail="Access denied")
    return transfer