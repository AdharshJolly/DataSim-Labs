"""Mapping transform helpers for semantic rules."""

from __future__ import annotations

from typing import Any


def apply_mapping(rule: dict[str, Any], row_context: dict[str, Any]) -> Any:
    """Apply mapping-based transformation (e.g., city -> state)."""
    transform = rule.get("transform", {})
    mapping_table = transform.get("mapping_table", {})
    sources = rule.get("sources", [])

    if not sources or not mapping_table:
        return None

    lookup_key_col = sources[0]
    if lookup_key_col not in row_context:
        return None

    lookup_key = row_context[lookup_key_col]
    return mapping_table.get(str(lookup_key))
