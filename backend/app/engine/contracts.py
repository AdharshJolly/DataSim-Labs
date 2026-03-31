"""Protocol contracts for generation, rules, and suggestion engines."""

from __future__ import annotations

from typing import Any, Protocol

import pandas as pd


class RuleEngineInterface(Protocol):
    """Contract for rule engines that mutate/derive dataframe values."""

    def apply_rule(self, rule: dict[str, Any], row_context: dict[str, Any]) -> Any:
        """Apply one rule against a row context and return derived value."""


class GeneratorInterface(Protocol):
    """Contract for generators producing synthetic tabular data."""

    def generate_dataframe(
        self,
        attributes: list[Any],
        row_count: int,
        realism_rules: list[dict[str, Any]] | None = None,
        semantic_groups: list[dict[str, Any]] | None = None,
        semantic_rules: list[dict[str, Any]] | None = None,
    ) -> pd.DataFrame:
        """Generate a dataframe from attribute specs."""


class SuggestionInterface(Protocol):
    """Contract for deterministic suggestion engines."""

    def suggest(self, attributes: list[Any]) -> dict[str, Any]:
        """Return suggestions for provided attributes."""
