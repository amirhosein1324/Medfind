from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User
from ..schemas import UserCreate, UserResponse
from ..security import get_current_user, hash_password, require_role

router = APIRouter()


@router.post("/", response_model=UserResponse, status_code=201)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    if user.role not in ("customer", "pharmacy_owner"):
        # Admin accounts are never created through open self-registration.
        raise HTTPException(status_code=400, detail="Invalid role for self-registration")

    new_user = User(
        full_name=user.full_name,
        email=user.email,
        password_hash=hash_password(user.password),
        phone=user.phone,
        role=user.role,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


@router.get("/me", response_model=UserResponse)
def get_my_profile(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Users can view their own profile; only admins can look up others.
    if current_user.user_id != user_id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to view this user")

    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user


@router.get("/", response_model=list[UserResponse])
def list_users(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_role("admin")),
):
    return db.query(User).all()
