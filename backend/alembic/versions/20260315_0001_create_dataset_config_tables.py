"""create dataset config tables

Revision ID: 20260315_0001
Revises: None
Create Date: 2026-03-15 00:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260315_0001"
down_revision = None
branch_labels = None
depends_on = None


dataset_status = postgresql.ENUM(
    "draft", "active", "archived", name="dataset_status", create_type=False
)
attribute_data_type = postgresql.ENUM(
    "integer",
    "float",
    "categorical",
    "boolean",
    "date",
    "text",
    "email",
    "name",
    "address",
    name="attribute_data_type",
    create_type=False,
)
attribute_distribution_type = postgresql.ENUM(
    "uniform",
    "normal",
    "skewed",
    "weighted_categorical",
    name="attribute_distribution_type",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    dataset_status.create(bind, checkfirst=True)
    attribute_data_type.create(bind, checkfirst=True)
    attribute_distribution_type.create(bind, checkfirst=True)

    op.create_table(
        "datasets",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", dataset_status, nullable=False, server_default="draft"),
        sa.Column("latest_version_id", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_datasets_latest_version_id", "datasets", ["latest_version_id"], unique=False
    )

    op.create_table(
        "dataset_versions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("dataset_id", sa.UUID(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column(
            "config_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("seed", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "dataset_id", "version_number", name="uq_dataset_versions_dataset_version"
        ),
    )
    op.create_index(
        "ix_dataset_versions_dataset_id",
        "dataset_versions",
        ["dataset_id"],
        unique=False,
    )

    op.create_table(
        "attributes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("dataset_version_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("data_type", attribute_data_type, nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "constraints_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("distribution", attribute_distribution_type, nullable=False),
        sa.Column("null_percentage", sa.Float(), nullable=False, server_default="0"),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "null_percentage >= 0 AND null_percentage <= 100",
            name="ck_attributes_null_percentage_range",
        ),
        sa.ForeignKeyConstraint(
            ["dataset_version_id"], ["dataset_versions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_attributes_dataset_version_id",
        "attributes",
        ["dataset_version_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_attributes_dataset_version_id", table_name="attributes")
    op.drop_table("attributes")
    op.drop_index("ix_dataset_versions_dataset_id", table_name="dataset_versions")
    op.drop_table("dataset_versions")
    op.drop_index("ix_datasets_latest_version_id", table_name="datasets")
    op.drop_table("datasets")

    bind = op.get_bind()
    attribute_distribution_type.drop(bind, checkfirst=True)
    attribute_data_type.drop(bind, checkfirst=True)
    dataset_status.drop(bind, checkfirst=True)
