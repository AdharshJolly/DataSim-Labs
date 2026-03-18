"""
realism_planner.py

Calls Gemini once per dataset version save.
Input:  list of AttributeSpec-like objects
        (name, data_type, constraints, distribution, null_percentage)
Output: list of validated rule dicts (the realism config)

Never raises - on any failure, logs and returns schema-driven fallback rules.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

# -- Rule contract -------------------------------------------------------------

VALID_RULE_TYPES = {
    "name_gender_alignment",
    "age_gate",
    "mutual_exclusion",
    "conditional_value",
    "country_state_alignment",
    "country_postal_format",
    "email_domain_match",
    "salary_band",
}

REQUIRED_KEYS: dict[str, set[str]] = {
    "name_gender_alignment": {"name_column", "gender_column"},
    "age_gate": {"age_column", "target_column", "minimum_age", "override_value"},
    "mutual_exclusion": {
        "primary_column",
        "primary_values",
        "secondary_column",
        "secondary_override",
    },
    "conditional_value": {
        "source_column",
        "condition",
        "threshold",
        "target_column",
        "value_when_true",
        "value_when_false",
    },
    "country_state_alignment": {"country_column", "state_column", "state_by_country"},
    "country_postal_format": {"country_column", "postal_column"},
    "email_domain_match": {"email_column", "org_column"},
    "salary_band": {"job_column", "salary_column", "bands"},
}

PLANNER_VERSION = "2.1.0"

_SYSTEM_PROMPT = """\
You are a data realism expert for a synthetic dataset generator.

Given a list of dataset attributes, identify
real-world relationships between columns that would make the generated data
more realistic. Return ONLY a valid JSON object - no markdown fences, no prose,
no explanation. The JSON must have exactly one key: "rules", which is an array.

Supported rule types and their exact schemas:

1. name_gender_alignment
   Use when a name column and a gender column are both present.
   { "type": "name_gender_alignment", "name_column": "...", "gender_column": "..." }

2. age_gate
   Use when an age column and a status/lifestyle column are both present
   and there is a logical minimum age for non-default values.
   {
     "type": "age_gate",
     "age_column": "...",
     "target_column": "...",
     "minimum_age": <integer>,
     "override_value": "<the forced value when row age is below minimum_age>"
   }

3. conditional_value
   Use when the value of one column logically constrains another.
   Supported conditions: "gt", "lt", "eq", "gte", "lte", "in"
   For "in", threshold must be a list of values.
   {
     "type": "conditional_value",
     "source_column": "...",
     "condition": "gt",
     "threshold": <value or list>,
     "target_column": "...",
     "value_when_true": "<value>",
     "value_when_false": "<value>"
   }

4. mutual_exclusion
   Use when one column value should force a specific value in another column.
   {
     "type": "mutual_exclusion",
     "primary_column": "...",
     "primary_values": ["student"],
     "secondary_column": "...",
     "secondary_override": "unemployed"
   }

5. country_state_alignment
   Use when both country and state columns are present.
   {
     "type": "country_state_alignment",
     "country_column": "...",
     "state_column": "...",
     "state_by_country": {
       "India": ["Maharashtra", "Karnataka"],
       "United States": ["California", "Texas"]
     }
   }

6. country_postal_format
   Use when country and postal code columns are present.
   {
     "type": "country_postal_format",
     "country_column": "...",
     "postal_column": "..."
   }

7. email_domain_match
   Use when an email column and a company/organisation column are both present.
   { "type": "email_domain_match", "email_column": "...", "org_column": "..." }

8. salary_band
   Use when a job/role column and a numeric salary/income column are both present.
   Infer realistic salary bands per role using your knowledge of typical ranges.
   Use USD. Provide at least 3 distinct roles if the categorical values are unknown.
   {
     "type": "salary_band",
     "job_column": "...",
     "salary_column": "...",
     "bands": {
       "<role_name>": [<min_integer>, <max_integer>],
       "default": [30000, 60000]
     }
   }

