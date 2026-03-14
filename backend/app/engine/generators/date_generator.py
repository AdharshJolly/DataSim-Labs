"""Date column generator."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

from app.engine.distribution_engine import sample_numeric


def _parse_date(value: str, fallback: datetime) -> datetime:
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return fallback


def generate_date(
    name: str,
    constraints: dict[str, Any],
    distribution: str,
    row_count: int,
    rng: np.random.Generator,
) -> pd.Series:
    """Generate a date/datetime series between start_date and end_date."""
    start = _parse_date(
        str(constraints.get("start_date", "2020-01-01")), datetime(2020, 1, 1)
    )
    end = _parse_date(
        str(constraints.get("end_date", "2025-12-31")), datetime(2025, 12, 31)
    )

    min_ts = start.timestamp()
    max_ts = end.timestamp()

    sampled_ts = sample_numeric(
        count=row_count,
        distribution=distribution,
        minimum=min(min_ts, max_ts),
        maximum=max(min_ts, max_ts),
        rng=rng,
    )
    values = pd.to_datetime(sampled_ts, unit="s").date
    return pd.Series(values, name=name)
