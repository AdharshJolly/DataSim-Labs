"""Shared API v1 dependencies."""

from __future__ import annotations

from app.auth.dependencies import get_current_user
from app.db.session import get_db

__all__ = ["get_db", "get_current_user"]
