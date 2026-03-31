"""Core raw-value generation for attribute columns."""

from __future__ import annotations

from typing import Any

import numpy as np
from faker import Faker

from app.engine.generators.boolean_generator import generate_boolean
from app.engine.generators.categorical_generator import generate_categorical
from app.engine.generators.date_generator import generate_date
from app.engine.generators.faker_generator import (
    generate_address,
    generate_city,
    generate_company,
    generate_country,
    generate_email,
    generate_gender,
    generate_name,
    generate_phone,
    generate_url,
    generate_zip,
)
from app.engine.generators.float_generator import generate_float
from app.engine.generators.identity_generator import (
    detect_semantic_type,
    generate_identity_batch,
)
from app.engine.generators.integer_generator import generate_integer
from app.engine.generators.text_generator import generate_text


class CoreGenerator:
    """Produces base column values before semantic/realism post-processing."""

    def __init__(self, rng: np.random.Generator, faker: Faker) -> None:
        self.rng = rng
        self.faker = faker

    def generate_column(self, attr: Any, row_count: int):
        data_type = attr.data_type
        distribution = attr.distribution
        constraints = attr.constraints

        if data_type == "integer":
            return generate_integer(
                attr.name, constraints, distribution, row_count, self.rng
            )
        if data_type == "float":
            return generate_float(
                attr.name, constraints, distribution, row_count, self.rng
            )
        if data_type == "categorical":
            return generate_categorical(attr.name, constraints, row_count, self.rng)
        if data_type == "boolean":
            return generate_boolean(attr.name, constraints, row_count, self.rng)
        if data_type == "date":
            return generate_date(
                attr.name, constraints, distribution, row_count, self.rng
            )
        if data_type == "text":
            return generate_text(
                attr.name, constraints, row_count, self.rng, self.faker
            )
        if data_type == "email":
            return generate_email(attr.name, row_count, self.faker)
        if data_type == "name":
            return generate_name(attr.name, row_count, self.faker)
        if data_type == "address":
            return generate_address(attr.name, row_count, self.faker)
        if data_type == "semantic":
            semantic_kind = str(constraints.get("semantic_type", "")).lower()
            if semantic_kind == "email":
                return generate_email(attr.name, row_count, self.faker)
            if semantic_kind == "name":
                return generate_name(attr.name, row_count, self.faker)
            if semantic_kind == "address":
                return generate_address(attr.name, row_count, self.faker)
            if semantic_kind == "phone":
                return generate_phone(attr.name, row_count, self.faker)
            if semantic_kind == "url":
                return generate_url(attr.name, row_count, self.faker)
            if semantic_kind == "company":
                return generate_company(attr.name, row_count, self.faker)
            if semantic_kind == "city":
                return generate_city(attr.name, row_count, self.faker)
            if semantic_kind == "country":
                return generate_country(attr.name, row_count, self.faker)
            if semantic_kind == "zip":
                return generate_zip(attr.name, row_count, self.faker)
            if semantic_kind == "gender":
                return generate_gender(attr.name, row_count, self.faker)
            return generate_text(
                attr.name, constraints, row_count, self.rng, self.faker
            )

        raise ValueError(f"Unsupported data type: {data_type}")

    def detect_semantic_groups(self, attributes: list[Any]) -> list[dict[str, Any]]:
        column_type_map: dict[str, str] = {}
        for attribute in attributes:
            inferred_type = detect_semantic_type(attribute.name)
            if inferred_type:
                column_type_map[attribute.name] = inferred_type

        name_columns = [
            column
            for column, semantic_type in column_type_map.items()
            if semantic_type == "name"
        ]
        email_columns = [
            column
            for column, semantic_type in column_type_map.items()
            if semantic_type == "email"
        ]

        if not name_columns or not email_columns:
            return []

        columns = [*name_columns, *email_columns]
        return [
            {
                "type": "identity",
                "columns": columns,
                "column_type_map": {
                    column: column_type_map[column]
                    for column in columns
                    if column in column_type_map
                },
            }
        ]

    def generate_semantic_group_columns(
        self,
        groups: list[dict[str, Any]],
        attributes: list[Any],
        row_count: int,
    ) -> dict[str, list[str]]:
        allowed_columns = {attribute.name for attribute in attributes}
        grouped_data: dict[str, list[str]] = {}
        already_bound: set[str] = set()

        for group in groups:
            if str(group.get("type", "")).lower() != "identity":
                continue

            requested_columns = [
                str(column)
                for column in group.get("columns", [])
                if str(column) in allowed_columns
            ]
            if not requested_columns or any(
                column in already_bound for column in requested_columns
            ):
                continue

            batch = generate_identity_batch(
                row_count=row_count,
                faker=self.faker,
                rng=self.rng,
                columns=requested_columns,
                email_domains=group.get("observed_domains"),
                email_domain_weights=group.get("observed_domain_weights"),
                column_type_map=group.get("column_type_map"),
            )
            for column in requested_columns:
                grouped_data[column] = batch.get(column, [""] * row_count)
                already_bound.add(column)

        return grouped_data
