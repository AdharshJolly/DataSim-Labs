"""
semantic_rule_inference.py

Calls Gemini to infer semantic rules from dataset samples.
Input: Dataset samples, column metadata
Output: Universal semantic rules.

Handles all Gemini failures gracefully.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any
import re

import pandas as pd

from app.core.config import settings

logger = logging.getLogger(__name__)

DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
FALLBACK_GEMINI_MODELS = ["gemini-2.5-flash-lite", "gemini-1.5-flash"]

_SEMANTIC_RULES_SYSTEM_PROMPT = """\
You are an expert data analyst specializing in detecting semantic relationships in datasets.
Your task is to analyze structured data and identify cross-column dependencies that define data quality rules.

Return ONLY a valid JSON object - no markdown fences, no prose, no explanation.

The response must have exactly one key: "rules", which is an array of rule objects.

Each rule MUST follow this exact structure:
{
    "id": "unique_string_identifier",
    "type": "derivation|mapping|conditional|function",
    "priority": <integer_lower_is_higher>,
    "target": "column_name",
    "sources": ["source_col1", "source_col2"],
    "transform": {
        "type": "template|mapping|conditional|function",
        "template": "string_template_with_placeholders",
        "extractors": {"key": "extraction_expression"},
        "domain_pool": ["value1", "value2"],
        "mapping_table": {"input": "output"},
        "conditions": [{"if": "condition_expr", "then": "value_expr"}],
        "function_name": "function_name",
        "prefix": "prefix_string",
        "suffix": "suffix_string"
    },
    "constraints": {
        "lowercase": false,
        "uppercase": false,
        "no_spaces": false,
        "no_special_chars": false,
        "max_length": 50
    },
    "confidence": 0.85
}

RULE TYPES:
- derivation: Column value is derived from other columns (e.g., email from name)
- mapping: Column value maps from another column using a lookup table
- conditional: Column value depends on conditions in other columns
- function: Apply a function to transform one column into another

TRANSFORM TYPES:
1. template:
   - Use when combining or formatting values from other columns
   - Example: email "{first}.{last}@{domain}" where extractors parse source columns
   - Extractors support: split(col)[index], lower(col), upper(col), substring(col,start,end)

2. mapping:
   - Use when values in one column directly map to another
   - mapping_table: Dict of source_value -> target_value

3. conditional:
   - Use when column values depend on conditions
   - conditions: List of if-then rules
   - Support conditions: column == "value", column != "value", column in ["v1","v2"]

4. function:
   - Apply standard functions: uppercase, lowercase, capitalize, hash, prefix, suffix

DETECTION GUIDELINES:
- column names in target and sources MUST be exact matches from the schema
- Analyze sample data for patterns:
  * Email addresses often contain parts of name columns
  * Phone numbers have country-specific prefixes
  * Cities/states/zips follow geographic patterns
  * Email domains relate to company/org columns
  * First/last names align with gender
- When a name column and an email column are present and row-level values are clearly correlated,
  you MUST generate a derivation rule with a template transform and set confidence >= 0.9.
- When an email value clearly includes first name, last name, or initials from a name value,
  you MUST assign high confidence >= 0.85.
- The `column_relationships` key in the payload explicitly lists row-matched pairs.
    You MUST use this evidence to infer derivation rules.
