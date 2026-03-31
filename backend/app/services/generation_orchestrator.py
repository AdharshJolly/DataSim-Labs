"""
generation_orchestrator.py

Orchestrates dataset generation workflow including orchestration, artifact management,
and quality evaluation.
"""

import json
import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
import uuid

import numpy as np
import pandas as pd
from pymongo.database import Database
from scipy.stats import anderson_ksamp, ks_2samp

from app.core.config import settings
from app.engine.dataset_generator import AttributeSpec, DatasetGenerator
from app.models.dataset import DatasetStatus, DatasetVersion
from app.engine.realism_planner import RealismPlanner
from app.engine.semantic_rule_engine import (
    build_deterministic_execution_order,
    normalize_conflict_policy,
    validate_semantic_rules,
)
from app.schemas.dataset import AttributeConfig
from app.services.dataset_repository import DatasetRepository


class GenerationOrchestrator:
    """Orchestrates dataset generation workflow."""

    @staticmethod
    def create_dataset_version(
        db: Database,
        user_id: uuid.UUID,
        dataset_id: uuid.UUID,
        attributes: list[AttributeConfig],
        seed: int | None = None,
        correlations: list[dict[str, Any]] | None = None,
    ) -> DatasetVersion:
        """Create a dataset version and attach inferred realism plan metadata."""
        attr_names = [attr.name for attr in attributes]
        if len(attr_names) != len(set(attr_names)):
            raise ValueError("Attribute names must be unique within a version")

        dataset = DatasetRepository.get_dataset(
            db=db,
            user_id=user_id,
            dataset_id=dataset_id,
        )

        planner_specs = [
            AttributeSpec(
                name=attribute.name,
                data_type=attribute.type.value,
                constraints=attribute.constraints,
                distribution=attribute.distribution.value,
                null_percentage=attribute.null_percentage,
            )
            for attribute in attributes
        ]

        realism_plan = GenerationOrchestrator.plan_realism_rules(
            attributes=planner_specs
        )
        realism_rules = realism_plan.get("rules", [])

        config_json = {
            "attributes": [
                attribute.model_dump(mode="json") for attribute in attributes
            ],
            "seed": seed,
            "correlations": correlations or [],
            "realism_rules": realism_rules,
            "realism": {
                "rules": realism_rules,
                "metadata": realism_plan.get("metadata", {}),
            },
        }

        return DatasetRepository.create_dataset_version(
            db=db,
            dataset=dataset,
            attributes=attributes,
            config_json=config_json,
            seed=seed,
        )

    @staticmethod
    def resolve_effective_dataset_status(
        dataset_id: uuid.UUID,
        current_status: DatasetStatus,
        output_root: Path,
        active_job_dataset_ids: set[str] | None = None,
    ) -> DatasetStatus:
        """Resolve dynamic status using active jobs and on-disk artifacts."""
        if current_status is DatasetStatus.archived:
            return DatasetStatus.archived

        if active_job_dataset_ids and str(dataset_id) in active_job_dataset_ids:
            return DatasetStatus.generating

        files = GenerationOrchestrator.list_generated_files(
            dataset_id=dataset_id,
            output_root=output_root,
        )
        return DatasetStatus.active if files else DatasetStatus.draft

    @staticmethod
    def generate_preview(
        db: Database,
        user_id: uuid.UUID,
        dataset_version_id: uuid.UUID,
        seed: int | None = None,
    ) -> dict[str, Any]:
        """Generate a 10-row preview from persisted attribute configuration."""
        version = DatasetRepository.get_dataset_version(db, dataset_version_id)
        DatasetRepository.get_dataset(
            db=db, user_id=user_id, dataset_id=version.dataset_id
        )

        attributes = GenerationOrchestrator._load_attributes_as_specs(
            db, dataset_version_id
        )
        realism_config = version.config_json.get("realism")
        if isinstance(realism_config, dict) and isinstance(
            realism_config.get("rules"), list
        ):
            realism_rules = realism_config.get("rules", [])
        else:
            realism_rules = version.config_json.get("realism_rules", [])
        semantic_rules = version.config_json.get("semantic_rules", [])
        if not isinstance(semantic_rules, list):
            semantic_rules = []
        semantic_settings = version.config_json.get("semantic_rule_settings", {})
        conflict_policy = normalize_conflict_policy(
            (semantic_settings or {}).get("conflict_policy")
        )
        available_columns = [attribute.name for attribute in attributes]
        semantic_validation = validate_semantic_rules(
            semantic_rules,
            available_columns=available_columns,
            conflict_policy=conflict_policy,
        )
        semantic_ordered_rules = build_deterministic_execution_order(
            semantic_validation.get("sanitized_rules", []),
            conflict_policy=conflict_policy,
        )

        generator_seed = seed if seed is not None else version.seed
        generator = DatasetGenerator(seed=generator_seed)
        frame = generator.generate_dataframe(
            attributes=attributes,
            row_count=10,
            realism_rules=realism_rules,
            semantic_rules=semantic_ordered_rules,
        )
        return {
            "data": frame.to_dict(orient="records"),
            "comparison": GenerationOrchestrator._build_preview_comparison(
                attributes=attributes,
                frame=frame,
                seed=generator_seed,
            ),
        }

    @staticmethod
    def explain_dataset_row(
        db: Database,
        user_id: uuid.UUID,
        dataset_version_id: uuid.UUID,
        row_index: int = 0,
        seed: int | None = None,
        column: str | None = None,
    ) -> dict[str, Any]:
        """Explain generated values for a preview row with lightweight provenance."""
        version = DatasetRepository.get_dataset_version_for_user(
            db=db,
            user_id=user_id,
            dataset_version_id=dataset_version_id,
        )

        attributes = GenerationOrchestrator._load_attributes_as_specs(
            db, dataset_version_id
        )
        if not attributes:
            raise ValueError("Dataset version has no attributes")

        available_columns = [attribute.name for attribute in attributes]

        realism_config = version.config_json.get("realism")
        if isinstance(realism_config, dict) and isinstance(
            realism_config.get("rules"), list
        ):
            realism_rules = realism_config.get("rules", [])
        else:
            realism_rules = version.config_json.get("realism_rules", [])

        semantic_rules = version.config_json.get("semantic_rules", [])
        if not isinstance(semantic_rules, list):
            semantic_rules = []
        semantic_settings = version.config_json.get("semantic_rule_settings", {})
        conflict_policy = normalize_conflict_policy(
            (semantic_settings or {}).get("conflict_policy")
        )
        semantic_validation = validate_semantic_rules(
            semantic_rules,
            available_columns=available_columns,
            conflict_policy=conflict_policy,
        )
        semantic_ordered_rules = build_deterministic_execution_order(
            semantic_validation.get("sanitized_rules", []),
            conflict_policy=conflict_policy,
        )

        generator_seed = seed if seed is not None else version.seed
        base_generator = DatasetGenerator(seed=generator_seed)
        base_frame = base_generator.generate_dataframe(
            attributes=attributes,
            row_count=10,
            realism_rules=realism_rules,
            semantic_rules=[],
        )

        final_generator = DatasetGenerator(seed=generator_seed)
        final_frame = final_generator.generate_dataframe(
            attributes=attributes,
            row_count=10,
            realism_rules=realism_rules,
            semantic_rules=semantic_ordered_rules,
        )

        if row_index >= len(final_frame.index):
            raise ValueError("row_index out of range for preview dataset")

        base_row = base_frame.iloc[row_index].to_dict()
        final_row = final_frame.iloc[row_index].to_dict()

        rules_by_target: dict[str, list[dict[str, Any]]] = {}
        for rule in semantic_ordered_rules:
            target = str(rule.get("target", "")).strip()
            if not target:
                continue
            rules_by_target.setdefault(target, []).append(rule)

        trace: dict[str, dict[str, Any]] = {}
        for key, value in final_row.items():
            entry: dict[str, Any] = {
                "value": GenerationOrchestrator._normalize_explain_value(value),
                "source": "attribute_generator",
                "generator": "base_distribution",
                "rule": None,
                "depends_on": [],
            }

            target_rules = rules_by_target.get(key, [])
            if target_rules and base_row.get(key) != value:
                applied_rule = target_rules[-1]
                transform = applied_rule.get("transform", {})
                transform_type = str(transform.get("type", "rule")).strip() or "rule"
                entry["source"] = f"semantic_{transform_type}"
                entry["generator"] = transform_type
                entry["rule"] = str(
                    applied_rule.get("id") or applied_rule.get("type") or "semantic_rule"
                )
                entry["depends_on"] = [
                    str(source)
                    for source in applied_rule.get("sources", [])
                    if isinstance(source, str) and source.strip()
                ]

            trace[key] = entry

        safe_row = {
            key: GenerationOrchestrator._normalize_explain_value(val)
            for key, val in final_row.items()
        }

        if column:
            if column not in safe_row:
                raise ValueError(f"Column '{column}' not found in generated row")
            safe_row = {column: safe_row[column]}
            trace = {column: trace[column]}

        return {
            "dataset_version_id": dataset_version_id,
            "row_index": row_index,
            "row": safe_row,
            "trace": trace,
        }

    @staticmethod
    def plan_realism_rules(
        attributes: list[AttributeSpec],
        api_key: str | None = None,
    ) -> dict[str, Any]:
        """Generate realism rules for attributes using Gemini."""
        return RealismPlanner.plan_with_metadata(
            attributes=attributes,
            api_key=api_key or settings.gemini_api_key,
        )

    @staticmethod
    def generate_dataset_files(
        db: Database,
        user_id: uuid.UUID,
        dataset_id: uuid.UUID,
        row_count: int,
        formats: list[str],
        output_root: Path,
        chunk_size: int,
        seed: int | None = None,
        dataset_version_id: uuid.UUID | None = None,
        retention_hours: int = 24,
        enforce_sync_limits: bool = True,
    ) -> dict[str, Any]:
        """Generate and export full datasets for a dataset's latest version."""
        dataset = DatasetRepository.get_dataset(
            db=db, user_id=user_id, dataset_id=dataset_id
        )

        target_version_id = dataset_version_id or dataset.latest_version_id
        if target_version_id is None:
            raise ValueError("Dataset has no attribute configuration")

        owned_version = DatasetRepository.get_dataset_version(db, target_version_id)

        attributes = GenerationOrchestrator._load_attributes_as_specs(
            db, target_version_id
        )
        if not attributes:
            raise ValueError("Dataset version has no attributes")

        preflight = GenerationOrchestrator.preflight_generation(
            db=db,
            user_id=user_id,
            dataset_id=dataset_id,
            dataset_version_id=target_version_id,
            row_count=row_count,
            formats=formats,
        )
        if enforce_sync_limits and preflight.get("requires_async"):
            raise ValueError(
                "Requested generation is too large for sync mode. Use /generate-async for this payload."
            )

        realism_config = owned_version.config_json.get("realism")
        if isinstance(realism_config, dict) and isinstance(
            realism_config.get("rules"), list
        ):
            realism_rules = realism_config.get("rules", [])
        else:
            realism_rules = owned_version.config_json.get("realism_rules", [])
        semantic_rules = owned_version.config_json.get("semantic_rules", [])
        if not isinstance(semantic_rules, list):
            semantic_rules = []
        semantic_settings = owned_version.config_json.get("semantic_rule_settings", {})
        conflict_policy = normalize_conflict_policy(
            (semantic_settings or {}).get("conflict_policy")
        )
        available_columns = [attribute.name for attribute in attributes]
        semantic_validation = validate_semantic_rules(
            semantic_rules,
            available_columns=available_columns,
            conflict_policy=conflict_policy,
        )
        semantic_ordered_rules = build_deterministic_execution_order(
            semantic_validation.get("sanitized_rules", []),
            conflict_policy=conflict_policy,
        )

        GenerationOrchestrator.cleanup_old_artifacts(
            db=db,
            output_root=output_root,
            max_age_hours=retention_hours,
        )
        generator_seed = seed if seed is not None else owned_version.seed
        generator = DatasetGenerator(seed=generator_seed)
        generation_signature = GenerationOrchestrator._build_generation_signature(
            dataset_id=dataset.id,
            dataset_version_id=owned_version.id,
            row_count=row_count,
            formats=formats,
            seed=generator_seed,
            attributes=attributes,
            realism_rules=realism_rules,
            realism_metadata=(
                realism_config.get("metadata", {})
                if isinstance(realism_config, dict)
                else {}
            ),
            correlations=(
                owned_version.config_json.get("correlations", [])
                if isinstance(owned_version.config_json, dict)
                else []
            ),
        )

        generation_result = generator.export_dataset_files(
            dataset_id=dataset_id,
            attributes=attributes,
            row_count=row_count,
            formats=formats,
            output_root=output_root,
            chunk_size=chunk_size,
            realism_rules=realism_rules,
            semantic_rules=semantic_ordered_rules,
            min_chunk_size=settings.generation_min_chunk_size,
            target_cells_per_chunk=settings.generation_target_cells_per_chunk,
        )

        run_payload = {
            "generation_signature": generation_signature,
            "dataset_id": str(dataset.id),
            "dataset_version_id": str(owned_version.id),
            "user_id": str(user_id),
            "row_count": row_count,
            "formats": sorted([fmt.lower() for fmt in formats]),
            "seed": generator_seed,
            "quality_report": generation_result.get("quality_report", {}),
            "files": generation_result.get("files", []),
            "created_at": datetime.now(timezone.utc),
        }
        run_id = GenerationOrchestrator._record_generation_run(
            db=db, run_payload=run_payload
        )
        GenerationOrchestrator.record_generation_artifacts(
            db=db,
            dataset_id=dataset.id,
            generation_run_id=run_id,
            files=generation_result.get("files", []),
            retention_hours=retention_hours,
        )
        comparison = GenerationOrchestrator._compare_with_previous_run(
            db=db,
            dataset_id=dataset.id,
            current_run_id=run_id,
            current_quality=run_payload["quality_report"],
        )
        quality_guardrails = GenerationOrchestrator.evaluate_quality_guardrails(
            quality_report=run_payload["quality_report"],
        )
        quality_dashboard = GenerationOrchestrator.build_quality_dashboard(
            quality_report=generation_result.get("quality_report"),
            validation_summary=generation_result.get("validation_summary"),
            row_count=row_count,
        )

        generation_result["generation_signature"] = generation_signature
        generation_result["generation_run_id"] = run_id
        generation_result["comparison"] = comparison
        generation_result["quality_guardrails"] = quality_guardrails
        generation_result["quality_dashboard"] = quality_dashboard
        generation_result["semantic_rule_metrics"] = (
            generation_result.get("quality_report", {}) or {}
        ).get("semantic_rules")
        return generation_result

    @staticmethod
    def preflight_generation(
        db: Database,
        user_id: uuid.UUID,
        dataset_id: uuid.UUID,
        row_count: int,
        formats: list[str],
        dataset_version_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        """Check if generation would exceed sync limits."""
        dataset = DatasetRepository.get_dataset(
            db=db, user_id=user_id, dataset_id=dataset_id
        )

        target_version_id = dataset_version_id or dataset.latest_version_id
        if target_version_id is None:
            raise ValueError("Dataset has no attribute configuration")

        attributes = GenerationOrchestrator._load_attributes_as_specs(
            db, target_version_id
        )
        if not attributes:
            raise ValueError("Dataset version has no attributes")

        estimated_cells = int(max(1, row_count) * max(1, len(attributes)))
        estimated_output_bytes = GenerationOrchestrator._estimate_dataset_size_bytes(
            row_count=row_count,
            attributes=attributes,
            formats=formats,
        )

        issues: list[dict[str, str]] = []
        if row_count > settings.generation_sync_row_limit:
            issues.append(
                {
                    "level": "warning",
                    "code": "row_limit",
                    "message": (
                        f"Row count {row_count} exceeds sync limit "
                        f"{settings.generation_sync_row_limit}."
                    ),
                }
            )

        if estimated_cells > settings.generation_sync_cell_limit:
            issues.append(
                {
                    "level": "warning",
                    "code": "cell_limit",
                    "message": (
                        f"Estimated cell count {estimated_cells} exceeds sync limit "
                        f"{settings.generation_sync_cell_limit}."
                    ),
                }
            )

        max_bytes = settings.generation_estimated_output_mb_limit * 1024 * 1024
        if estimated_output_bytes > max_bytes:
            issues.append(
                {
                    "level": "warning",
                    "code": "estimated_output_size",
                    "message": (
                        "Estimated output size exceeds configured sync safety limit "
                        f"({settings.generation_estimated_output_mb_limit} MB)."
                    ),
                }
            )

        requires_async = bool(issues)
        return {
            "ok": not requires_async,
            "requires_async": requires_async,
            "estimated_cells": estimated_cells,
            "estimated_output_bytes": estimated_output_bytes,
            "issues": issues,
        }

    @staticmethod
    def list_generated_files(
        dataset_id: uuid.UUID,
        output_root: Path,
    ) -> list[dict[str, Any]]:
        """List generated files available for a dataset on disk."""
        dataset_dir = output_root / str(dataset_id)
        if not dataset_dir.exists():
            return []

        result: list[dict[str, Any]] = []
        for path in sorted(dataset_dir.glob("*")):
            if not path.is_file():
                continue

            suffix = path.suffix.lower()
            if suffix == ".csv":
                export_format = "csv"
            elif suffix == ".json":
                export_format = "json"
            elif suffix == ".jsonl":
                export_format = "jsonl"
            elif suffix == ".xlsx":
                export_format = "excel"
            else:
                continue

            result.append(
                {
                    "format": export_format,
                    "file_name": path.name,
                    "size_bytes": path.stat().st_size,
                }
            )

        return result

    @staticmethod
    def resolve_generated_file(
        dataset_id: uuid.UUID,
        output_root: Path,
        export_format: str,
    ) -> Path | None:
        """Resolve one generated file for download by dataset and format."""
        suffix_map = {
            "csv": ".csv",
            "json": ".json",
            "jsonl": ".jsonl",
            "excel": ".xlsx",
        }
        suffix = suffix_map.get(export_format.lower())
        if suffix is None:
            return None

        dataset_dir = output_root / str(dataset_id)
        if not dataset_dir.exists():
            return None

        candidates = sorted(
            dataset_dir.glob(f"*{suffix}"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        return candidates[0] if candidates else None

    @staticmethod
    def sanitize_download_filename(file_name: str) -> str:
        """Sanitize user-facing download name to avoid unsafe path characters."""
        safe = "".join(ch for ch in file_name if ch.isalnum() or ch in {"-", "_", "."})
        if not safe or safe.startswith("."):
            return "dataset_export"
        return safe

    @staticmethod
    def cleanup_old_artifacts(
        output_root: Path,
        max_age_hours: int,
        db: Database | None = None,
    ) -> None:
        """Delete generated files older than retention window."""
        if not output_root.exists():
            return

        cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        for dataset_dir in output_root.glob("*"):
            if not dataset_dir.is_dir():
                continue
            for file_path in dataset_dir.glob("*"):
                if not file_path.is_file():
                    continue
                modified_at = datetime.fromtimestamp(
                    file_path.stat().st_mtime, tz=timezone.utc
                )
                if modified_at < cutoff:
                    if db is not None:
                        db["dataset_generation_artifacts"].update_many(
                            {
                                "dataset_id": dataset_dir.name,
                                "file_name": file_path.name,
                                "status": "available",
                            },
                            {
                                "$set": {
                                    "status": "expired",
                                    "deleted_at": datetime.now(timezone.utc),
                                }
                            },
                        )
                    file_path.unlink(missing_ok=True)

    @staticmethod
    def record_generation_artifacts(
        db: Database,
        dataset_id: uuid.UUID,
        generation_run_id: str,
        files: list[dict[str, Any]],
        retention_hours: int,
    ) -> None:
        """Record generated artifacts in database."""
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=retention_hours)
        for file in files:
            file_name = str(file.get("file_name", "")).strip()
            if not file_name:
                continue
            db["dataset_generation_artifacts"].update_one(
                {
                    "dataset_id": str(dataset_id),
                    "generation_run_id": generation_run_id,
                    "file_name": file_name,
                },
                {
                    "$set": {
                        "dataset_id": str(dataset_id),
                        "generation_run_id": generation_run_id,
                        "format": str(file.get("format", "")),
                        "file_name": file_name,
                        "size_bytes": int(file.get("size_bytes", 0)),
                        "status": "available",
                        "created_at": now,
                        "expires_at": expires_at,
                        "deleted_at": None,
                    }
                },
                upsert=True,
            )

    @staticmethod
    def evaluate_quality_guardrails(quality_report: dict[str, Any]) -> dict[str, Any]:
        """Evaluate quality guardrails for generation."""
        alerts = (
            quality_report.get("alerts", []) if isinstance(quality_report, dict) else []
        )
        alert_count = len(alerts) if isinstance(alerts, list) else 0
        max_alerts = settings.quality_alert_threshold
        return {
            "passed": alert_count <= max_alerts,
            "max_alerts": max_alerts,
            "actual_alerts": alert_count,
            "message": (
                "Quality checks passed"
                if alert_count <= max_alerts
                else "Quality checks exceeded alert threshold"
            ),
        }

    @staticmethod
    def build_quality_dashboard(
        quality_report: dict[str, Any] | None,
        validation_summary: dict[str, Any] | None,
        row_count: int,
    ) -> dict[str, Any]:
        """Build score-based quality dashboard payload for UI reporting."""
        quality_report = quality_report if isinstance(quality_report, dict) else {}
        validation_summary = (
            validation_summary if isinstance(validation_summary, dict) else {}
        )

        distribution_fidelity = GenerationOrchestrator._score_distribution_fidelity(
            validation_summary
        )
        relationship_integrity = GenerationOrchestrator._score_relationship_integrity(
            validation_summary
        )
        null_pattern_match = GenerationOrchestrator._score_null_pattern_match(
            quality_report, validation_summary
        )
        uniqueness = GenerationOrchestrator._score_uniqueness(validation_summary)
        freshness = GenerationOrchestrator._score_freshness(validation_summary)

        weighted_total = (
            distribution_fidelity * 0.30
            + relationship_integrity * 0.20
            + null_pattern_match * 0.20
            + uniqueness * 0.15
            + freshness * 0.15
        )
        overall_score = int(round(max(0.0, min(100.0, weighted_total))))

        warnings: list[str] = []
        alerts = quality_report.get("alerts", [])
        if isinstance(alerts, list) and alerts:
            warnings.extend(
                [
                    str(alert.get("details") or alert.get("type") or "Quality alert")
                    for alert in alerts[:5]
                    if isinstance(alert, dict)
                ]
            )

        validator_warnings = validation_summary.get("warnings", [])
        if isinstance(validator_warnings, list):
            warnings.extend(
                [
                    str(item.get("message", "Validation warning"))
                    for item in validator_warnings[:5]
                    if isinstance(item, dict)
                ]
            )

        recommendations: list[str] = []
        if distribution_fidelity < 85:
            recommendations.append(
                "Adjust numeric constraints/distributions for better fidelity alignment."
            )
        if null_pattern_match < 90:
            recommendations.append(
                "Revisit null percentages for columns with high null drift."
            )
        if relationship_integrity < 90:
            recommendations.append(
                "Add or strengthen correlation and semantic dependency rules."
            )
        if row_count < 50000:
            recommendations.append(
                "Use at least 50,000 rows for higher-confidence validation metrics."
            )

        return {
            "overall_score": overall_score,
            "metrics": {
                "distribution_fidelity": int(round(distribution_fidelity)),
                "relationship_integrity": int(round(relationship_integrity)),
                "null_pattern_match": int(round(null_pattern_match)),
                "uniqueness": int(round(uniqueness)),
                "freshness": int(round(freshness)),
            },
            "warnings": warnings[:6],
            "recommendations": recommendations,
        }

    @staticmethod
    def _score_distribution_fidelity(validation_summary: dict[str, Any]) -> float:
        ks_tests = validation_summary.get("ks_tests", {})
        kl_divergence = validation_summary.get("kl_divergence", {})
        column_comparisons = validation_summary.get("column_comparisons", {})

        numeric_score = 85.0
        if isinstance(ks_tests, dict) and ks_tests:
            p_values = [
                float(item.get("p_value", 0.0))
                for item in ks_tests.values()
                if isinstance(item, dict)
            ]
            pass_rate = sum(1 for p in p_values if p > 0.05) / max(len(p_values), 1)
            mean_p = sum(p_values) / max(len(p_values), 1)
            numeric_score = 100.0 * (0.7 * pass_rate + 0.3 * min(1.0, mean_p))

        emd_penalty = 0.0
        if isinstance(column_comparisons, dict):
            emd_values = [
                float(item.get("emd", 0.0))
                for item in column_comparisons.values()
                if isinstance(item, dict) and item.get("type") == "numeric"
            ]
            if emd_values:
                emd_penalty = min(20.0, (sum(emd_values) / len(emd_values)) * 5.0)

        categorical_score = 100.0
        if isinstance(kl_divergence, dict) and kl_divergence:
            kl_values = [
                float(item.get("kl_div", 0.0))
                for item in kl_divergence.values()
                if isinstance(item, dict)
            ]
            avg_kl = sum(kl_values) / max(len(kl_values), 1)
            categorical_score = max(0.0, 100.0 - (avg_kl * 120.0))

        combined = (numeric_score * 0.7) + (categorical_score * 0.3) - emd_penalty
        return max(0.0, min(100.0, combined))

    @staticmethod
    def _score_relationship_integrity(validation_summary: dict[str, Any]) -> float:
        correlation_error = validation_summary.get("correlation_error", {})
        if not isinstance(correlation_error, dict):
            return 95.0

        frob = correlation_error.get("frobenius_norm")
        max_pair = correlation_error.get("max_pair_error")
        if frob is None and max_pair is None:
            return 95.0

        frob_component = 1.0 - min(float(frob or 0.0) / 1.2, 1.0)
        max_component = 1.0 - min(float(max_pair or 0.0) / 1.0, 1.0)
        score = 100.0 * ((0.7 * frob_component) + (0.3 * max_component))
        return max(0.0, min(100.0, score))

    @staticmethod
    def _score_null_pattern_match(
        quality_report: dict[str, Any],
        validation_summary: dict[str, Any],
    ) -> float:
        columns = quality_report.get("columns", {})
        drifts: list[float] = []
        if isinstance(columns, dict):
            for item in columns.values():
                if isinstance(item, dict) and item.get("null_drift") is not None:
                    drifts.append(float(item.get("null_drift", 0.0)))

        if not drifts:
            null_fidelity = validation_summary.get("null_fidelity", {})
            if isinstance(null_fidelity, dict):
                drifts = [
                    float(item.get("drift", 0.0))
                    for item in null_fidelity.values()
                    if isinstance(item, dict)
                ]

        if not drifts:
            return 90.0

        avg_drift = sum(drifts) / len(drifts)
        score = 100.0 * (1.0 - min(avg_drift / 0.15, 1.0))
        return max(0.0, min(100.0, score))

    @staticmethod
    def _score_uniqueness(validation_summary: dict[str, Any]) -> float:
        uniqueness = validation_summary.get("uniqueness", {})
        if not isinstance(uniqueness, dict) or not uniqueness:
            return 92.0

        ratios = [
            float(item.get("unique_ratio", 1.0))
            for item in uniqueness.values()
            if isinstance(item, dict)
        ]
        if not ratios:
            return 92.0
        return max(0.0, min(100.0, (sum(ratios) / len(ratios)) * 100.0))

    @staticmethod
    def _score_freshness(validation_summary: dict[str, Any]) -> float:
        freshness = validation_summary.get("freshness", {})
        if not isinstance(freshness, dict) or not freshness:
            return 95.0

        ratios = [
            float(item.get("in_range_ratio", 1.0))
            for item in freshness.values()
            if isinstance(item, dict)
        ]
        if not ratios:
            return 95.0
        return max(0.0, min(100.0, (sum(ratios) / len(ratios)) * 100.0))

    # ── Private Helper Methods ─────────────────────────────────────────────────

    @staticmethod
    def _load_attributes_as_specs(
        db: Database,
        dataset_version_id: uuid.UUID,
    ) -> list[AttributeSpec]:
        """Load attributes and convert to AttributeSpec."""
        attributes = DatasetRepository.load_version_attributes(db, dataset_version_id)
        return [
            AttributeSpec(
                name=attr.name,
                data_type=attr.data_type.value,
                constraints=attr.constraints_json or {},
                distribution=attr.distribution.value,
                null_percentage=attr.null_percentage,
            )
            for attr in attributes
        ]

    @staticmethod
    def _normalize_explain_value(value: Any) -> Any:
        """Convert numpy/pandas scalar values to API-safe Python primitives."""
        if value is None:
            return None
        if pd.isna(value):
            return None
        if isinstance(value, np.generic):
            return value.item()
        return value

    @staticmethod
    def _build_generation_signature(
        dataset_id: uuid.UUID,
        dataset_version_id: uuid.UUID,
        row_count: int,
        formats: list[str],
        seed: int | None,
        attributes: list[AttributeSpec],
        realism_rules: list[dict[str, Any]],
        realism_metadata: dict[str, Any],
        correlations: list[dict[str, Any]],
    ) -> str:
        """Build a deterministic signature of generation parameters."""
        payload = {
            "dataset_id": str(dataset_id),
            "dataset_version_id": str(dataset_version_id),
            "row_count": row_count,
            "formats": sorted([fmt.lower() for fmt in formats]),
            "seed": seed,
            "attributes": [
                {
                    "name": attr.name,
                    "data_type": attr.data_type,
                    "constraints": attr.constraints,
                    "distribution": attr.distribution,
                    "null_percentage": attr.null_percentage,
                }
                for attr in attributes
            ],
            "realism_rules": realism_rules,
            "realism_metadata": realism_metadata,
            "correlations": correlations,
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @staticmethod
    def _estimate_dataset_size_bytes(
        row_count: int,
        attributes: list[AttributeSpec],
        formats: list[str],
    ) -> int:
        """Rough output-size estimate used for generation preflight checks."""
        per_type_bytes = {
            "integer": 12,
            "float": 16,
            "categorical": 18,
            "boolean": 6,
            "date": 16,
            "text": 28,
            "email": 26,
            "name": 22,
            "address": 48,
        }
        bytes_per_row = 0
        for attr in attributes:
            bytes_per_row += per_type_bytes.get(attr.data_type, 20)

        bytes_per_row += max(8, len(attributes) * 2)

        format_multiplier = 0.0
        clean_formats = {str(fmt).lower() for fmt in formats}
        if "csv" in clean_formats:
            format_multiplier += 1.0
        if "json" in clean_formats:
            format_multiplier += 1.25
        if "jsonl" in clean_formats:
            format_multiplier += 1.2
        if "excel" in clean_formats:
            format_multiplier += 1.35
        if format_multiplier == 0:
            format_multiplier = 1.0

        return int(max(1, row_count) * bytes_per_row * format_multiplier)

    @staticmethod
    def _build_preview_comparison(
        attributes: list[AttributeSpec],
        frame: pd.DataFrame,
        seed: int | None,
    ) -> dict[str, Any]:
        """Compute chart-ready preview comparison metrics by column."""
        rng = np.random.default_rng(seed if seed is not None else 42)
        column_payloads: list[dict[str, Any]] = []

        for attr in attributes:
            column = attr.name
            if column not in frame.columns:
                continue

            payload: dict[str, Any] = {
                "column": column,
                "data_type": attr.data_type,
                "distribution": attr.distribution,
                "numeric": None,
            }

            if attr.data_type in {"integer", "float"}:
                payload["numeric"] = (
                    GenerationOrchestrator._build_numeric_preview_stats(
                        attr=attr,
                        frame=frame,
                        rng=rng,
                    )
                )

            column_payloads.append(payload)

        return {"columns": column_payloads}

    @staticmethod
    def _build_numeric_preview_stats(
        attr: AttributeSpec,
        frame: pd.DataFrame,
        rng: np.random.Generator,
    ) -> dict[str, Any]:
        series = pd.to_numeric(frame[attr.name], errors="coerce")
        synthetic = series.dropna().astype(float).to_numpy()

        expected_missing_pct = float(max(0.0, min(100.0, attr.null_percentage)))
        synthetic_missing_pct = float(round(series.isna().mean() * 100.0, 4))

        expected = GenerationOrchestrator._sample_expected_numeric(
            attr, len(series), rng
        )
        expected_series = pd.Series(expected, dtype=float)
        expected_non_null = expected_series.dropna().to_numpy(dtype=float)

        synthetic_min = float(np.min(synthetic)) if synthetic.size else None
        synthetic_max = float(np.max(synthetic)) if synthetic.size else None
        synthetic_mean = float(np.mean(synthetic)) if synthetic.size else None

        expected_min = (
            float(np.min(expected_non_null)) if expected_non_null.size else None
        )
        expected_max = (
            float(np.max(expected_non_null)) if expected_non_null.size else None
        )
        expected_mean = (
            float(np.mean(expected_non_null)) if expected_non_null.size else None
        )

        expected_skewness = GenerationOrchestrator._safe_skew(expected_non_null)
        synthetic_skewness = GenerationOrchestrator._safe_skew(synthetic)
        expected_kurtosis = GenerationOrchestrator._safe_kurtosis(expected_non_null)
        synthetic_kurtosis = GenerationOrchestrator._safe_kurtosis(synthetic)

        ks_statistic: float | None = None
        ks_p_value: float | None = None
        ks_passed: bool | None = None
        ad_statistic: float | None = None
        ad_significance_level: float | None = None
        ad_passed: bool | None = None

        if synthetic.size >= 3 and expected_non_null.size >= 3:
            ks_result = ks_2samp(synthetic, expected_non_null)
            ks_statistic = float(ks_result.statistic)
            ks_p_value = float(ks_result.pvalue)
            ks_passed = bool(ks_p_value > 0.05)

            try:
                ad_result = anderson_ksamp([synthetic, expected_non_null])
                ad_statistic = float(ad_result.statistic)
                ad_significance_level = float(ad_result.significance_level)
                ad_passed = bool(ad_significance_level > 5.0)
            except Exception:
                ad_statistic = None
                ad_significance_level = None
                ad_passed = None

        histogram_bins = GenerationOrchestrator._build_histogram_overlay(
            expected=expected_non_null,
            synthetic=synthetic,
            bin_count=10,
        )

        low_variance = False
        if (
            synthetic.size >= 2
            and synthetic_min is not None
            and synthetic_max is not None
        ):
            value_range = max(1e-9, synthetic_max - synthetic_min)
            low_variance = bool(float(np.std(synthetic)) < (0.05 * value_range))

        return {
            "expected_min": expected_min,
            "expected_max": expected_max,
            "expected_mean": expected_mean,
            "synthetic_min": synthetic_min,
            "synthetic_max": synthetic_max,
            "synthetic_mean": synthetic_mean,
            "expected_skewness": expected_skewness,
            "synthetic_skewness": synthetic_skewness,
            "expected_kurtosis": expected_kurtosis,
            "synthetic_kurtosis": synthetic_kurtosis,
            "ks_statistic": ks_statistic,
            "ks_p_value": ks_p_value,
            "ks_passed": ks_passed,
            "ad_statistic": ad_statistic,
            "ad_significance_level": ad_significance_level,
            "ad_passed": ad_passed,
            "expected_missing_pct": round(expected_missing_pct, 4),
            "synthetic_missing_pct": synthetic_missing_pct,
            "low_variance": low_variance,
            "histogram_bins": histogram_bins,
        }

    @staticmethod
    def _sample_expected_numeric(
        attr: AttributeSpec,
        sample_size: int,
        rng: np.random.Generator,
    ) -> np.ndarray:
        constraints = attr.constraints or {}
        minimum = float(constraints.get("min", 0.0))
        maximum = float(constraints.get("max", minimum + 100.0))
        if maximum < minimum:
            minimum, maximum = maximum, minimum
        if maximum == minimum:
            maximum = minimum + 1.0

        distribution = str(attr.distribution or "uniform")
        count = max(10, int(sample_size))

        if distribution == "normal":
            mean = (minimum + maximum) / 2.0
            std = max((maximum - minimum) / 6.0, 1e-6)
            samples = rng.normal(loc=mean, scale=std, size=count)
        elif distribution == "skewed":
            direction = str(constraints.get("skew_direction", "right"))
            intensity = max(float(constraints.get("skew_intensity", 2.0)), 0.1)
            if direction == "left":
                a_param = intensity * 2.5
                b_param = intensity
            else:
                a_param = intensity
                b_param = intensity * 2.5
            beta_samples = rng.beta(a=a_param, b=b_param, size=count)
            samples = minimum + beta_samples * (maximum - minimum)
        else:
            samples = rng.uniform(low=minimum, high=maximum, size=count)

        samples = np.clip(samples, minimum, maximum)
        if attr.data_type == "integer":
            samples = np.rint(samples)
        return samples.astype(float)

    @staticmethod
    def _build_histogram_overlay(
        expected: np.ndarray,
        synthetic: np.ndarray,
        bin_count: int,
    ) -> list[dict[str, float]]:
        if expected.size == 0 and synthetic.size == 0:
            return []

        merged = np.concatenate([expected, synthetic])
        merged_min = float(np.min(merged))
        merged_max = float(np.max(merged))
        if merged_min == merged_max:
            merged_max = merged_min + 1.0

        edges = np.linspace(merged_min, merged_max, bin_count + 1)
        expected_hist, _ = np.histogram(expected, bins=edges)
        synthetic_hist, _ = np.histogram(synthetic, bins=edges)

        payload: list[dict[str, float]] = []
        for index in range(bin_count):
            payload.append(
                {
                    "bin_start": float(edges[index]),
                    "bin_end": float(edges[index + 1]),
                    "expected_count": float(expected_hist[index]),
                    "synthetic_count": float(synthetic_hist[index]),
                }
            )
        return payload

    @staticmethod
    def _safe_skew(values: np.ndarray) -> float | None:
        if values.size < 3:
            return None
        series = pd.Series(values)
        if series.nunique(dropna=True) <= 1:
            return 0.0
        return float(series.skew())

    @staticmethod
    def _safe_kurtosis(values: np.ndarray) -> float | None:
        if values.size < 4:
            return None
        series = pd.Series(values)
        if series.nunique(dropna=True) <= 1:
            return 0.0
        return float(series.kurt())

    @staticmethod
    def _record_generation_run(db: Database, run_payload: dict[str, Any]) -> str:
        """Record a generation run in the database."""
        run_id = str(uuid.uuid4())
        document = {"_id": run_id, **run_payload}
        db["dataset_generation_runs"].insert_one(document)
        return run_id

    @staticmethod
    def _compare_with_previous_run(
        db: Database,
        dataset_id: uuid.UUID,
        current_run_id: str,
        current_quality: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Compare current generation run with previous run."""
        previous = db["dataset_generation_runs"].find_one(
            {
                "dataset_id": str(dataset_id),
                "_id": {"$ne": current_run_id},
            },
            sort=[("created_at", -1)],
        )
        if previous is None:
            return None

        previous_quality = previous.get("quality_report", {})
        current_realism = current_quality.get("realism", {})
        previous_realism = previous_quality.get("realism", {})

        current_rows_affected = int(current_realism.get("total_rows_affected", 0))
        previous_rows_affected = int(previous_realism.get("total_rows_affected", 0))

        return {
            "previous_run_id": str(previous.get("_id")),
            "previous_signature": str(previous.get("generation_signature", "")),
            "delta_rows_affected": current_rows_affected - previous_rows_affected,
            "previous_created_at": (
                previous.get("created_at").isoformat()
                if previous.get("created_at") is not None
                else None
            ),
        }
