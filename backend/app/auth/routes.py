"""Authentication API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
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


def _set_auth_cookies(
    response: Response, access_token: str, refresh_token: str
) -> None:
    secure_cookie = settings.auth_cookie_secure or settings.app_env == "production"
    common_kwargs = {
        "httponly": True,
        "secure": secure_cookie,
        "samesite": settings.auth_cookie_samesite,
        "path": settings.auth_cookie_path,
    }
    if settings.auth_cookie_domain:
        common_kwargs["domain"] = settings.auth_cookie_domain

    response.set_cookie(
        key=settings.auth_access_cookie_name,
        value=access_token,
        max_age=settings.jwt_expiration_minutes * 60,
        **common_kwargs,
    )
    response.set_cookie(
        key=settings.auth_refresh_cookie_name,
        value=refresh_token,
        max_age=settings.jwt_refresh_expiration_days * 24 * 60 * 60,
        **common_kwargs,
    )


def _clear_auth_cookies(response: Response) -> None:
    secure_cookie = settings.auth_cookie_secure or settings.app_env == "production"
    clear_kwargs = {
        "secure": secure_cookie,
        "samesite": settings.auth_cookie_samesite,
        "path": settings.auth_cookie_path,
    }
    if settings.auth_cookie_domain:
        clear_kwargs["domain"] = settings.auth_cookie_domain

    response.delete_cookie(key=settings.auth_access_cookie_name, **clear_kwargs)
    response.delete_cookie(key=settings.auth_refresh_cookie_name, **clear_kwargs)


def _raise_database_unavailable() -> None:
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Database unavailable. Please try again shortly.",
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
    refresh_token = create_refresh_token({"user_id": str(user.id), "email": user.email})
    _set_auth_cookies(response, token, refresh_token)
    return AuthResponse(
        access_token=token,
        refresh_token=refresh_token,
        user_id=user.id,
        email=user.email,
    )


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
    refresh_token = create_refresh_token({"user_id": str(user.id), "email": user.email})
    _set_auth_cookies(response, token, refresh_token)
    return AuthResponse(
        access_token=token,
        refresh_token=refresh_token,
        user_id=user.id,
        email=user.email,
    )


@router.post("/refresh", response_model=TokenRefreshResponse)
def refresh_token(
    request: Request,
    response: Response,
    payload: RefreshTokenRequest | None = None,
    db: Database = Depends(get_db),
) -> TokenRefreshResponse:
    """Issue a new access token and refresh token."""
    raw_refresh_token = (
        payload.refresh_token if payload else None
    ) or request.cookies.get(settings.auth_refresh_cookie_name)
    if not raw_refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing",
        )

    try:
        decoded = decode_refresh_token(raw_refresh_token)
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)
        ) from exc

    user_id = decoded.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing user identifier",
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
    new_access_token = create_access_token(
        {"user_id": str(user.id), "email": user.email}
    )
    new_refresh_token = create_refresh_token(
        {"user_id": str(user.id), "email": user.email}
    )
    _set_auth_cookies(response, new_access_token, new_refresh_token)

    return TokenRefreshResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
    )


@router.post("/logout")
def logout_user(response: Response) -> dict[str, str]:
    """Client-side token logout acknowledgement."""
    _clear_auth_cookies(response)
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
