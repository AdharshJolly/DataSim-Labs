import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict


def _parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class DataProfile:
    id: uuid.UUID
    dataset_version_id: uuid.UUID
    columns: Dict[str, Any]
    dependency_graph: list[Dict[str, Any]]
    correlation_matrices: Dict[str, Any]
    semantic_groups: list[Dict[str, Any]]
    row_count: int
    metadata: Dict[str, Any]
    created_at: datetime

    @classmethod
    def new(
        cls,
        dataset_version_id: uuid.UUID,
        columns: Dict[str, Any],
        dependency_graph: list[Dict[str, Any]],
        correlation_matrices: Dict[str, Any],
        row_count: int,
        semantic_groups: list[Dict[str, Any]] | None = None,
        metadata: Dict[str, Any] | None = None,
    ) -> "DataProfile":
        return cls(
            id=uuid.uuid4(),
            dataset_version_id=dataset_version_id,
            columns=columns,
            dependency_graph=dependency_graph,
            correlation_matrices=correlation_matrices,
            semantic_groups=semantic_groups or [],
            row_count=row_count,
            metadata=metadata or {},
            created_at=datetime.now(timezone.utc),
        )

    @classmethod
    def from_document(cls, document: dict[str, Any]) -> "DataProfile":
        return cls(
            id=uuid.UUID(str(document["_id"])),
            dataset_version_id=uuid.UUID(str(document["dataset_version_id"])),
            columns=document.get("columns", {}),
            dependency_graph=document.get("dependency_graph", []),
            correlation_matrices=document.get("correlation_matrices", {}),
            semantic_groups=document.get("semantic_groups", []),
            row_count=document.get("row_count", 0),
            metadata=document.get("metadata", {}),
            created_at=_parse_datetime(document.get("created_at")),
        )

    def to_document(self) -> dict[str, Any]:
        return {
            "_id": str(self.id),
            "dataset_version_id": str(self.dataset_version_id),
            "columns": self.columns,
            "dependency_graph": self.dependency_graph,
            "correlation_matrices": self.correlation_matrices,
            "semantic_groups": self.semantic_groups,
            "row_count": self.row_count,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }
