from pymongo import ASCENDING, DESCENDING

from app.db.session import database


def init_db() -> None:
    database["users"].create_index([("email", ASCENDING)], unique=True)
    database["datasets"].create_index(
        [("user_id", ASCENDING), ("created_at", DESCENDING)]
    )
    database["dataset_versions"].create_index(
        [("dataset_id", ASCENDING), ("version_number", DESCENDING)]
    )
    database["dataset_versions"].create_index(
        [("dataset_id", ASCENDING), ("version_number", ASCENDING)],
        unique=True,
    )
    database["attributes"].create_index(
        [("dataset_version_id", ASCENDING), ("order_index", ASCENDING)]
    )
    database["attributes"].create_index(
        [("dataset_version_id", ASCENDING), ("name", ASCENDING)],
        unique=True,
        name="uq_version_attr_name",
    )
    database["dataset_generation_runs"].create_index(
        [("dataset_id", ASCENDING), ("created_at", DESCENDING)]
    )
    database["dataset_generation_jobs"].create_index(
        [("user_id", ASCENDING), ("created_at", DESCENDING)]
    )
    database["dataset_generation_jobs"].create_index(
        [("dataset_id", ASCENDING), ("created_at", DESCENDING)]
    )
    database["dataset_generation_jobs"].create_index(
        [("status", ASCENDING), ("updated_at", DESCENDING)]
    )
