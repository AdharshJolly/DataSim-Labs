from __future__ import annotations

import json
from pathlib import Path
from typing import Any
import uuid


_TEMPLATES_PATH = Path(__file__).parent.parent / "data" / "templates.json"


class TemplateService:
    _cache: list[dict[str, Any]] | None = None

    @staticmethod
    def get_all_templates() -> list[dict[str, Any]]:
        """Return prebuilt dataset templates."""
        if TemplateService._cache is None:
            TemplateService._cache = json.loads(
                _TEMPLATES_PATH.read_text(encoding="utf-8")
            )
        return TemplateService._cache

    @staticmethod
    def get_all_personas() -> list[dict[str, Any]]:
        """Return prebuilt data personas."""
        return [
            {
                "id": "persona-college",
                "name": "College Students",
                "overrides": {
                    "age": {
                        "data_type": "integer",
                        "distribution": {
                            "type": "normal",
                            "mean": 21.0,
                            "std": 2.0,
                            "min": 17,
                            "max": 26,
                        },
                    },
                    "income": {
                        "data_type": "float",
                        "distribution": {
                            "type": "normal",
                            "mean": 15000.0,
                            "std": 5000.0,
                            "min": 0.0,
                            "max": 40000.0,
                        },
                    },
                },
            },
            {
                "id": "persona-startup",
                "name": "Startup Employees",
                "overrides": {
                    "age": {
                        "data_type": "integer",
                        "distribution": {
                            "type": "normal",
                            "mean": 28.0,
                            "std": 5.0,
                            "min": 20,
                            "max": 45,
                        },
                    },
                    "income": {
                        "data_type": "float",
                        "distribution": {
                            "type": "normal",
                            "mean": 95000.0,
                            "std": 30000.0,
                            "min": 50000.0,
                            "max": 250000.0,
                        },
                    },
                    "job_role": {
                        "data_type": "categorical",
                        "distribution": {
                            "type": "weighted_categorical",
                            "categories": ["Engineer", "Designer", "Product", "Sales"],
                            "probabilities": [0.5, 0.2, 0.15, 0.15],
                        },
                    },
                },
            },
        ]
