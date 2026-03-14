"""Distribution helpers used by per-type generators."""

from __future__ import annotations

import math
from typing import Any

import numpy as np


def sample_numeric(
    count: int,
    distribution: str,
    minimum: float,
    maximum: float,
    rng: np.random.Generator,
) -> np.ndarray:
    """Sample numeric values using supported distributions and clamp to range."""
    if minimum > maximum:
        raise ValueError("Minimum cannot be greater than maximum")

    if distribution == "normal":
        mean = (minimum + maximum) / 2
        std = max((maximum - minimum) / 6, 1e-9)
        values = rng.normal(loc=mean, scale=std, size=count)
    elif distribution == "skewed":
        beta_samples = rng.beta(a=2.0, b=5.0, size=count)
        values = minimum + beta_samples * (maximum - minimum)
    else:
        values = rng.uniform(low=minimum, high=maximum, size=count)

    return np.clip(values, minimum, maximum)


def sample_weighted_categories(
    categories: list[Any],
    weights: list[float] | None,
    count: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """Sample categorical values with optional normalized weights."""
    if not categories:
        raise ValueError("Categorical generator requires at least one category")

    if weights is None or len(weights) != len(categories):
        probabilities = np.full(shape=len(categories), fill_value=1 / len(categories))
    else:
        total = math.fsum(weights)
        if total <= 0:
            raise ValueError("Categorical weights must sum to a positive value")
        probabilities = np.array(weights, dtype=float) / total

    return rng.choice(categories, size=count, p=probabilities)
