import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class DatasetStatus(str, Enum):
    draft = "draft"
    active = "active"
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


class Dataset(Base):
    __tablename__ = "datasets"

    __table_args__ = (
        Index("ix_datasets_latest_version_id", "latest_version_id"),
        Index("ix_datasets_user_id", "user_id"),
    )
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[DatasetStatus] = mapped_column(
        SAEnum(DatasetStatus, name="dataset_status"),
        default=DatasetStatus.draft,
        nullable=False,
    )
    latest_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    versions: Mapped[list["DatasetVersion"]] = relationship(
        "DatasetVersion", back_populates="dataset", cascade="all, delete-orphan"
    )
    user: Mapped["User"] = relationship("User", back_populates="datasets")


class DatasetVersion(Base):
    __tablename__ = "dataset_versions"

    __table_args__ = (
        UniqueConstraint(
            "dataset_id", "version_number", name="uq_dataset_versions_dataset_version"
        ),
        Index("ix_dataset_versions_dataset_id", "dataset_id"),
    )
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    config_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    seed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    dataset: Mapped[Dataset] = relationship("Dataset", back_populates="versions")
    attributes: Mapped[list["Attribute"]] = relationship(
        "Attribute", back_populates="dataset_version", cascade="all, delete-orphan"
    )


class Attribute(Base):
    __tablename__ = "attributes"

    __table_args__ = (
        Index("ix_attributes_dataset_version_id", "dataset_version_id"),
        CheckConstraint(
            "null_percentage >= 0 AND null_percentage <= 100",
            name="ck_attributes_null_percentage_range",
        ),
    )
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    dataset_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dataset_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    data_type: Mapped[DataType] = mapped_column(
        SAEnum(DataType, name="attribute_data_type"), nullable=False
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    constraints_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    distribution: Mapped[DistributionType] = mapped_column(
        SAEnum(DistributionType, name="attribute_distribution_type"), nullable=False
    )
    null_percentage: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    dataset_version: Mapped[DatasetVersion] = relationship(
        "DatasetVersion", back_populates="attributes"
    )
