"""Authentication domain models for MongoDB persistence."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from datetime import timezone
from typing import Any


def _parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class User:
    """Application user account."""

    id: uuid.UUID
    email: str
    password_hash: str
    created_at: datetime

    @classmethod
    def new(cls, email: str, password_hash: str) -> "User":
        return cls(
            id=uuid.uuid4(),
            email=email,
            password_hash=password_hash,
            created_at=datetime.now(timezone.utc),
        )

    @classmethod
    def from_document(cls, document: dict[str, Any]) -> "User":
        return cls(
            id=uuid.UUID(str(document["_id"])),
            email=str(document["email"]),
            password_hash=str(document["password_hash"]),
            created_at=_parse_datetime(document.get("created_at")),
        )

    def to_document(self) -> dict[str, Any]:
        return {
            "_id": str(self.id),
            "email": self.email,
            "password_hash": self.password_hash,
            "created_at": self.created_at,
        }
