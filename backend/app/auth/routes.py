"""Authentication API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pymongo.database import Database
from pymongo.errors import PyMongoError

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.auth.schemas import (
    AuthResponse,
    CurrentUserResponse,
    LoginRequest,
    RegisterRequest,
)
from app.auth.security import create_access_token, hash_password, verify_password
from app.core.config import settings
from app.db.session import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


def _raise_database_unavailable() -> None:
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Database unavailable. Please try again shortly.",
    )


def _set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=token,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
        max_age=settings.jwt_expiration_minutes * 60,
        path="/",
    )


@router.post("/register", response_model=AuthResponse)
def register_user(
    payload: RegisterRequest,
    response: Response,
    db: Database = Depends(get_db),
) -> AuthResponse:
    """Register a new user account and return JWT token."""
    normalized_email = payload.email.strip().lower()
    try:
        existing_user = db["users"].find_one({"email": normalized_email})
    except PyMongoError:
        _raise_database_unavailable()
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        )

    user = User.new(
        email=normalized_email, password_hash=hash_password(payload.password)
    )
    try:
        db["users"].insert_one(user.to_document())
    except PyMongoError:
        _raise_database_unavailable()

    token = create_access_token({"user_id": str(user.id), "email": user.email})
    _set_auth_cookie(response, token)
    return AuthResponse(access_token=token, user_id=user.id, email=user.email)


@router.post("/login", response_model=AuthResponse)
def login_user(
    payload: LoginRequest,
    response: Response,
    db: Database = Depends(get_db),
) -> AuthResponse:
    """Authenticate an existing user and return JWT token."""
    normalized_email = payload.email.strip().lower()
    try:
        user_doc = db["users"].find_one({"email": normalized_email})
    except PyMongoError:
        _raise_database_unavailable()
    user = User.from_document(user_doc) if user_doc else None
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )

    token = create_access_token({"user_id": str(user.id), "email": user.email})
    _set_auth_cookie(response, token)
    return AuthResponse(access_token=token, user_id=user.id, email=user.email)


@router.post("/logout")
def logout_user(response: Response) -> dict[str, str]:
    """Clear auth cookie for logout."""
    response.delete_cookie(key=settings.auth_cookie_name, path="/")
    return {"message": "Logged out"}


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
