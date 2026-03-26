import uuid
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from pymongo import DESCENDING, ReturnDocument
from pymongo.database import Database

from app.core.config import settings
from app.engine.dataset_generator import AttributeSpec, DatasetGenerator
from app.models.dataset import Attribute, Dataset, DatasetStatus, DatasetVersion
from app.schemas.dataset import AttributeConfig


class DatasetService:
    TERMINAL_JOB_STATUSES = {"completed", "failed", "cancelled"}

    @staticmethod
    def create_dataset(
        db: Database,
        user_id: uuid.UUID,
        name: str,
        description: str | None,
    ) -> Dataset:
        dataset = Dataset.new(user_id=user_id, name=name, description=description)
        db["datasets"].insert_one(dataset.to_document())
        return dataset

    @staticmethod
    def create_dataset_version(
        db: Database,
        user_id: uuid.UUID,
        dataset_id: uuid.UUID,
        attributes: list[AttributeConfig],
        seed: int | None = None,
        correlations: list[dict[str, Any]] | None = None,
    ) -> DatasetVersion:
        attr_names = [attr.name for attr in attributes]
        if len(attr_names) != len(set(attr_names)):
            raise ValueError("Attribute names must be unique within a version")

        dataset_doc = db["datasets"].find_one(
            {"_id": str(dataset_id), "user_id": str(user_id)}
        )
        if dataset_doc is None:
            raise ValueError("Dataset not found")
        dataset = Dataset.from_document(dataset_doc)

        latest_version = db["dataset_versions"].find_one(
            {"dataset_id": str(dataset_id)},
            sort=[("version_number", DESCENDING)],
        )
        next_version_number = (
            int(latest_version["version_number"]) + 1 if latest_version else 1
        )

        config_json = {
            "attributes": [
                attribute.model_dump(mode="json") for attribute in attributes
            ],
            "seed": seed,
            "correlations": correlations or [],
        }

        # ── Gemini Realism Planning ────────────────────────────────────────────
        from app.engine.realism_planner import RealismPlanner  # deferred import

        specs_for_planner = [
            AttributeSpec(
                name=a.name,
                data_type=a.type.value,
                constraints=a.constraints,
                distribution=a.distribution.value,
                null_percentage=a.null_percentage,
            )
            for a in attributes
        ]
        realism_plan = RealismPlanner.plan_with_metadata(
            attributes=specs_for_planner,
            api_key=settings.gemini_api_key,
        )
        realism_rules = realism_plan.get("rules", [])
        config_json["realism_rules"] = realism_rules
        config_json["realism"] = {
            "rules": realism_rules,
            "metadata": realism_plan.get("metadata", {}),
        }
        # ─────────────────────────────────────────────────────────────────────

        version = DatasetVersion.new(
            dataset_id=dataset_id,
            version_number=next_version_number,
            config_json=config_json,
            seed=seed,
        )
        db["dataset_versions"].insert_one(version.to_document())

        attribute_documents: list[dict[str, Any]] = []
        for index, attribute in enumerate(attributes):
            attribute_documents.append(
                Attribute.new(
                    dataset_version_id=version.id,
                    name=attribute.name,
                    data_type=attribute.type,
                    description=attribute.description,
                    constraints_json=attribute.constraints,
                    distribution=attribute.distribution,
                    null_percentage=attribute.null_percentage,
                    order_index=index,
                ).to_document()
            )

        if attribute_documents:
            db["attributes"].insert_many(attribute_documents)

        now = datetime.now(timezone.utc)
        db["datasets"].update_one(
            {"_id": str(dataset.id)},
            {
                "$set": {
                    "latest_version_id": str(version.id),
                    "status": DatasetStatus.active.value,
                    "updated_at": now,
                }
            },
        )
        return version

    @staticmethod
    def generate_preview(
        db: Database,
        user_id: uuid.UUID,
        dataset_version_id: uuid.UUID,
        seed: int | None = None,
    ) -> list[dict[str, Any]]:
        """Generate a 10-row preview from persisted attribute configuration."""
        version_doc = db["dataset_versions"].find_one({"_id": str(dataset_version_id)})
        if version_doc is None:
            raise ValueError("Dataset version not found")
        version = DatasetVersion.from_document(version_doc)

        dataset_doc = db["datasets"].find_one(
            {"_id": str(version.dataset_id), "user_id": str(user_id)}
        )
        if dataset_doc is None:
            raise ValueError("Dataset version not found")

        attributes = DatasetService._load_version_attributes(db, dataset_version_id)
        realism_config = version.config_json.get("realism")
        if isinstance(realism_config, dict) and isinstance(
            realism_config.get("rules"), list
        ):
            realism_rules = realism_config.get("rules", [])
        else:
            realism_rules = version.config_json.get("realism_rules", [])
        generator_seed = seed if seed is not None else version.seed
        generator = DatasetGenerator(seed=generator_seed)
        semantic_groups = DatasetService._load_semantic_groups_for_version(
            db=db,
            dataset_version_id=dataset_version_id,
        )
        return generator.generate_preview(
            attributes=attributes,
            realism_rules=realism_rules,
            semantic_groups=semantic_groups,
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
        dataset_doc = db["datasets"].find_one(
            {"_id": str(dataset_id), "user_id": str(user_id)}
        )
        if dataset_doc is None:
            raise ValueError("Dataset not found")
        dataset = Dataset.from_document(dataset_doc)

        target_version_id = dataset_version_id or dataset.latest_version_id
        if target_version_id is None:
            raise ValueError("Dataset has no attribute configuration")

        version_doc = db["dataset_versions"].find_one(
            {"_id": str(target_version_id), "dataset_id": str(dataset.id)}
        )
        if version_doc is None:
            raise ValueError("Dataset version not found")
        owned_version = DatasetVersion.from_document(version_doc)

        attributes = DatasetService._load_version_attributes(db, target_version_id)
        if not attributes:
            raise ValueError("Dataset version has no attributes")

        preflight = DatasetService.preflight_generation(
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

        DatasetService.cleanup_old_artifacts(
            db=db,
            output_root=output_root,
            max_age_hours=retention_hours,
        )
        generator_seed = seed if seed is not None else owned_version.seed
        generator = DatasetGenerator(seed=generator_seed)
        semantic_groups = DatasetService._load_semantic_groups_for_version(
            db=db,
            dataset_version_id=owned_version.id,
        )
        generation_signature = DatasetService._build_generation_signature(
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
        run_id = DatasetService._record_generation_run(db=db, run_payload=run_payload)
        DatasetService.record_generation_artifacts(
            db=db,
            dataset_id=dataset.id,
            generation_run_id=run_id,
            files=generation_result.get("files", []),
            retention_hours=retention_hours,
        )
        comparison = DatasetService._compare_with_previous_run(
            db=db,
            dataset_id=dataset.id,
            current_run_id=run_id,
            current_quality=run_payload["quality_report"],
        )
        quality_guardrails = DatasetService.evaluate_quality_guardrails(
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
        dataset = DatasetService.get_dataset(
            db=db, user_id=user_id, dataset_id=dataset_id
        )

        target_version_id = dataset_version_id or dataset.latest_version_id
        if target_version_id is None:
            raise ValueError("Dataset has no attribute configuration")

        version_doc = db["dataset_versions"].find_one(
            {"_id": str(target_version_id), "dataset_id": str(dataset.id)}
        )
        if version_doc is None:
            raise ValueError("Dataset version not found")

        attributes = DatasetService._load_version_attributes(db, target_version_id)
        if not attributes:
            raise ValueError("Dataset version has no attributes")

        estimated_cells = int(max(1, row_count) * max(1, len(attributes)))
        estimated_output_bytes = DatasetService._estimate_dataset_size_bytes(
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
    def create_generation_job(
        db: Database,
        user_id: uuid.UUID,
        dataset_id: uuid.UUID,
        row_count: int,
        formats: list[str],
        seed: int | None = None,
        dataset_version_id: uuid.UUID | None = None,
        source_job_id: str | None = None,
        drift_profile: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        dataset = DatasetService.get_dataset(
            db=db, user_id=user_id, dataset_id=dataset_id
        )

        target_version_id = dataset_version_id or dataset.latest_version_id
        if target_version_id is None:
            raise ValueError("Dataset has no attribute configuration")

        version_doc = db["dataset_versions"].find_one(
            {"_id": str(target_version_id), "dataset_id": str(dataset.id)}
        )
        if version_doc is None:
            raise ValueError("Dataset version not found")

        attributes = DatasetService._load_version_attributes(db, target_version_id)
        if not attributes:
            raise ValueError("Dataset version has no attributes")

        now = datetime.now(timezone.utc)
        job_id = str(uuid.uuid4())
        document: dict[str, Any] = {
            "_id": job_id,
            "user_id": str(user_id),
            "dataset_id": str(dataset.id),
            "dataset_version_id": str(target_version_id),
            "row_count": row_count,
            "formats": sorted([fmt.lower() for fmt in formats]),
            "seed": seed,
            "source_job_id": source_job_id,
            "drift_profile": drift_profile or {"enabled": False},
            "status": "queued",
            "stage": "queued",
            "progress_percentage": 0,
            "cancel_requested": False,
            "error": None,
            "result": None,
            "created_at": now,
            "updated_at": now,
            "started_at": None,
            "finished_at": None,
        }
        db["dataset_generation_jobs"].insert_one(document)
        return document

    @staticmethod
    def list_generation_jobs(
        db: Database,
        user_id: uuid.UUID,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        max_limit = max(1, min(limit, 100))
        cursor = (
            db["dataset_generation_jobs"]
            .find({"user_id": str(user_id)})
            .sort("created_at", DESCENDING)
            .limit(max_limit)
        )
        return list(cursor)

    @staticmethod
    def retry_generation_job(
        db: Database,
        user_id: uuid.UUID,
        job_id: str,
    ) -> dict[str, Any]:
        job = DatasetService.get_generation_job(db=db, user_id=user_id, job_id=job_id)
        status = str(job.get("status", "queued"))
        if status not in {"failed", "cancelled", "completed"}:
            raise ValueError("Only failed, cancelled, or completed jobs can be retried")

        return DatasetService.create_generation_job(
            db=db,
            user_id=user_id,
            dataset_id=uuid.UUID(str(job["dataset_id"])),
            dataset_version_id=(
                uuid.UUID(str(job["dataset_version_id"]))
                if job.get("dataset_version_id")
                else None
            ),
            row_count=int(job["row_count"]),
            formats=[str(item) for item in job.get("formats", ["csv"])],
            seed=(int(job["seed"]) if job.get("seed") is not None else None),
            source_job_id=job_id,
            drift_profile=(
                dict(job.get("drift_profile", {}))
                if isinstance(job.get("drift_profile"), dict)
                else {"enabled": False}
            ),
        )

    @staticmethod
    def list_active_generation_job_dataset_ids(
        db: Database,
        user_id: uuid.UUID,
    ) -> set[str]:
        # Consider only the most recent job per dataset; older stuck jobs should not
        # override a newer terminal state like completed/failed/cancelled.
        rows = db["dataset_generation_jobs"].find(
            {"user_id": str(user_id)},
            {"dataset_id": 1, "status": 1, "created_at": 1, "updated_at": 1},
        )

        latest_by_dataset: dict[str, dict[str, Any]] = {}
        for row in rows:
            dataset_id = str(row.get("dataset_id", ""))
            if not dataset_id:
                continue

            existing = latest_by_dataset.get(dataset_id)
            if existing is None:
                latest_by_dataset[dataset_id] = row
                continue

            current_created = row.get("created_at")
            existing_created = existing.get("created_at")
            current_updated = row.get("updated_at")
            existing_updated = existing.get("updated_at")

            if (
                isinstance(current_created, datetime)
                and isinstance(existing_created, datetime)
                and current_created > existing_created
            ):
                latest_by_dataset[dataset_id] = row
                continue

            if isinstance(current_created, datetime) and not isinstance(
                existing_created, datetime
            ):
                latest_by_dataset[dataset_id] = row
                continue

            if (
                isinstance(current_created, datetime)
                and isinstance(existing_created, datetime)
                and current_created == existing_created
                and isinstance(current_updated, datetime)
                and isinstance(existing_updated, datetime)
                and current_updated > existing_updated
            ):
                latest_by_dataset[dataset_id] = row

        active_statuses = {"queued", "running"}
        return {
            dataset_id
            for dataset_id, job in latest_by_dataset.items()
            if str(job.get("status", "")) in active_statuses
        }

    @staticmethod
    def get_generation_job(
        db: Database,
        user_id: uuid.UUID,
        job_id: str,
    ) -> dict[str, Any]:
        document = db["dataset_generation_jobs"].find_one(
            {"_id": job_id, "user_id": str(user_id)}
        )
        if document is None:
            raise ValueError("Generation job not found")
        return document

    @staticmethod
    def cancel_generation_job(
        db: Database,
        user_id: uuid.UUID,
        job_id: str,
    ) -> dict[str, Any]:
        job = DatasetService.get_generation_job(db=db, user_id=user_id, job_id=job_id)
        now = datetime.now(timezone.utc)
        status = str(job.get("status", "queued"))

        if status in DatasetService.TERMINAL_JOB_STATUSES:
            return job

        update: dict[str, Any] = {
            "cancel_requested": True,
            "updated_at": now,
            "stage": "cancel_requested",
        }

        if status == "queued":
            update["status"] = "cancelled"
            update["progress_percentage"] = 100
            update["finished_at"] = now
            update["stage"] = "cancelled"

        db["dataset_generation_jobs"].update_one(
            {"_id": job_id, "user_id": str(user_id)},
            {"$set": update},
        )
        return DatasetService.get_generation_job(db=db, user_id=user_id, job_id=job_id)

    @staticmethod
    def mark_job_running(db: Database, job_id: str) -> dict[str, Any] | None:
        now = datetime.now(timezone.utc)
        result = db["dataset_generation_jobs"].find_one_and_update(
            {
                "_id": job_id,
                "status": {"$in": ["queued", "running"]},
            },
            {
                "$set": {
                    "status": "running",
                    "stage": "generating",
                    "progress_percentage": 10,
                    "updated_at": now,
                    "started_at": now,
                }
            },
            return_document=ReturnDocument.AFTER,
        )
        return result

    @staticmethod
    def mark_job_cancelled(db: Database, job_id: str, stage: str = "cancelled") -> None:
        now = datetime.now(timezone.utc)
        db["dataset_generation_jobs"].update_one(
            {"_id": job_id},
            {
                "$set": {
                    "status": "cancelled",
                    "stage": stage,
                    "progress_percentage": 100,
                    "cancel_requested": True,
                    "updated_at": now,
                    "finished_at": now,
                }
            },
        )

    @staticmethod
    def mark_job_completed(
        db: Database, job_id: str, result_payload: dict[str, Any]
    ) -> None:
        now = datetime.now(timezone.utc)
        db["dataset_generation_jobs"].update_one(
            {"_id": job_id},
            {
                "$set": {
                    "status": "completed",
                    "stage": "completed",
                    "progress_percentage": 100,
                    "updated_at": now,
                    "finished_at": now,
                    "result": result_payload,
                    "error": None,
                }
            },
        )

    @staticmethod
    def mark_job_failed(db: Database, job_id: str, message: str) -> None:
        now = datetime.now(timezone.utc)
        db["dataset_generation_jobs"].update_one(
            {"_id": job_id},
            {
                "$set": {
                    "status": "failed",
                    "stage": "failed",
                    "progress_percentage": 100,
                    "updated_at": now,
                    "finished_at": now,
                    "error": message,
                }
            },
        )

    @staticmethod
    def serialize_generation_job(job: dict[str, Any]) -> dict[str, Any]:
        result_payload = job.get("result")
        if not isinstance(result_payload, dict):
            result_payload = None

        def _iso(value: Any) -> str | None:
            if isinstance(value, datetime):
                return value.isoformat()
            return None

        return {
            "job_id": str(job.get("_id")),
            "dataset_id": uuid.UUID(str(job.get("dataset_id"))),
            "dataset_version_id": (
                uuid.UUID(str(job.get("dataset_version_id")))
                if job.get("dataset_version_id")
                else None
            ),
            "status": str(job.get("status", "queued")),
            "stage": str(job.get("stage", "queued")),
            "progress_percentage": int(job.get("progress_percentage", 0)),
            "row_count": int(job.get("row_count", 0)),
            "formats": [str(item) for item in job.get("formats", [])],
            "seed": job.get("seed"),
            "cancel_requested": bool(job.get("cancel_requested", False)),
            "created_at": _iso(job.get("created_at"))
            or datetime.now(timezone.utc).isoformat(),
            "started_at": _iso(job.get("started_at")),
            "finished_at": _iso(job.get("finished_at")),
            "error": str(job.get("error")) if job.get("error") else None,
            "result": result_payload,
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
    def list_datasets(db: Database, user_id: uuid.UUID) -> list[Dataset]:
        """List all datasets owned by a user."""
        rows = (
            db["datasets"]
            .find({"user_id": str(user_id)})
            .sort("created_at", DESCENDING)
        )
        return [Dataset.from_document(row) for row in rows]

    @staticmethod
    def resolve_effective_dataset_status(
        dataset: Dataset,
        output_root: Path,
        active_job_dataset_ids: set[str] | None = None,
    ) -> DatasetStatus:
        """Resolve runtime status from artifact availability for dashboard UX."""
        if dataset.status is DatasetStatus.archived:
            return DatasetStatus.archived

        if active_job_dataset_ids and str(dataset.id) in active_job_dataset_ids:
            return DatasetStatus.generating

        files = DatasetService.list_generated_files(
            dataset_id=dataset.id,
            output_root=output_root,
        )
        return DatasetStatus.active if files else DatasetStatus.draft

    @staticmethod
    def get_dataset(db: Database, user_id: uuid.UUID, dataset_id: uuid.UUID) -> Dataset:
        """Get one dataset if owned by the user."""
        row = db["datasets"].find_one({"_id": str(dataset_id), "user_id": str(user_id)})
        if row is None:
            raise ValueError("Dataset not found")
        return Dataset.from_document(row)

    @staticmethod
    def get_dataset_versions(
        db: Database,
        user_id: uuid.UUID,
        dataset_id: uuid.UUID,
    ) -> list[DatasetVersion]:
        """Get all versions for one dataset if owned by user."""
        dataset = DatasetService.get_dataset(
            db=db, user_id=user_id, dataset_id=dataset_id
        )
        rows = (
            db["dataset_versions"]
            .find({"dataset_id": str(dataset.id)})
            .sort("version_number", DESCENDING)
        )
        return [DatasetVersion.from_document(row) for row in rows]

    @staticmethod
    def delete_dataset(db: Database, user_id: uuid.UUID, dataset_id: uuid.UUID) -> None:
        """Delete dataset and all versions/attributes if owned by user."""
        dataset = DatasetService.get_dataset(
            db=db, user_id=user_id, dataset_id=dataset_id
        )
        versions = db["dataset_versions"].find({"dataset_id": str(dataset.id)})
        version_ids = [row["_id"] for row in versions]
        if version_ids:
            db["attributes"].delete_many({"dataset_version_id": {"$in": version_ids}})
        db["dataset_versions"].delete_many({"dataset_id": str(dataset.id)})
        db["datasets"].delete_one({"_id": str(dataset.id)})

    @staticmethod
    def update_dataset_status(
        db: Database,
        user_id: uuid.UUID,
        dataset_id: uuid.UUID,
        status: DatasetStatus,
    ) -> Dataset:
        """Update dataset status if owned by user."""
        dataset = DatasetService.get_dataset(
            db=db,
            user_id=user_id,
            dataset_id=dataset_id,
        )
        now = datetime.now(timezone.utc)
        db["datasets"].update_one(
            {"_id": str(dataset.id)},
            {"$set": {"status": status.value, "updated_at": now}},
        )
        dataset.status = status
        dataset.updated_at = now
        return dataset

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
    def _load_version_attributes(
        db: Database, dataset_version_id: uuid.UUID
    ) -> list[AttributeSpec]:
        """Load and normalize version attributes for generation engine use."""
        rows = (
            db["attributes"]
            .find({"dataset_version_id": str(dataset_version_id)})
            .sort("order_index", 1)
        )
        attributes = [Attribute.from_document(row) for row in rows]

        return [
            AttributeSpec(
                name=row.name,
                data_type=row.data_type.value,
                constraints=row.constraints_json or {},
                distribution=row.distribution.value,
                null_percentage=row.null_percentage,
            )
            for row in attributes
        ]

    @staticmethod
    def _load_semantic_groups_for_version(
        db: Database,
        dataset_version_id: uuid.UUID,
    ) -> list[dict[str, Any]]:
        """Load persisted semantic dependency groups for profile-aware generation."""
        profile_doc = db["data_profiles"].find_one(
            {"dataset_version_id": str(dataset_version_id)},
            {"semantic_groups": 1},
        )
        groups = profile_doc.get("semantic_groups", []) if profile_doc else []
        if isinstance(groups, list):
            return [group for group in groups if isinstance(group, dict)]
        return []

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

        # Include rough separators/metadata overhead.
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
        previous = db["dataset_generation_runs"].find_one(
            {
                "dataset_id": str(dataset_id),
                "_id": {"$ne": current_run_id},
            },
            sort=[("created_at", DESCENDING)],
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
