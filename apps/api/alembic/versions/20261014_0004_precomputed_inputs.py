"""precomputed inputs: population cells, catchments, facilities, nearest-centre minutes

Also drops need_estimate.top_drivers (never read), and lets centre fields the NCDA register
may not publish be unknown.

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-14 18:26:28.258669
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geometry
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_geospatial_table(
        "facility",
        sa.Column("id", sa.String(length=64), nullable=False, comment="Source id"),
        sa.Column(
            "kind",
            sa.Enum(
                "school",
                "childcare",
                "health",
                name="facilitykind",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
            comment="school | childcare | health",
        ),
        sa.Column(
            "name", sa.String(length=160), nullable=True, comment="Name, when the source has one"
        ),
        sa.Column(
            "sector_code",
            sa.String(length=64),
            nullable=False,
            comment="Sector containing the facility",
        ),
        sa.Column(
            "location",
            Geometry(
                geometry_type="POINT",
                srid=4326,
                dimension=2,
                spatial_index=False,
                from_text="ST_GeomFromEWKT",
                name="geometry",
                nullable=False,
            ),
            nullable=False,
            comment="Facility location, EPSG:4326",
        ),
        sa.Column(
            "source",
            sa.String(length=160),
            nullable=False,
            comment='Named source, for example "NISR Census 2022" or "IrereroAI demo generator"',
        ),
        sa.Column(
            "reference_year",
            sa.SmallInteger(),
            nullable=False,
            comment="Year the values describe, not the year they were loaded",
        ),
        sa.Column(
            "origin",
            sa.Enum(
                "official",
                "public",
                "partner",
                "simulated",
                name="origin",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
            comment="official | public | partner | simulated. Drives UI badges",
        ),
        sa.Column(
            "pipeline_run_id",
            sa.Uuid(),
            nullable=True,
            comment="Pipeline run that loaded the row. Null for records entered through the app",
        ),
        sa.ForeignKeyConstraint(
            ["pipeline_run_id"],
            ["pipeline_run.id"],
            name=op.f("fk_facility_pipeline_run_id_pipeline_run"),
        ),
        sa.ForeignKeyConstraint(
            ["sector_code"], ["admin_unit.code"], name=op.f("fk_facility_sector_code_admin_unit")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_facility")),
    )
    op.create_geospatial_index(
        "idx_facility_location",
        "facility",
        ["location"],
        unique=False,
        postgresql_using="gist",
        postgresql_ops={},
    )
    op.create_index(
        op.f("ix_facility_pipeline_run_id"), "facility", ["pipeline_run_id"], unique=False
    )
    op.create_index(op.f("ix_facility_sector_code"), "facility", ["sector_code"], unique=False)
    op.create_geospatial_table(
        "population_cell",
        sa.Column(
            "id",
            sa.String(length=64),
            nullable=False,
            comment="'{sector}:{cell}', cell on the 500 m grid",
        ),
        sa.Column(
            "sector_code",
            sa.String(length=64),
            nullable=False,
            comment="Sector the cell belongs to",
        ),
        sa.Column(
            "location",
            Geometry(
                geometry_type="POINT",
                srid=4326,
                dimension=2,
                spatial_index=False,
                from_text="ST_GeomFromEWKT",
                name="geometry",
                nullable=False,
            ),
            nullable=False,
            comment="Cell point, EPSG:4326",
        ),
        sa.Column(
            "share",
            sa.Float(),
            nullable=False,
            comment="Share of the sector's children living in the cell",
        ),
        sa.Column(
            "source",
            sa.String(length=160),
            nullable=False,
            comment='Named source, for example "NISR Census 2022" or "IrereroAI demo generator"',
        ),
        sa.Column(
            "reference_year",
            sa.SmallInteger(),
            nullable=False,
            comment="Year the values describe, not the year they were loaded",
        ),
        sa.Column(
            "origin",
            sa.Enum(
                "official",
                "public",
                "partner",
                "simulated",
                name="origin",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
            comment="official | public | partner | simulated. Drives UI badges",
        ),
        sa.Column(
            "pipeline_run_id",
            sa.Uuid(),
            nullable=True,
            comment="Pipeline run that loaded the row. Null for records entered through the app",
        ),
        sa.ForeignKeyConstraint(
            ["pipeline_run_id"],
            ["pipeline_run.id"],
            name=op.f("fk_population_cell_pipeline_run_id_pipeline_run"),
        ),
        sa.ForeignKeyConstraint(
            ["sector_code"],
            ["admin_unit.code"],
            name=op.f("fk_population_cell_sector_code_admin_unit"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_population_cell")),
    )
    op.create_geospatial_index(
        "idx_population_cell_location",
        "population_cell",
        ["location"],
        unique=False,
        postgresql_using="gist",
        postgresql_ops={},
    )
    op.create_index(
        op.f("ix_population_cell_pipeline_run_id"),
        "population_cell",
        ["pipeline_run_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_population_cell_sector_code"), "population_cell", ["sector_code"], unique=False
    )
    op.create_table(
        "catchment",
        sa.Column(
            "seat_id",
            sa.String(length=32),
            nullable=False,
            comment="Centre code or candidate site code",
        ),
        sa.Column("cell_id", sa.String(length=64), nullable=False, comment="Population cell"),
        sa.Column(
            "walk_minutes", sa.Float(), nullable=False, comment="Estimated walking time in minutes"
        ),
        sa.Column(
            "method",
            sa.Enum(
                "road_network",
                "straight_line",
                name="travelmethod",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
            comment="road_network | straight_line",
        ),
        sa.ForeignKeyConstraint(
            ["cell_id"],
            ["population_cell.id"],
            name=op.f("fk_catchment_cell_id_population_cell"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("seat_id", "cell_id", name=op.f("pk_catchment")),
    )
    op.add_column(
        "candidate_site",
        sa.Column(
            "nearest_centre_minutes",
            sa.SmallInteger(),
            nullable=True,
            comment="Walking minutes to the nearest active centre. Precomputed by the build",
        ),
    )
    op.alter_column(
        "centre",
        "opening_hours",
        existing_type=sa.VARCHAR(length=64),
        nullable=True,
        comment='OpenStreetMap opening_hours syntax, e.g. "Mo-Fr 07:30-12:00". Null if unknown',
        existing_comment='OpenStreetMap opening_hours syntax, e.g. "Mo-Fr 07:30-12:00"',
    )
    op.alter_column(
        "centre",
        "fee_band",
        existing_type=sa.VARCHAR(length=32),
        nullable=True,
        comment="Monthly fee per child in RWF: free | under_1000 | from_1000_to_5000 | over_5000. Null if unknown",
        existing_comment="Monthly fee per child in RWF: free | under_1000 | from_1000_to_5000 | over_5000",
    )
    op.alter_column(
        "centre",
        "offers_growth_monitoring",
        existing_type=sa.BOOLEAN(),
        nullable=True,
        comment="Hosts growth monitoring or refers to it. Null if unknown",
        existing_comment="Hosts growth monitoring or refers to it",
    )
    op.alter_column(
        "centre",
        "disability_inclusive",
        existing_type=sa.BOOLEAN(),
        nullable=True,
        comment="Has adapted space and trained caregivers for children with disabilities. Null if unknown",
        existing_comment="Has adapted space and trained caregivers for children with disabilities",
    )
    op.drop_column("need_estimate", "top_drivers")


def downgrade() -> None:
    unknown = (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT count(*) FROM centre WHERE opening_hours IS NULL OR fee_band IS NULL "
                "OR offers_growth_monitoring IS NULL OR disability_inclusive IS NULL"
            )
        )
        .scalar_one()
    )
    if unknown:
        raise RuntimeError(
            f"{unknown} centres have unknown values that revision 0003 cannot hold. "
            "Migrate them by hand."
        )
    op.add_column(
        "need_estimate",
        sa.Column(
            "top_drivers",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
            comment="Up to five drivers: [{feature, label_en, label_rw, contribution}]",
        ),
    )
    op.alter_column("need_estimate", "top_drivers", server_default=None)
    op.alter_column(
        "centre",
        "disability_inclusive",
        existing_type=sa.BOOLEAN(),
        nullable=False,
        comment="Has adapted space and trained caregivers for children with disabilities",
        existing_comment="Has adapted space and trained caregivers for children with disabilities. Null if unknown",
    )
    op.alter_column(
        "centre",
        "offers_growth_monitoring",
        existing_type=sa.BOOLEAN(),
        nullable=False,
        comment="Hosts growth monitoring or refers to it",
        existing_comment="Hosts growth monitoring or refers to it. Null if unknown",
    )
    op.alter_column(
        "centre",
        "fee_band",
        existing_type=sa.VARCHAR(length=32),
        nullable=False,
        comment="Monthly fee per child in RWF: free | under_1000 | from_1000_to_5000 | over_5000",
        existing_comment="Monthly fee per child in RWF: free | under_1000 | from_1000_to_5000 | over_5000. Null if unknown",
    )
    op.alter_column(
        "centre",
        "opening_hours",
        existing_type=sa.VARCHAR(length=64),
        nullable=False,
        comment='OpenStreetMap opening_hours syntax, e.g. "Mo-Fr 07:30-12:00"',
        existing_comment='OpenStreetMap opening_hours syntax, e.g. "Mo-Fr 07:30-12:00". Null if unknown',
    )
    op.drop_column("candidate_site", "nearest_centre_minutes")
    op.drop_table("catchment")
    op.drop_index(op.f("ix_population_cell_sector_code"), table_name="population_cell")
    op.drop_index(op.f("ix_population_cell_pipeline_run_id"), table_name="population_cell")
    op.drop_geospatial_index(
        "idx_population_cell_location",
        table_name="population_cell",
        postgresql_using="gist",
        column_name="location",
    )
    op.drop_geospatial_table("population_cell")
    op.drop_index(op.f("ix_facility_sector_code"), table_name="facility")
    op.drop_index(op.f("ix_facility_pipeline_run_id"), table_name="facility")
    op.drop_geospatial_index(
        "idx_facility_location",
        table_name="facility",
        postgresql_using="gist",
        column_name="location",
    )
    op.drop_geospatial_table("facility")
