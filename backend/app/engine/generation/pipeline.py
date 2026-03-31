"""Pipeline orchestration for one generation chunk."""

from __future__ import annotations

from typing import Any, Callable

import pandas as pd

from app.engine.rules.rule_engine import CONFIDENCE_THRESHOLD
from app.engine.rules.rule_executor import filter_rules_by_confidence
from app.engine.null_injector import inject_nulls


class GenerationPipeline:
    """Coordinates grouped generation, semantic rules, realism, and null injection."""

    def __init__(
        self,
        core_generator: Any,
        rng: Any,
        faker: Any,
        apply_semantic_rules: Callable[..., tuple[pd.DataFrame, dict[str, Any]]],
        topological_sort_rules: Callable[[list[dict[str, Any]]], list[dict[str, Any]]],
        extract_dependencies: Callable[
            [list[dict[str, Any]]], tuple[set[str], set[str]]
        ],
    ) -> None:
        self.core_generator = core_generator
        self.rng = rng
        self.faker = faker
        self.apply_semantic_rules = apply_semantic_rules
        self.topological_sort_rules = topological_sort_rules
        self.extract_dependencies = extract_dependencies

    def generate_chunk(
        self,
        attributes: list[Any],
        row_count: int,
        realism_rules: list[dict] | None,
        semantic_groups: list[dict[str, Any]] | None,
        semantic_rules: list[dict[str, Any]] | None,
    ) -> tuple[pd.DataFrame, dict[str, Any]]:
        resolved_groups = semantic_groups or self.core_generator.detect_semantic_groups(
            attributes
        )
        filtered_semantic_rules = filter_rules_by_confidence(
            semantic_rules or [], CONFIDENCE_THRESHOLD
        )
        sorted_semantic_rules = self.topological_sort_rules(filtered_semantic_rules)
        _, dependent_columns = self.extract_dependencies(sorted_semantic_rules)

        data: dict[str, pd.Series] = {}
        grouped_columns: set[str] = set()
        grouped_data = self.core_generator.generate_semantic_group_columns(
            groups=resolved_groups,
            attributes=attributes,
            row_count=row_count,
        )
        for column_name, values in grouped_data.items():
            grouped_columns.add(column_name)
            data[column_name] = pd.Series(values, name=column_name)

        for attr in attributes:
            if attr.name in grouped_columns:
                continue
            if attr.name in dependent_columns:
                continue
            data[attr.name] = self.core_generator.generate_column(
                attr=attr,
                row_count=row_count,
            )

        frame = pd.DataFrame(data)

        semantic_stats: dict[str, Any] = {
            "rule_metrics": {},
            "totals": {
                "rules_considered": 0,
                "attempted_rows": 0,
                "applied_rows": 0,
                "skipped_rows": 0,
                "error_rows": 0,
            },
        }
        if sorted_semantic_rules:
            frame, semantic_stats = self.apply_semantic_rules(
                frame=frame,
                rules=sorted_semantic_rules,
                attributes=attributes,
            )

        realism_stats: dict[str, Any] = {
            "rule_impacts": {},
            "total_rows_affected": 0,
            "rule_count": 0,
        }

        if realism_rules:
            from app.engine.realism_processor import RealismProcessor  # deferred

            processor = RealismProcessor(faker=self.faker, rng=self.rng)
            frame, realism_stats = processor.apply_with_stats(frame, realism_rules)

        for attr in attributes:
            if attr.name not in frame.columns:
                frame[attr.name] = pd.Series([None] * row_count, name=attr.name)
            frame[attr.name] = inject_nulls(
                series=frame[attr.name],
                null_percentage=attr.null_percentage,
                rng=self.rng,
            )

        return frame, {
            **realism_stats,
            "semantic_rules": semantic_stats,
        }