Rules to follow:
- Only emit a rule if you can clearly identify both columns in the schema.
- Do not invent column names - use only the exact names from the input list.
- Use attribute constraints when useful (for example, categories for role/status).
- Prefer rule values that are valid with the provided constraints.
- If no rules apply, return { "rules": [] }.
- Never include a rule type not listed above.
- The response must be parseable by Python's json.loads() with no pre-processing.
"""


def _safe_attr_payload(attr: Any) -> dict[str, Any]:
    """Build a JSON-serializable payload for one attribute."""
    return {
        "name": str(getattr(attr, "name", "")),
        "data_type": str(getattr(attr, "data_type", "")),
        "distribution": str(getattr(attr, "distribution", "uniform")),
        "constraints": dict(getattr(attr, "constraints", {}) or {}),
        "null_percentage": float(getattr(attr, "null_percentage", 0.0) or 0.0),
    }


def _keyword_match(name: str, keywords: set[str]) -> bool:
    lowered = name.lower()
    return any(keyword in lowered for keyword in keywords)


def _find_first_column(
    attributes: list[Any],
    keywords: set[str],
    allowed_types: set[str] | None = None,
) -> str | None:
    for attr in attributes:
        name = str(getattr(attr, "name", ""))
        data_type = str(getattr(attr, "data_type", "")).lower()
        if not name:
            continue
        if allowed_types and data_type not in allowed_types:
            continue
        if _keyword_match(name, keywords):
            return name
    return None


def _find_first_attribute(
    attributes: list[Any],
    keywords: set[str],
    allowed_types: set[str] | None = None,
) -> Any | None:
    for attr in attributes:
        name = str(getattr(attr, "name", ""))
        data_type = str(getattr(attr, "data_type", "")).lower()
        if not name:
            continue
        if allowed_types and data_type not in allowed_types:
            continue
        if _keyword_match(name, keywords):
            return attr
    return None


def _infer_salary_band_for_role(role_name: str) -> tuple[int, int]:
    """Infer a practical salary range using role keywords."""
    role = role_name.lower()
    if any(token in role for token in {"intern", "trainee", "apprentice"}):
        return (15000, 30000)
    if any(token in role for token in {"junior", "associate"}):
        return (35000, 65000)
    if any(token in role for token in {"senior", "lead", "principal"}):
        return (90000, 160000)
    if any(token in role for token in {"manager", "director", "head", "vp", "chief"}):
        return (110000, 220000)
    if any(
        token in role for token in {"engineer", "developer", "scientist", "analyst"}
    ):
        return (70000, 140000)
    if any(
        token in role for token in {"teacher", "nurse", "clerk", "assistant", "support"}
    ):
        return (30000, 70000)
    return (45000, 90000)


def _default_age_gate_override(target_attr: Any) -> Any:
    """Pick an age-gate override aligned to target type/constraints."""
    data_type = str(getattr(target_attr, "data_type", "")).lower()
    constraints = dict(getattr(target_attr, "constraints", {}) or {})
    categories = constraints.get("categories")

    if data_type == "boolean":
        return False

    if data_type == "categorical" and isinstance(categories, list):
        lowered = {
            str(item).strip().lower(): str(item)
            for item in categories
            if isinstance(item, str) and item.strip()
        }
        for candidate in ("single", "unemployed", "no", "none", "false"):
            if candidate in lowered:
                return lowered[candidate]
        if categories:
            return categories[0]

    target_name = str(getattr(target_attr, "name", "")).lower()
    if "marital" in target_name:
        return "single"
    if "employ" in target_name:
        return "unemployed"
    if "license" in target_name or "licence" in target_name:
        return False
    return "none"


def _build_fallback_rules(attributes: list[Any]) -> list[dict[str, Any]]:
    """Schema-driven fallback when LLM planning is unavailable or returns no rules."""
    rules: list[dict[str, Any]] = []

    name_col = _find_first_column(
        attributes,
        keywords={"name", "full_name", "first_name", "last_name"},
        allowed_types={"name", "text", "categorical"},
    )
    gender_col = _find_first_column(
        attributes,
        keywords={"gender", "sex"},
        allowed_types={"categorical", "text"},
    )
    if name_col and gender_col:
        rules.append(
            {
                "type": "name_gender_alignment",
                "name_column": name_col,
                "gender_column": gender_col,
            }
        )

    age_attr = _find_first_attribute(
        attributes,
        keywords={"age"},
        allowed_types={"integer", "float"},
    )
    if age_attr is not None:
        age_col = str(getattr(age_attr, "name", ""))
        gate_targets = [
            (
                _find_first_attribute(
                    attributes,
                    keywords={"marital", "marriage"},
                    allowed_types={"categorical", "text"},
                ),
                18,
            ),
            (
                _find_first_attribute(
                    attributes,
                    keywords={"employ", "employment", "job_status", "work_status"},
                    allowed_types={"categorical", "text"},
                ),
                16,
            ),
            (
                _find_first_attribute(
                    attributes,
                    keywords={
                        "driving_license",
                        "driving_licence",
                        "license",
                        "licence",
                    },
                    allowed_types={"boolean", "categorical", "text"},
                ),
                16,
            ),
        ]

        for target_attr, minimum_age in gate_targets:
            if target_attr is None:
                continue
            rules.append(
                {
                    "type": "age_gate",
                    "age_column": age_col,
                    "target_column": str(getattr(target_attr, "name", "")),
                    "minimum_age": minimum_age,
                    "override_value": _default_age_gate_override(target_attr),
                }
            )

        salary_col = _find_first_column(
            attributes,
            keywords={"salary", "income", "wage", "compensation", "pay"},
            allowed_types={"integer", "float"},
        )
        if salary_col:
            rules.append(
                {
                    "type": "age_gate",
                    "age_column": age_col,
                    "target_column": salary_col,
                    "minimum_age": 16,
                    "override_value": 0,
                }
            )

    email_col = _find_first_column(
        attributes,
        keywords={"email", "mail"},
        allowed_types={"email", "text"},
    )
    org_col = _find_first_column(
        attributes,
        keywords={"company", "organization", "organisation", "org", "employer"},
        allowed_types={"categorical", "text"},
    )
    if email_col and org_col:
        rules.append(
            {
                "type": "email_domain_match",
                "email_column": email_col,
                "org_column": org_col,
            }
        )

    country_attr = _find_first_attribute(
        attributes,
        keywords={"country", "nation"},
        allowed_types={"categorical", "text"},
    )
    state_attr = _find_first_attribute(
        attributes,
        keywords={"state", "province", "region"},
        allowed_types={"categorical", "text"},
    )
    postal_col = _find_first_column(
        attributes,
        keywords={"postal", "zip", "zipcode", "postcode", "pin", "pincode"},
        allowed_types={"text", "integer", "categorical"},
    )

    if country_attr is not None and state_attr is not None:
        country_constraints = dict(getattr(country_attr, "constraints", {}) or {})
        state_constraints = dict(getattr(state_attr, "constraints", {}) or {})
        country_categories = country_constraints.get("categories")
        state_categories = state_constraints.get("categories")

        country_values = [
            str(value)
            for value in (country_categories or [])
            if isinstance(value, str) and value.strip()
        ]
        state_values = [
            str(value)
            for value in (state_categories or [])
            if isinstance(value, str) and value.strip()
        ]

        base_map: dict[str, list[str]] = {
            "India": ["Maharashtra", "Karnataka", "Tamil Nadu", "Delhi"],
            "United States": ["California", "Texas", "New York", "Florida"],
            "Canada": ["Ontario", "Quebec", "British Columbia", "Alberta"],
            "Australia": [
                "New South Wales",
                "Victoria",
                "Queensland",
                "Western Australia",
            ],
            "United Kingdom": ["England", "Scotland", "Wales", "Northern Ireland"],
        }

        selected_map: dict[str, list[str]] = {}
        for country_name, states in base_map.items():
            if country_values and country_name not in country_values:
                continue
            if state_values:
                overlap = [state for state in states if state in state_values]
                if not overlap:
                    continue
                selected_map[country_name] = overlap
            else:
                selected_map[country_name] = states

        if selected_map:
            rules.append(
                {
                    "type": "country_state_alignment",
                    "country_column": str(getattr(country_attr, "name", "")),
                    "state_column": str(getattr(state_attr, "name", "")),
                    "state_by_country": selected_map,
                }
            )

    if country_attr is not None and postal_col:
        rules.append(
            {
                "type": "country_postal_format",
                "country_column": str(getattr(country_attr, "name", "")),
                "postal_column": postal_col,
            }
        )

    student_attr = _find_first_attribute(
        attributes,
        keywords={"student", "is_student", "student_status"},
        allowed_types={"boolean", "categorical", "text"},
    )
    employment_attr = _find_first_attribute(
        attributes,
        keywords={"employment", "employ", "job_status", "work_status"},
        allowed_types={"categorical", "text", "boolean"},
    )
    if student_attr is not None and employment_attr is not None:
        primary_values: list[Any] = ["student", "yes", "true"]
        if str(getattr(student_attr, "data_type", "")).lower() == "boolean":
            primary_values = [True]

        override_value: Any = "unemployed"
        employment_constraints = dict(getattr(employment_attr, "constraints", {}) or {})
        employment_categories = employment_constraints.get("categories")
        if isinstance(employment_categories, list):
            lowered = {
                str(item).strip().lower(): str(item)
                for item in employment_categories
                if isinstance(item, str) and item.strip()
            }
            for candidate in ("unemployed", "not employed", "none", "student"):
                if candidate in lowered:
                    override_value = lowered[candidate]
                    break

        rules.append(
            {
                "type": "mutual_exclusion",
                "primary_column": str(getattr(student_attr, "name", "")),
                "primary_values": primary_values,
                "secondary_column": str(getattr(employment_attr, "name", "")),
                "secondary_override": override_value,
            }
        )

    job_attr = _find_first_attribute(
        attributes,
        keywords={"job", "role", "position", "occupation", "title"},
        allowed_types={"categorical", "text"},
    )
    salary_col = _find_first_column(
        attributes,
        keywords={"salary", "income", "wage", "compensation", "pay"},
        allowed_types={"integer", "float"},
    )
    if job_attr is not None and salary_col:
        job_constraints = dict(getattr(job_attr, "constraints", {}) or {})
        categories = job_constraints.get("categories")
        role_names = [
            str(role)
            for role in (categories or [])
            if isinstance(role, str) and role.strip()
        ]

        if not role_names:
            role_names = ["Engineer", "Manager", "Analyst"]

        bands: dict[str, list[int]] = {
            role_name: list(_infer_salary_band_for_role(role_name))
            for role_name in role_names[:20]
        }
        bands["default"] = [45000, 90000]

        rules.append(
            {
                "type": "salary_band",
                "job_column": str(getattr(job_attr, "name", "")),
                "salary_column": salary_col,
                "bands": bands,
            }
        )

    return rules


def _fallback_result(
    fallback_rules: list[dict[str, Any]], generated_at: str
) -> dict[str, Any]:
    fallback_explanations = [
        {
            "rule_index": index,
            "type": str(rule.get("type", "unknown")),
            "confidence": 0.78,
            "reason": "Schema-based fallback inferred this rule from attribute names and constraints.",
            "source": "fallback",
        }
        for index, rule in enumerate(fallback_rules)
    ]
    conflicts = _detect_rule_conflicts(fallback_rules)
    return {
        "rules": fallback_rules,
        "metadata": {
            "planner_version": PLANNER_VERSION,
            "source": "fallback",
            "generated_at": generated_at,
            "fallback_rule_count": len(fallback_rules),
            "gemini_rule_count": 0,
            "validated_rule_count": 0,
            "rule_explanations": fallback_explanations,
            "conflicts": conflicts,
        },
    }


def _build_rule_explanations(
    rules: list[dict[str, Any]],
    source: str,
) -> list[dict[str, Any]]:
    """Attach lightweight explainability metadata per rule."""
    explanations: list[dict[str, Any]] = []
    base_confidence = 0.83 if source == "gemini" else 0.78

    reason_map = {
        "name_gender_alignment": "Name and gender attributes indicate identity consistency.",
        "age_gate": "Age-dependent target field indicates eligibility threshold behavior.",
        "mutual_exclusion": "Fields imply logically incompatible states that require override rules.",
        "conditional_value": "Source field condition strongly determines target field value.",
        "country_state_alignment": "Country and state fields require geo-consistent combinations.",
        "country_postal_format": "Country field implies locale-specific postal code formatting.",
        "email_domain_match": "Email and organization fields imply domain consistency.",
        "salary_band": "Role-related field implies realistic salary range constraints.",
    }

    for index, rule in enumerate(rules):
        rule_type = str(rule.get("type", "unknown"))
        explanations.append(
            {
                "rule_index": index,
                "type": rule_type,
                "confidence": base_confidence,
                "reason": reason_map.get(
                    rule_type,
                    "Rule selected based on schema signal strength.",
                ),
                "source": source,
            }
        )

    return explanations


def _detect_rule_conflicts(rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Detect simple rule conflicts where multiple rules target same column inconsistently."""
    conflicts: list[dict[str, Any]] = []

    age_gates_by_target: dict[str, set[Any]] = {}
    for rule in rules:
        if str(rule.get("type")) != "age_gate":
            continue
        target_col = str(rule.get("target_column", "")).strip()
        override_value = rule.get("override_value")
        if not target_col:
            continue
        age_gates_by_target.setdefault(target_col, set()).add(str(override_value))

    for target_col, override_values in age_gates_by_target.items():
        if len(override_values) > 1:
            conflicts.append(
                {
                    "severity": "warning",
                    "type": "age_gate_override_conflict",
                    "target_column": target_col,
                    "details": f"Multiple override values detected: {sorted(override_values)}",
                }
            )

    mutual_by_secondary: dict[str, set[Any]] = {}
    for rule in rules:
        if str(rule.get("type")) != "mutual_exclusion":
            continue
        secondary_col = str(rule.get("secondary_column", "")).strip()
        secondary_override = rule.get("secondary_override")
        if not secondary_col:
            continue
        mutual_by_secondary.setdefault(secondary_col, set()).add(
            str(secondary_override)
        )

    for secondary_col, overrides in mutual_by_secondary.items():
        if len(overrides) > 1:
            conflicts.append(
                {
                    "severity": "warning",
                    "type": "mutual_exclusion_override_conflict",
                    "target_column": secondary_col,
                    "details": f"Multiple override values detected: {sorted(overrides)}",
                }
            )

    return conflicts


