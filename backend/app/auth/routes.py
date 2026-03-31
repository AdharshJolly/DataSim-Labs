"""Authentication API routes."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pymongo.database import Database
from pymongo.errors import PyMongoError

from app.api.errors import raise_database_unavailable
from app.auth.cookie_utils import _clear_auth_cookies, _client_key, _set_auth_cookies
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
from app.auth.rate_limit import (
    rate_limiter,
)
from app.auth.rate_limit_policies import LOGIN_POLICY, REFRESH_POLICY, REGISTER_POLICY
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


@router.post("/register", response_model=AuthResponse)
def register_user(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    db: Database = Depends(get_db),
) -> AuthResponse:
    """Register a new user account and return JWT token."""
    normalized_email = payload.email.strip().lower()
    rate_limiter.check(
        _client_key(request, "register", normalized_email),
        REGISTER_POLICY,
    )

    try:
        existing_user = db["users"].find_one({"email": normalized_email})
    except PyMongoError:
        raise_database_unavailable()
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
        raise_database_unavailable()

    token = create_access_token({"user_id": str(user.id), "email": user.email})
    refresh_token = create_refresh_token({"user_id": str(user.id), "email": user.email})
    decoded_refresh = decode_refresh_token(refresh_token)
    refresh_jti = str(decoded_refresh.get("jti", ""))
    session_exp_epoch = int(decoded_refresh.get("session_exp", 0))

    try:
        db["users"].update_one(
            {"_id": str(user.id)},
            {
                "$set": {
                    "refresh_jti": refresh_jti,
                    "session_expires_at": datetime.fromtimestamp(
                        session_exp_epoch,
                        tz=timezone.utc,
                    ),
                }
            },
        )
    except PyMongoError:
        raise_database_unavailable()

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
    request: Request,
    response: Response,
    db: Database = Depends(get_db),
) -> AuthResponse:
    """Authenticate an existing user and return JWT token."""
    normalized_email = payload.email.strip().lower()
    rate_limiter.check(
        _client_key(request, "login", normalized_email),
        LOGIN_POLICY,
    )

    try:
        user_doc = db["users"].find_one({"email": normalized_email})
    except PyMongoError:
        raise_database_unavailable()
    user = User.from_document(user_doc) if user_doc else None
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )

    token = create_access_token({"user_id": str(user.id), "email": user.email})
    refresh_token = create_refresh_token({"user_id": str(user.id), "email": user.email})
    decoded_refresh = decode_refresh_token(refresh_token)
    refresh_jti = str(decoded_refresh.get("jti", ""))
    session_exp_epoch = int(decoded_refresh.get("session_exp", 0))

    try:
        db["users"].update_one(
            {"_id": str(user.id)},
            {
                "$set": {
                    "refresh_jti": refresh_jti,
                    "session_expires_at": datetime.fromtimestamp(
                        session_exp_epoch,
                        tz=timezone.utc,
                    ),
                }
            },
        )
    except PyMongoError:
        raise_database_unavailable()

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
    rate_limiter.check(_client_key(request, "refresh"), REFRESH_POLICY)

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
    token_jti = str(decoded.get("jti", ""))
    session_exp_epoch = int(decoded.get("session_exp", 0))
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing user identifier",
        )
    if not token_jti:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
    if session_exp_epoch <= int(datetime.now(timezone.utc).timestamp()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired",
        )

    try:
        user_doc = db["users"].find_one({"_id": user_id})
    except PyMongoError:
        raise_database_unavailable()

    if not user_doc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )

    stored_refresh_jti = str(user_doc.get("refresh_jti", ""))
    if not stored_refresh_jti or stored_refresh_jti != token_jti:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been rotated",
        )

    session_expires_at = user_doc.get("session_expires_at")
    if isinstance(session_expires_at, datetime) and session_expires_at <= datetime.now(
        timezone.utc
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired",
        )

    user = User.from_document(user_doc)
    new_access_token = create_access_token(
        {"user_id": str(user.id), "email": user.email}
    )
    new_refresh_token = create_refresh_token(
        {"user_id": str(user.id), "email": user.email}
    )
    decoded_new = decode_refresh_token(new_refresh_token)
    new_jti = str(decoded_new.get("jti", ""))
    new_session_exp_epoch = int(decoded_new.get("session_exp", 0))

    try:
        update_result = db["users"].update_one(
            {"_id": str(user.id), "refresh_jti": token_jti},
            {
                "$set": {
                    "refresh_jti": new_jti,
                    "session_expires_at": datetime.fromtimestamp(
                        new_session_exp_epoch,
                        tz=timezone.utc,
                    ),
                }
            },
        )
    except PyMongoError:
        raise_database_unavailable()

    if update_result.modified_count != 1:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been rotated",
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