- confidence must be [0.0, 1.0] based on pattern strength
- If no rules detected, return {"rules": []}
- ONLY include rules you can validate from the provided data
"""


def _detect_semantic_type(column_name: str | None) -> str | None:
    if not column_name:
        return None

    normalized = re.sub(r"[^a-z0-9]+", "_", str(column_name).strip().lower())
    compact = normalized.replace("_", "")

    def has_any(patterns: list[str]) -> bool:
        return any(pattern in normalized or pattern in compact for pattern in patterns)

    if has_any(["email", "mail", "e_mail", "emailid"]):
        return "email"
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


def _prepare_sample_data(
    df: pd.DataFrame,
    column_metadata: dict[str, Any] | None = None,
    max_rows: int = 20,
) -> dict[str, Any]:
    """Prepare sample data for Gemini analysis."""
    sample_df = df.head(max_rows) if len(df) > max_rows else df.copy()

    name_columns: list[str] = []
    email_columns: list[str] = []
    for column in sample_df.columns:
        semantic_type = None
        if column_metadata and column in column_metadata:
            semantic_type = column_metadata[column].get("semantic_type")
        if not semantic_type:
            semantic_type = _detect_semantic_type(column)
        if semantic_type == "name":
            name_columns.append(column)
        elif semantic_type == "email":
            email_columns.append(column)

    column_relationships: list[dict[str, Any]] = []
    for name_column in name_columns:
        for email_column in email_columns:
            paired_rows = sample_df[[name_column, email_column]].dropna().head(3)
            if paired_rows.empty:
                continue
            examples = [
                {
                    "name": str(row[name_column]),
                    "email": str(row[email_column]),
                }
                for _, row in paired_rows.iterrows()
            ]
            column_relationships.append(
                {
                    "columns": [name_column, email_column],
                    "examples": examples,
                }
            )

    return {
        "columns": {
            col: {
                "type": str(df[col].dtype),
                "null_count": int(df[col].isna().sum()),
                "unique_count": int(df[col].nunique()),
                "sample_values": df[col].dropna().head(5).tolist(),
            }
            for col in df.columns
        },
        "sample_rows": sample_df.to_dict(orient="records"),
        "column_relationships": column_relationships,
        "row_count": len(df),
    }


def infer_semantic_rules(
    df: pd.DataFrame,
    column_metadata: dict[str, Any] | None = None,
    api_key: str | None = None,
) -> dict[str, Any]:
    """
    Infer semantic rules from dataset using Gemini.

    Args:
        df: DataFrame to analyze
        column_metadata: Optional metadata about columns
        api_key: Gemini API key (defaults to settings.gemini_api_key)

    Returns:
        Dict with 'rules' and 'metadata' keys
    """
    generated_at = datetime.now(timezone.utc).isoformat()

    if df.empty:
        return {
            "rules": [],
            "metadata": {
                "generated_at": generated_at,
                "source": "none",
                "rule_count": 0,
                "error": "Empty dataset",
            },
        }

    if api_key is None:
        api_key = settings.gemini_api_key

    if not api_key or not api_key.strip():
        logger.warning("GEMINI_API_KEY not set - semantic rule inference disabled")
        return {
            "rules": [],
            "metadata": {
                "generated_at": generated_at,
                "source": "none",
                "rule_count": 0,
                "error": "API key not configured",
            },
        }

    # Prepare payload
    sample_payload = _prepare_sample_data(df, column_metadata)
    user_message = (
        "Analyze this dataset and detect semantic relationships between columns.\n\n"
        + json.dumps(sample_payload, indent=2, default=str)
        + "\n\nReturn structured rules in JSON format."
    )

    configured_model = settings.gemini_model.strip() or DEFAULT_GEMINI_MODEL
    candidate_models = list(dict.fromkeys([configured_model, *FALLBACK_GEMINI_MODELS]))

    try:
        from google import genai  # type: ignore[import-untyped]
        from google.genai import types  # type: ignore[import-untyped]
    except ImportError:
        logger.error("google-genai is not installed. Run: pip install google-genai")
        return {
            "rules": [],
            "metadata": {
                "generated_at": generated_at,
                "source": "none",
                "rule_count": 0,
                "error": "google-genai not installed",
            },
        }

    parsed: dict[str, Any] | None = None
    last_error: Exception | None = None
    used_model: str | None = None

    client = genai.Client(api_key=api_key)
    for model_name in candidate_models:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=user_message,
                config=types.GenerateContentConfig(
                    system_instruction=_SEMANTIC_RULES_SYSTEM_PROMPT,
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
                raise ValueError("Response JSON root is not an object")

            parsed = parsed_candidate
            used_model = model_name
            if model_name != configured_model:
                logger.warning(
                    "Gemini fallback: %s -> %s", configured_model, model_name
                )
            break
        except json.JSONDecodeError as exc:
            logger.error("Malformed JSON from %s: %s", model_name, exc)
            last_error = exc
            break
        except Exception as exc:
            last_error = exc
            error_message = str(exc)
            if "404" in error_message or "not found" in error_message.lower():
                logger.warning("Model %s unavailable, trying fallback", model_name)
                continue
            logger.error("API call failed for %s: %s", model_name, exc)
            break

    if parsed is None:
        if last_error:
            logger.error("Semantic rule inference failed: %s", last_error)
        return {
            "rules": [],
            "metadata": {
                "generated_at": generated_at,
                "source": "error",
                "rule_count": 0,
                "error": str(last_error) if last_error else "Unknown error",
            },
        }

    raw_rules = parsed.get("rules", []) if isinstance(parsed, dict) else []
    if not isinstance(raw_rules, list):
        logger.warning("Response missing 'rules' array")
        return {
            "rules": [],
            "metadata": {
                "generated_at": generated_at,
                "source": "partial",
                "rule_count": 0,
                "error": "Invalid response format",
            },
        }

    # Validate rules
    column_names = set(df.columns)
    valid_rules = []

    for idx, rule in enumerate(raw_rules):
        if not isinstance(rule, dict):
            logger.debug("Rule %d is not a dict", idx)
            continue

        # Validate required fields
        target = rule.get("target")
        sources = rule.get("sources", [])
        rule_type = rule.get("type", "").lower()
        transform = rule.get("transform", {})
        confidence = rule.get("confidence", 0.5)

        # Basic validation
        if not target or target not in column_names:
            logger.debug("Rule %d: invalid or missing target column", idx)
            continue

        if not sources or not isinstance(sources, list):
            logger.debug("Rule %d: invalid or missing sources", idx)
            continue

        if not all(src in column_names for src in sources):
            logger.debug("Rule %d: source column not in dataset", idx)
            continue

        if rule_type not in {"derivation", "mapping", "conditional", "function"}:
            logger.debug("Rule %d: invalid rule type: %s", idx, rule_type)
            continue

        if not isinstance(transform, dict) or not transform.get("type"):
            logger.debug("Rule %d: invalid or missing transform", idx)
            continue

        if not isinstance(confidence, (int, float)) or not (0 <= confidence <= 1):
            logger.debug("Rule %d: invalid confidence value", idx)
            continue

        # Add rule
        rule["id"] = f"rule_{idx}_{int(datetime.now(timezone.utc).timestamp())}"
        valid_rules.append(rule)

    return {
        "rules": valid_rules,
        "metadata": {
            "generated_at": generated_at,
            "source": "gemini",
            "model": used_model,
            "rule_count": len(valid_rules),
            "raw_rule_count": len(raw_rules),
        },
    }
