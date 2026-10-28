from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, status
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.security import (hash_password,verify_password,hash_token,
                               create_access_token,create_refresh_token)
from app.models import User, Role, RefreshToken


from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models.models import User, Role
from app.core.security import hash_password


def register_user(
    db: Session,
    full_name: str,
    email: str,
    password: str,
    role_name: str = "customer",
):
    existing_user = (
        db.query(User)
        .filter(User.email == email)
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=409,
            detail="Email is already registered",
        )

    # Find the requested role
    selected_role = (
        db.query(Role)
        .filter(Role.name. ilike(role_name.strip()))
        .first()
    )

    if not selected_role:
        raise HTTPException(
            status_code=400,
            detail=f"Role '{role_name}' is not configured",
        )

    # Create the user; do not call register_user() here
    user = User(
        full_name=full_name,
        email=email,
        hashed_password=hash_password(password),
        role_id=selected_role.id,
        is_active=True,
    )

    try:
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    except Exception:
        db.rollback()
        raise


def login_user(db: Session, email: str, password: str):
    user = db.query(User).filter(User.email == email).first()
    if (not user
        or not user.is_active
        or not verify_password(password, user.hashed_password)):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid email or password")
    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    db.add(RefreshToken(
            user_id=user.id,
            token_hash=hash_token(refresh_token),
            expires_at=expires_at))
    db.commit()
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",}

def refresh_user_token(db: Session, raw_token: str):
    invalid_token = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                  detail="Invalid or expired refresh token")
    try:
        payload = jwt.decode(
            raw_token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM])
        if payload.get("type") != "refresh":
            raise invalid_token
        user_id = int(payload["sub"])
    except (JWTError, ValueError, KeyError, TypeError):
        raise invalid_token
    stored_token = (
        db.query(RefreshToken)
        .filter(RefreshToken.token_hash == hash_token(raw_token))
        .with_for_update()
        .first())
    if (not stored_token
        or stored_token.user_id != user_id
        or stored_token.revoked_at is not None):
        raise invalid_token
    now = datetime.now(timezone.utc)
    expiry = stored_token.expires_at
    # Handle databases that return timezone-naive timestamps.
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    user = db.query(User).filter(User.id == user_id).first()
    if expiry <= now or not user or not user.is_active:
        raise invalid_token
    # Rotate the refresh token: revoke the old one and store the new one.
    stored_token.revoked_at = now
    new_refresh_token = create_refresh_token(user.id)
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_token(new_refresh_token),
            expires_at=now + timedelta(
                days=settings.REFRESH_TOKEN_EXPIRE_DAYS
            ),
        )
    )
    new_access_token = create_access_token(
    data={"sub": str(user.id)})
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
    }

def logout_user(db: Session, raw_token: str):
    token_hash = hash_token(raw_token)
    stored_token = (
        db.query(RefreshToken)
        .filter(RefreshToken.token_hash == token_hash)
        .with_for_update()
        .first())
    if stored_token and stored_token.revoked_at is None:
        stored_token.revoked_at = datetime.now(timezone.utc)
        db.commit()
    return {"message": "Logged out successfully"}

def change_user_password(
    db: Session,
    user: User,
    old_password: str,
    new_password: str,):
    if not verify_password(old_password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Current password is incorrect",)
    if verify_password(new_password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="New password must be different",)
    user.hashed_password = hash_password(new_password)
    # Revoke all refresh tokens after a password change.
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user.id,
        RefreshToken.revoked_at.is_(None),
    ).update(
        {"revoked_at": datetime.now(timezone.utc)},
        synchronize_session=False,
    )
    db.commit()
    return {"message": "Password changed successfully"}
