import json
import os
from typing import Dict, Any

class CoPilotService:
    @staticmethod
    def generate_profile_from_prompt(prompt: str) -> Dict[str, Any]:
        """Convert a natural language prompt into a structured Dataset Profile using AI."""
        try:
            from google import genai
            from google.genai import types
        except ImportError:
            raise ValueError("google-genai library is not installed or available.")

        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            # Fallback to a mock for demonstration if no API key is present
            return CoPilotService._generate_mock_profile(prompt)

        try:
            client = genai.Client(api_key=api_key)
            model_id = os.environ.get("GEMINI_MODEL", "gemini-2.5-pro")

            schema = {
                "type": "object",
                "properties": {
                    "columns": {
                        "type": "object",
                        "description": "Dictionary of columns. Key is column name. Value is dict with 'data_type' (integer, float, categorical, boolean, text, date), 'null_percentage' (float), and 'distribution' dict. Distribution dict has 'type' (normal, uniform, skewed, weighted_categorical), and params (mean, std, min, max, categories, probabilities).",
                        "additionalProperties": {"type": "object"}
                    },
                    "dependency_graph": {
                        "type": "array",
                        "description": "List of dependencies. E.g., {'source': ['age'], 'target': 'salary', 'type': 'linear_regression', 'coefficients': {'age': 1000}, 'intercept': 20000, 'residual_std': 5000, 'r2': 0.8} OR {'source': ['country'], 'target': 'city', 'type': 'conditional_probability', 'cpt': {'US': {'NY': 0.5, 'SF': 0.5}}}",
                        "items": {"type": "object"}
                    },
                    "row_count": {
                        "type": "integer",
                        "description": "Suggested row count if the user mentioned one, otherwise 1000."
                    }
                },
                "required": ["columns", "dependency_graph", "row_count"]
            }

            response = client.models.generate_content(
                model=model_id,
                contents=f"Generate a robust, statistically sound dataset profile matching this request: '{prompt}'. Include logical columns, realistic statistical distributions (mean, min, max), and meaningful dependencies/correlations between the fields.",
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=schema,
                    temperature=0.4
                )
            )

            result = json.loads(response.text)
            return result
        except Exception as e:
            import logging
            logging.error(f"AI Generation Failed: {e}")
            return CoPilotService._generate_mock_profile(prompt)

    @staticmethod
    def _generate_mock_profile(prompt: str) -> Dict[str, Any]:
        """Fallback mock profile when API is unavailable."""
        return {
            "columns": {
                "user_id": {"data_type": "text", "distribution": {"min_length": 8, "max_length": 12}, "null_percentage": 0.0},
                "age": {"data_type": "integer", "distribution": {"type": "normal", "mean": 35.0, "std": 10.0, "min": 18, "max": 80}, "null_percentage": 2.0},
                "income": {"data_type": "float", "distribution": {"type": "skewed", "skew_direction": "right", "min": 10000.0, "max": 200000.0, "mean": 50000.0}, "null_percentage": 5.0}
            },
            "dependency_graph": [
                {
                    "source": ["age"],
                    "target": "income",
                    "type": "linear_regression",
                    "coefficients": {"age": 1500.0},
                    "intercept": 20000.0,
                    "residual_std": 10000.0,
                    "r2": 0.6
                }
            ],
            "row_count": 1000
        }
