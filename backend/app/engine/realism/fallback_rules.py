"""Schema-driven fallback rule builders and planner metadata helpers."""

from __future__ import annotations

import re
from typing import Any


def keyword_match(name: str, keywords: set[str]) -> bool:
    lowered = name.lower()
    return any(keyword in lowered for keyword in keywords)


def find_first_column(
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
        if keyword_match(name, keywords):
            return name
    return None


def find_first_attribute(
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
        if keyword_match(name, keywords):
            return attr
    return None


def infer_salary_band_for_role(role_name: str) -> tuple[int, int]:
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


def default_age_gate_override(target_attr: Any) -> Any:
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


def build_fallback_rules(attributes: list[Any]) -> list[dict[str, Any]]:
    rules: list[dict[str, Any]] = []

    name_col = find_first_column(
        attributes,
        keywords={"name", "full_name", "first_name", "last_name"},
        allowed_types={"name", "text", "categorical"},
    )
    gender_col = find_first_column(
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

    age_attr = find_first_attribute(
        attributes,
        keywords={"age"},
        allowed_types={"integer", "float"},
    )
    if age_attr is not None:
        age_col = str(getattr(age_attr, "name", ""))
        gate_targets = [
            (
                find_first_attribute(
                    attributes,
                    keywords={"marital", "marriage"},
                    allowed_types={"categorical", "text"},
                ),
                18,
            ),
            (
                find_first_attribute(
                    attributes,
                    keywords={"employ", "employment", "job_status", "work_status"},
                    allowed_types={"categorical", "text"},
                ),
                16,
            ),
            (
                find_first_attribute(
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
                    "override_value": default_age_gate_override(target_attr),
                }
            )

        salary_col = find_first_column(
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

    email_col = find_first_column(
        attributes,
        keywords={"email", "mail"},
        allowed_types={"email", "text"},
    )
    org_col = find_first_column(
        attributes,
        keywords={"company", "organization", "organisation", "org", "employer"},
        allowed_types={"categorical", "text"},
    )
    country_attr = find_first_attribute(
        attributes,
        keywords={"country", "nation"},
        allowed_types={"categorical", "text"},
    )

    phone_col = find_first_column(
        attributes,
        keywords={"phone", "mobile", "telephone", "contact_number", "tel"},
        allowed_types={"text", "categorical"},
    )
    if country_attr is not None and phone_col:
        rules.append(
            {
                "type": "phone_format_by_country",
                "country_column": str(getattr(country_attr, "name", "")),
                "phone_column": phone_col,
            }
        )

    card_col = find_first_column(
        attributes,
        keywords={
            "card_number",
            "credit_card",
            "payment_card",
            "debit_card",
            "cc_number",
        },
        allowed_types={"text", "categorical", "integer"},
    )
    if card_col:
        rules.append(
            {
                "type": "credit_card_luhn",
                "card_column": card_col,
                "length": 16,
                "prefix": "4",
            }
        )

    id_col = find_first_column(
        attributes,
        keywords={
            "order_id",
            "user_id",
            "txn_id",
            "transaction_id",
            "invoice_id",
            "record_id",
            "identifier",
        },
        allowed_types={"text", "categorical", "integer"},
    )
    if id_col:
        compact_name = re.sub(r"[^A-Za-z0-9]+", "", id_col).upper()
        prefix = compact_name[:3] or "ID"
        rules.append(
            {
                "type": "sequential_id",
                "target_column": id_col,
                "prefix": prefix,
                "start": 1,
                "padding": 6,
                "separator": "-",
            }
        )

    url_col = find_first_column(
        attributes,
        keywords={"website", "url", "web", "homepage", "site"},
        allowed_types={"text", "categorical"},
    )
    company_col = find_first_column(
        attributes,
        keywords={"company", "organization", "organisation", "org", "employer"},
        allowed_types={"categorical", "text"},
    )
    if url_col and company_col:
        rules.append(
            {
                "type": "url_from_company",
                "url_column": url_col,
                "company_column": company_col,
                "protocol": "https",
                "include_www": True,
            }
        )

    iban_col = find_first_column(
        attributes,
        keywords={"iban", "bank_account", "account_number", "bank_iban"},
        allowed_types={"text", "categorical"},
    )
    if country_attr is not None and iban_col:
        rules.append(
            {
                "type": "iban_format",
                "country_column": str(getattr(country_attr, "name", "")),
                "iban_column": iban_col,
            }
        )

    dept_col = find_first_column(
        attributes,
        keywords={"department", "dept", "team", "division"},
        allowed_types={"categorical", "text"},
    )
    org_is_department = org_col is not None and org_col == dept_col

    if email_col and org_col and not org_is_department:
        rules.append(
            {
                "type": "email_domain_match",
                "email_column": email_col,
                "org_column": org_col,
            }
        )

    name_col_for_email = find_first_column(
        attributes,
        keywords={"name", "full_name", "first_name", "last_name"},
        allowed_types={"name", "text", "categorical"},
    )
    if name_col_for_email and email_col:
        rules.append(
            {
                "type": "name_email_alignment",
                "name_column": name_col_for_email,
                "email_column": email_col,
            }
        )

    date_attr_names = [
        str(getattr(attr, "name", ""))
        for attr in attributes
        if str(getattr(attr, "data_type", "")).lower() == "date"
        and str(getattr(attr, "name", "")).strip()
    ]
    date_name_to_lower = {name: name.lower() for name in date_attr_names}

    def find_date_pair(
        source_keywords: set[str], target_keywords: set[str]
    ) -> tuple[str | None, str | None]:
        source = next(
            (
                name
                for name, lowered in date_name_to_lower.items()
                if any(keyword in lowered for keyword in source_keywords)
            ),
            None,
        )
        target = next(
            (
                name
                for name, lowered in date_name_to_lower.items()
                if any(keyword in lowered for keyword in target_keywords)
            ),
            None,
        )
        return source, target

    created_col, updated_col = find_date_pair(
        {"created", "creation", "inserted"},
        {"updated", "modified", "last_update", "last_modified"},
    )
    if created_col and updated_col and created_col != updated_col:
        rules.append(
            {
                "type": "date_relative_to",
                "target_column": updated_col,
                "source_column": created_col,
                "relation": "after",
                "min_offset_days": 0,
                "max_offset_days": 365,
            }
        )

    start_col, end_col = find_date_pair(
        {"start", "begin"},
        {"end", "finish", "close"},
    )
    if start_col and end_col and start_col != end_col:
        rules.append(
            {
                "type": "date_relative_to",
                "target_column": end_col,
                "source_column": start_col,
                "relation": "after",
                "min_offset_days": 0,
                "max_offset_days": 365,
            }
        )

    birth_col, hire_col = find_date_pair(
        {"birth", "dob"},
        {"hire", "joining", "join_date", "employment_start"},
    )
    if birth_col and hire_col and birth_col != hire_col:
        rules.append(
            {
                "type": "date_relative_to",
                "target_column": hire_col,
                "source_column": birth_col,
                "relation": "after",
                "min_offset_days": 18 * 365,
                "max_offset_days": 50 * 365,
            }
        )

    state_attr = find_first_attribute(
        attributes,
        keywords={"state", "province", "region"},
        allowed_types={"categorical", "text"},
    )
    postal_col = find_first_column(
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

    student_attr = find_first_attribute(
        attributes,
        keywords={"student", "is_student", "student_status"},
        allowed_types={"boolean", "categorical", "text"},
    )
    employment_attr = find_first_attribute(
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

    job_attr = find_first_attribute(
        attributes,
        keywords={"job", "role", "position", "occupation", "title"},
        allowed_types={"categorical", "text"},
    )
    salary_col = find_first_column(
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
            role_name: list(infer_salary_band_for_role(role_name))
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


def build_rule_explanations(
    rules: list[dict[str, Any]],
    source: str,
) -> list[dict[str, Any]]:
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
        "name_email_alignment": "Email local-part must be derived from the person's name for row-level realism.",
        "date_relative_to": "Date columns indicate a directional temporal dependency that must be enforced.",
        "phone_format_by_country": "Country information implies locale-specific phone formatting.",
        "credit_card_luhn": "Payment card fields should contain values passing Luhn checks.",
        "sequential_id": "Identifier fields often require deterministic sequential patterns.",
        "url_from_company": "Website fields should align with company naming.",
        "iban_format": "Bank account identifiers should follow IBAN format where applicable.",
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


def detect_rule_conflicts(rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
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


def fallback_result(
    fallback_rules: list[dict[str, Any]],
    generated_at: str,
    planner_version: str,
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
    conflicts = detect_rule_conflicts(fallback_rules)
    return {
        "rules": fallback_rules,
        "metadata": {
            "planner_version": planner_version,
            "source": "fallback",
            "generated_at": generated_at,
            "fallback_rule_count": len(fallback_rules),
            "gemini_rule_count": 0,
            "validated_rule_count": 0,
            "rule_explanations": fallback_explanations,
            "conflicts": conflicts,
        },
    }
