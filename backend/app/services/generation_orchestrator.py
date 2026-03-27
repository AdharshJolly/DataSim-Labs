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

from pymongo.database import Database

from app.core.config import settings
from app.engine.dataset_generator import AttributeSpec, DatasetGenerator
from app.engine.realism_planner import RealismPlanner
from app.services.dataset_repository import DatasetRepository


class GenerationOrchestrator:
    """Orchestrates dataset generation workflow."""

    @staticmethod
    def generate_preview(
        db: Database,
        user_id: uuid.UUID,
        dataset_version_id: uuid.UUID,
        seed: int | None = None,
    ) -> list[dict[str, Any]]:
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

        generator_seed = seed if seed is not None else version.seed
        generator = DatasetGenerator(seed=generator_seed)
        semantic_groups = DatasetRepository.load_semantic_groups_for_version(
            db=db,
            dataset_version_id=dataset_version_id,
        )
        return generator.generate_preview(
            attributes=attributes,
            realism_rules=realism_rules,
            semantic_groups=semantic_groups,
        )

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
        drift_profile: dict[str, Any] | None = None,
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

        GenerationOrchestrator.cleanup_old_artifacts(
            db=db,
            output_root=output_root,
            max_age_hours=retention_hours,
        )
        generator_seed = seed if seed is not None else owned_version.seed
        generator = DatasetGenerator(seed=generator_seed)
        semantic_groups = DatasetRepository.load_semantic_groups_for_version(
            db=db,
            dataset_version_id=owned_version.id,
        )
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
            drift_profile=drift_profile or {},
        )

        generation_result = generator.export_dataset_files(
            dataset_id=dataset_id,
            attributes=attributes,
            row_count=row_count,
            formats=formats,
            output_root=output_root,
            chunk_size=chunk_size,
            realism_rules=realism_rules,
            semantic_groups=semantic_groups,
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

        generation_result["generation_signature"] = generation_signature
        generation_result["generation_run_id"] = run_id
        generation_result["comparison"] = comparison
        generation_result["quality_guardrails"] = quality_guardrails
        generation_result["drift_simulation"] = drift_profile or {"enabled": False}
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
        drift_profile: dict[str, Any],
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
            "drift_profile": drift_profile,
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
