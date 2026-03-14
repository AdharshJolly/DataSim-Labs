"""Null value injection utilities."""

from __future__ import annotations

import numpy as np
import pandas as pd


def inject_nulls(
    series: pd.Series,
    null_percentage: float,
    rng: np.random.Generator,
) -> pd.Series:
    """Randomly replace an exact percentage of values with None/NaN."""
    if null_percentage <= 0:
        return series

    if null_percentage > 100:
        raise ValueError("null_percentage cannot exceed 100")

    count = len(series)
    null_count = int(round(count * (null_percentage / 100.0)))
    if null_count <= 0:
        return series

    null_indices = rng.choice(count, size=min(null_count, count), replace=False)
    result = series.copy()
    result.iloc[null_indices] = None
    return result
