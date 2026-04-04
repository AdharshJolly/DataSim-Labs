"""Shared helpers for issuing and persisting token pairs."""

from __future__ import annotations

from datetime import datetime, timezone

from pymongo.database import Database
from pymongo.errors import PyMongoError

from app.api.errors import raise_database_unavailable
from app.auth.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
)


def issue_token_pair(user_id: str, email: str) -> tuple[str, str]:
    """Create and return (access_token, refresh_token) for the given user."""
    access_token = create_access_token({"user_id": user_id, "email": email})
    refresh_token = create_refresh_token({"user_id": user_id, "email": email})
    return access_token, refresh_token


def persist_refresh_token(db: Database, user_id: str, refresh_token: str) -> None:
    """Decode refresh token and persist token rotation metadata to the user record."""
    decoded = decode_refresh_token(refresh_token)
    refresh_jti = str(decoded.get("jti", ""))
    session_exp_epoch = int(decoded.get("session_exp", 0))
    try:
        db["users"].update_one(
            {"_id": user_id},
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
