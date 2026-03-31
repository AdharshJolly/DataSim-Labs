"""Attribute conversion helpers shared across routes/services."""

from __future__ import annotations

from typing import Any

from app.engine.dataset_generator import AttributeSpec


def model_attributes_to_specs(attributes: list[Any]) -> list[AttributeSpec]:
    """Convert persisted attribute models to engine-ready specs."""
    return [
        AttributeSpec(
            name=attribute.name,
            data_type=attribute.data_type.value,
            constraints=attribute.constraints_json,
            distribution=attribute.distribution.value,
            null_percentage=attribute.null_percentage,
        )
        for attribute in attributes
    ]
