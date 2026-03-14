"""Authentication API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.auth.schemas import (
    AuthResponse,
    CurrentUserResponse,
    LoginRequest,
    RegisterRequest,
)
from app.auth.security import create_access_token, hash_password, verify_password
from app.db.session import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse)
def register_user(
    payload: RegisterRequest, db: Session = Depends(get_db)
) -> AuthResponse:
    """Register a new user account and return JWT token."""
    normalized_email = payload.email.strip().lower()
    existing_user = db.scalar(select(User).where(User.email == normalized_email))
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        )

    user = User(email=normalized_email, password_hash=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"user_id": str(user.id), "email": user.email})
    return AuthResponse(access_token=token, user_id=user.id, email=user.email)


@router.post("/login", response_model=AuthResponse)
def login_user(payload: LoginRequest, db: Session = Depends(get_db)) -> AuthResponse:
    """Authenticate an existing user and return JWT token."""
    normalized_email = payload.email.strip().lower()
    user = db.scalar(select(User).where(User.email == normalized_email))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )

    token = create_access_token({"user_id": str(user.id), "email": user.email})
    return AuthResponse(access_token=token, user_id=user.id, email=user.email)


@router.get("/me", response_model=CurrentUserResponse)
def read_current_user(
    current_user: User = Depends(get_current_user),
) -> CurrentUserResponse:
    """Return profile details of currently authenticated user."""
    return CurrentUserResponse(
        id=current_user.id,
        email=current_user.email,
        created_at=current_user.created_at,
    )
