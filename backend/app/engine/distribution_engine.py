"""Distribution helpers used by per-type generators."""

from __future__ import annotations

import math
from typing import Any

import numpy as np
from scipy.stats import truncnorm


def sample_numeric(
    count: int,
    distribution: str,
    minimum: float,
    maximum: float,
    rng: np.random.Generator,
    *,
    skew_direction: str = "right",
    skew_intensity: float = 2.0,
) -> np.ndarray:
    """Sample numeric values using supported distributions within [minimum, maximum]."""
    if minimum > maximum:
        raise ValueError("Minimum cannot be greater than maximum")

    if distribution == "normal":
        mean = (minimum + maximum) / 2
        std = max((maximum - minimum) / 6, 1e-9)
        a_bound = (minimum - mean) / std
        b_bound = (maximum - mean) / std
        values = truncnorm.rvs(
            a_bound,
            b_bound,
            loc=mean,
            scale=std,
            size=count,
            random_state=rng,
        )
    elif distribution == "skewed":
        intensity = max(float(skew_intensity), 0.1)
        if skew_direction == "left":
            a_param = intensity * 2.5
            b_param = intensity
        else:
            a_param = intensity
            b_param = intensity * 2.5
        beta_samples = rng.beta(a=a_param, b=b_param, size=count)
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
