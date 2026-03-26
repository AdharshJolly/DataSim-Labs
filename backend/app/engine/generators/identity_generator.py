"""Identity-aware semantic generator for linked name/email style columns."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

import numpy as np

EMAIL_DOMAINS = ["gmail.com", "yahoo.com", "outlook.com"]


def _normalize_token(value: str) -> str:
    ascii_value = (
        unicodedata.normalize("NFKD", value)
        .encode("ascii", "ignore")
        .decode("ascii")
        .lower()
    )
    cleaned = re.sub(r"[^a-z0-9]+", "", ascii_value)
    return cleaned


def _split_name(full_name: str) -> tuple[str, str]:
    parts = re.findall(r"[A-Za-z]+", full_name)
    if not parts:
        return "user", "profile"
    if len(parts) == 1:
        return parts[0], "profile"
    return parts[0], parts[-1]


def _build_email(first_name: str, last_name: str, rng: np.random.Generator) -> str:
    first = _normalize_token(first_name) or "user"
    last = _normalize_token(last_name) or "profile"

    domain = EMAIL_DOMAINS[int(rng.integers(0, len(EMAIL_DOMAINS)))]
    pattern_index = int(rng.integers(0, 3))

    if pattern_index == 0:
        username = f"{first}.{last}"
    elif pattern_index == 1:
        username = f"{first}{last}"
    else:
        username = f"{first[0]}_{last}"

    return f"{username}@{domain}"


def generate_identity_batch(
    row_count: int,
    faker: Any,
    rng: np.random.Generator,
    columns: list[str],
) -> dict[str, list[str]]:
    """Generate linked identity values for a column group.

    Supported output keys include: name, first_name, last_name, and email.
    """
    output: dict[str, list[str]] = {column: [] for column in columns}

    for _ in range(row_count):
        full_name = faker.name()
        first_name, last_name = _split_name(full_name)
        email = _build_email(first_name, last_name, rng)

        for column in columns:
            normalized = column.strip().lower()
            if normalized in {"name", "full_name", "fullname"}:
                output[column].append(full_name)
            elif normalized in {"first_name", "firstname", "given_name"}:
                output[column].append(first_name)
            elif normalized in {"last_name", "lastname", "surname"}:
                output[column].append(last_name)
            elif normalized in {"email", "e_mail", "mail"}:
                output[column].append(email)
            else:
                output[column].append(full_name)

    return output
