from fastapi import APIRouter, Depends,HTTPException,status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.security import get_current_user,create_access_token,verify_password
from app.models import User
from app.schemas.auth import (RegisterRequest,LoginRequest,RefreshRequest,
                              LogoutRequest,ChangePasswordRequest,UserResponse,TokenResponse,)
from app.services.auth_service import (register_user,login_user,refresh_user_token,
                                       logout_user,change_user_password,)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/register", response_model=UserResponse, status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    return register_user(
        db=db,
        full_name=payload.full_name,
        email=str(payload.email).lower(),
        password=payload.password.get_secret_value(),
        role_name=payload.role,)


@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(),
          db: Session = Depends(get_db)):
    user = (
        db.query(User)
        .filter(User.email == form_data.username.lower())
        .first())
    if not user or not verify_password(
        form_data.password,
        user.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"})
    access_token = create_access_token(user.id)
    return {"access_token": access_token,
            "token_type": "bearer",}


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    return refresh_user_token(db, payload.refresh_token)

@router.post("/logout")
def logout(payload: LogoutRequest, db: Session = Depends(get_db)):
    return logout_user(db, payload.refresh_token)

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),):
    return change_user_password(
        db,
        current_user,
        payload.old_password.get_secret_value(),
        payload.new_password.get_secret_value(),
    )
