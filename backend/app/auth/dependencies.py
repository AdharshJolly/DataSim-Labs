"""Auth dependencies used across API routes."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from pymongo.database import Database

from app.auth.models import User
from app.auth.security import InvalidTokenError, decode_access_token
from app.core.config import settings
from app.db.session import get_db


def get_current_user(
    request: Request,
    db: Database = Depends(get_db),
) -> User:
    """Return currently authenticated user from the access token cookie only."""
    token = request.cookies.get(settings.auth_access_cookie_name)

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
