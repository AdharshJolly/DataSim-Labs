from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, Field, model_validator

from app.core.enums import DataType, DistributionType


class AttributeConfig(BaseModel):
    name: str = Field(..., min_length=1)
    type: DataType
    description: str = ""
    constraints: dict[str, Any] = Field(default_factory=dict)
    distribution: DistributionType = DistributionType.uniform
    null_percentage: float = Field(default=0.0, ge=0.0, le=100.0)

    @model_validator(mode="after")
    def validate_constraints(self) -> "AttributeConfig":
        allowed_keys: set[str] = set()
        if self.type in {DataType.integer, DataType.float}:
            allowed_keys = {"min", "max", "skew_direction", "skew_intensity"}
            if self.type is DataType.float:
                allowed_keys.add("precision")
            min_value = self.constraints.get("min")
            max_value = self.constraints.get("max")
            if min_value is not None and not isinstance(min_value, (int, float)):
                raise ValueError("Numeric attributes require numeric 'min'")
            if max_value is not None and not isinstance(max_value, (int, float)):
                raise ValueError("Numeric attributes require numeric 'max'")
            if (
                min_value is not None
                and max_value is not None
                and float(min_value) > float(max_value)
            ):
                raise ValueError("Numeric attribute 'min' cannot be greater than 'max'")

            precision = self.constraints.get("precision")
            if precision is not None:
                if not isinstance(precision, int):
                    raise ValueError("Float 'precision' must be an integer")
                if precision < 0 or precision > 10:
                    raise ValueError("Float 'precision' must be between 0 and 10")

            skew_direction = self.constraints.get("skew_direction")
            if skew_direction is not None:
                if skew_direction not in {"left", "right"}:
                    raise ValueError("'skew_direction' must be 'left' or 'right'")

            skew_intensity = self.constraints.get("skew_intensity")
            if skew_intensity is not None:
                if not isinstance(skew_intensity, (int, float)):
                    raise ValueError("'skew_intensity' must be a number")
                if float(skew_intensity) <= 0 or float(skew_intensity) > 10:
                    raise ValueError(
                        "'skew_intensity' must be between 0 (exclusive) and 10"
                    )

        elif self.type is DataType.categorical:
            allowed_keys = {"categories", "weights"}
            categories = self.constraints.get("categories")
            weights = self.constraints.get("weights")
            if categories is not None and (
                not isinstance(categories, list)
                or not all(
                    isinstance(item, str) and item.strip() for item in categories
                )
            ):
                raise ValueError(
                    "Categorical attributes require string array 'categories'"
                )
            if weights is not None and (
                not isinstance(weights, list)
                or not all(isinstance(item, (int, float)) for item in weights)
            ):
                raise ValueError(
                    "Categorical attributes require numeric array 'weights'"
                )
            if isinstance(weights, list):
                if any(float(w) < 0 for w in weights):
                    raise ValueError("Categorical weights must be non-negative")
            if isinstance(categories, list) and isinstance(weights, list):
                if len(categories) != len(weights):
                    raise ValueError("'weights' length must match 'categories' length")
                if sum(float(weight) for weight in weights) <= 0:
                    raise ValueError(
                        "Categorical 'weights' must sum to a positive value"
                    )
        elif self.type is DataType.date:
            allowed_keys = {"start_date", "end_date"}
            start_date = self.constraints.get("start_date")
            end_date = self.constraints.get("end_date")
            if start_date is not None and not isinstance(start_date, str):
                raise ValueError("Date attributes require string 'start_date'")
            if end_date is not None and not isinstance(end_date, str):
                raise ValueError("Date attributes require string 'end_date'")
            if isinstance(start_date, str) and isinstance(end_date, str):
                if date.fromisoformat(start_date) > date.fromisoformat(end_date):
                    raise ValueError(
                        "Date attribute 'start_date' cannot be after 'end_date'"
                    )
        elif self.type is DataType.text:
            allowed_keys = {"max_length"}
            max_length = self.constraints.get("max_length")
            if max_length is not None:
                if not isinstance(max_length, int):
                    raise ValueError("Text 'max_length' must be an integer")
                if max_length < 1:
                    raise ValueError("Text 'max_length' must be at least 1")
        elif self.type is DataType.boolean:
            allowed_keys = {"true_probability"}
            true_probability = self.constraints.get("true_probability")
            if true_probability is not None:
                if not isinstance(true_probability, (int, float)):
                    raise ValueError("Boolean 'true_probability' must be a number")
                if float(true_probability) < 0 or float(true_probability) > 1:
                    raise ValueError(
                        "Boolean 'true_probability' must be between 0 and 1"
                    )

        unknown_keys = set(self.constraints.keys()) - allowed_keys
        if unknown_keys:
            keys = ", ".join(sorted(unknown_keys))
            raise ValueError(
                f"Unsupported constraint keys for {self.type.value}: {keys}"
            )

        if (
            self.distribution is DistributionType.weighted_categorical
            and self.type is not DataType.categorical
        ):
            raise ValueError(
                "'weighted_categorical' distribution is only valid for categorical type"
            )

        if (
            self.type
            in {
                DataType.boolean,
                DataType.text,
                DataType.email,
                DataType.name,
                DataType.address,
            }
            and self.distribution is not DistributionType.uniform
        ):
            raise ValueError(
                f"{self.type.value} attributes only support 'uniform' distribution"
            )

        return self
