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
import hashlib

import pandas as pd

from app.core.config import settings

logger = logging.getLogger(__name__)

DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
FALLBACK_GEMINI_MODELS = ["gemini-2.5-flash-lite", "gemini-1.5-flash"]

# In-memory cache: schema_hash -> (rules, timestamp)
_SEMANTIC_RULES_CACHE: dict[str, tuple[dict[str, Any], float]] = {}
_CACHE_TTL_SECONDS = 86400  # 24 hours

_SEMANTIC_RULES_SYSTEM_PROMPT = """\
Detect semantic relationships in datasets. Return JSON: {"rules": [rule1, rule2, ...]}.

Each rule: {"id":"str","type":"derivation|mapping|conditional|function","priority":int,"target":"col","sources":["col1","col2"],"transform":{...},"confidence":0.0-1.0}

Transform types:
- template: "{col1}.{col2}" with extractors
- mapping: column→value lookup
- conditional: if X then Y
- function: uppercase/lowercase/capitalize/hash/prefix/suffix

Detection rules:
- Email often derived from name: confidence >= 0.85
- Use column_relationships examples as evidence
- Return [] if no relationships found
- Use exact column names
"""


def _compute_schema_hash(df: pd.DataFrame, column_metadata: dict[str, Any] | None = None) -> str:
    """Compute hash of dataset schema to use as cache key."""
    schema_info = {
        "cols": sorted(df.columns.tolist()),
        "dtypes": {col: str(df[col].dtype) for col in df.columns},
    }
    if column_metadata:
        schema_info["metadata"] = {k: v.get("semantic_type", "") for k, v in column_metadata.items()}
    
    schema_json = json.dumps(schema_info, sort_keys=True)
    return hashlib.md5(schema_json.encode()).hexdigest()


def _should_skip_inference(df: pd.DataFrame, column_metadata: dict[str, Any] | None = None) -> bool:
    """Skip Gemini call if dataset is too small or has no semantic columns."""
    if len(df) < 5:
        logger.info("Skipping semantic inference: dataset < 5 rows")
        return True
    
    # Check if dataset has name or email columns (main targets for derivation rules)
    has_semantic_cols = False
    for col in df.columns:
        semantic_type = None
        if column_metadata and col in column_metadata:
            semantic_type = column_metadata[col].get("semantic_type")
        if not semantic_type:
            semantic_type = _detect_semantic_type(col)
        if semantic_type in ("name", "email"):
            has_semantic_cols = True
            break
    
    if not has_semantic_cols:
        logger.info("Skipping semantic inference: no semantic columns detected")
        return True
    
    return False


def _get_cached_rules(schema_hash: str) -> dict[str, Any] | None:
    """Retrieve rules from cache if valid."""
    if schema_hash not in _SEMANTIC_RULES_CACHE:
        return None
    
    rules, timestamp = _SEMANTIC_RULES_CACHE[schema_hash]
    age_seconds = datetime.now(timezone.utc).timestamp() - timestamp
    
    if age_seconds > _CACHE_TTL_SECONDS:
        del _SEMANTIC_RULES_CACHE[schema_hash]
        return None
    
    return rules


def _cache_rules(schema_hash: str, rules: dict[str, Any]) -> None:
    """Store rules in cache."""
    _SEMANTIC_RULES_CACHE[schema_hash] = (rules, datetime.now(timezone.utc).timestamp())


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
    max_rows: int = 5,
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
            paired_rows = sample_df[[name_column, email_column]].dropna().head(1)
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
        "cols": {
            col: {
                "type": str(df[col].dtype),
                "nulls": int(df[col].isna().sum()),
                "uniq": int(df[col].nunique()),
            }
            for col in df.columns
        },
        "rows": sample_df.to_dict(orient="records"),
        "rels": column_relationships,
        "total": len(df),
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

    # Compute schema hash for caching
    schema_hash = _compute_schema_hash(df, column_metadata)
    
    # Check cache first
    cached_result = _get_cached_rules(schema_hash)
    if cached_result is not None:
        logger.info(f"Using cached rules for schema {schema_hash[:8]}")
        return {
            "rules": cached_result.get("rules", []),
            "metadata": {
                "generated_at": generated_at,
                "source": "cache",
                "rule_count": len(cached_result.get("rules", [])),
                "cache_hit": True,
            },
        }
    
    # Check if inference should be skipped
    if _should_skip_inference(df, column_metadata):
        logger.info("Skipping semantic inference for this dataset")
        return {
            "rules": [],
            "metadata": {
                "generated_at": generated_at,
                "source": "skip",
                "rule_count": 0,
                "skipped": True,
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

    result = {
        "rules": valid_rules,
        "metadata": {
            "generated_at": generated_at,
            "source": "gemini",
            "model": used_model,
            "rule_count": len(valid_rules),
            "raw_rule_count": len(raw_rules),
        },
    }
    
    # Cache the result
    _cache_rules(schema_hash, result)
    logger.info(f"Cached rules for schema {schema_hash[:8]} ({len(valid_rules)} rules)")
    
    return result
