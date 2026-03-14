"""Integer column generator."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from app.engine.distribution_engine import sample_numeric


def generate_integer(
    name: str,
    constraints: dict[str, Any],
    distribution: str,
    row_count: int,
    rng: np.random.Generator,
) -> pd.Series:
    """Generate an integer series honoring constraints and distribution."""
    minimum = int(constraints.get("min", 0))
    maximum = int(constraints.get("max", 100))
    values = sample_numeric(
        count=row_count,
        distribution=distribution,
        minimum=float(minimum),
        maximum=float(maximum),
        rng=rng,
    )
    return pd.Series(np.rint(values).astype(int), name=name)
