from typing import Dict, Any, List
import uuid

class TemplateService:
    @staticmethod
    def get_all_templates() -> List[Dict[str, Any]]:
        """Return prebuilt dataset templates."""
        return [
            {
                "id": "tpl-ecommerce",
                "name": "E-Commerce Transactions",
                "description": "A dataset of e-commerce orders, including products, prices, and user demographics.",
                "columns": {
                    "order_id": {"data_type": "text", "distribution": {"min_length": 8, "max_length": 12}},
                    "user_age": {"data_type": "integer", "distribution": {"type": "normal", "mean": 35.0, "std": 10.0, "min": 18, "max": 80}},
                    "product_category": {"data_type": "categorical", "distribution": {"type": "weighted_categorical", "categories": ["Electronics", "Clothing", "Home", "Toys"], "probabilities": [0.4, 0.3, 0.2, 0.1]}},
                    "purchase_amount": {"data_type": "float", "distribution": {"type": "skewed", "skew_direction": "right", "min": 5.0, "max": 5000.0, "mean": 120.0}},
                    "is_fraud": {"data_type": "boolean", "distribution": {"categories": ["False", "True"], "probabilities": [0.98, 0.02]}}
                },
                "dependency_graph": [
                    {
                        "source": ["product_category"],
                        "target": "purchase_amount",
                        "type": "conditional_numeric",
                        "distributions": {
                            "Electronics": {"mean": 500.0, "std": 200.0, "min": 50.0, "max": 3000.0},
                            "Clothing": {"mean": 60.0, "std": 30.0, "min": 10.0, "max": 500.0}
                        }
                    }
                ]
            },
            {
                "id": "tpl-healthcare",
                "name": "Healthcare Patient Records",
                "description": "Patient demographics, vitals, and diagnostic outcomes.",
                "columns": {
                    "patient_id": {"data_type": "text", "distribution": {"min_length": 6, "max_length": 8}},
                    "age": {"data_type": "integer", "distribution": {"type": "normal", "mean": 55.0, "std": 20.0, "min": 1, "max": 100}},
                    "blood_pressure": {"data_type": "integer", "distribution": {"type": "normal", "mean": 120.0, "std": 15.0, "min": 80, "max": 180}},
                    "diagnosis": {"data_type": "categorical", "distribution": {"type": "weighted_categorical", "categories": ["Healthy", "Hypertension", "Diabetes"], "probabilities": [0.6, 0.3, 0.1]}}
                },
                "dependency_graph": [
                    {
                        "source": ["age"],
                        "target": "blood_pressure",
                        "type": "linear_regression",
                        "coefficients": {"age": 0.5},
                        "intercept": 90.0,
                        "residual_std": 10.0,
                        "r2": 0.4
                    },
                    {
                        "source": ["blood_pressure"],
                        "target": "diagnosis",
                        "type": "numeric_to_categorical",
                        "bins": [80, 120, 140, 180],
                        "cpt": {
                            "80.0,120.0": {"Healthy": 0.9, "Hypertension": 0.1, "Diabetes": 0.0},
                            "120.0,140.0": {"Healthy": 0.5, "Hypertension": 0.4, "Diabetes": 0.1},
                            "140.0,180.0": {"Healthy": 0.1, "Hypertension": 0.8, "Diabetes": 0.1}
                        }
                    }
                ]
            }
        ]

    @staticmethod
    def get_all_personas() -> List[Dict[str, Any]]:
        """Return prebuilt data personas."""
        return [
            {
                "id": "persona-college",
                "name": "College Students",
                "overrides": {
                    "age": {"data_type": "integer", "distribution": {"type": "normal", "mean": 21.0, "std": 2.0, "min": 17, "max": 26}},
                    "income": {"data_type": "float", "distribution": {"type": "normal", "mean": 15000.0, "std": 5000.0, "min": 0.0, "max": 40000.0}}
                }
            },
            {
                "id": "persona-startup",
                "name": "Startup Employees",
                "overrides": {
                    "age": {"data_type": "integer", "distribution": {"type": "normal", "mean": 28.0, "std": 5.0, "min": 20, "max": 45}},
                    "income": {"data_type": "float", "distribution": {"type": "normal", "mean": 95000.0, "std": 30000.0, "min": 50000.0, "max": 250000.0}},
                    "job_role": {"data_type": "categorical", "distribution": {"type": "weighted_categorical", "categories": ["Engineer", "Designer", "Product", "Sales"], "probabilities": [0.5, 0.2, 0.15, 0.15]}}
                }
            }
        ]
