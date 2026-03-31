"""Typed trace schema used by explainability endpoints."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(slots=True)
class TraceEntry:
    """Explainability trace for one generated column value."""

    value: Any
    source: str
    generator: str
    rule: str | None
    depends_on: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
