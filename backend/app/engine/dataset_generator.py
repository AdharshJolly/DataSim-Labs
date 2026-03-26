"""Dataset generator orchestrating per-column generators and file export."""

from __future__ import annotations

from collections import Counter
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
        realism_rules: list[dict] | None = None,
    ) -> pd.DataFrame:
        """Generate a dataframe for the provided attributes and row count."""
        frame, _ = self._generate_dataframe_with_stats(
            attributes=attributes,
            row_count=row_count,
            realism_rules=realism_rules,
        )
        return frame

    def generate_preview(
        self,
        attributes: list[AttributeSpec],
        realism_rules: list[dict] | None = None,
    ) -> list[dict[str, Any]]:
        """Generate a fixed-size 10-row preview payload."""
        frame = self.generate_dataframe(
            attributes=attributes, row_count=10, realism_rules=realism_rules
        )
        return frame.to_dict(orient="records")

    def export_dataset_files(
        self,
        dataset_id: UUID,
        attributes: list[AttributeSpec],
        row_count: int,
        formats: list[str],
        output_root: Path,
        chunk_size: int = 100_000,
        realism_rules: list[dict] | None = None,
        min_chunk_size: int = 10_000,
        target_cells_per_chunk: int = 1_500_000,
    ) -> dict[str, Any]:
        """Export datasets in one consistent pass and return files + quality report."""
        clean_formats = [
            fmt.lower()
            for fmt in formats
            if fmt.lower() in {"csv", "json", "jsonl", "excel"}
        ]
        if not clean_formats:
            clean_formats = ["csv"]

        dataset_dir = output_root / str(dataset_id)
        dataset_dir.mkdir(parents=True, exist_ok=True)

        file_paths: dict[str, Path] = {
            "csv": dataset_dir / f"dataset_{dataset_id}.csv",
            "json": dataset_dir / f"dataset_{dataset_id}.json",
            "jsonl": dataset_dir / f"dataset_{dataset_id}.jsonl",
            "excel": dataset_dir / f"dataset_{dataset_id}.xlsx",
        }

        for export_format in clean_formats:
            file_paths[export_format].unlink(missing_ok=True)

        effective_chunk_size = self._effective_chunk_size(
            base_chunk_size=chunk_size,
            attribute_count=max(1, len(attributes)),
            row_count=row_count,
            min_chunk_size=min_chunk_size,
            target_cells_per_chunk=target_cells_per_chunk,
        )

        csv_first = True
        jsonl_first = True
        json_first = True
        excel_writer: pd.ExcelWriter | None = None
        excel_state = {
            "sheet_index": 1,
            "sheet_name": "dataset_1",
            "startrow": 0,
        }

        if "json" in clean_formats:
            json_handle = open(file_paths["json"], "w", encoding="utf-8")
            json_handle.write("[\n")
        else:
            json_handle = None

        if "excel" in clean_formats:
            excel_writer = pd.ExcelWriter(file_paths["excel"], engine="openpyxl")

        quality = self._init_quality_state(attributes=attributes)

        try:
            for current_chunk_size in self._iter_chunks(
                row_count, effective_chunk_size
            ):
                frame, chunk_stats = self._generate_dataframe_with_stats(
                    attributes=attributes,
                    row_count=current_chunk_size,
                    realism_rules=realism_rules,
                )
                self._update_quality_state(quality, frame, chunk_stats)

                if "csv" in clean_formats:
                    frame.to_csv(
                        file_paths["csv"],
                        mode="w" if csv_first else "a",
                        header=csv_first,
                        index=False,
                    )
                    csv_first = False

                if "jsonl" in clean_formats:
                    frame.to_json(
                        file_paths["jsonl"],
                        orient="records",
                        lines=True,
                        mode="w" if jsonl_first else "a",
                        date_format="iso",
                    )
                    jsonl_first = False

                if json_handle is not None:
                    payload = frame.to_json(orient="records", date_format="iso")
                    records_blob = payload.strip()
                    if records_blob.startswith("[") and records_blob.endswith("]"):
                        records_blob = records_blob[1:-1].strip()
                    if records_blob:
                        if not json_first:
                            json_handle.write(",\n")
                        json_handle.write(records_blob)
                        json_first = False

                if excel_writer is not None:
                    self._append_excel_chunk(excel_writer, excel_state, frame)
        finally:
            if json_handle is not None:
                json_handle.write("\n]\n")
                json_handle.close()
            if excel_writer is not None:
                excel_writer.close()

        outputs = [
            self._file_metadata(file_paths[fmt], fmt)
            for fmt in clean_formats
            if file_paths[fmt].exists()
        ]

        quality_report = self._finalize_quality_report(
            quality,
            row_count=row_count,
            chunk_size_used=effective_chunk_size,
            requested_chunk_size=chunk_size,
        )

        # ── Statistical Validation ─────────────────────────────────────────────────
        validation_summary: dict[str, Any] | None = None
        try:
            from app.engine.profiling.validator import StatisticalValidator

            column_profiles: dict[str, Any] = {}
            for attr in attributes:
                dist_profile: dict[str, Any] = {
                    "type": attr.distribution,
                    "mean": float(
                        attr.constraints.get(
                            "mean",
                            (
                                float(attr.constraints.get("min", 0))
                                + float(attr.constraints.get("max", 100))
                            )
                            / 2,
                        )
                    ),
                    "std": float(
                        attr.constraints.get(
                            "std",
                            (
                                float(attr.constraints.get("max", 100))
                                - float(attr.constraints.get("min", 0))
                            )
                            / 6,
                        )
                    ),
                    "min": float(attr.constraints.get("min", 0)),
                    "max": float(attr.constraints.get("max", 100)),
                }
                if attr.data_type in ("categorical", "boolean"):
                    cats = attr.constraints.get("categories", [])
                    weights = attr.constraints.get("weights")
                    if cats:
                        if weights and len(weights) == len(cats):
                            total = sum(weights)
                            probs = [w / total for w in weights]
                        else:
                            probs = [1.0 / len(cats)] * len(cats)
                        dist_profile = {
                            "type": "weighted_categorical",
                            "categories": list(cats),
                            "probabilities": probs,
                        }

                column_profiles[attr.name] = {
                    "name": attr.name,
                    "data_type": attr.data_type,
                    "null_percentage": float(attr.null_percentage),
                    "distribution": dist_profile,
                }

            # Use the last generated chunk stored in quality state as a sample.
            if quality.get("_last_chunk") is not None:
                validation_df = quality["_last_chunk"]
            else:
                validation_df = self.generate_dataframe(
                    attributes=attributes,
                    row_count=min(2000, row_count),
                    realism_rules=realism_rules,
                )

            validator = StatisticalValidator()
            validation_summary = validator.validate(
                generated_df=validation_df,
                column_profiles=column_profiles,
                correlation_target=None,
            )
        except Exception as _val_exc:
            import logging as _log

            _log.getLogger(__name__).warning(
                "Validation step failed (non-fatal): %s", _val_exc
            )
        # ─────────────────────────────────────────────────────────────────────────────

        return {
            "files": outputs,
            "quality_report": quality_report,
            "validation_summary": validation_summary,
        }

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
        if data_type == "semantic":
            semantic_kind = str(constraints.get("semantic_type", "")).lower()
            if semantic_kind == "email":
                return generate_email(attr.name, row_count, self.faker)
            if semantic_kind == "name":
                return generate_name(attr.name, row_count, self.faker)
            if semantic_kind == "address":
                return generate_address(attr.name, row_count, self.faker)
            return generate_text(
                attr.name, constraints, row_count, self.rng, self.faker
            )

        raise ValueError(f"Unsupported data type: {data_type}")

    def _generate_dataframe_with_stats(
        self,
        attributes: list[AttributeSpec],
        row_count: int,
        realism_rules: list[dict] | None,
    ) -> tuple[pd.DataFrame, dict[str, Any]]:
        """Generate one chunk, apply realism, then inject nulls to preserve targets."""
        data: dict[str, pd.Series] = {}
        for attr in attributes:
            data[attr.name] = self._generate_column(attr=attr, row_count=row_count)

        frame = pd.DataFrame(data)
        realism_stats: dict[str, Any] = {
            "rule_impacts": {},
            "total_rows_affected": 0,
            "rule_count": 0,
        }

        if realism_rules:
            from app.engine.realism_processor import RealismProcessor  # deferred

            processor = RealismProcessor(faker=self.faker, rng=self.rng)
            frame, realism_stats = processor.apply_with_stats(frame, realism_rules)

        for attr in attributes:
            frame[attr.name] = inject_nulls(
                series=frame[attr.name],
                null_percentage=attr.null_percentage,
                rng=self.rng,
            )

        return frame, realism_stats

    def _iter_chunks(self, row_count: int, chunk_size: int) -> list[int]:
        """Return chunk sizes that sum exactly to row_count."""
        full_chunks, remainder = divmod(row_count, chunk_size)
        chunks = [chunk_size] * full_chunks
        if remainder:
            chunks.append(remainder)
        return chunks or [row_count]

    def _effective_chunk_size(
        self,
        base_chunk_size: int,
        attribute_count: int,
        row_count: int,
        min_chunk_size: int,
        target_cells_per_chunk: int,
    ) -> int:
        """Compute adaptive chunk size to reduce peak memory pressure."""
        by_cells = max(1, target_cells_per_chunk // max(1, attribute_count))
        bounded = min(base_chunk_size, by_cells)
        bounded = max(min_chunk_size, bounded)
        return max(1, min(bounded, row_count))

    def _append_excel_chunk(
        self,
        writer: pd.ExcelWriter,
        state: dict[str, Any],
        frame: pd.DataFrame,
    ) -> None:
        """Append chunk to xlsx, splitting sheets at Excel row limit."""
        excel_row_limit = 1_048_576
        remaining = frame

        while len(remaining) > 0:
            startrow = int(state["startrow"])
            include_header = startrow == 0
            header_offset = 1 if include_header else 0
            space = excel_row_limit - startrow - header_offset

            if space <= 0:
                state["sheet_index"] = int(state["sheet_index"]) + 1
                state["sheet_name"] = f"dataset_{state['sheet_index']}"
                state["startrow"] = 0
                startrow = 0
                include_header = True
                header_offset = 1
                space = excel_row_limit - 1

            chunk = remaining.iloc[:space]
            remaining = remaining.iloc[space:]

            chunk.to_excel(
                writer,
                sheet_name=str(state["sheet_name"]),
                startrow=startrow,
                index=False,
                header=include_header,
            )
            state["startrow"] = startrow + len(chunk) + header_offset

    def _init_quality_state(self, attributes: list[AttributeSpec]) -> dict[str, Any]:
        column_metrics = {
            attr.name: {
                "null_count": 0,
                "numeric_sum": 0.0,
                "numeric_count": 0,
                "numeric_min": None,
                "numeric_max": None,
                "top_counter": Counter(),
                "target_null_ratio": float(attr.null_percentage / 100.0),
            }
            for attr in attributes
        }

        return {
            "column_metrics": column_metrics,
            "rows_generated": 0,
            "rule_impacts": Counter(),
            "rules_total_rows_affected": 0,
            "rules_total_count": 0,
            "_last_chunk": None,
        }

    def _update_quality_state(
        self,
        quality: dict[str, Any],
        frame: pd.DataFrame,
        chunk_stats: dict[str, Any],
    ) -> None:
        quality["rows_generated"] += len(frame)

        for column in frame.columns:
            col_metric = quality["column_metrics"][column]
            series = frame[column]

            col_metric["null_count"] += int(series.isna().sum())

            numeric_series = pd.to_numeric(series, errors="coerce")
            numeric_non_null = numeric_series.dropna()
            if not numeric_non_null.empty:
                col_metric["numeric_sum"] += float(numeric_non_null.sum())
                col_metric["numeric_count"] += int(len(numeric_non_null))

                chunk_min = float(numeric_non_null.min())
                chunk_max = float(numeric_non_null.max())
                if (
                    col_metric["numeric_min"] is None
                    or chunk_min < col_metric["numeric_min"]
                ):
                    col_metric["numeric_min"] = chunk_min
                if (
                    col_metric["numeric_max"] is None
                    or chunk_max > col_metric["numeric_max"]
                ):
                    col_metric["numeric_max"] = chunk_max

            top_values = series.dropna().astype(str).value_counts().head(10)
            col_metric["top_counter"].update(top_values.to_dict())

        impacts = chunk_stats.get("rule_impacts", {})
        if isinstance(impacts, dict):
            for key, value in impacts.items():
                quality["rule_impacts"][str(key)] += int(value)

        quality["rules_total_rows_affected"] += int(
            chunk_stats.get("total_rows_affected", 0)
        )
        quality["rules_total_count"] = max(
            int(quality["rules_total_count"]),
            int(chunk_stats.get("rule_count", 0)),
        )

        quality["_last_chunk"] = frame  # keep reference to last chunk for validator

    def _finalize_quality_report(
        self,
        quality: dict[str, Any],
        row_count: int,
        chunk_size_used: int,
        requested_chunk_size: int,
    ) -> dict[str, Any]:
        report_columns: dict[str, Any] = {}
        alerts: list[dict[str, Any]] = []

        for column, metric in quality["column_metrics"].items():
            rows_generated = max(1, int(quality["rows_generated"]))
            null_count = int(metric["null_count"])
            null_ratio = round(null_count / rows_generated, 6)
            target_null_ratio = float(metric.get("target_null_ratio", 0.0))
            null_drift = abs(null_ratio - target_null_ratio)

            numeric_mean = None
            if metric["numeric_count"] > 0:
                numeric_mean = float(metric["numeric_sum"] / metric["numeric_count"])

            report_columns[column] = {
                "null_count": null_count,
                "null_ratio": null_ratio,
                "target_null_ratio": round(target_null_ratio, 6),
                "null_drift": round(null_drift, 6),
                "numeric_min": metric["numeric_min"],
                "numeric_max": metric["numeric_max"],
                "numeric_mean": numeric_mean,
                "top_values": dict(metric["top_counter"].most_common(5)),
            }

            if null_drift > 0.03:
                alerts.append(
                    {
                        "severity": "warning",
                        "type": "null_ratio_drift",
                        "column": column,
                        "details": (
                            "Observed null ratio differs from configured target by "
                            f"{round(null_drift, 6)}"
                        ),
                    }
                )

        rule_count = int(quality["rules_total_count"])
        total_rows_affected = int(quality["rules_total_rows_affected"])
        if rule_count > 0 and total_rows_affected == 0:
            alerts.append(
                {
                    "severity": "warning",
                    "type": "realism_no_effect",
                    "details": "Realism rules were provided but did not change any rows.",
                }
            )

        return {
            "rows_generated": int(quality["rows_generated"]),
            "requested_rows": row_count,
            "requested_chunk_size": requested_chunk_size,
            "effective_chunk_size": chunk_size_used,
            "columns": report_columns,
            "alerts": alerts,
            "realism": {
                "rule_count": rule_count,
                "total_rows_affected": total_rows_affected,
                "rule_impacts": dict(quality["rule_impacts"]),
            },
        }

    def _file_metadata(self, file_path: Path, export_format: str) -> dict[str, Any]:
        """Return metadata for a generated output file."""
        return {
            "format": export_format,
            "file_name": file_path.name,
            "file_path": str(file_path),
            "size_bytes": file_path.stat().st_size,
        }
