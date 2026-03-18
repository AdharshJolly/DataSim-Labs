import uuid
from dataclasses import dataclass
from datetime import datetime
from datetime import timezone
from enum import Enum
from typing import Any


def _parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc)


class DatasetStatus(str, Enum):
    draft = "draft"
    active = "active"
    generating = "generating"
    archived = "archived"


class DataType(str, Enum):
    integer = "integer"
    float = "float"
    categorical = "categorical"
    boolean = "boolean"
    date = "date"
    text = "text"
    email = "email"
    name = "name"
    address = "address"


class DistributionType(str, Enum):
    uniform = "uniform"
    normal = "normal"
    skewed = "skewed"
    weighted_categorical = "weighted_categorical"


@dataclass(slots=True)
class Dataset:
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    description: str | None
    status: DatasetStatus
    latest_version_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def new(
        cls,
        user_id: uuid.UUID,
        name: str,
        description: str | None,
    ) -> "Dataset":
        now = datetime.now(timezone.utc)
        return cls(
            id=uuid.uuid4(),
            user_id=user_id,
            name=name,
            description=description,
            status=DatasetStatus.draft,
            latest_version_id=None,
            created_at=now,
            updated_at=now,
        )

    @classmethod
    def from_document(cls, document: dict[str, Any]) -> "Dataset":
        latest_version_id = document.get("latest_version_id")
        return cls(
            id=uuid.UUID(str(document["_id"])),
            user_id=uuid.UUID(str(document["user_id"])),
            name=str(document["name"]),
            description=document.get("description"),
            status=DatasetStatus(
                str(document.get("status", DatasetStatus.draft.value))
            ),
            latest_version_id=(
                uuid.UUID(str(latest_version_id)) if latest_version_id else None
            ),
            created_at=_parse_datetime(document.get("created_at")),
            updated_at=_parse_datetime(document.get("updated_at")),
        )

    def to_document(self) -> dict[str, Any]:
        return {
            "_id": str(self.id),
            "user_id": str(self.user_id),
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "latest_version_id": (
                str(self.latest_version_id) if self.latest_version_id else None
            ),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass(slots=True)
class DatasetVersion:
    id: uuid.UUID
    dataset_id: uuid.UUID
    version_number: int
    config_json: dict[str, Any]
    seed: int | None
    created_at: datetime

    @classmethod
    def new(
        cls,
        dataset_id: uuid.UUID,
        version_number: int,
        config_json: dict[str, Any],
        seed: int | None,
    ) -> "DatasetVersion":
        return cls(
            id=uuid.uuid4(),
            dataset_id=dataset_id,
            version_number=version_number,
            config_json=config_json,
            seed=seed,
            created_at=datetime.now(timezone.utc),
        )

    @classmethod
    def from_document(cls, document: dict[str, Any]) -> "DatasetVersion":
        return cls(
            id=uuid.UUID(str(document["_id"])),
            dataset_id=uuid.UUID(str(document["dataset_id"])),
            version_number=int(document["version_number"]),
            config_json=dict(document.get("config_json", {})),
            seed=document.get("seed"),
            created_at=_parse_datetime(document.get("created_at")),
        )

    def to_document(self) -> dict[str, Any]:
        return {
            "_id": str(self.id),
            "dataset_id": str(self.dataset_id),
            "version_number": self.version_number,
            "config_json": self.config_json,
            "seed": self.seed,
            "created_at": self.created_at,
        }


@dataclass(slots=True)
class Attribute:
    id: uuid.UUID
    dataset_version_id: uuid.UUID
    name: str
    data_type: DataType
    description: str | None
    constraints_json: dict[str, Any]
    distribution: DistributionType
    null_percentage: float
    order_index: int
    created_at: datetime

    @classmethod
    def new(
        cls,
        dataset_version_id: uuid.UUID,
        name: str,
        data_type: DataType,
        description: str | None,
        constraints_json: dict[str, Any],
        distribution: DistributionType,
        null_percentage: float,
        order_index: int,
    ) -> "Attribute":
        return cls(
            id=uuid.uuid4(),
            dataset_version_id=dataset_version_id,
            name=name,
            data_type=data_type,
            description=description,
            constraints_json=constraints_json,
            distribution=distribution,
            null_percentage=null_percentage,
            order_index=order_index,
            created_at=datetime.now(timezone.utc),
        )

    @classmethod
    def from_document(cls, document: dict[str, Any]) -> "Attribute":
        return cls(
            id=uuid.UUID(str(document["_id"])),
            dataset_version_id=uuid.UUID(str(document["dataset_version_id"])),
            name=str(document["name"]),
            data_type=DataType(str(document["data_type"])),
            description=document.get("description"),
            constraints_json=dict(document.get("constraints_json", {})),
            distribution=DistributionType(str(document["distribution"])),
            null_percentage=float(document.get("null_percentage", 0.0)),
            order_index=int(document.get("order_index", 0)),
            created_at=_parse_datetime(document.get("created_at")),
        )

    def to_document(self) -> dict[str, Any]:
        return {
            "_id": str(self.id),
            "dataset_version_id": str(self.dataset_version_id),
            "name": self.name,
            "data_type": self.data_type.value,
            "description": self.description,
            "constraints_json": self.constraints_json,
            "distribution": self.distribution.value,
            "null_percentage": self.null_percentage,
            "order_index": self.order_index,
            "created_at": self.created_at,
        }
