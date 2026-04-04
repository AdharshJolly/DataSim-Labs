"""Gemini-backed realism planner with schema-driven fallback."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from app.core.config import settings
from app.engine.realism.fallback_rules import (
    build_fallback_rules,
    build_rule_explanations,
    detect_rule_conflicts,
    fallback_result,
)
from app.engine.realism.prompts import (
    DEFAULT_GEMINI_MODEL,
    FALLBACK_GEMINI_MODELS,
    PLANNER_VERSION,
    REQUIRED_KEYS,
    SYSTEM_PROMPT,
    VALID_RULE_TYPES,
)

logger = logging.getLogger(__name__)


def _safe_attr_payload(attr: Any) -> dict[str, Any]:
    return {
        "name": str(getattr(attr, "name", "")),
        "data_type": str(getattr(attr, "data_type", "")),
        "distribution": str(getattr(attr, "distribution", "uniform")),
        "constraints": dict(getattr(attr, "constraints", {}) or {}),
        "null_percentage": float(getattr(attr, "null_percentage", 0.0) or 0.0),
    }


class RealismPlanner:
    """Calls Gemini to produce realism rules for a given attribute schema."""

    @staticmethod
    def plan(attributes: list, api_key: str) -> list[dict]:
        plan_result = RealismPlanner.plan_with_metadata(attributes, api_key)
        return plan_result["rules"]

    @staticmethod
    def plan_with_metadata(attributes: list, api_key: str) -> dict[str, Any]:
        fallback_rules = build_fallback_rules(attributes)
        generated_at = datetime.now(timezone.utc).isoformat()

        if not api_key or not api_key.strip():
            logger.warning(
                "GEMINI_API_KEY is not set - using schema-driven realism planning fallback."
            )
            return fallback_result(fallback_rules, generated_at, PLANNER_VERSION)

        if not attributes:
            return {
                "rules": [],
                "metadata": {
                    "planner_version": PLANNER_VERSION,
                    "source": "none",
                    "generated_at": generated_at,
                    "fallback_rule_count": 0,
                    "gemini_rule_count": 0,
                    "validated_rule_count": 0,
                    "rule_explanations": [],
                    "conflicts": [],
                },
            }

        user_message = (
            "Here is the dataset schema. Each item is an attribute with rich metadata.\n\n"
            + json.dumps([_safe_attr_payload(a) for a in attributes], indent=2)
            + "\n\nIdentify all applicable realism rules for this schema."
        )

        configured_model = settings.gemini_model.strip() or DEFAULT_GEMINI_MODEL
        candidate_models = list(
            dict.fromkeys([configured_model, *FALLBACK_GEMINI_MODELS])
        )

        try:
            from google import genai  # type: ignore[import-untyped]
            from google.genai import types  # type: ignore[import-untyped]
        except ImportError:
            logger.error("google-genai is not installed. Run: pip install google-genai")
            return fallback_result(fallback_rules, generated_at, PLANNER_VERSION)

        parsed: dict[str, Any] | None = None
        last_error: Exception | None = None

        client = genai.Client(api_key=api_key)
        for model_name in candidate_models:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=user_message,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        response_mime_type="application/json",
                    ),
                )
                raw_text = (response.text or "").strip()
                if raw_text.startswith("```"):
                    lines = raw_text.splitlines()
                    raw_text = "\n".join(
                        line for line in lines if not line.startswith("```")
                    ).strip()

                parsed_candidate = json.loads(raw_text)
                if not isinstance(parsed_candidate, dict):
                    raise ValueError("Gemini response JSON root is not an object")
                parsed = parsed_candidate
                if model_name != configured_model:
                    logger.warning(
                        "Gemini model fallback applied: '%s' -> '%s'",
                        configured_model,
                        model_name,
                    )
                break
            except json.JSONDecodeError as exc:
                logger.error(
                    "Gemini returned malformed JSON from '%s': %s", model_name, exc
                )
                last_error = exc
                break
            except Exception as exc:
                last_error = exc
                error_message = str(exc)
                if "404" in error_message or "not found" in error_message.lower():
                    logger.warning(
                        "Gemini model '%s' unavailable, trying fallback if available.",
                        model_name,
                    )
                    continue
                logger.error(
                    "Gemini API call failed for model '%s': %s", model_name, exc
                )
                break

        if parsed is None:
            if last_error is not None:
                logger.error(
                    "Gemini planning failed; using fallback rules. Last error: %s",
                    last_error,
                )
            return fallback_result(fallback_rules, generated_at, PLANNER_VERSION)

        raw_rules = parsed.get("rules") if isinstance(parsed, dict) else None
        if not isinstance(raw_rules, list):
            logger.warning(
                "Gemini response missing 'rules' array - using fallback rules"
            )
            return fallback_result(fallback_rules, generated_at, PLANNER_VERSION)

        column_names = {a.name for a in attributes}
        valid_rules: list[dict[str, Any]] = []

        for rule in raw_rules:
            if not isinstance(rule, dict):
                continue

            rule_type = rule.get("type")
            if rule_type not in VALID_RULE_TYPES:
                logger.debug("Skipping unknown rule type: %r", rule_type)
                continue

            required = REQUIRED_KEYS[rule_type]
            if not required.issubset(rule.keys()):
                missing = required - rule.keys()
                logger.warning(
                    "Rule '%s' is missing required keys %s - skipping",
                    rule_type,
                    missing,
                )
                continue

            if rule_type == "salary_band":
                bands = rule.get("bands")
                if not isinstance(bands, dict) or not bands:
                    logger.warning(
                        "salary_band rule has invalid 'bands' payload - skipping"
                    )
                    continue

                invalid_band = False
                for _, band in bands.items():
                    if not isinstance(band, list) or len(band) != 2:
                        invalid_band = True
                        break
                    if not all(isinstance(value, (int, float)) for value in band):
                        invalid_band = True
                        break

                if invalid_band:
                    logger.warning(
                        "salary_band rule has invalid band values - skipping"
                    )
                    continue

            if rule_type == "country_state_alignment":
                state_by_country = rule.get("state_by_country")
                if not isinstance(state_by_country, dict) or not state_by_country:
                    logger.warning(
                        "country_state_alignment has invalid mapping - skipping"
                    )
                    continue

            if rule_type == "mutual_exclusion":
                primary_values = rule.get("primary_values")
                if not isinstance(primary_values, list) or not primary_values:
                    logger.warning("mutual_exclusion requires non-empty primary_values")
                    continue

            if rule_type == "date_relative_to":
                relation = str(rule.get("relation", "")).strip().lower()
                if relation not in {"after", "before", "same_day"}:
                    logger.warning(
                        "date_relative_to requires relation in {after,before,same_day}"
                    )
                    continue

                min_offset_days = rule.get("min_offset_days", 0)
                max_offset_days = rule.get("max_offset_days", 365)
                try:
                    min_offset_int = int(min_offset_days)
                    max_offset_int = int(max_offset_days)
                except (TypeError, ValueError):
                    logger.warning(
                        "date_relative_to offsets must be integers - skipping"
                    )
                    continue

                if min_offset_int < 0 or max_offset_int < 0:
                    logger.warning(
                        "date_relative_to offsets must be non-negative - skipping"
                    )
                    continue

                if max_offset_int < min_offset_int:
                    logger.warning(
                        "date_relative_to max_offset_days cannot be below min_offset_days - skipping"
                    )
                    continue

                rule["relation"] = relation
                rule["min_offset_days"] = min_offset_int
                rule["max_offset_days"] = max_offset_int

            if rule_type == "credit_card_luhn":
                length = rule.get("length", 16)
                try:
                    length_int = int(length)
                except (TypeError, ValueError):
                    logger.warning("credit_card_luhn length must be an integer")
                    continue
                if length_int < 12 or length_int > 19:
                    logger.warning("credit_card_luhn length must be between 12 and 19")
                    continue
                rule["length"] = length_int
                prefix = str(rule.get("prefix", "4"))
                rule["prefix"] = "".join(ch for ch in prefix if ch.isdigit()) or "4"

            if rule_type == "sequential_id":
                try:
                    start_int = int(rule.get("start", 1))
                    padding_int = int(rule.get("padding", 6))
                except (TypeError, ValueError):
                    logger.warning("sequential_id start/padding must be integers")
                    continue
                if padding_int < 1 or padding_int > 16:
                    logger.warning("sequential_id padding must be between 1 and 16")
                    continue
                if start_int < 0:
                    logger.warning("sequential_id start must be >= 0")
                    continue
                rule["start"] = start_int
                rule["padding"] = padding_int
                rule["prefix"] = str(rule.get("prefix", "ID"))
                rule["separator"] = str(rule.get("separator", ""))

            if rule_type == "url_from_company":
                protocol = str(rule.get("protocol", "https")).strip().lower()
                if protocol not in {"http", "https"}:
                    protocol = "https"
                rule["protocol"] = protocol
                rule["include_www"] = bool(rule.get("include_www", True))

            referenced_columns: set[str] = set()
            for key in (
                "name_column",
                "gender_column",
                "age_column",
                "target_column",
                "source_column",
                "email_column",
                "org_column",
                "job_column",
                "salary_column",
                "country_column",
                "state_column",
                "postal_column",
                "primary_column",
                "secondary_column",
                "phone_column",
                "card_column",
                "url_column",
                "company_column",
                "iban_column",
            ):
                if key in rule and isinstance(rule[key], str):
                    referenced_columns.add(rule[key])

            unknown = referenced_columns - column_names
            if unknown:
                logger.warning(
                    "Rule '%s' references columns not in schema: %s - skipping",
                    rule_type,
                    unknown,
                )
                continue

            valid_rules.append(rule)

        if valid_rules:
            logger.info(
                "Realism planner: %d/%d Gemini rules validated and accepted",
                len(valid_rules),
                len(raw_rules),
            )
            rule_explanations = build_rule_explanations(valid_rules, source="gemini")
            conflicts = detect_rule_conflicts(valid_rules)
            return {
                "rules": valid_rules,
                "metadata": {
                    "planner_version": PLANNER_VERSION,
                    "source": "gemini",
                    "generated_at": generated_at,
                    "fallback_rule_count": len(fallback_rules),
                    "gemini_rule_count": len(raw_rules),
                    "validated_rule_count": len(valid_rules),
                    "rule_explanations": rule_explanations,
                    "conflicts": conflicts,
                },
            }

        logger.info(
            "Realism planner: Gemini returned no usable rules; using %d fallback rule(s)",
            len(fallback_rules),
        )
        return {
            "rules": fallback_rules,
            "metadata": {
                "planner_version": PLANNER_VERSION,
                "source": "fallback",
                "generated_at": generated_at,
                "fallback_rule_count": len(fallback_rules),
                "gemini_rule_count": len(raw_rules),
                "validated_rule_count": 0,
                "rule_explanations": build_rule_explanations(
                    fallback_rules,
                    source="fallback",
                ),
                "conflicts": detect_rule_conflicts(fallback_rules),
            },
        }
