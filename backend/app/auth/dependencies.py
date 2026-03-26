"""Auth dependencies used across API routes."""

from __future__ import annotations

import logging

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pymongo.database import Database

from app.auth.models import User
from app.auth.security import InvalidTokenError, decode_access_token
from app.core.config import settings
from app.db.session import get_db

bearer_scheme = HTTPBearer(auto_error=False)
logger = logging.getLogger("app.auth")


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Database = Depends(get_db),
) -> User:
    """Return currently authenticated user from cookie-first auth with header fallback."""
    header_token: str | None = (
        credentials.credentials
        if credentials is not None and credentials.scheme.lower() == "bearer"
        else None
    )
    cookie_token = request.cookies.get(settings.auth_access_cookie_name)
    token = cookie_token
    fallback_reason: str | None = None

    if not token and header_token:
        token = header_token
        fallback_reason = "cookie_missing"

    if token and token == cookie_token:
        try:
            payload = decode_access_token(token)
        except InvalidTokenError:
            if header_token:
                token = header_token
                fallback_reason = "cookie_invalid"
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired token",
                )
        else:
            user_id = payload.get("user_id")
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token missing user identifier",
                )

            user_doc = db["users"].find_one({"_id": user_id})
            if user_doc is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found",
                )
            return User.from_document(user_doc)

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    try:
        payload = decode_access_token(token)
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    if fallback_reason:
        fallback_user_id = payload.get("user_id") or "unknown"
        logger.warning(
            "auth_header_fallback_used reason=%s method=%s path=%s env=%s user_id=%s",
            fallback_reason,
            request.method,
            request.url.path,
            settings.app_env,
            fallback_user_id,
        )

    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing user identifier",
        )

    user_doc = db["users"].find_one({"_id": user_id})
    if user_doc is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return User.from_document(user_doc)
