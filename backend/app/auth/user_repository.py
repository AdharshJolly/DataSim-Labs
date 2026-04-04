"""Low-level data access helpers for the users collection."""

from __future__ import annotations

from datetime import datetime

from pymongo.database import Database
from pymongo.errors import PyMongoError

from app.api.errors import raise_database_unavailable
from app.auth.models import User


def find_user_by_email(db: Database, email: str) -> User | None:
    """Fetch a user by email, returning None when no record exists."""
    try:
        doc = db["users"].find_one({"email": email})
    except PyMongoError:
        raise_database_unavailable()
    return User.from_document(doc) if doc else None


def find_user_by_id(db: Database, user_id: str) -> User | None:
    """Fetch a user by id, returning None when no record exists."""
    try:
        doc = db["users"].find_one({"_id": user_id})
    except PyMongoError:
        raise_database_unavailable()
    return User.from_document(doc) if doc else None


def insert_user(db: Database, user: User) -> None:
    """Insert a new user document."""
    try:
        db["users"].insert_one(user.to_document())
    except PyMongoError:
        raise_database_unavailable()


def find_refresh_session_state(
    db: Database, user_id: str
) -> tuple[str, datetime | None] | None:
    """Return persisted refresh_jti and session_expires_at for a user."""
    try:
        doc = db["users"].find_one(
            {"_id": user_id},
            {"refresh_jti": 1, "session_expires_at": 1},
        )
    except PyMongoError:
        raise_database_unavailable()

    if doc is None:
        return None

    refresh_jti = str(doc.get("refresh_jti", ""))
    session_expires_at_raw = doc.get("session_expires_at")
    session_expires_at = (
        session_expires_at_raw if isinstance(session_expires_at_raw, datetime) else None
    )
    return refresh_jti, session_expires_at
