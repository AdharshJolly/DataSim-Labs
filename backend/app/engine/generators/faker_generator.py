"""Faker-backed specialized generators."""

from __future__ import annotations

import re
import unicodedata

import numpy as np
import pandas as pd
from faker import Faker


def _normalize_token(value: str) -> str:
    """Lowercase ASCII-only token from an arbitrary Unicode string."""
    ascii_value = (
        unicodedata.normalize("NFKD", value)
        .encode("ascii", "ignore")
        .decode("ascii")
        .lower()
    )
    return re.sub(r"[^a-z0-9]+", "", ascii_value)


def _split_name(full_name: str) -> tuple[str, str]:
    """Split a full name into (first, last) tokens."""
    parts = re.findall(r"[A-Za-z]+", full_name)
    if not parts:
        return "user", "profile"
    if len(parts) == 1:
        return parts[0], "profile"
    return parts[0], parts[-1]


_DEFAULT_DOMAINS = ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com"]


def generate_email_from_name(
    col_name: str,
    names: pd.Series,
    rng: np.random.Generator,
    observed_domains: list[str] | None = None,
) -> pd.Series:
    """Derive email addresses from an already-generated name column.

    Each email local-part is built from the person's name tokens, making it
    consistent with the name in the same row.
    """
    domains = [d.strip().lower() for d in (observed_domains or []) if d.strip()]
    if not domains:
        domains = list(_DEFAULT_DOMAINS)

    results: list[str] = []
    for raw_name in names:
        name_str = str(raw_name) if not pd.isna(raw_name) else "User Profile"
        first, last = _split_name(name_str)
        first = _normalize_token(first) or "user"
        last = _normalize_token(last) or "profile"

        domain = domains[int(rng.integers(0, len(domains)))]
        pattern_index = int(rng.integers(0, 5))

        if pattern_index == 0:
            username = f"{first}.{last}"
        elif pattern_index == 1:
            username = f"{first}{last}"
        elif pattern_index == 2:
            username = f"{first[0]}_{last}"
        elif pattern_index == 3:
            username = f"{first}_{last[0]}"
        else:
            username = f"{last}.{first}"

        results.append(f"{username}@{domain}")

    return pd.Series(results, name=col_name)


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
