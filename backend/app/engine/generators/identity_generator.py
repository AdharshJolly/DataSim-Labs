"""Identity-aware semantic generator for linked name/email style columns."""

from __future__ import annotations

import logging
import re
import unicodedata
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Context-aware email domain defaults
# ---------------------------------------------------------------------------

_DOMAIN_PRESETS: dict[str, list[str]] = {
    "personal": ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com"],
    "corporate": ["company.com", "corp.net", "enterprise.org"],
    "mixed": [
        "gmail.com",
        "yahoo.com",
        "outlook.com",
        "hotmail.com",
        "company.com",
        "corp.net",
        "enterprise.org",
    ],
}


def get_default_email_domains(context: str = "personal") -> list[str]:
    """Return default email domains appropriate for *context*.

    Supported contexts: ``"personal"``, ``"corporate"``, ``"mixed"``.
    Falls back to ``"personal"`` for unknown values.
    """
    return list(_DOMAIN_PRESETS.get(context, _DOMAIN_PRESETS["personal"]))


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
    suffix: int = 0,
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

    if suffix > 0:
        username = f"{username}{suffix}"

    return f"{username}@{domain}"


def generate_identity_batch(
    row_count: int,
    faker: Any,
    rng: np.random.Generator,
    columns: list[str],
    email_domains: list[str] | None = None,
    email_domain_weights: dict[str, float] | None = None,
    column_type_map: dict[str, str] | None = None,
    email_context: str = "personal",
    unique: bool = True,
) -> dict[str, list[str]]:
    """Generate linked identity values for a column group.

    Supported output keys include: name, first_name, last_name, and email.
    """
    output: dict[str, list[str]] = {column: [] for column in columns}

    resolved_domains = [str(domain).strip().lower() for domain in (email_domains or []) if str(domain).strip()]
    if not resolved_domains:
        resolved_domains = get_default_email_domains(email_context)

    # Normalize column_type_map keys (strip + lowercase comparison) to prevent key mismatches.
    normalized_type_map: dict[str, str] = {}
    for column, semantic_type in (column_type_map or {}).items():
        if semantic_type:
            norm_key = str(column).strip()
            normalized_type_map[norm_key] = str(semantic_type).strip().lower()

    logger.debug(
        "generate_identity_batch: columns=%s, resolved_type_map=%s, domains=%s",
        columns,
        normalized_type_map,
        resolved_domains,
    )

    seen_names: set[str] = set()
    seen_emails: set[str] = set()
    seen_pairs: set[tuple[str, str]] = set()

    for _ in range(row_count):
        max_attempts = 500 if unique else 1
        full_name = ""
        first_name = ""
        last_name = ""
        email = ""

        for attempt in range(max_attempts):
            full_name = faker.name()
            first_name, last_name = _split_name(full_name)
            email = _build_email(
                first_name,
                last_name,
                rng,
                email_domains=resolved_domains,
                email_domain_weights=email_domain_weights,
                suffix=attempt,
            )

            if not unique:
                break

            normalized_name = full_name.strip().lower()
            normalized_email = email.strip().lower()
            pair = (normalized_name, normalized_email)

            if (
                normalized_name not in seen_names
                and normalized_email not in seen_emails
                and pair not in seen_pairs
            ):
                seen_names.add(normalized_name)
                seen_emails.add(normalized_email)
                seen_pairs.add(pair)
                break
        else:
            # Hard fallback to guarantee progress in high collision scenarios.
            fallback_suffix = int(rng.integers(10_000, 999_999))
            full_name = f"{full_name} {fallback_suffix}"
            email = _build_email(
                first_name,
                last_name,
                rng,
                email_domains=resolved_domains,
                email_domain_weights=email_domain_weights,
                suffix=fallback_suffix,
            )

        for column in columns:
            col_key = str(column).strip()
            semantic_type = normalized_type_map.get(col_key) or detect_semantic_type(col_key)
            if semantic_type == "name":
                output[column].append(full_name)
            elif semantic_type == "first_name":
                output[column].append(first_name)
            elif semantic_type == "last_name":
                output[column].append(last_name)
            elif semantic_type == "email":
                output[column].append(email)
            else:
                logger.warning(
                    "Column '%s' has unresolved semantic type in identity batch — "
                    "falling back to full_name. Pass column_type_map to fix this.",
                    column,
                )
                output[column].append(full_name)

    return output
