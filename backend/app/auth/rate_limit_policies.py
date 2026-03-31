"""Authentication route rate limit policies."""

from __future__ import annotations

from app.auth.rate_limit import LOGIN_POLICY, REFRESH_POLICY, REGISTER_POLICY

__all__ = ["REGISTER_POLICY", "LOGIN_POLICY", "REFRESH_POLICY"]
