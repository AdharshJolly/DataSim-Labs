"""Float column generator."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from app.engine.distribution_engine import sample_numeric


def generate_float(
    name: str,
    constraints: dict[str, Any],
    distribution: str,
    row_count: int,
    rng: np.random.Generator,
) -> pd.Series:
    """Generate a float series honoring constraints and distribution."""
    minimum = float(constraints.get("min", 0.0))
    maximum = float(constraints.get("max", 1000.0))
    precision = int(constraints.get("precision", 2))

    skew_direction = str(constraints.get("skew_direction", "right"))
    skew_intensity = float(constraints.get("skew_intensity", 2.0))

    values = sample_numeric(
        count=row_count,
        distribution=distribution,
        minimum=minimum,
        maximum=maximum,
        rng=rng,
        skew_direction=skew_direction,
        skew_intensity=skew_intensity,
    )
    return pd.Series(np.round(values, precision), name=name)