class RealismPlanner:
    """Calls Gemini to produce realism rules for a given attribute schema."""

    @staticmethod
    def plan(attributes: list, api_key: str) -> list[dict]:
        plan_result = RealismPlanner.plan_with_metadata(attributes, api_key)
        return plan_result["rules"]

    @staticmethod
    def plan_with_metadata(attributes: list, api_key: str) -> dict[str, Any]:
        """Call Gemini and return validated realism rules with planner metadata."""
        fallback_rules = _build_fallback_rules(attributes)
        generated_at = datetime.now(timezone.utc).isoformat()

        if not api_key or not api_key.strip():
            logger.warning(
                "GEMINI_API_KEY is not set - using schema-driven realism planning fallback."
            )
            return _fallback_result(fallback_rules, generated_at)

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

        try:
            import google.generativeai as genai  # type: ignore[import-untyped]
        except ImportError:
            logger.error(
                "google-generativeai is not installed. "
                "Run: pip install google-generativeai>=0.8.0"
            )
            return _fallback_result(fallback_rules, generated_at)

        user_message = (
            "Here is the dataset schema. Each item is an attribute with rich metadata.\n\n"
            + json.dumps([_safe_attr_payload(a) for a in attributes], indent=2)
            + "\n\nIdentify all applicable realism rules for this schema."
        )

        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(
                model_name="gemini-2.0-flash",
                system_instruction=_SYSTEM_PROMPT,
            )
            response = model.generate_content(user_message)
            raw_text = response.text.strip()

            if raw_text.startswith("```"):
                lines = raw_text.splitlines()
                raw_text = "\n".join(
                    line for line in lines if not line.startswith("```")
                ).strip()

            parsed = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            logger.error("Gemini returned malformed JSON: %s", exc)
            return _fallback_result(fallback_rules, generated_at)
        except Exception as exc:
            logger.error("Gemini API call failed: %s", exc)
            return _fallback_result(fallback_rules, generated_at)

        raw_rules = parsed.get("rules") if isinstance(parsed, dict) else None
        if not isinstance(raw_rules, list):
            logger.warning(
                "Gemini response missing 'rules' array - using fallback rules"
            )
            return _fallback_result(fallback_rules, generated_at)

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
            rule_explanations = _build_rule_explanations(valid_rules, source="gemini")
            conflicts = _detect_rule_conflicts(valid_rules)
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
                "rule_explanations": _build_rule_explanations(
                    fallback_rules,
                    source="fallback",
                ),
                "conflicts": _detect_rule_conflicts(fallback_rules),
            },
        }
