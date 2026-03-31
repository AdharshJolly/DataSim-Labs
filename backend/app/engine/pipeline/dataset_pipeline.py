"""Unified execution helpers for dataset generation flows."""

from __future__ import annotations

from typing import Any

import pandas as pd

from app.engine.context.generation_context import GenerationContext
from app.engine.dataset_generator import DatasetGenerator


class DatasetPipeline:
    """Executes generation through a single pipeline entry point."""

    @staticmethod
    def generate_dataframe(
        generator: DatasetGenerator,
        context: GenerationContext | None = None,
        *,
        attributes: list[Any] | None = None,
        row_count: int | None = None,
        realism_rules: list[dict[str, Any]] | None = None,
        semantic_rules: list[dict[str, Any]] | None = None,
    ) -> pd.DataFrame:
        if context is not None:
            return generator.generate_dataframe(context=context)

        return generator.generate_dataframe(
            attributes=attributes,
            row_count=row_count,
            realism_rules=realism_rules,
            semantic_rules=semantic_rules,
        )
