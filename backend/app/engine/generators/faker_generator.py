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


def generate_phone(name: str, row_count: int, faker_instance: Faker) -> pd.Series:
    """Generate phone numbers."""
    return pd.Series(
        [faker_instance.phone_number() for _ in range(row_count)], name=name
    )


def generate_url(name: str, row_count: int, faker_instance: Faker) -> pd.Series:
    """Generate URLs."""
    return pd.Series([faker_instance.url() for _ in range(row_count)], name=name)


def generate_company(name: str, row_count: int, faker_instance: Faker) -> pd.Series:
    """Generate company names."""
    return pd.Series([faker_instance.company() for _ in range(row_count)], name=name)


def generate_city(name: str, row_count: int, faker_instance: Faker) -> pd.Series:
    """Generate city names."""
    return pd.Series([faker_instance.city() for _ in range(row_count)], name=name)


def generate_country(name: str, row_count: int, faker_instance: Faker) -> pd.Series:
    """Generate country names."""
    return pd.Series([faker_instance.country() for _ in range(row_count)], name=name)


def generate_zip(name: str, row_count: int, faker_instance: Faker) -> pd.Series:
    """Generate postal or zip codes."""
    return pd.Series([faker_instance.postcode() for _ in range(row_count)], name=name)


def generate_gender(name: str, row_count: int, faker_instance: Faker) -> pd.Series:
    """Generate gender labels."""
    return pd.Series(
        [
            faker_instance.random_element(elements=("Male", "Female", "Other"))
            for _ in range(row_count)
        ],
        name=name,
    )
