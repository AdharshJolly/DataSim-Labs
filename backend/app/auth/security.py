"""Password hashing and JWT utilities."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class InvalidTokenError(ValueError):
    """Raised when JWT token is invalid or expired."""


def hash_password(password: str) -> str:
    """Hash plaintext password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify plaintext password against hashed password."""
    return pwd_context.verify(password, password_hash)


def create_access_token(subject: dict[str, Any]) -> str:
    """Create signed JWT token with expiration and user claims."""
    expire_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.jwt_expiration_minutes
    )
    payload = {
        **subject,
        "type": "access",
        "exp": expire_at,
    }
    return jwt.encode(
        payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )


def create_refresh_token(subject: dict[str, Any]) -> str:
    """Create signed JWT refresh token with extended expiration."""
    session_started_at = datetime.now(timezone.utc)
    session_expires_at = session_started_at + timedelta(
        days=settings.jwt_refresh_expiration_days
    )
    expire_at = datetime.now(timezone.utc) + timedelta(
        days=settings.jwt_refresh_expiration_days
    )
    payload = {
        **subject,
        "type": "refresh",
        "jti": str(uuid4()),
        "session_iat": int(session_started_at.timestamp()),
        "session_exp": int(session_expires_at.timestamp()),
        "exp": expire_at,
    }
    return jwt.encode(
        payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate JWT access token."""
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        if payload.get("type") != "access":
            raise InvalidTokenError("Invalid token type")
        return payload
    except JWTError as exc:
        raise InvalidTokenError("Invalid or expired token") from exc


def decode_refresh_token(token: str) -> dict[str, Any]:
    """Decode and validate JWT refresh token."""
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        if payload.get("type") != "refresh":
            raise InvalidTokenError("Invalid token type")
        return payload
    except JWTError as exc:
        raise InvalidTokenError("Invalid or expired token") from exc
