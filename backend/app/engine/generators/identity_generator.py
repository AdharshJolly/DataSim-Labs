"""Identity-aware semantic generator for linked name/email style columns."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

import numpy as np

EMAIL_DOMAINS = ["gmail.com", "yahoo.com", "outlook.com"]


def detect_semantic_type(column_name: str | None) -> str | None:
    """Infer semantic type from a column name using flexible heuristics."""
    if not column_name:
        return None

    normalized = re.sub(r"[^a-z0-9]+", "_", str(column_name).strip().lower())
    compact = normalized.replace("_", "")

    def has_any(patterns: list[str]) -> bool:
        return any(pattern in normalized or pattern in compact for pattern in patterns)

    if has_any(["email", "mail", "e_mail", "emailid"]):
        return "email"
    if has_any(["first_name", "firstname", "given_name", "givenname"]):
        return "first_name"
    if has_any(["last_name", "lastname", "surname", "family_name", "familyname"]):
        return "last_name"
    if has_any(
        [
            "fullname",
            "full_name",
            "display_name",
            "username",
            "user_name",
            "person_name",
            "employee_name",
            "name",
            "person",
            "employee",
        ]
    ):
        return "name"
    return None


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


def _build_email(
    first_name: str,
    last_name: str,
    rng: np.random.Generator,
    email_domains: list[str],
    email_domain_weights: dict[str, float] | None,
) -> str:
    first = _normalize_token(first_name) or "user"
    last = _normalize_token(last_name) or "profile"

    if email_domain_weights:
        domains = [domain for domain in email_domains if domain in email_domain_weights]
        if not domains:
            domains = list(email_domains)
        weights = np.array([email_domain_weights.get(domain, 0.0) for domain in domains], dtype=float)
        if weights.sum() <= 0:
            domain = domains[int(rng.integers(0, len(domains)))]
        else:
            weights = weights / weights.sum()
            domain = str(rng.choice(domains, p=weights))
    else:
        domain = email_domains[int(rng.integers(0, len(email_domains)))]

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
    email_domains: list[str] | None = None,
    email_domain_weights: dict[str, float] | None = None,
    column_type_map: dict[str, str] | None = None,
) -> dict[str, list[str]]:
    """Generate linked identity values for a column group.

    Supported output keys include: name, first_name, last_name, and email.
    """
    output: dict[str, list[str]] = {column: [] for column in columns}

    resolved_domains = [str(domain).strip().lower() for domain in (email_domains or []) if str(domain).strip()]
    if not resolved_domains:
        resolved_domains = list(EMAIL_DOMAINS)

    normalized_type_map = {
        str(column): str(semantic_type).strip().lower()
        for column, semantic_type in (column_type_map or {}).items()
        if semantic_type
    }

    for _ in range(row_count):
        full_name = faker.name()
        first_name, last_name = _split_name(full_name)
        email = _build_email(
            first_name,
            last_name,
            rng,
            email_domains=resolved_domains,
            email_domain_weights=email_domain_weights,
        )

        for column in columns:
            semantic_type = normalized_type_map.get(column) or detect_semantic_type(column)
            if semantic_type == "name":
                output[column].append(full_name)
            elif semantic_type == "first_name":
                output[column].append(first_name)
            elif semantic_type == "last_name":
                output[column].append(last_name)
            elif semantic_type == "email":
                output[column].append(email)
            else:
                output[column].append(full_name)

    return output
