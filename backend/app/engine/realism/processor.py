"""
realism_processor.py

Applies a list of realism rules to a generated DataFrame.
Rules were produced by realism_planner.py and stored in config_json.
All operations are vectorised pandas where possible.
Never raises — invalid or inapplicable rules are skipped with a warning log.
"""

from __future__ import annotations

import logging
import re
import string
import unicodedata
from typing import Any

import numpy as np
import pandas as pd
from faker import Faker
from app.engine.realism.handlers.handler_map import build_handler_map

logger = logging.getLogger(__name__)

# Gender normalisation maps
_MALE_ALIASES = frozenset({"male", "m", "man", "männlich", "masculino"})
_FEMALE_ALIASES = frozenset({"female", "f", "woman", "weiblich", "femenino"})

_RULE_PHASES: dict[str, int] = {
    "sequential_id": 1,
    "name_email_alignment": 1,
    "name_gender_alignment": 1,
    "age_gate": 2,
    "mutual_exclusion": 2,
    "conditional_value": 2,
    "date_relative_to": 2,
    "credit_card_luhn": 2,
    "country_state_alignment": 3,
    "country_postal_format": 3,
    "phone_format_by_country": 3,
    "email_domain_match": 3,
    "url_from_company": 3,
    "iban_format": 3,
    "salary_band": 3,
}

