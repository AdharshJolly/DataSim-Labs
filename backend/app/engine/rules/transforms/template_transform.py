"""Template transform helpers for semantic rules."""

from __future__ import annotations

import re
from typing import Any

import numpy as np


def evaluate_expression(expr: str, row_context: dict[str, Any]) -> str:
    """Evaluate safe expressions like split(name)[0] and column references."""
    expr = expr.strip()

    if expr in row_context:
        val = row_context[expr]
        return str(val) if val is not None else ""

    split_match = re.match(r"split\((\w+)\)\[(-?\d+)\]", expr)
    if split_match:
        col_name = split_match.group(1)
        index = int(split_match.group(2))
        if col_name in row_context:
            parts = str(row_context[col_name]).split()
            if -len(parts) <= index < len(parts):
                return parts[index]
            return ""

    lower_match = re.match(r"lower\((\w+)\)", expr)
    if lower_match:
        col_name = lower_match.group(1)
        if col_name in row_context:
            return str(row_context[col_name]).lower()

    upper_match = re.match(r"upper\((\w+)\)", expr)
    if upper_match:
        col_name = upper_match.group(1)
        if col_name in row_context:
            return str(row_context[col_name]).upper()

    substr_match = re.match(r"substring\((\w+),\s*(\d+),\s*(\d+)\)", expr)
    if substr_match:
        col_name = substr_match.group(1)
        start = int(substr_match.group(2))
        end = int(substr_match.group(3))
        if col_name in row_context:
            return str(row_context[col_name])[start:end]

    prefix_match = re.match(r"prefix\(['\"]([^'\"]*)['\"]\)", expr)
    if prefix_match:
        return prefix_match.group(1)

    raise ValueError(f"Unknown expression: {expr}")


def apply_template(rule: dict[str, Any], row_context: dict[str, Any]) -> str:
    """Apply template-based transformation (e.g., email: {first}.{last}@{domain})."""
    transform = rule.get("transform", {})
    template = transform.get("template", "")
    extractors = transform.get("extractors", {})
    domain_pool = transform.get("domain_pool", [])

    name_value = str(row_context.get("name", "") or "").strip()
    name_parts = [part for part in name_value.split() if part]
    default_first = name_parts[0].lower() if name_parts else "user"
    default_last = name_parts[-1].lower() if name_parts else "unknown"

    context = {}
    for key, expr in extractors.items():
        try:
            context[key] = evaluate_expression(expr, row_context)
        except Exception:
            context[key] = ""

    if "first" not in context or not str(context.get("first", "")).strip():
        context["first"] = default_first
    if "last" not in context or not str(context.get("last", "")).strip():
        context["last"] = default_last

    if domain_pool and "domain" not in context:
        rng = row_context.get("__rng__")
        if isinstance(rng, np.random.Generator):
            context["domain"] = str(rng.choice(domain_pool))
        else:
            context["domain"] = str(domain_pool[0])
    elif "domain" not in context:
        context["domain"] = "gmail.com"

    if not template:
        return f"{context['first']}.{context['last']}@{context['domain']}"
    return template.format(**context)
