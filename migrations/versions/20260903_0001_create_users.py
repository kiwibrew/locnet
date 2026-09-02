"""Create the users table.

Revision ID: 20260903_0001
Revises:
Create Date: 2026-09-03
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260903_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column(
            "api_access_enabled",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
        sa.Column("bearer_token_hash", sa.String(length=64), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("is_admin", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reset_token_hash", sa.String(length=64), nullable=True),
        sa.Column(
            "reset_token_expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.CheckConstraint(
            "(is_admin = 0) OR "
            "(api_access_enabled = 0 AND bearer_token_hash IS NULL)",
            name="admin_has_no_api_token",
        ),
        sa.CheckConstraint(
            "(api_access_enabled = 0 AND bearer_token_hash IS NULL) OR "
            "(api_access_enabled = 1 AND bearer_token_hash IS NOT NULL)",
            name="api_token_matches_enabled",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index(
        "ix_users_bearer_token_hash",
        "users",
        ["bearer_token_hash"],
        unique=True,
    )
    op.create_index(
        "ix_users_reset_token_hash",
        "users",
        ["reset_token_hash"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_users_reset_token_hash", table_name="users")
    op.drop_index("ix_users_bearer_token_hash", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