_DEPARTMENT_KEYWORDS = frozenset(
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


class RealismProcessor:
    """Mutates a DataFrame in-place according to a list of realism rules."""

    def __init__(self, faker: Faker, rng: np.random.Generator) -> None:
        self.faker = faker
        self.rng = rng
        self._handler_map = build_handler_map()

    # ── Public API ─────────────────────────────────────────────────────────────

    def apply(self, df: pd.DataFrame, rules: list[dict[str, Any]]) -> pd.DataFrame:
        """Apply all rules to *df* (mutating in-place) and return it."""
        df, _ = self.apply_with_stats(df, rules)
        return df

    def apply_with_stats(
        self,
        df: pd.DataFrame,
        rules: list[dict[str, Any]],
    ) -> tuple[pd.DataFrame, dict[str, Any]]:
        """Apply rules and return both dataframe and rule impact stats."""
        rule_impacts: dict[str, int] = {}
        total_rows_affected = 0

        sorted_rules = sorted(
            rules,
            key=lambda item: _RULE_PHASES.get(str(item.get("type")), 999),
        )

        for rule in sorted_rules:
            rule_type = rule.get("type")
            try:
                handler = self._handler_map.get(str(rule_type))
                if handler is None:
                    logger.warning(
                        "Unknown rule type in processor: %r — skipping", rule_type
                    )
                    continue
                affected_rows = handler(self, df, rule)

                typed_rule = str(rule_type)
                rule_impacts[typed_rule] = rule_impacts.get(typed_rule, 0) + int(
                    affected_rows
                )
                total_rows_affected += int(affected_rows)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Rule '%s' failed during apply: %s — skipping", rule_type, exc
                )

        return df, {
            "rule_impacts": rule_impacts,
            "total_rows_affected": total_rows_affected,
            "rule_count": len(sorted_rules),
        }

    # ── Rule implementations ──────────────────────────────────────────────────

    def _apply_sequential_id(self, df: pd.DataFrame, rule: dict) -> int:
        target_col = str(rule.get("target_column", ""))
        if target_col not in df.columns:
            logger.warning(
                "sequential_id: column '%s' not in DataFrame — skipping",
                target_col,
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

    def _apply_name_gender_alignment(self, df: pd.DataFrame, rule: dict) -> int:
        name_col = rule["name_column"]
        gender_col = rule["gender_column"]

        if name_col not in df.columns or gender_col not in df.columns:
            logger.warning(
                "name_gender_alignment: column '%s' or '%s' not in DataFrame — skipping",
                name_col,
                gender_col,
            )
            return 0

        gender_norm = df[gender_col].astype(str).str.lower().str.strip()

        def _pick_name(row_gender: str) -> str | None:
            if row_gender in _MALE_ALIASES:
                return self.faker.name_male()
            if row_gender in _FEMALE_ALIASES:
                return self.faker.name_female()
            return None  # leave unchanged for non-binary / unknown

        updates = 0
        # Only update rows where gender is not null
        non_null_mask = df[gender_col].notna()
        for idx in df[non_null_mask].index:
            new_name = _pick_name(gender_norm.at[idx])
            if new_name is not None:
                df.at[idx, name_col] = new_name
                updates += 1
        return updates

    def _apply_name_email_alignment(self, df: pd.DataFrame, rule: dict) -> int:
        """Ensure each email's local part is derived from the corresponding name."""
        name_col = rule["name_column"]
        email_col = rule["email_column"]

        if name_col not in df.columns or email_col not in df.columns:
            logger.warning(
                "name_email_alignment: column '%s' or '%s' not in DataFrame — skipping",
                name_col,
                email_col,
            )
            return 0

        def _normalize(value: str) -> str:
            ascii_val = (
                unicodedata.normalize("NFKD", value)
                .encode("ascii", "ignore")
                .decode("ascii")
                .lower()
            )
            return re.sub(r"[^a-z0-9]+", "", ascii_val)

        def _name_tokens(full_name: str) -> list[str]:
            parts = re.findall(r"[A-Za-z]+", full_name)
            return [_normalize(p) for p in parts if len(p) >= 2]

        def _build_local_part(first: str, last: str) -> str:
            f = _normalize(first) or "user"
            l = _normalize(last) or "profile"
            idx = int(self.rng.integers(0, 5))
            if idx == 0:
                return f"{f}.{l}"
            if idx == 1:
                return f"{f}{l}"
            if idx == 2:
                return f"{f[0]}_{l}"
            if idx == 3:
                return f"{f}_{l[0]}"
            return f"{l}.{f}"

        updates = 0
        both_present = df[name_col].notna() & df[email_col].notna()

        for row_idx in df[both_present].index:
            name_val = str(df.at[row_idx, name_col])
            email_val = str(df.at[row_idx, email_col])

            if "@" not in email_val:
                continue

            local_part, domain = email_val.rsplit("@", 1)
            tokens = _name_tokens(name_val)

            # Check if local part already contains at least one name token.
            local_lower = local_part.lower()
            if any(tok in local_lower for tok in tokens if tok):
                continue

            # Regenerate local part from name.
            parts = re.findall(r"[A-Za-z]+", name_val)
            first = parts[0] if parts else "user"
            last = parts[-1] if len(parts) > 1 else "profile"
            new_local = _build_local_part(first, last)
            df.at[row_idx, email_col] = f"{new_local}@{domain}"
            updates += 1

        return updates

    def _apply_age_gate(self, df: pd.DataFrame, rule: dict) -> int:
        age_col = rule["age_column"]
        target_col = rule["target_column"]
        minimum_age = int(rule["minimum_age"])
        override_value = rule["override_value"]

        if age_col not in df.columns or target_col not in df.columns:
            logger.warning(
                "age_gate: column '%s' or '%s' not in DataFrame — skipping",
                age_col,
                target_col,
            )
            return 0

        numeric_age = pd.to_numeric(df[age_col], errors="coerce")
        # NaN rows are NOT triggered — only rows with a known age below the threshold
        mask = numeric_age.notna() & (numeric_age < minimum_age)

        if mask.any():
            # Cast override_value to match target column dtype if it's numeric
            target_dtype = df[target_col].dtype
            typed_override: Any = override_value
            if pd.api.types.is_integer_dtype(target_dtype):
                try:
                    typed_override = int(override_value)
                except (ValueError, TypeError):
                    pass
            elif pd.api.types.is_float_dtype(target_dtype):
                try:
                    typed_override = float(override_value)
                except (ValueError, TypeError):
                    pass

            df.loc[mask, target_col] = typed_override
            return int(mask.sum())
        return 0

    def _apply_mutual_exclusion(self, df: pd.DataFrame, rule: dict) -> int:
        primary_col = rule["primary_column"]
        primary_values = rule["primary_values"]
        secondary_col = rule["secondary_column"]
        secondary_override = rule["secondary_override"]

        if primary_col not in df.columns or secondary_col not in df.columns:
            logger.warning(
                "mutual_exclusion: column '%s' or '%s' not in DataFrame — skipping",
                primary_col,
                secondary_col,
            )
            return 0

        threshold_values = (
            primary_values if isinstance(primary_values, list) else [primary_values]
        )
        lowered = {str(item).strip().lower() for item in threshold_values}
        mask = df[primary_col].astype(str).str.strip().str.lower().isin(lowered)
        if not mask.any():
            return 0

        df.loc[mask, secondary_col] = secondary_override
        return int(mask.sum())

    def _apply_conditional_value(self, df: pd.DataFrame, rule: dict) -> int:
        source_col = rule["source_column"]
        target_col = rule["target_column"]
        condition = rule["condition"]
        threshold = rule["threshold"]
        value_when_true = rule["value_when_true"]
        value_when_false = rule["value_when_false"]

        if source_col not in df.columns or target_col not in df.columns:
            logger.warning(
                "conditional_value: column '%s' or '%s' not in DataFrame — skipping",
                source_col,
                target_col,
            )
            return 0

        source = df[source_col]
        non_null = source.notna()

        if condition == "gt":
            mask = non_null & (source > threshold)
        elif condition == "lt":
            mask = non_null & (source < threshold)
        elif condition == "eq":
            mask = non_null & (source == threshold)
        elif condition == "gte":
            mask = non_null & (source >= threshold)
        elif condition == "lte":
            mask = non_null & (source <= threshold)
        elif condition == "in":
            if not isinstance(threshold, list):
                logger.warning(
                    "conditional_value 'in' requires threshold to be a list — skipping"
                )
                return 0
            mask = non_null & source.isin(threshold)
        else:
            logger.warning(
                "conditional_value: unknown condition '%s' — skipping", condition
            )
            return 0

        df.loc[mask, target_col] = value_when_true
        df.loc[~mask & non_null, target_col] = value_when_false
        return int(non_null.sum())

    def _apply_country_state_alignment(self, df: pd.DataFrame, rule: dict) -> int:
        country_col = rule["country_column"]
        state_col = rule["state_column"]
        state_by_country = rule["state_by_country"]

        if country_col not in df.columns or state_col not in df.columns:
            logger.warning(
                "country_state_alignment: column '%s' or '%s' not in DataFrame — skipping",
                country_col,
                state_col,
            )
            return 0

        normalized_mapping: dict[str, list[str]] = {}
        for country, states in state_by_country.items():
            if not isinstance(country, str) or not isinstance(states, list):
                continue
            valid_states = [
                str(state) for state in states if isinstance(state, str) and state
            ]
            if valid_states:
                normalized_mapping[country.strip().lower()] = valid_states

        if not normalized_mapping:
            return 0

        updates = 0
        for idx in df.index:
            country = df.at[idx, country_col]
            state = df.at[idx, state_col]
            if pd.isna(country):
                continue

            allowed = normalized_mapping.get(str(country).strip().lower())
            if not allowed:
                continue

            allowed_lower = {item.lower() for item in allowed}
            state_text = "" if pd.isna(state) else str(state).strip().lower()
            if state_text not in allowed_lower:
                df.at[idx, state_col] = allowed[0]
                updates += 1

        return updates

    def _apply_date_relative_to(self, df: pd.DataFrame, rule: dict) -> int:
        source_col = rule.get("source_column")
        target_col = rule.get("target_column")
        relation = str(rule.get("relation", "after")).strip().lower()

        if source_col not in df.columns or target_col not in df.columns:
            logger.warning(
                "date_relative_to: column '%s' or '%s' not in DataFrame — skipping",
                source_col,
                target_col,
            )
            return 0

        if relation not in {"after", "before", "same_day"}:
            logger.warning(
                "date_relative_to: unsupported relation '%s' — skipping",
                relation,
            )
            return 0

        min_offset_days = max(0, int(rule.get("min_offset_days", 0)))
        max_offset_days = max(min_offset_days, int(rule.get("max_offset_days", 365)))

        source_series = pd.to_datetime(df[source_col], errors="coerce")
        target_series = pd.to_datetime(df[target_col], errors="coerce")

        updates = 0
        for idx in df.index:
            src_val = source_series.at[idx]
            tgt_val = target_series.at[idx]
            if pd.isna(src_val) or pd.isna(tgt_val):
                continue

            if relation == "same_day":
                if pd.Timestamp(tgt_val).date() != pd.Timestamp(src_val).date():
                    df.at[idx, target_col] = pd.Timestamp(src_val).normalize()
                    updates += 1
                continue

            random_offset_days = int(
                self.rng.integers(min_offset_days, max_offset_days + 1)
            )
            offset = pd.Timedelta(days=random_offset_days)

            if relation == "after":
                min_allowed = pd.Timestamp(src_val) + pd.Timedelta(days=min_offset_days)
                max_allowed = pd.Timestamp(src_val) + pd.Timedelta(days=max_offset_days)
                if (
                    pd.Timestamp(tgt_val) < min_allowed
                    or pd.Timestamp(tgt_val) > max_allowed
                ):
                    df.at[idx, target_col] = pd.Timestamp(src_val) + offset
                    updates += 1
                continue

            # relation == "before"
            min_allowed = pd.Timestamp(src_val) - pd.Timedelta(days=max_offset_days)
            max_allowed = pd.Timestamp(src_val) - pd.Timedelta(days=min_offset_days)
            if (
                pd.Timestamp(tgt_val) < min_allowed
                or pd.Timestamp(tgt_val) > max_allowed
            ):
                df.at[idx, target_col] = pd.Timestamp(src_val) - offset
                updates += 1

        return updates

    def _apply_country_postal_format(self, df: pd.DataFrame, rule: dict) -> int:
        country_col = rule["country_column"]
        postal_col = rule["postal_column"]

        if country_col not in df.columns or postal_col not in df.columns:
            logger.warning(
                "country_postal_format: column '%s' or '%s' not in DataFrame — skipping",
                country_col,
                postal_col,
            )
            return 0

        updates = 0
        for idx in df.index:
            country = df.at[idx, country_col]
            if pd.isna(country):
                continue
            normalized_country = str(country).strip().lower()
            current = (
                ""
                if pd.isna(df.at[idx, postal_col])
                else str(df.at[idx, postal_col]).strip()
            )
            replacement = self._postal_for_country(normalized_country)

            if not replacement:
                continue
            if current != replacement:
                df.at[idx, postal_col] = replacement
                updates += 1

        return updates

    def _apply_phone_format_by_country(self, df: pd.DataFrame, rule: dict) -> int:
        country_col = rule["country_column"]
        phone_col = rule["phone_column"]

        if country_col not in df.columns or phone_col not in df.columns:
            logger.warning(
                "phone_format_by_country: column '%s' or '%s' not in DataFrame — skipping",
                country_col,
                phone_col,
            )
            return 0

        updates = 0
        for idx in df.index:
            country = df.at[idx, country_col]
            if pd.isna(country):
                continue

            phone_value = self._phone_for_country(str(country).strip().lower())
            if not phone_value:
                continue
            if str(df.at[idx, phone_col]) != phone_value:
                df.at[idx, phone_col] = phone_value
                updates += 1

        return updates

    def _apply_credit_card_luhn(self, df: pd.DataFrame, rule: dict) -> int:
        card_col = rule["card_column"]
        if card_col not in df.columns:
            logger.warning(
                "credit_card_luhn: column '%s' not in DataFrame — skipping",
                card_col,
            )
            return 0

        length = max(12, min(19, int(rule.get("length", 16))))
        prefix = "".join(ch for ch in str(rule.get("prefix", "4")) if ch.isdigit())
        prefix = prefix or "4"

        updates = 0
        for idx in df.index:
            card_number = self._generate_luhn_number(length=length, prefix=prefix)
            if str(df.at[idx, card_col]) != card_number:
                df.at[idx, card_col] = card_number
                updates += 1
        return updates

    def _apply_email_domain_match(self, df: pd.DataFrame, rule: dict) -> int:
        email_col = rule["email_column"]
        org_col = rule["org_column"]

        if email_col not in df.columns or org_col not in df.columns:
            logger.warning(
                "email_domain_match: column '%s' or '%s' not in DataFrame — skipping",
                email_col,
                org_col,
            )
            return 0

        # Validate that org_col is actually an organization-type column, not a
        # department / team / categorical field with a handful of distinct values.
        org_values = df[org_col].dropna().astype(str).str.strip().str.lower()
        unique_org_values = set(org_values.unique())
        if len(unique_org_values) <= 15:
            dept_overlap = unique_org_values & _DEPARTMENT_KEYWORDS
            if dept_overlap:
                logger.warning(
                    "email_domain_match: org column '%s' appears to be a department "
                    "(matched keywords: %s), not a company name — skipping rule.",
                    org_col,
                    dept_overlap,
                )
                return 0

        both_present = df[email_col].notna() & df[org_col].notna()

        def _make_domain(org: str) -> str:
            cleaned = org.lower().strip()
            # Remove non-alphanumeric except hyphens and spaces
            cleaned = re.sub(r"[^a-z0-9\s-]", "", cleaned)
            # Replace spaces with hyphens
            cleaned = re.sub(r"\s+", "-", cleaned)
            # Collapse multiple hyphens
            cleaned = re.sub(r"-{2,}", "-", cleaned)
            cleaned = cleaned.strip("-")
            return f"{cleaned}.com" if cleaned else "example.com"

        def _replace_domain(row: pd.Series) -> str:
            email = str(row[email_col])
            org = str(row[org_col])
            if "@" not in email:
                return email
            local_part = email.rsplit("@", 1)[0]
            return f"{local_part}@{_make_domain(org)}"

        df.loc[both_present, email_col] = df[both_present].apply(
            _replace_domain, axis=1
        )
        return int(both_present.sum())

    def _apply_salary_band(self, df: pd.DataFrame, rule: dict) -> int:
        job_col = rule["job_column"]
        salary_col = rule["salary_column"]
        bands: dict[str, list[float]] = rule["bands"]

        if job_col not in df.columns or salary_col not in df.columns:
            logger.warning(
                "salary_band: column '%s' or '%s' not in DataFrame — skipping",
                job_col,
                salary_col,
            )
            return 0

        default_band = bands.get("default")

        updates = 0
        for idx in df.index:
            job_value = df.at[idx, job_col]
            if pd.isna(job_value):
                continue

            band = bands.get(str(job_value))
            if band is None:
                band = default_band
            if band is None:
                continue  # No band and no default → leave unchanged

            try:
                lo, hi = float(band[0]), float(band[1])
            except (IndexError, TypeError, ValueError):
                logger.warning(
                    "salary_band: invalid band for job '%s' — skipping row", job_value
                )
                continue

            if lo > hi:
                lo, hi = hi, lo

            df.at[idx, salary_col] = round(float(self.rng.uniform(lo, hi)), 2)
            updates += 1

        return updates

    def _apply_url_from_company(self, df: pd.DataFrame, rule: dict) -> int:
        url_col = rule["url_column"]
        company_col = rule["company_column"]
        protocol = str(rule.get("protocol", "https")).lower()
        include_www = bool(rule.get("include_www", True))

        if url_col not in df.columns or company_col not in df.columns:
            logger.warning(
                "url_from_company: column '%s' or '%s' not in DataFrame — skipping",
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

            slug = self._slugify_company(str(company))
            if not slug:
                continue
            host = f"www.{slug}.com" if include_www else f"{slug}.com"
            url = f"{protocol}://{host}"
            if str(df.at[idx, url_col]) != url:
                df.at[idx, url_col] = url
                updates += 1

        return updates

    def _apply_iban_format(self, df: pd.DataFrame, rule: dict) -> int:
        country_col = rule["country_column"]
        iban_col = rule["iban_column"]

        if country_col not in df.columns or iban_col not in df.columns:
            logger.warning(
                "iban_format: column '%s' or '%s' not in DataFrame — skipping",
                country_col,
                iban_col,
            )
            return 0

        updates = 0
        for idx in df.index:
            country = df.at[idx, country_col]
            if pd.isna(country):
                continue

            country_code = self._country_to_iban_code(str(country).strip().lower())
            if not country_code:
                continue

            iban_value = self._generate_country_iban(country_code)
            if str(df.at[idx, iban_col]) != iban_value:
                df.at[idx, iban_col] = iban_value
                updates += 1

        return updates

    def _postal_for_country(self, normalized_country: str) -> str:
        if normalized_country in {"india", "in"}:
            return "".join(str(digit) for digit in self.rng.integers(0, 10, size=6))
        if normalized_country in {"united states", "usa", "us"}:
            return "".join(str(digit) for digit in self.rng.integers(0, 10, size=5))
        if normalized_country in {"australia", "au"}:
            return "".join(str(digit) for digit in self.rng.integers(0, 10, size=4))
        if normalized_country in {"canada", "ca"}:
            letters = "".join(self.rng.choice(list(string.ascii_uppercase), size=3))
            digits = "".join(str(digit) for digit in self.rng.integers(0, 10, size=3))
            return (
                f"{letters[0]}{digits[0]}{letters[1]}{digits[1]}{letters[2]}{digits[2]}"
            )
        if normalized_country in {"united kingdom", "uk", "gb", "great britain"}:
            letters = "".join(self.rng.choice(list(string.ascii_uppercase), size=2))
            numbers = "".join(str(digit) for digit in self.rng.integers(0, 10, size=2))
            return f"{letters[0]}{numbers[0]}{numbers[1]} {letters[1]}{self.rng.choice(list(string.ascii_uppercase))}"
        return ""

    def _phone_for_country(self, normalized_country: str) -> str:
        if normalized_country in {"india", "in"}:
            first = int(self.rng.integers(6, 10))
            rest = "".join(str(digit) for digit in self.rng.integers(0, 10, size=9))
            return f"+91 {first}{rest[:4]} {rest[4:]}"
        if normalized_country in {"united states", "usa", "us"}:
            area = "".join(str(digit) for digit in self.rng.integers(2, 10, size=1))
            area += "".join(str(digit) for digit in self.rng.integers(0, 10, size=2))
            exchange = "".join(str(digit) for digit in self.rng.integers(2, 10, size=1))
            exchange += "".join(
                str(digit) for digit in self.rng.integers(0, 10, size=2)
            )
            line = "".join(str(digit) for digit in self.rng.integers(0, 10, size=4))
            return f"({area}) {exchange}-{line}"
        if normalized_country in {"united kingdom", "uk", "gb", "great britain"}:
            tail = "".join(str(digit) for digit in self.rng.integers(0, 10, size=9))
            return f"+44 7{tail[:3]} {tail[3:]}"
        if normalized_country in {"australia", "au"}:
            tail = "".join(str(digit) for digit in self.rng.integers(0, 10, size=8))
            return f"+61 4{tail[:2]} {tail[2:5]} {tail[5:]}"
        return ""

    def _generate_luhn_number(self, length: int = 16, prefix: str = "4") -> str:
        if length < len(prefix) + 1:
            length = len(prefix) + 1

        body_len = length - 1
        body = prefix
        if body_len > len(prefix):
            body += "".join(
                str(digit)
                for digit in self.rng.integers(0, 10, size=body_len - len(prefix))
            )

        check_digit = self._luhn_check_digit(body)
        return f"{body}{check_digit}"

    def _luhn_check_digit(self, number_without_check: str) -> str:
        digits = [int(ch) for ch in number_without_check if ch.isdigit()]
        total = 0
        parity = (len(digits) + 1) % 2
        for idx, digit in enumerate(digits):
            if idx % 2 == parity:
                doubled = digit * 2
                total += doubled - 9 if doubled > 9 else doubled
            else:
                total += digit
        return str((10 - (total % 10)) % 10)

    def _slugify_company(self, name: str) -> str:
        cleaned = (
            unicodedata.normalize("NFKD", name)
            .encode("ascii", "ignore")
            .decode("ascii")
        )
        cleaned = cleaned.lower().strip()
        cleaned = re.sub(r"[^a-z0-9\s-]", "", cleaned)
        cleaned = re.sub(r"\s+", "-", cleaned)
        cleaned = re.sub(r"-{2,}", "-", cleaned)
        return cleaned.strip("-")

    def _country_to_iban_code(self, normalized_country: str) -> str | None:
        mapping = {
            "united kingdom": "GB",
            "uk": "GB",
            "gb": "GB",
            "germany": "DE",
            "de": "DE",
            "france": "FR",
            "fr": "FR",
            "spain": "ES",
            "es": "ES",
            "italy": "IT",
            "it": "IT",
            "netherlands": "NL",
            "nl": "NL",
            "belgium": "BE",
            "be": "BE",
            "switzerland": "CH",
            "ch": "CH",
            "austria": "AT",
            "at": "AT",
            "ireland": "IE",
            "ie": "IE",
            "poland": "PL",
            "pl": "PL",
            "portugal": "PT",
            "pt": "PT",
            "turkey": "TR",
            "tr": "TR",
            "united arab emirates": "AE",
            "uae": "AE",
            "ae": "AE",
            "saudi arabia": "SA",
            "sa": "SA",
        }
        return mapping.get(normalized_country)

    def _generate_country_iban(self, country_code: str) -> str:
        iban_lengths = {
            "GB": 22,
            "DE": 22,
            "FR": 27,
            "ES": 24,
            "IT": 27,
            "NL": 18,
            "BE": 16,
            "CH": 21,
            "AT": 20,
            "IE": 22,
            "PL": 28,
            "PT": 25,
            "TR": 26,
            "AE": 23,
            "SA": 24,
        }
        length = iban_lengths.get(country_code, 22)
        bban_length = length - 4
        alphabet = list(string.ascii_uppercase + string.digits)
        bban = "".join(self.rng.choice(alphabet, size=bban_length))
        check = self._iban_check_digits(country_code=country_code, bban=bban)
        return f"{country_code}{check}{bban}"

    def _iban_check_digits(self, country_code: str, bban: str) -> str:
        rearranged = f"{bban}{country_code}00"
        numeric = ""
        for char in rearranged:
            if char.isdigit():
                numeric += char
            else:
                numeric += str(ord(char.upper()) - 55)

        remainder = 0
        for digit_char in numeric:
            remainder = (remainder * 10 + int(digit_char)) % 97

        return f"{98 - remainder:02d}"
