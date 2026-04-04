"""Function transform helpers for semantic rules."""

from __future__ import annotations

import hashlib
from typing import Any


def apply_function(rule: dict[str, Any], row_context: dict[str, Any]) -> Any:
    """Apply function-based transformation (e.g., uppercase, hash)."""
    transform = rule.get("transform", {})
    function_name = transform.get("function_name", "").lower()
    sources = rule.get("sources", [])

    if not sources:
        return None

    source_col = sources[0]
    if source_col not in row_context:
        return None

    value = row_context[source_col]

    try:
        if function_name == "uppercase":
            return str(value).upper()
        if function_name == "lowercase":
            return str(value).lower()
        if function_name == "capitalize":
            return str(value).capitalize()
        if function_name == "reverse":
            return str(value)[::-1]
        if function_name == "hash":
            return hashlib.sha256(str(value).encode()).hexdigest()[:16]
        if function_name == "prefix":
            prefix = transform.get("prefix", "")
            return f"{prefix}{value}"
        if function_name == "suffix":
            suffix = transform.get("suffix", "")
            return f"{value}{suffix}"
    except Exception:
        return None

    return None
