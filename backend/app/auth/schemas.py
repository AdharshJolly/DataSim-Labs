"""Pydantic schemas for auth endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    """Payload for user registration."""

    email: str = Field(..., min_length=5)
    password: str = Field(..., min_length=8)


class LoginRequest(BaseModel):
    """Payload for user login."""

    email: str = Field(..., min_length=5)
    password: str = Field(..., min_length=8)


class AuthResponse(BaseModel):
    """Response containing bearer token and lightweight user data."""

    access_token: str
    token_type: str = "bearer"
    user_id: UUID
    email: str


class CurrentUserResponse(BaseModel):
    """Authenticated user profile response."""

    id: UUID
    email: str
    created_at: datetime
