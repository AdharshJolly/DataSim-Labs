"""Dataset generator orchestrating per-column generators and file export."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID

import numpy as np
import pandas as pd
from faker import Faker

from app.engine.generators.boolean_generator import generate_boolean
from app.engine.generators.categorical_generator import generate_categorical
from app.engine.generators.date_generator import generate_date
from app.engine.generators.faker_generator import (
    generate_address,
    generate_email,
    generate_name,
)
from app.engine.generators.float_generator import generate_float
from app.engine.generators.integer_generator import generate_integer
from app.engine.generators.text_generator import generate_text
from app.engine.null_injector import inject_nulls


@dataclass(slots=True)
class AttributeSpec:
    """Normalized attribute configuration used by the generation engine."""

    name: str
    data_type: str
    constraints: dict[str, Any]
    distribution: str
    null_percentage: float


class DatasetGenerator:
    """Generate DataFrames and export synthetic datasets in multiple formats."""

    def __init__(self, seed: int | None = None) -> None:
        self.seed = seed
        self.rng = np.random.default_rng(seed)
        self.faker = Faker()
        if seed is not None:
            self.faker.seed_instance(seed)

    def generate_dataframe(
        self,
        attributes: list[AttributeSpec],
        row_count: int,
    ) -> pd.DataFrame:
        """Generate a dataframe for the provided attributes and row count."""
        data: dict[str, pd.Series] = {}
        for attr in attributes:
            column = self._generate_column(attr=attr, row_count=row_count)
            data[attr.name] = inject_nulls(
                series=column,
                null_percentage=attr.null_percentage,
                rng=self.rng,
            )
        return pd.DataFrame(data)

    def generate_preview(
        self,
        attributes: list[AttributeSpec],
    ) -> list[dict[str, Any]]:
        """Generate a fixed-size 10-row preview payload."""
        frame = self.generate_dataframe(attributes=attributes, row_count=10)
        return frame.to_dict(orient="records")

    def export_dataset_files(
        self,
        dataset_id: UUID,
        attributes: list[AttributeSpec],
        row_count: int,
        formats: list[str],
        output_root: Path,
        chunk_size: int = 100_000,
    ) -> list[dict[str, Any]]:
        """Export datasets in requested formats, chunking large generations."""
        clean_formats = [
            fmt.lower() for fmt in formats if fmt.lower() in {"csv", "json", "jsonl", "excel"}
        ]
        if not clean_formats:
            clean_formats = ["csv"]

        dataset_dir = output_root / str(dataset_id)
        dataset_dir.mkdir(parents=True, exist_ok=True)

        outputs: list[dict[str, Any]] = []
        if "csv" in clean_formats:
            csv_path = dataset_dir / f"dataset_{dataset_id}.csv"
            self._write_csv(csv_path, attributes, row_count, chunk_size)
            outputs.append(self._file_metadata(csv_path, "csv"))

        if "json" in clean_formats:
            json_path = dataset_dir / f"dataset_{dataset_id}.json"
            self._write_json(json_path, attributes, row_count, chunk_size)
            outputs.append(self._file_metadata(json_path, "json"))

        if "jsonl" in clean_formats:
            jsonl_path = dataset_dir / f"dataset_{dataset_id}.jsonl"
            self._write_jsonl(jsonl_path, attributes, row_count, chunk_size)
            outputs.append(self._file_metadata(jsonl_path, "jsonl"))

        if "excel" in clean_formats:
            xlsx_path = dataset_dir / f"dataset_{dataset_id}.xlsx"
            self._write_excel(xlsx_path, attributes, row_count, chunk_size)
            outputs.append(self._file_metadata(xlsx_path, "excel"))

        return outputs

    def _generate_column(self, attr: AttributeSpec, row_count: int) -> pd.Series:
        """Dispatch one attribute to its dedicated generator."""
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

        raise ValueError(f"Unsupported data type: {data_type}")

    def _iter_chunks(self, row_count: int, chunk_size: int) -> list[int]:
        """Return chunk sizes that sum exactly to row_count."""
        full_chunks, remainder = divmod(row_count, chunk_size)
        chunks = [chunk_size] * full_chunks
        if remainder:
            chunks.append(remainder)
        return chunks or [row_count]

    def _write_csv(
        self,
        file_path: Path,
        attributes: list[AttributeSpec],
        row_count: int,
        chunk_size: int,
    ) -> None:
        """Write chunked CSV output."""
        first = True
        for current_chunk_size in self._iter_chunks(row_count, chunk_size):
            frame = self.generate_dataframe(attributes, current_chunk_size)
            frame.to_csv(
                file_path, mode="w" if first else "a", header=first, index=False
            )
            first = False

    def _write_json(
        self,
        file_path: Path,
        attributes: list[AttributeSpec],
        row_count: int,
        chunk_size: int,
    ) -> None:
        """Write a JSON array (all rows as a single top-level array)."""
        import json as _json

        with open(file_path, "w", encoding="utf-8") as fh:
            fh.write("[\n")
            first_row = True
            for current_chunk_size in self._iter_chunks(row_count, chunk_size):
                frame = self.generate_dataframe(attributes, current_chunk_size)
                records = frame.to_dict(orient="records")
                for record in records:
                    if not first_row:
                        fh.write(",\n")
                    fh.write("  " + _json.dumps(record, default=str))
                    first_row = False
            fh.write("\n]\n")

    def _write_jsonl(
        self,
        file_path: Path,
        attributes: list[AttributeSpec],
        row_count: int,
        chunk_size: int,
    ) -> None:
        """Write newline-delimited JSON (one record per line, .jsonl)."""
        first = True
        for current_chunk_size in self._iter_chunks(row_count, chunk_size):
            frame = self.generate_dataframe(attributes, current_chunk_size)
            frame.to_json(
                file_path,
                orient="records",
                lines=True,
                mode="w" if first else "a",
                date_format="iso",
            )
            first = False

    def _write_excel(
        self,
        file_path: Path,
        attributes: list[AttributeSpec],
        row_count: int,
        chunk_size: int,
    ) -> None:
        """Write XLSX output, auto-splitting into multiple sheets at Excel's row limit."""
        _EXCEL_ROW_LIMIT = 1_048_576
        sheet_index = 1
        sheet_name = f"dataset_{sheet_index}"
        startrow = 0
        first_sheet = True

        with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
            for current_chunk_size in self._iter_chunks(row_count, chunk_size):
                frame = self.generate_dataframe(attributes, current_chunk_size)
                remaining = frame

                while len(remaining) > 0:
                    # Rows available in the current sheet (excluding header row)
                    header_offset = 1 if startrow == 0 else 0
                    space = _EXCEL_ROW_LIMIT - startrow - header_offset

                    if space <= 0:
                        # Start a new sheet
                        sheet_index += 1
                        sheet_name = f"dataset_{sheet_index}"
                        startrow = 0
                        first_sheet = False

                    include_header = startrow == 0
                    header_offset = 1 if include_header else 0
                    space = _EXCEL_ROW_LIMIT - startrow - header_offset
                    chunk = remaining.iloc[:space]
                    remaining = remaining.iloc[space:]

                    chunk.to_excel(
                        writer,
                        sheet_name=sheet_name,
                        startrow=startrow,
                        index=False,
                        header=include_header,
                    )
                    startrow += len(chunk) + header_offset
                    _ = first_sheet  # suppress unused warning

    def _file_metadata(self, file_path: Path, export_format: str) -> dict[str, Any]:
        """Return metadata for a generated output file."""
        return {
            "format": export_format,
            "file_name": file_path.name,
            "file_path": str(file_path),
            "size_bytes": file_path.stat().st_size,
        }
