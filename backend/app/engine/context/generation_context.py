"""Shared generation context for engine and orchestration flows."""

from __future__ import annotations

from typing import Any


class GenerationContext:
    """Carries generation inputs across services and engine boundaries."""

    def __init__(
        self,
        attributes: list[Any],
        semantic_rules: list[dict[str, Any]] | None = None,
        realism_rules: list[dict[str, Any]] | None = None,
        seed: int | None = None,
        config: dict[str, Any] | None = None,
    ) -> None:
        self.attributes = attributes
        self.semantic_rules = semantic_rules or []
        self.realism_rules = realism_rules or []
        self.seed = seed
        self.config = config or {}
