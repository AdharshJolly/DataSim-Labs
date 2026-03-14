"""Boolean column generator."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def generate_boolean(
    name: str,
    constraints: dict[str, Any],
    row_count: int,
    rng: np.random.Generator,
) -> pd.Series:
    """Generate a boolean series using true probability."""
    true_probability = float(constraints.get("true_probability", 0.5))
    true_probability = min(max(true_probability, 0.0), 1.0)
    values = rng.binomial(n=1, p=true_probability, size=row_count).astype(bool)
    return pd.Series(values, name=name)
