"""Prompt and rule contract constants for realism planning."""

from __future__ import annotations

VALID_RULE_TYPES = {
    "name_gender_alignment",
    "age_gate",
    "mutual_exclusion",
    "conditional_value",
    "country_state_alignment",
    "country_postal_format",
    "email_domain_match",
    "salary_band",
    "name_email_alignment",
    "date_relative_to",
    "phone_format_by_country",
    "credit_card_luhn",
    "sequential_id",
    "url_from_company",
    "iban_format",
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
    "name_email_alignment": {"name_column", "email_column"},
    "date_relative_to": {"target_column", "source_column", "relation"},
    "phone_format_by_country": {"country_column", "phone_column"},
    "credit_card_luhn": {"card_column"},
    "sequential_id": {"target_column", "prefix", "start", "padding"},
    "url_from_company": {"url_column", "company_column"},
    "iban_format": {"country_column", "iban_column"},
}

PLANNER_VERSION = "2.3.0"
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
FALLBACK_GEMINI_MODELS = ["gemini-2.5-flash-lite", "gemini-1.5-flash"]

SYSTEM_PROMPT = """\
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
   Do NOT use this rule if the only available org-like column is a department,
   team, or categorical field with few distinct values - departments are not
   company names and produce unrealistic domains.
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

9. name_email_alignment
   Use when a name column and an email column are both present.
   Ensures the local part of the email address is derived from the person's
   name so that "Alice Johnson" gets an email like alice.johnson@domain.com
   instead of a random email.
   { "type": "name_email_alignment", "name_column": "...", "email_column": "..." }

10. date_relative_to
    Use when two date columns have a logical ordering relationship.
    Supported relation values: "after", "before", "same_day"
    min_offset_days and max_offset_days are optional and default to [0, 365].
    {
      "type": "date_relative_to",
      "target_column": "updated_at",
      "source_column": "created_at",
      "relation": "after",
      "min_offset_days": 0,
      "max_offset_days": 365
    }

11. phone_format_by_country
        Use when country and phone columns are present.
        {
            "type": "phone_format_by_country",
            "country_column": "country",
            "phone_column": "phone_number"
        }

12. credit_card_luhn
        Use when a payment card number column is present.
        length is optional (default 16), prefix is optional.
        {
            "type": "credit_card_luhn",
            "card_column": "card_number",
            "length": 16,
            "prefix": "4"
        }

13. sequential_id
        Use for identifier columns that should be ordered and formatted.
        {
            "type": "sequential_id",
            "target_column": "order_id",
            "prefix": "ORD",
            "start": 1,
            "padding": 6,
            "separator": "-"
        }

14. url_from_company
        Use when website/url and company columns are present.
        {
            "type": "url_from_company",
            "url_column": "website",
            "company_column": "company",
            "protocol": "https",
            "include_www": true
        }

15. iban_format
        Use when country and IBAN/bank account columns are present.
        {
            "type": "iban_format",
            "country_column": "country",
            "iban_column": "iban"
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
