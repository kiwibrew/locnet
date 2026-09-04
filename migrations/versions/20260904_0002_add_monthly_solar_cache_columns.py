"""Add monthly solar irradiance to the solar cache.

Revision ID: 20260904_0002
Revises: 20260903_0001
Create Date: 2026-09-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260904_0002"
down_revision: str | None = "20260903_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


MONTHLY_SUN_COLUMNS = (
    "sun_jan",
    "sun_feb",
    "sun_mar",
    "sun_apr",
    "sun_may",
    "sun_jun",
    "sun_jul",
    "sun_aug",
    "sun_sep",
    "sun_oct",
    "sun_nov",
    "sun_dec",
)


def upgrade() -> None:
    with op.batch_alter_table("Solar_cache") as batch_op:
        for column in MONTHLY_SUN_COLUMNS:
            batch_op.add_column(sa.Column(column, sa.Float(), nullable=True))

    op.create_index(
        "ix_solar_cache_coordinates",
        "Solar_cache",
        ["latitude", "longitude"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_solar_cache_coordinates", table_name="Solar_cache")

    with op.batch_alter_table("Solar_cache") as batch_op:
        for column in MONTHLY_SUN_COLUMNS:
            batch_op.drop_column(column)
