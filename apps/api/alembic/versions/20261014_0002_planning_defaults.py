"""planning defaults

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-13 23:40:36.863717
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "planning_default",
        sa.Column(
            "area_code",
            sa.String(length=64),
            nullable=False,
            comment="District, or RW for national",
        ),
        sa.Column("budget_rwf", sa.BigInteger(), nullable=False, comment="Default budget in RWF"),
        sa.Column("weight_stunting", sa.Float(), nullable=False, comment="Default stunting weight"),
        sa.Column(
            "weight_readiness", sa.Float(), nullable=False, comment="Default readiness weight"
        ),
        sa.Column("weight_jobs", sa.Float(), nullable=False, comment="Default jobs weight"),
        sa.Column("updated_by", sa.Uuid(), nullable=True, comment="Analyst who last changed it"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="When the row was written",
        ),
        sa.ForeignKeyConstraint(
            ["area_code"],
            ["admin_unit.code"],
            name=op.f("fk_planning_default_area_code_admin_unit"),
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["user_account.id"],
            name=op.f("fk_planning_default_updated_by_user_account"),
        ),
        sa.PrimaryKeyConstraint("area_code", name=op.f("pk_planning_default")),
    )


def downgrade() -> None:
    op.drop_table("planning_default")
