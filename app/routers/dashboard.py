from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database import get_db
from app.models import User
from app.services.dashboard_service import (admin_dashboard,support_dashboard,customer_dashboard)

router = APIRouter(prefix="/api/dashboard",
                   tags=["Dashboard"],)

@router.get("/admin")
def get_admin_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),):
    if current_user.role.name not in {"Super Admin", "Admin"}:
        raise HTTPException(status_code=403,
                            detail="Admin dashboard access required",)
    return admin_dashboard(db)

@router.get("/support")
def get_support_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),):
    if current_user.role.name not in {
        "Super Admin",
        "Admin",
        "Support Agent",}:
        raise HTTPException(status_code=403,
                            detail="Support dashboard access required",)
    return support_dashboard(db)

@router.get("/customer")
def get_customer_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),):
    if current_user.role.name != "Customer":
        raise HTTPException(status_code=403,
                            detail="Customer dashboard access required",)
    return customer_dashboard(db, current_user)