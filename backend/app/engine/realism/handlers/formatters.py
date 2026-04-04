"""Formatting-related realism rule handlers."""

from __future__ import annotations

import logging
import re
from typing import Any, Protocol

import pandas as pd

logger = logging.getLogger(__name__)

DEPARTMENT_KEYWORDS = frozenset(
    {
        "tech",
        "hr",
        "human resources",
        "marketing",
        "sales",
        "engineering",
        "finance",
        "legal",
        "operations",
        "support",
        "design",
        "product",
        "research",
        "it",
        "admin",
        "management",
        "accounting",
        "logistics",
        "customer service",
    }
)


class _FormatterProcessorLike(Protocol):
    def _slugify_company(self, name: str) -> str: ...


def apply_sequential_id(df: pd.DataFrame, rule: dict[str, Any]) -> int:
    target_col = str(rule.get("target_column", ""))
    if target_col not in df.columns:
        logger.warning(
            "sequential_id: column '%s' not in DataFrame - skipping", target_col
        )
        return 0

    prefix = str(rule.get("prefix", "ID"))
    separator = str(rule.get("separator", ""))
    start = int(rule.get("start", 1))
    padding = max(1, int(rule.get("padding", 6)))

    updates = 0
    for offset, idx in enumerate(df.index):
        sequence = start + offset
        value = f"{prefix}{separator}{sequence:0{padding}d}"
        if df.at[idx, target_col] != value:
            df.at[idx, target_col] = value
            updates += 1
    return updates


def apply_email_domain_match(df: pd.DataFrame, rule: dict[str, Any]) -> int:
    email_col = rule["email_column"]
    org_col = rule["org_column"]

    if email_col not in df.columns or org_col not in df.columns:
        logger.warning(
            "email_domain_match: column '%s' or '%s' not in DataFrame - skipping",
            email_col,
            org_col,
        )
        return 0

    org_values = df[org_col].dropna().astype(str).str.strip().str.lower()
    unique_org_values = set(org_values.unique())
    if len(unique_org_values) <= 15:
        dept_overlap = unique_org_values & DEPARTMENT_KEYWORDS
        if dept_overlap:
            logger.warning(
                "email_domain_match: org column '%s' appears to be a department (matched keywords: %s), not a company name - skipping rule.",
                org_col,
                dept_overlap,
            )
            return 0

    both_present = df[email_col].notna() & df[org_col].notna()

    def make_domain(org: str) -> str:
        cleaned = org.lower().strip()
        cleaned = re.sub(r"[^a-z0-9\s-]", "", cleaned)
        cleaned = re.sub(r"\s+", "-", cleaned)
        cleaned = re.sub(r"-{2,}", "-", cleaned)
        cleaned = cleaned.strip("-")
        return f"{cleaned}.com" if cleaned else "example.com"

    def replace_domain(row: pd.Series) -> str:
        email = str(row[email_col])
        org = str(row[org_col])
        if "@" not in email:
            return email
        local_part = email.rsplit("@", 1)[0]
        return f"{local_part}@{make_domain(org)}"

    df.loc[both_present, email_col] = df[both_present].apply(replace_domain, axis=1)
    return int(both_present.sum())


def apply_url_from_company(
    processor: _FormatterProcessorLike,
    df: pd.DataFrame,
    rule: dict[str, Any],
) -> int:
    url_col = rule["url_column"]
    company_col = rule["company_column"]
    protocol = str(rule.get("protocol", "https")).lower()
    include_www = bool(rule.get("include_www", True))

    if url_col not in df.columns or company_col not in df.columns:
        logger.warning(
            "url_from_company: column '%s' or '%s' not in DataFrame - skipping",
            url_col,
            company_col,
        )
        return 0

    if protocol not in {"http", "https"}:
        protocol = "https"

    updates = 0
    for idx in df.index:
        company = df.at[idx, company_col]
        if pd.isna(company):
            continue

        slug = processor._slugify_company(str(company))
        if not slug:
            continue
        host = f"www.{slug}.com" if include_www else f"{slug}.com"
        url = f"{protocol}://{host}"
        if str(df.at[idx, url_col]) != url:
            df.at[idx, url_col] = url
            updates += 1

    return updates
