"""Authentication API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.database import Database
from pymongo.errors import PyMongoError

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.auth.schemas import (
    AuthResponse,
    CurrentUserResponse,
    LoginRequest,
    RegisterRequest,
    RefreshTokenRequest,
    TokenRefreshResponse,
)
from app.auth.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    verify_password,
    InvalidTokenError,
)
from app.db.session import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


def _raise_database_unavailable() -> None:
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Database unavailable. Please try again shortly.",
    )


@router.post("/register", response_model=AuthResponse)
def register_user(
    payload: RegisterRequest,
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
    refresh_token = create_refresh_token({"user_id": str(user.id), "email": user.email})
    return AuthResponse(
        access_token=token,
        refresh_token=refresh_token,
        user_id=user.id,
        email=user.email,
    )


@router.post("/login", response_model=AuthResponse)
def login_user(
    payload: LoginRequest,
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
    refresh_token = create_refresh_token({"user_id": str(user.id), "email": user.email})
    return AuthResponse(
        access_token=token,
        refresh_token=refresh_token,
        user_id=user.id,
        email=user.email,
    )


@router.post("/refresh", response_model=TokenRefreshResponse)
def refresh_token(
    payload: RefreshTokenRequest,
    db: Database = Depends(get_db),
) -> TokenRefreshResponse:
    """Issue a new access token and refresh token."""
    try:
        decoded = decode_refresh_token(payload.refresh_token)
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)
        ) from exc

    user_id = decoded.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing user identifier"
        )

    try:
        user_doc = db["users"].find_one({"_id": user_id})
    except PyMongoError:
        _raise_database_unavailable()

    if not user_doc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )

    user = User.from_document(user_doc)
    new_access_token = create_access_token({"user_id": str(user.id), "email": user.email})
    new_refresh_token = create_refresh_token({"user_id": str(user.id), "email": user.email})

    return TokenRefreshResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
    )


@router.post("/logout")
def logout_user() -> dict[str, str]:
    """Client-side token logout acknowledgement."""
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
