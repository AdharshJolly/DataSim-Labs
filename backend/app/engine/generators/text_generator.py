"""Generic text column generator."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from faker import Faker


def generate_text(
    name: str,
    constraints: dict[str, Any],
    row_count: int,
    rng: np.random.Generator,
    faker_instance: Faker,
) -> pd.Series:
    """Generate free-form text snippets with configurable max length."""
    max_length = int(constraints.get("max_length", 64))
    max_length = max(max_length, 8)

    values = []
    for _ in range(row_count):
        sentence = faker_instance.sentence(nb_words=int(rng.integers(4, 10)))
        values.append(sentence[:max_length])

    return pd.Series(values, name=name)
