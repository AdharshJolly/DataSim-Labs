"""Core raw-value generation for attribute columns."""

from __future__ import annotations

from typing import Any, Callable, Protocol

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

        self._type_dispatch: dict[str, Callable[[AttributeLike, int], Any]] = {
            "integer": lambda attr, row_count: generate_integer(
                attr.name,
                attr.constraints,
                attr.distribution,
                row_count,
                self.rng,
            ),
            "float": lambda attr, row_count: generate_float(
                attr.name,
                attr.constraints,
                attr.distribution,
                row_count,
                self.rng,
            ),
            "categorical": lambda attr, row_count: generate_categorical(
                attr.name,
                attr.constraints,
                row_count,
                self.rng,
            ),
            "boolean": lambda attr, row_count: generate_boolean(
                attr.name,
                attr.constraints,
                row_count,
                self.rng,
            ),
            "date": lambda attr, row_count: generate_date(
                attr.name,
                attr.constraints,
                attr.distribution,
                row_count,
                self.rng,
            ),
            "text": lambda attr, row_count: generate_text(
                attr.name,
                attr.constraints,
                row_count,
                self.rng,
                self.faker,
            ),
            "email": lambda attr, row_count: generate_email(
                attr.name,
                row_count,
                self.faker,
            ),
            "name": lambda attr, row_count: generate_name(
                attr.name,
                row_count,
                self.faker,
            ),
            "address": lambda attr, row_count: generate_address(
                attr.name,
                row_count,
                self.faker,
            ),
        }

        self._semantic_dispatch: dict[str, Callable[[str, int], Any]] = {
            "email": lambda name, row_count: generate_email(
                name, row_count, self.faker
            ),
            "name": lambda name, row_count: generate_name(name, row_count, self.faker),
            "address": lambda name, row_count: generate_address(
                name, row_count, self.faker
            ),
            "phone": lambda name, row_count: generate_phone(
                name, row_count, self.faker
            ),
            "url": lambda name, row_count: generate_url(name, row_count, self.faker),
            "company": lambda name, row_count: generate_company(
                name, row_count, self.faker
            ),
            "city": lambda name, row_count: generate_city(name, row_count, self.faker),
            "country": lambda name, row_count: generate_country(
                name, row_count, self.faker
            ),
            "zip": lambda name, row_count: generate_zip(name, row_count, self.faker),
            "gender": lambda name, row_count: generate_gender(
                name, row_count, self.faker
            ),
        }

    def generate_column(self, attr: AttributeLike, row_count: int) -> Any:
        data_type = str(attr.data_type).lower()
        constraints = attr.constraints

        if data_type == "semantic":
            semantic_kind = str(constraints.get("semantic_type", "")).lower()
            semantic_handler = self._semantic_dispatch.get(semantic_kind)
            if semantic_handler is not None:
                return semantic_handler(attr.name, row_count)
            return generate_text(
                attr.name,
                constraints,
                row_count,
                self.rng,
                self.faker,
            )

        handler = self._type_dispatch.get(data_type)
        if handler is None:
            raise ValueError(f"Unsupported data type: {data_type}")
        return handler(attr, row_count)

    def detect_semantic_groups(
        self, attributes: list[AttributeLike]
    ) -> list[dict[str, Any]]:
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
        attributes: list[AttributeLike],
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


class AttributeLike(Protocol):
    """Minimal attribute contract required by CoreGenerator."""

    name: str
    data_type: str
    constraints: dict[str, Any]
    distribution: str
