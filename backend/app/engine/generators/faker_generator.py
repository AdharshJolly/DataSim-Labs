"""Faker-backed specialized generators."""

from __future__ import annotations

import pandas as pd
from faker import Faker


def generate_email(name: str, row_count: int, faker_instance: Faker) -> pd.Series:
    """Generate email addresses."""
    return pd.Series([faker_instance.email() for _ in range(row_count)], name=name)


def generate_name(name: str, row_count: int, faker_instance: Faker) -> pd.Series:
    """Generate person names."""
    return pd.Series([faker_instance.name() for _ in range(row_count)], name=name)


def generate_address(name: str, row_count: int, faker_instance: Faker) -> pd.Series:
    """Generate addresses as single-line strings."""
    return pd.Series(
        [faker_instance.address().replace("\n", ", ") for _ in range(row_count)],
        name=name,
    )
