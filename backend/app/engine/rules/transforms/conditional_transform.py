"""Conditional transform helpers for semantic rules."""

from __future__ import annotations

import re
from typing import Any

from app.engine.rules.transforms.template_transform import evaluate_expression


def evaluate_condition(condition: str, row_context: dict[str, Any]) -> bool:
    """Evaluate safe conditions like country == 'India'."""
    condition = condition.strip()

    eq_match = re.match(r"(\w+)\s*==\s*['\"]([^'\"]+)['\"]", condition)
    if eq_match:
        col_name = eq_match.group(1)
        expected_value = eq_match.group(2)
        return str(row_context.get(col_name, "")) == expected_value

    neq_match = re.match(r"(\w+)\s*!=\s*['\"]([^'\"]+)['\"]", condition)
    if neq_match:
        col_name = neq_match.group(1)
        expected_value = neq_match.group(2)
        return str(row_context.get(col_name, "")) != expected_value

    in_match = re.match(r"(\w+)\s+in\s+\[([^\]]+)\]", condition)
    if in_match:
        col_name = in_match.group(1)
        values_str = in_match.group(2)
        values = [v.strip().strip("\"'") for v in values_str.split(",")]
        return str(row_context.get(col_name, "")) in values

    def _compare_numeric(pattern: str, comparator: str) -> bool | None:
        match = re.match(pattern, condition)
        if not match:
            return None
        col_name = match.group(1)
        threshold = float(match.group(2))
        try:
            value = float(row_context[col_name])
        except (KeyError, TypeError, ValueError):
            return False
        if comparator == ">=":
            return value >= threshold
        if comparator == ">":
            return value > threshold
        if comparator == "<=":
            return value <= threshold
        return value < threshold

    gte = _compare_numeric(r"(\w+)\s*>=\s*(\d+(?:\.\d+)?)", ">=")
    if gte is not None:
        return gte
    gt = _compare_numeric(r"(\w+)\s*>\s*(\d+(?:\.\d+)?)", ">")
    if gt is not None:
        return gt
    lte = _compare_numeric(r"(\w+)\s*<=\s*(\d+(?:\.\d+)?)", "<=")
    if lte is not None:
        return lte
    lt = _compare_numeric(r"(\w+)\s*<\s*(\d+(?:\.\d+)?)", "<")
    if lt is not None:
        return lt

    raise ValueError(f"Unknown condition: {condition}")


def apply_conditional(rule: dict[str, Any], row_context: dict[str, Any]) -> Any:
    """Apply conditional transformation (if-then logic)."""
    transform = rule.get("transform", {})
    conditions = transform.get("conditions", [])

    for condition in conditions:
        if_expr = condition.get("if", "")
        then_expr = condition.get("then", "")

        try:
            if evaluate_condition(if_expr, row_context):
                return evaluate_expression(then_expr, row_context)
        except Exception:
            continue

    return None
