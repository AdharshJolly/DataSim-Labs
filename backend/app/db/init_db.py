from __future__ import annotations

from pymongo import ASCENDING, DESCENDING

from app.db.session import database


def init_db() -> None:
    # Enforces unique user accounts by email and accelerates login/register lookups.
    database["users"].create_index([("email", ASCENDING)], unique=True)
    # Speeds per-user dataset listing ordered by newest first.
    database["datasets"].create_index(
        [("user_id", ASCENDING), ("created_at", DESCENDING)]
    )
    # Optimizes retrieval of latest versions for a dataset.
    database["dataset_versions"].create_index(
        [("dataset_id", ASCENDING), ("version_number", DESCENDING)]
    )
    # Guarantees unique version numbers within a dataset.
    database["dataset_versions"].create_index(
        [("dataset_id", ASCENDING), ("version_number", ASCENDING)],
        unique=True,
    )
    # Keeps ordered attribute fetches fast for a specific dataset version.
    database["attributes"].create_index(
        [("dataset_version_id", ASCENDING), ("order_index", ASCENDING)]
    )
    # Prevents duplicate attribute names in the same dataset version.
    database["attributes"].create_index(
        [("dataset_version_id", ASCENDING), ("name", ASCENDING)],
        unique=True,
        name="uq_version_attr_name",
    )
    # Accelerates generation run history lookups per dataset.
    database["dataset_generation_runs"].create_index(
        [("dataset_id", ASCENDING), ("created_at", DESCENDING)]
    )
    # Supports listing jobs per user by recency.
    database["dataset_generation_jobs"].create_index(
        [("user_id", ASCENDING), ("created_at", DESCENDING)]
    )
    # Supports listing jobs per dataset by recency.
    database["dataset_generation_jobs"].create_index(
        [("dataset_id", ASCENDING), ("created_at", DESCENDING)]
    )
    # Speeds workers querying active/updated jobs by status.
    database["dataset_generation_jobs"].create_index(
        [("status", ASCENDING), ("updated_at", DESCENDING)]
    )
    # Enables retries/lineage traversal from source job id.
    database["dataset_generation_jobs"].create_index(
        [("source_job_id", ASCENDING), ("created_at", DESCENDING)]
    )
    # Optimizes artifact listing per dataset by recency.
    database["dataset_generation_artifacts"].create_index(
        [("dataset_id", ASCENDING), ("created_at", DESCENDING)]
    )
    # Ensures one artifact filename per generation run.
    database["dataset_generation_artifacts"].create_index(
        [("generation_run_id", ASCENDING), ("file_name", ASCENDING)],
        unique=True,
        name="uq_generation_run_file",
    )
    # Helps cleanup queries over artifact lifecycle status and expiry.
    database["dataset_generation_artifacts"].create_index(
        [("status", ASCENDING), ("expires_at", ASCENDING)]
    )
