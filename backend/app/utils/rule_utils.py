"""Reusable helpers for semantic rule policy/ordering/validation."""

from __future__ import annotations

from typing import Any

from app.engine.rules.rule_executor import build_deterministic_execution_order
from app.engine.rules.rule_utils import normalize_conflict_policy
from app.engine.rules.rule_validator import validate_semantic_rules


def resolve_conflict_policy(value: str | None) -> str:
    """Normalize conflict policy value to supported enum-like string."""
    return normalize_conflict_policy(value)


def validate_and_order_semantic_rules(
    *,
    semantic_rules: list[dict[str, Any]],
    available_columns: list[str],
    conflict_policy: str | None,
) -> dict[str, Any]:
    """Validate semantic rules and produce deterministic execution order."""
    normalized_policy = resolve_conflict_policy(conflict_policy)
    validation = validate_semantic_rules(
        semantic_rules,
        available_columns=available_columns,
        conflict_policy=normalized_policy,
    )
    ordered = build_deterministic_execution_order(
        validation.get("sanitized_rules", []),
        conflict_policy=normalized_policy,
    )
    return {
        "validation": validation,
        "ordered_rules": ordered,
        "conflict_policy": normalized_policy,
    }
