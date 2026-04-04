"""Centralized realism rule handler map."""

from __future__ import annotations

from typing import Any, Callable, Protocol

import pandas as pd

from app.engine.realism.handlers.conditional import (
    apply_age_gate,
    apply_conditional_value,
    apply_date_relative_to,
    apply_mutual_exclusion,
)
from app.engine.realism.handlers.financial import (
    apply_credit_card_luhn,
    apply_salary_band,
)
from app.engine.realism.handlers.formatters import (
    apply_email_domain_match,
    apply_sequential_id,
    apply_url_from_company,
)
from app.engine.realism.handlers.geography import (
    apply_country_postal_format,
    apply_country_state_alignment,
    apply_iban_format,
    apply_phone_format_by_country,
)
from app.engine.realism.handlers.identity import (
    apply_name_email_alignment,
    apply_name_gender_alignment,
)


class _ProcessorLike(Protocol):
    pass


RuleHandler = Callable[[_ProcessorLike, pd.DataFrame, dict[str, Any]], int]


def _static(handler: Callable[[pd.DataFrame, dict[str, Any]], int]) -> RuleHandler:
    return lambda _processor, df, rule: handler(df, rule)


def build_handler_map() -> dict[str, RuleHandler]:
    return {
        "sequential_id": _static(apply_sequential_id),
        "name_gender_alignment": apply_name_gender_alignment,
        "name_email_alignment": apply_name_email_alignment,
        "age_gate": _static(apply_age_gate),
        "mutual_exclusion": _static(apply_mutual_exclusion),
        "conditional_value": _static(apply_conditional_value),
        "date_relative_to": apply_date_relative_to,
        "credit_card_luhn": apply_credit_card_luhn,
        "country_state_alignment": _static(apply_country_state_alignment),
        "country_postal_format": apply_country_postal_format,
        "phone_format_by_country": apply_phone_format_by_country,
        "email_domain_match": _static(apply_email_domain_match),
        "url_from_company": apply_url_from_company,
        "iban_format": apply_iban_format,
        "salary_band": apply_salary_band,
    }
