"""add users and dataset ownership

Revision ID: 20260315_0002
Revises: 20260315_0001
Create Date: 2026-03-15 01:00:00
"""

from alembic import op
import sqlalchemy as sa

revision = "20260315_0002"
down_revision = "20260315_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )

    op.add_column("datasets", sa.Column("user_id", sa.UUID(), nullable=True))
    op.create_index("ix_datasets_user_id", "datasets", ["user_id"], unique=False)
    op.create_foreign_key(
        "fk_datasets_user_id_users",
        "datasets",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("fk_datasets_user_id_users", "datasets", type_="foreignkey")
    op.drop_index("ix_datasets_user_id", table_name="datasets")
    op.drop_column("datasets", "user_id")
    op.drop_table("users")
