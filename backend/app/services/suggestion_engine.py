"""Heuristic suggestion engine for attribute settings and lightweight relationships."""

from __future__ import annotations

from typing import Any

from app.schemas.dataset import AttributeConfig


class SuggestionEngine:
    """Build deterministic suggestions from attribute configuration."""

    @staticmethod
    def suggest(
        attributes: list[AttributeConfig],
    ) -> dict[str, Any]:
        attribute_suggestions: list[dict[str, Any]] = []

        normalized_names = [attr.name.strip().lower() for attr in attributes]

        for attr in attributes:
            name = attr.name.strip().lower()
            constraints = dict(attr.constraints or {})

            if attr.type.value in {"integer", "float"}:
                if any(
                    k in name
                    for k in ["salary", "income", "price", "amount", "cost", "revenue"]
                ):
                    attribute_suggestions.append(
                        {
                            "attribute_name": attr.name,
                            "suggested_distribution": "skewed",
                            "suggested_constraints": {
                                "skew_direction": "right",
                                "skew_intensity": float(
                                    constraints.get("skew_intensity", 2.0)
                                ),
                            },
                            "confidence": 0.86,
                            "reason": "Financial-like numeric columns are typically right-skewed.",
                        }
                    )
                elif attr.distribution.value == "uniform":
                    attribute_suggestions.append(
                        {
                            "attribute_name": attr.name,
                            "suggested_distribution": "normal",
                            "suggested_constraints": {},
                            "confidence": 0.73,
                            "reason": "Numeric column appears suitable for normal distribution default.",
                        }
                    )

            if attr.type.value == "categorical":
                categories = constraints.get("categories")
                weights = constraints.get("weights")
                if (
                    isinstance(categories, list)
                    and categories
                    and not isinstance(weights, list)
                ):
                    equal_weight = round(1.0 / len(categories), 4)
                    attribute_suggestions.append(
                        {
                            "attribute_name": attr.name,
                            "suggested_distribution": "weighted_categorical",
                            "suggested_constraints": {
                                "weights": [equal_weight for _ in categories],
                            },
                            "confidence": 0.8,
                            "reason": "Categorical column has labels but no explicit weights.",
                        }
                    )

            if attr.type.value == "text":
                if "email" in name:
                    attribute_suggestions.append(
                        {
                            "attribute_name": attr.name,
                            "suggested_distribution": attr.distribution.value,
                            "suggested_constraints": {
                                "max_length": int(constraints.get("max_length", 64)),
                            },
                            "confidence": 0.78,
                            "reason": "Email-like fields usually benefit from bounded text length.",
                        }
                    )

        relationship_suggestions: list[dict[str, Any]] = []

        if "city" in normalized_names and "state" in normalized_names:
            relationship_suggestions.append(
                {
                    "source": "city",
                    "target": "state",
                    "strength": 0.9,
                    "confidence": 0.9,
                    "reason": "Detected geographic mapping pattern city -> state.",
                }
            )

        if "name" in normalized_names and "email" in normalized_names:
            relationship_suggestions.append(
                {
                    "source": "name",
                    "target": "email",
                    "strength": 0.84,
                    "confidence": 0.84,
                    "reason": "Detected likely derivation pattern name -> email.",
                }
            )

        if "company" in normalized_names and (
            "domain" in normalized_names or "email_domain" in normalized_names
        ):
            relationship_suggestions.append(
                {
                    "source": "company",
                    "target": (
                        "domain" if "domain" in normalized_names else "email_domain"
                    ),
                    "strength": 0.82,
                    "confidence": 0.82,
                    "reason": "Detected likely company to domain mapping pattern.",
                }
            )

        return {
            "attribute_suggestions": attribute_suggestions,
            "relationship_suggestions": relationship_suggestions,
            "metadata": {
                "attribute_count": len(attributes),
                "attribute_suggestion_count": len(attribute_suggestions),
                "relationship_suggestion_count": len(relationship_suggestions),
                "engine": "heuristic_v1",
            },
        }
