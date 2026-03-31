"""Centralized row-level trace construction for explainability."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from app.engine.trace.trace_schema import TraceEntry


class TraceManager:
    """Build and normalize explainability traces for generated rows."""

    @staticmethod
    def normalize_value(value: Any) -> Any:
        if value is None:
            return None
        if pd.isna(value):
            return None
        if isinstance(value, np.generic):
            return value.item()
        return value

    @staticmethod
    def build_row_trace(
        *,
        base_row: dict[str, Any],
        final_row: dict[str, Any],
        semantic_rules: list[dict[str, Any]],
        column: str | None = None,
    ) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
        rules_by_target: dict[str, list[dict[str, Any]]] = {}
        for rule in semantic_rules:
            target = str(rule.get("target", "")).strip()
            if not target:
                continue
            rules_by_target.setdefault(target, []).append(rule)

        safe_row: dict[str, Any] = {
            key: TraceManager.normalize_value(value) for key, value in final_row.items()
        }

        trace: dict[str, dict[str, Any]] = {}
        for key, value in final_row.items():
            entry = TraceEntry(
                value=TraceManager.normalize_value(value),
                source="attribute_generator",
                generator="base_distribution",
                rule=None,
                depends_on=[],
            )

            target_rules = rules_by_target.get(key, [])
            if target_rules and base_row.get(key) != value:
                applied_rule = target_rules[-1]
                transform = applied_rule.get("transform", {})
                transform_type = str(transform.get("type", "rule")).strip() or "rule"
                entry.source = f"semantic_{transform_type}"
                entry.generator = transform_type
                entry.rule = str(
                    applied_rule.get("id")
                    or applied_rule.get("type")
                    or "semantic_rule"
                )
                entry.depends_on = [
                    str(source)
                    for source in applied_rule.get("sources", [])
                    if isinstance(source, str) and source.strip()
                ]

            trace[key] = entry.to_dict()

        if column:
            if column not in safe_row:
                raise ValueError(f"Column '{column}' not found in generated row")
            return {column: safe_row[column]}, {column: trace[column]}

        return safe_row, trace
