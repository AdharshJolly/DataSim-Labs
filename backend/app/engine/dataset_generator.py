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

from app.engine.contracts import GeneratorInterface
from app.engine.context.generation_context import GenerationContext
from app.engine.generation.chunk_processor import ChunkProcessor
from app.engine.generation.core_generator import CoreGenerator
from app.engine.generation.pipeline import GenerationPipeline
from app.engine.rules.rule_engine import SemanticRuleEngine
from app.engine.rules.rule_executor import sort_rules_by_priority


@dataclass(slots=True)
class AttributeSpec:
    """Normalized attribute configuration used by the generation engine."""

    name: str
    data_type: str
    constraints: dict[str, Any]
    distribution: str
    null_percentage: float


class DatasetGenerator(GeneratorInterface):
    """Generate DataFrames and export synthetic datasets in multiple formats."""

    def __init__(self, seed: int | None = None) -> None:
        self.seed = seed
        self.rng = np.random.default_rng(seed)
        self.faker = Faker()
        if seed is not None:
            self.faker.seed_instance(seed)
        self.core_generator = CoreGenerator(rng=self.rng, faker=self.faker)
        self.chunk_processor = ChunkProcessor()
        self.generation_pipeline = GenerationPipeline(
            core_generator=self.core_generator,
            rng=self.rng,
            faker=self.faker,
            apply_semantic_rules=self._apply_semantic_rules,
            topological_sort_rules=self._topological_sort_semantic_rules,
            extract_dependencies=self._extract_dependencies,
        )

    def generate_dataframe(
        self,
        attributes: list[AttributeSpec] | None = None,
        row_count: int | None = None,
        realism_rules: list[dict] | None = None,
        semantic_groups: list[dict[str, Any]] | None = None,
        semantic_rules: list[dict[str, Any]] | None = None,
        context: GenerationContext | None = None,
    ) -> pd.DataFrame:
        """Generate a dataframe for the provided attributes and row count."""
        (
            resolved_attributes,
            resolved_row_count,
            resolved_realism_rules,
            resolved_semantic_rules,
        ) = self._resolve_generation_request(
            attributes=attributes,
            row_count=row_count,
            realism_rules=realism_rules,
            semantic_rules=semantic_rules,
            context=context,
        )
        frame, _ = self._generate_dataframe_with_stats(
            attributes=resolved_attributes,
            row_count=resolved_row_count,
            realism_rules=resolved_realism_rules,
            semantic_groups=semantic_groups,
            semantic_rules=resolved_semantic_rules,
        )
        return frame

    def generate_preview(
        self,
        attributes: list[AttributeSpec] | None = None,
        realism_rules: list[dict] | None = None,
        semantic_groups: list[dict[str, Any]] | None = None,
        semantic_rules: list[dict[str, Any]] | None = None,
        context: GenerationContext | None = None,
    ) -> list[dict[str, Any]]:
        """Generate a fixed-size 10-row preview payload."""
        preview_row_count = 10
        if context is not None:
            configured_preview_rows = context.config.get("preview_row_count")
            if isinstance(configured_preview_rows, int) and configured_preview_rows > 0:
                preview_row_count = configured_preview_rows

        frame = self.generate_dataframe(
            attributes=attributes,
            row_count=preview_row_count,
            realism_rules=realism_rules,
            semantic_groups=semantic_groups,
            semantic_rules=semantic_rules,
            context=context,
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
        semantic_groups: list[dict[str, Any]] | None = None,
        semantic_rules: list[dict[str, Any]] | None = None,
        min_chunk_size: int = 10_000,
        target_cells_per_chunk: int = 1_500_000,
        context: GenerationContext | None = None,
    ) -> dict[str, Any]:
        """Export datasets in one consistent pass and return files + quality report."""
        (
            resolved_attributes,
            resolved_row_count,
            resolved_realism_rules,
            resolved_semantic_rules,
        ) = self._resolve_generation_request(
            attributes=attributes,
            row_count=row_count,
            realism_rules=realism_rules,
            semantic_rules=semantic_rules,
            context=context,
        )

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

        resolved_chunk_size = self.chunk_processor.resolve_chunk_size(
            base_chunk_size=chunk_size,
            attribute_count=max(1, len(resolved_attributes)),
            row_count=resolved_row_count,
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

        quality = self._init_quality_state(attributes=resolved_attributes)

        try:
            for current_chunk_size in self.chunk_processor.iterate_chunks(
                resolved_row_count, resolved_chunk_size
            ):
                frame, chunk_stats = self._generate_dataframe_with_stats(
                    attributes=resolved_attributes,
                    row_count=current_chunk_size,
                    realism_rules=resolved_realism_rules,
                    semantic_groups=semantic_groups,
                    semantic_rules=resolved_semantic_rules,
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
            row_count=resolved_row_count,
            chunk_size_used=resolved_chunk_size,
            requested_chunk_size=chunk_size,
        )

        validation_summary: dict[str, Any] | None = None

        return {
            "files": outputs,
            "quality_report": quality_report,
            "validation_summary": validation_summary,
        }

    def _resolve_generation_request(
        self,
        attributes: list[AttributeSpec] | None,
        row_count: int | None,
        realism_rules: list[dict] | None,
        semantic_rules: list[dict[str, Any]] | None,
        context: GenerationContext | None,
    ) -> tuple[
        list[AttributeSpec],
        int,
        list[dict] | None,
        list[dict[str, Any]] | None,
    ]:
        """Resolve legacy args plus optional generation context into one request."""
        resolved_attributes = attributes
        resolved_realism_rules = realism_rules
        resolved_semantic_rules = semantic_rules

        configured_row_count: int | None = None
        if context is not None:
            if resolved_attributes is None:
                resolved_attributes = context.attributes
            if resolved_realism_rules is None:
                resolved_realism_rules = context.realism_rules
            if resolved_semantic_rules is None:
                resolved_semantic_rules = context.semantic_rules

            config_row_count = context.config.get("row_count")
            if isinstance(config_row_count, int):
                configured_row_count = config_row_count

        resolved_row_count = (
            row_count if row_count is not None else configured_row_count
        )

        if resolved_attributes is None:
            raise ValueError("attributes are required for dataframe generation")
        if resolved_row_count is None or resolved_row_count <= 0:
            raise ValueError("row_count must be a positive integer")

        return (
            resolved_attributes,
            resolved_row_count,
            resolved_realism_rules,
            resolved_semantic_rules,
        )

    def _generate_column(self, attr: AttributeSpec, row_count: int) -> pd.Series:
        """Dispatch one attribute to its dedicated generator."""
        return self.core_generator.generate_column(attr=attr, row_count=row_count)

    def _generate_dataframe_with_stats(
        self,
        attributes: list[AttributeSpec],
        row_count: int,
        realism_rules: list[dict] | None,
        semantic_groups: list[dict[str, Any]] | None,
        semantic_rules: list[dict[str, Any]] | None,
    ) -> tuple[pd.DataFrame, dict[str, Any]]:
        """Generate one chunk, apply realism, then inject nulls to preserve targets."""
        return self.generation_pipeline.generate_chunk(
            attributes=attributes,
            row_count=row_count,
            realism_rules=realism_rules,
            semantic_groups=semantic_groups,
            semantic_rules=semantic_rules,
        )

    def _extract_dependencies(
        self,
        rules: list[dict[str, Any]],
    ) -> tuple[set[str], set[str]]:
        dependent_cols: set[str] = set()
        source_cols: set[str] = set()

        for rule in rules:
            target = str(rule.get("target", "")).strip()
            if target:
                dependent_cols.add(target)

            sources = rule.get("sources", []) or []
            if isinstance(sources, str):
                sources = [sources]
            for src in sources:
                src_name = str(src).strip()
                if src_name:
                    source_cols.add(src_name)

        independent_cols = source_cols - dependent_cols
        return independent_cols, dependent_cols

    def _topological_sort_semantic_rules(
        self,
        rules: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        if not rules:
            return []

        targets = {
            str(rule.get("target", "")).strip()
            for rule in rules
            if str(rule.get("target", "")).strip()
        }

        unresolved = list(sort_rules_by_priority(rules))
        sorted_rules: list[dict[str, Any]] = []
        resolved_targets: set[str] = set()

        while unresolved:
            progress = False
            remaining: list[dict[str, Any]] = []

            for rule in unresolved:
                sources = rule.get("sources", []) or []
                if isinstance(sources, str):
                    sources = [sources]

                can_run = all(
                    str(src) not in targets or str(src) in resolved_targets
                    for src in sources
                )
                if can_run:
                    sorted_rules.append(rule)
                    target = str(rule.get("target", "")).strip()
                    if target:
                        resolved_targets.add(target)
                    progress = True
                else:
                    remaining.append(rule)

            if not progress:
                sorted_rules.extend(sort_rules_by_priority(remaining))
                break

            unresolved = remaining

        return sorted_rules

    def _apply_semantic_rules(
        self,
        frame: pd.DataFrame,
        rules: list[dict[str, Any]],
        attributes: list[AttributeSpec],
    ) -> tuple[pd.DataFrame, dict[str, Any]]:
        attribute_names = {attr.name for attr in attributes}
        metrics: dict[str, dict[str, Any]] = {}
        totals = {
            "rules_considered": len(rules),
            "attempted_rows": 0,
            "applied_rows": 0,
            "skipped_rows": 0,
            "error_rows": 0,
        }

        def ensure_metric(rule: dict[str, Any], target: str) -> dict[str, Any]:
            rule_id = str(rule.get("id", "") or "unknown_rule")
            if rule_id not in metrics:
                metrics[rule_id] = {
                    "rule_id": rule_id,
                    "target": target,
                    "attempted_rows": 0,
                    "applied_rows": 0,
                    "skipped_rows": 0,
                    "error_rows": 0,
                }
            return metrics[rule_id]

        for rule in rules:
            target = str(rule.get("target", "")).strip()
            if target and target not in frame.columns and target in attribute_names:
                frame[target] = None

        for idx in frame.index:
            row_context = frame.loc[idx].to_dict()
            row_context["__rng__"] = self.rng
            for rule in rules:
                target = str(rule.get("target", "")).strip()
                if not target or target not in attribute_names:
                    continue
                metric = ensure_metric(rule, target)
                sources = rule.get("sources", []) or []
                if isinstance(sources, str):
                    sources = [sources]
                if any(str(src) not in row_context for src in sources):
                    metric["skipped_rows"] += 1
                    totals["skipped_rows"] += 1
                    continue

                metric["attempted_rows"] += 1
                totals["attempted_rows"] += 1

                try:
                    value = SemanticRuleEngine.apply_rule(rule, row_context)
                except Exception:
                    metric["error_rows"] += 1
                    totals["error_rows"] += 1
                    continue
                if value is None:
                    metric["skipped_rows"] += 1
                    totals["skipped_rows"] += 1
                    continue
                frame.at[idx, target] = value
                row_context[target] = value
                metric["applied_rows"] += 1
                totals["applied_rows"] += 1

        return frame, {
            "rule_metrics": metrics,
            "totals": totals,
        }

    def _detect_semantic_groups(
        self,
        attributes: list[AttributeSpec],
    ) -> list[dict[str, Any]]:
        """Infer identity groups from configured attributes using semantic type heuristics."""
        return self.core_generator.detect_semantic_groups(attributes=attributes)

    def _generate_semantic_group_columns(
        self,
        groups: list[dict[str, Any]],
        attributes: list[AttributeSpec],
        row_count: int,
    ) -> dict[str, list[str]]:
        return self.core_generator.generate_semantic_group_columns(
            groups=groups,
            attributes=attributes,
            row_count=row_count,
        )

    def _iter_chunks(self, row_count: int, chunk_size: int) -> list[int]:
        """Backward-compatible wrapper for shared chunk helper."""
        return self.chunk_processor.iterate_chunks(
            row_count=row_count,
            chunk_size=chunk_size,
        )

    def _effective_chunk_size(
        self,
        base_chunk_size: int,
        attribute_count: int,
        row_count: int,
        min_chunk_size: int,
        target_cells_per_chunk: int,
    ) -> int:
        """Backward-compatible wrapper for shared chunk-size helper."""
        return self.chunk_processor.resolve_chunk_size(
            base_chunk_size=base_chunk_size,
            attribute_count=attribute_count,
            row_count=row_count,
            min_chunk_size=min_chunk_size,
            target_cells_per_chunk=target_cells_per_chunk,
        )

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
            "semantic_rule_metrics": {},
            "semantic_rule_totals": {
                "rules_considered": 0,
                "attempted_rows": 0,
                "applied_rows": 0,
                "skipped_rows": 0,
                "error_rows": 0,
            },
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

        semantic_stats = chunk_stats.get("semantic_rules", {})
        semantic_rule_metrics = semantic_stats.get("rule_metrics", {})
        if isinstance(semantic_rule_metrics, dict):
            for rule_id, metric in semantic_rule_metrics.items():
                current = quality["semantic_rule_metrics"].setdefault(
                    str(rule_id),
                    {
                        "rule_id": str(rule_id),
                        "target": metric.get("target"),
                        "attempted_rows": 0,
                        "applied_rows": 0,
                        "skipped_rows": 0,
                        "error_rows": 0,
                    },
                )
                current["attempted_rows"] += int(metric.get("attempted_rows", 0))
                current["applied_rows"] += int(metric.get("applied_rows", 0))
                current["skipped_rows"] += int(metric.get("skipped_rows", 0))
                current["error_rows"] += int(metric.get("error_rows", 0))

        semantic_totals = semantic_stats.get("totals", {})
        if isinstance(semantic_totals, dict):
            for key in quality["semantic_rule_totals"].keys():
                value = int(semantic_totals.get(key, 0))
                if key == "rules_considered":
                    quality["semantic_rule_totals"][key] = max(
                        int(quality["semantic_rule_totals"][key]),
                        value,
                    )
                else:
                    quality["semantic_rule_totals"][key] += value

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
            "semantic_rules": {
                "rule_metrics": quality["semantic_rule_metrics"],
                "totals": quality["semantic_rule_totals"],
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
