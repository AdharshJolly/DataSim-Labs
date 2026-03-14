"""Categorical column generator."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from app.engine.distribution_engine import sample_weighted_categories


def generate_categorical(
    name: str,
    constraints: dict[str, Any],
    row_count: int,
    rng: np.random.Generator,
) -> pd.Series:
    """Generate a categorical series using uniform or weighted sampling."""
    categories = constraints.get("categories", [])
    if not categories:
        categories = ["A", "B", "C"]

    weights = constraints.get("weights")
    values = sample_weighted_categories(
        categories=list(categories),
        weights=list(weights) if isinstance(weights, list) else None,
        count=row_count,
        rng=rng,
    )
    return pd.Series(values, name=name)
