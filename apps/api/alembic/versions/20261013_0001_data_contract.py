"""data contract

Revision ID: 0001
Revises: none
Create Date: 2026-10-13 23:13:46.587962
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geometry
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


AUDIT_GUARD = """
CREATE FUNCTION audit_log_append_only() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'audit_log is append-only';
END;
$$;
CREATE TRIGGER audit_log_no_update BEFORE UPDATE OR DELETE ON audit_log
    FOR EACH ROW EXECUTE FUNCTION audit_log_append_only();
CREATE TRIGGER audit_log_no_truncate BEFORE TRUNCATE ON audit_log
    FOR EACH STATEMENT EXECUTE FUNCTION audit_log_append_only();
"""


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.create_table(
        "data_source",
        sa.Column(
            "id", sa.String(length=48), nullable=False, comment="Adapter name, e.g. census_2022"
        ),
        sa.Column(
            "name", sa.String(length=160), nullable=False, comment="Human-readable source name"
        ),
        sa.Column(
            "publisher", sa.String(length=120), nullable=False, comment="Publishing institution"
        ),
        sa.Column("reference_year", sa.SmallInteger(), nullable=True, comment="Year described"),
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
            comment="Origin once loaded",
        ),
        sa.Column(
            "status",
            sa.Enum(
                "loaded",
                "simulated_stand_in",
                "planned",
                name="sourcestatus",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
            comment="loaded | simulated_stand_in | planned",
        ),
        sa.Column(
            "licence", sa.String(length=160), nullable=False, comment="Licence or access terms"
        ),
        sa.Column(
            "url", sa.String(length=300), nullable=True, comment="Where the source is published"
        ),
        sa.Column(
            "feeds",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            comment="Tables or indicators this source feeds",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_data_source")),
    )
    op.create_table(
        "otp_challenge",
        sa.Column("id", sa.Uuid(), nullable=False, comment="Id"),
        sa.Column("phone", sa.String(length=16), nullable=False, comment="E.164 phone"),
        sa.Column(
            "code_hash", sa.String(length=255), nullable=False, comment="Argon2id hash of the code"
        ),
        sa.Column("attempts", sa.SmallInteger(), nullable=False, comment="Failed attempts"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False, comment="Expiry"),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True, comment="Used"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="When the row was written",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_otp_challenge")),
    )
    op.create_index(op.f("ix_otp_challenge_phone"), "otp_challenge", ["phone"], unique=False)
    op.create_table(
        "pipeline_run",
        sa.Column("id", sa.Uuid(), nullable=False, comment="Run id"),
        sa.Column(
            "pipeline",
            sa.String(length=48),
            nullable=False,
            comment="Adapter or generator name, e.g. demo_generator",
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
            comment="Origin of the rows loaded",
        ),
        sa.Column(
            "status",
            sa.Enum(
                "running",
                "succeeded",
                "failed",
                name="runstatus",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
            comment="running | succeeded | failed",
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, comment="Start time"),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True, comment="End time"),
        sa.Column(
            "code_version",
            sa.String(length=64),
            nullable=False,
            comment="Git commit or package version",
        ),
        sa.Column(
            "inputs",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            comment="Input files with sha256 and size: [{path, sha256, bytes}]",
        ),
        sa.Column(
            "row_counts",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            comment="Rows written per table",
        ),
        sa.Column(
            "checks",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            comment="Checks run: [{name, passed, detail}]",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_pipeline_run")),
    )
    op.create_index(op.f("ix_pipeline_run_pipeline"), "pipeline_run", ["pipeline"], unique=False)
    op.create_table(
        "user_account",
        sa.Column("id", sa.Uuid(), nullable=False, comment="Id"),
        sa.Column(
            "role",
            sa.Enum(
                "parent",
                "caregiver",
                "sector_officer",
                "district_planner",
                "national_analyst",
                "admin",
                name="role",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
            comment="Role",
        ),
        sa.Column(
            "scope_level",
            sa.Enum(
                "none",
                "centre",
                "sector",
                "district",
                "national",
                name="scopelevel",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
            comment="none | centre | sector | district | national",
        ),
        sa.Column(
            "scope_code",
            sa.String(length=64),
            nullable=True,
            comment="Centre code or admin unit code the account may see",
        ),
        sa.Column(
            "display_name", sa.String(length=120), nullable=False, comment="Name shown in the app"
        ),
        sa.Column("email", sa.String(length=254), nullable=True, comment="Staff login"),
        sa.Column(
            "phone",
            sa.String(length=16),
            nullable=True,
            comment="E.164 phone, parent and caregiver login",
        ),
        sa.Column("password_hash", sa.String(length=255), nullable=True, comment="Argon2id hash"),
        sa.Column(
            "totp_secret",
            sa.String(length=64),
            nullable=True,
            comment="TOTP secret. Required for admins",
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, comment="Can sign in"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="When the row was written",
        ),
        sa.CheckConstraint(
            "(scope_level IN ('none', 'national')) = (scope_code IS NULL)",
            name=op.f("ck_user_account_scope"),
        ),
        sa.CheckConstraint(
            "email IS NOT NULL OR phone IS NOT NULL", name=op.f("ck_user_account_has_login")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_account")),
        sa.UniqueConstraint("email", name=op.f("uq_user_account_email")),
        sa.UniqueConstraint("phone", name=op.f("uq_user_account_phone")),
    )
    op.create_geospatial_table(
        "admin_unit",
        sa.Column(
            "code",
            sa.String(length=64),
            nullable=False,
            comment="Stable IrereroAI code, e.g. D-GICUMBI or S-GICUMBI-BYUMBA. All tables join on it",
        ),
        sa.Column(
            "name", sa.String(length=120), nullable=False, comment="Official name as published"
        ),
        sa.Column(
            "level",
            sa.Enum(
                "country",
                "province",
                "district",
                "sector",
                "cell",
                "village",
                name="adminlevel",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
            comment="country | province | district | sector | cell | village",
        ),
        sa.Column(
            "parent_code", sa.String(length=64), nullable=True, comment="Code of the enclosing unit"
        ),
        sa.Column(
            "nisr_code",
            sa.String(length=16),
            nullable=True,
            comment="Official NISR administrative code. Filled by the Phase 2 boundaries adapter",
        ),
        sa.Column(
            "source_ref",
            sa.String(length=64),
            nullable=True,
            comment="Identifier in the boundary source, e.g. the geoBoundaries shapeID",
        ),
        sa.Column(
            "geom",
            Geometry(
                geometry_type="MULTIPOLYGON",
                srid=4326,
                dimension=2,
                spatial_index=False,
                from_text="ST_GeomFromEWKT",
                name="geometry",
                nullable=False,
            ),
            nullable=False,
            comment="Boundary, EPSG:4326, full detail",
        ),
        sa.Column(
            "geom_medium",
            Geometry(
                geometry_type="MULTIPOLYGON",
                srid=4326,
                dimension=2,
                spatial_index=False,
                from_text="ST_GeomFromEWKT",
                name="geometry",
                nullable=False,
            ),
            nullable=False,
            comment="Boundary simplified for district zoom (about 50 m tolerance)",
        ),
        sa.Column(
            "geom_coarse",
            Geometry(
                geometry_type="MULTIPOLYGON",
                srid=4326,
                dimension=2,
                spatial_index=False,
                from_text="ST_GeomFromEWKT",
                name="geometry",
                nullable=False,
            ),
            nullable=False,
            comment="Boundary simplified for national zoom (about 500 m tolerance)",
        ),
        sa.Column(
            "centroid",
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
            comment="Point on surface, EPSG:4326",
        ),
        sa.Column(
            "area_km2", sa.Float(), nullable=False, comment="Area computed in EPSG:32735 (UTM 35S)"
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
            ["parent_code"], ["admin_unit.code"], name=op.f("fk_admin_unit_parent_code_admin_unit")
        ),
        sa.ForeignKeyConstraint(
            ["pipeline_run_id"],
            ["pipeline_run.id"],
            name=op.f("fk_admin_unit_pipeline_run_id_pipeline_run"),
        ),
        sa.PrimaryKeyConstraint("code", name=op.f("pk_admin_unit")),
        sa.UniqueConstraint("nisr_code", name=op.f("uq_admin_unit_nisr_code")),
    )
    op.create_geospatial_index(
        "idx_admin_unit_centroid",
        "admin_unit",
        ["centroid"],
        unique=False,
        postgresql_using="gist",
        postgresql_ops={},
    )
    op.create_geospatial_index(
        "idx_admin_unit_geom",
        "admin_unit",
        ["geom"],
        unique=False,
        postgresql_using="gist",
        postgresql_ops={},
    )
    op.create_geospatial_index(
        "idx_admin_unit_geom_coarse",
        "admin_unit",
        ["geom_coarse"],
        unique=False,
        postgresql_using="gist",
        postgresql_ops={},
    )
    op.create_geospatial_index(
        "idx_admin_unit_geom_medium",
        "admin_unit",
        ["geom_medium"],
        unique=False,
        postgresql_using="gist",
        postgresql_ops={},
    )
    op.create_index(op.f("ix_admin_unit_level"), "admin_unit", ["level"], unique=False)
    op.create_index(op.f("ix_admin_unit_parent_code"), "admin_unit", ["parent_code"], unique=False)
    op.create_index(
        op.f("ix_admin_unit_pipeline_run_id"), "admin_unit", ["pipeline_run_id"], unique=False
    )
    op.create_table(
        "audit_log",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, comment="Id"),
        sa.Column("actor_id", sa.Uuid(), nullable=True, comment="Account that acted"),
        sa.Column(
            "actor_role",
            sa.Enum(
                "parent",
                "caregiver",
                "sector_officer",
                "district_planner",
                "national_analyst",
                "admin",
                name="role",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
            comment="Role at the time",
        ),
        sa.Column(
            "action",
            sa.String(length=48),
            nullable=False,
            comment="e.g. recommendation.reject, centre.verify, alert.resolve",
        ),
        sa.Column(
            "entity_type", sa.String(length=48), nullable=False, comment="Table of the changed row"
        ),
        sa.Column(
            "entity_id", sa.String(length=64), nullable=False, comment="Key of the changed row"
        ),
        sa.Column(
            "before",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Values before",
        ),
        sa.Column(
            "after", postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment="Values after"
        ),
        sa.Column("reason", sa.Text(), nullable=True, comment="Reason given by the person"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="When the row was written",
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"], ["user_account.id"], name=op.f("fk_audit_log_actor_id_user_account")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_log")),
    )
    op.create_index(op.f("ix_audit_log_action"), "audit_log", ["action"], unique=False)
    op.create_index(op.f("ix_audit_log_actor_id"), "audit_log", ["actor_id"], unique=False)
    op.create_index(op.f("ix_audit_log_entity_id"), "audit_log", ["entity_id"], unique=False)
    op.create_table(
        "model_version",
        sa.Column(
            "id", sa.String(length=64), nullable=False, comment="Version id, e.g. need-baseline-1"
        ),
        sa.Column(
            "component",
            sa.Enum(
                "need",
                "coverage",
                "optimizer",
                "early_warning",
                "explainer",
                name="enginecomponent",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
            comment="need | coverage | optimizer | early_warning | explainer",
        ),
        sa.Column(
            "description", sa.Text(), nullable=False, comment="What the model does, in plain words"
        ),
        sa.Column(
            "params",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            comment="Parameters and thresholds",
        ),
        sa.Column(
            "metrics",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            comment="Evaluation metrics. Empty for rule-based baselines",
        ),
        sa.Column(
            "trained_on_run_id",
            sa.Uuid(),
            nullable=True,
            comment="Pipeline run that produced the training data",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="When the row was written",
        ),
        sa.ForeignKeyConstraint(
            ["trained_on_run_id"],
            ["pipeline_run.id"],
            name=op.f("fk_model_version_trained_on_run_id_pipeline_run"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_model_version")),
    )
    op.create_table(
        "refresh_token",
        sa.Column("id", sa.Uuid(), nullable=False, comment="Token id"),
        sa.Column("user_id", sa.Uuid(), nullable=False, comment="Owner"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False, comment="Expiry"),
        sa.Column(
            "revoked_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Set on rotation or sign-out",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="When the row was written",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user_account.id"],
            name=op.f("fk_refresh_token_user_id_user_account"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_refresh_token")),
    )
    op.create_index(op.f("ix_refresh_token_user_id"), "refresh_token", ["user_id"], unique=False)
    op.create_geospatial_table(
        "saved_search",
        sa.Column("id", sa.Uuid(), nullable=False, comment="Id"),
        sa.Column("user_id", sa.Uuid(), nullable=False, comment="Parent"),
        sa.Column("label", sa.String(length=80), nullable=False, comment="Name the parent gave it"),
        sa.Column("grid_cell", sa.String(length=32), nullable=False, comment="500 m cell id"),
        sa.Column(
            "cell_centre",
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
            comment="Centre of the cell, EPSG:4326",
        ),
        sa.Column(
            "filters",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            comment="{age_band, meals, max_fee_band, max_km}",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="When the row was written",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user_account.id"],
            name=op.f("fk_saved_search_user_id_user_account"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_saved_search")),
    )
    op.create_geospatial_index(
        "idx_saved_search_cell_centre",
        "saved_search",
        ["cell_centre"],
        unique=False,
        postgresql_using="gist",
        postgresql_ops={},
    )
    op.create_index(op.f("ix_saved_search_user_id"), "saved_search", ["user_id"], unique=False)
    op.create_table(
        "unit_cost",
        sa.Column(
            "action",
            sa.Enum(
                "build",
                "upgrade",
                "support",
                name="action",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
            comment="build | upgrade | support",
        ),
        sa.Column(
            "band",
            sa.Enum(
                "low",
                "medium",
                "high",
                name="costband",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
            comment="low | medium | high",
        ),
        sa.Column("cost_rwf", sa.BigInteger(), nullable=False, comment="Expected cost in RWF"),
        sa.Column("cost_low_rwf", sa.BigInteger(), nullable=False, comment="Lower bound in RWF"),
        sa.Column("cost_high_rwf", sa.BigInteger(), nullable=False, comment="Upper bound in RWF"),
        sa.Column(
            "places_added", sa.Integer(), nullable=False, comment="New places the action creates"
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
        sa.CheckConstraint(
            "cost_low_rwf <= cost_rwf AND cost_rwf <= cost_high_rwf",
            name=op.f("ck_unit_cost_ordered"),
        ),
        sa.ForeignKeyConstraint(
            ["pipeline_run_id"],
            ["pipeline_run.id"],
            name=op.f("fk_unit_cost_pipeline_run_id_pipeline_run"),
        ),
        sa.PrimaryKeyConstraint("action", "band", name=op.f("pk_unit_cost")),
    )
    op.create_index(
        op.f("ix_unit_cost_pipeline_run_id"), "unit_cost", ["pipeline_run_id"], unique=False
    )
    op.create_table(
        "area_indicator",
        sa.Column("id", sa.Uuid(), nullable=False, comment="Row id"),
        sa.Column(
            "area_code", sa.String(length=64), nullable=False, comment="Area the value describes"
        ),
        sa.Column(
            "indicator",
            sa.String(length=64),
            nullable=False,
            comment="Indicator code from docs/DATA_CONTRACT.md#indicators",
        ),
        sa.Column("value", sa.Float(), nullable=False, comment="Value in the indicator's unit"),
        sa.Column(
            "low", sa.Float(), nullable=True, comment="Lower bound when the source gives one"
        ),
        sa.Column(
            "high", sa.Float(), nullable=True, comment="Upper bound when the source gives one"
        ),
        sa.Column(
            "unit", sa.String(length=32), nullable=False, comment="count | share | minutes | rwf"
        ),
        sa.Column(
            "sample_size",
            sa.Integer(),
            nullable=True,
            comment="Survey respondents behind the value, when survey-based",
        ),
        sa.Column(
            "reference_date",
            sa.Date(),
            nullable=True,
            comment="Exact date when finer than reference_year",
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
        sa.CheckConstraint(
            "(low IS NULL AND high IS NULL) OR (low <= value AND value <= high)",
            name=op.f("ck_area_indicator_range_ordered"),
        ),
        sa.ForeignKeyConstraint(
            ["area_code"], ["admin_unit.code"], name=op.f("fk_area_indicator_area_code_admin_unit")
        ),
        sa.ForeignKeyConstraint(
            ["pipeline_run_id"],
            ["pipeline_run.id"],
            name=op.f("fk_area_indicator_pipeline_run_id_pipeline_run"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_area_indicator")),
    )
    op.create_index(
        op.f("ix_area_indicator_area_code"), "area_indicator", ["area_code"], unique=False
    )
    op.create_index(
        op.f("ix_area_indicator_indicator"), "area_indicator", ["indicator"], unique=False
    )
    op.create_index(
        op.f("ix_area_indicator_pipeline_run_id"),
        "area_indicator",
        ["pipeline_run_id"],
        unique=False,
    )
    op.create_geospatial_table(
        "centre",
        sa.Column("code", sa.String(length=32), nullable=False, comment="IrereroAI centre code"),
        sa.Column(
            "name", sa.String(length=160), nullable=False, comment="Centre name as registered"
        ),
        sa.Column(
            "type",
            sa.Enum(
                "home_based",
                "community_based",
                "school_based",
                "centre_based",
                name="centretype",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
            comment="home_based | community_based | school_based | centre_based",
        ),
        sa.Column(
            "status",
            sa.Enum(
                "active",
                "closed",
                name="centrestatus",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
            comment="active | closed",
        ),
        sa.Column(
            "sector_code", sa.String(length=64), nullable=False, comment="Sector the centre is in"
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
            comment="Centre location, EPSG:4326",
        ),
        sa.Column(
            "capacity",
            sa.Integer(),
            nullable=False,
            comment="Number of children the centre can take",
        ),
        sa.Column("serves_0_2", sa.Boolean(), nullable=False, comment="Takes children aged 0 to 2"),
        sa.Column("serves_3_6", sa.Boolean(), nullable=False, comment="Takes children aged 3 to 6"),
        sa.Column(
            "opening_hours",
            sa.String(length=64),
            nullable=False,
            comment='OpenStreetMap opening_hours syntax, e.g. "Mo-Fr 07:30-12:00"',
        ),
        sa.Column(
            "fee_band",
            sa.Enum(
                "free",
                "under_1000",
                "from_1000_to_5000",
                "over_5000",
                name="feeband",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
            comment="Monthly fee per child in RWF: free | under_1000 | from_1000_to_5000 | over_5000",
        ),
        sa.Column(
            "offers_meals", sa.Boolean(), nullable=False, comment="Serves at least one meal a day"
        ),
        sa.Column(
            "offers_growth_monitoring",
            sa.Boolean(),
            nullable=False,
            comment="Hosts growth monitoring or refers to it",
        ),
        sa.Column(
            "disability_inclusive",
            sa.Boolean(),
            nullable=False,
            comment="Has adapted space and trained caregivers for children with disabilities",
        ),
        sa.Column(
            "verified",
            sa.Boolean(),
            nullable=False,
            comment="A sector officer has checked the centre in person",
        ),
        sa.Column(
            "verified_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When the last verification happened",
        ),
        sa.Column(
            "verified_by", sa.Uuid(), nullable=True, comment="Officer who verified the centre"
        ),
        sa.Column(
            "reliability_score",
            sa.Float(),
            nullable=False,
            comment="0 to 1. Share of the last 12 weeks reported on time without quality flags",
        ),
        sa.Column(
            "ncda_ref",
            sa.String(length=64),
            nullable=True,
            comment="Record identifier in the NCDA ECD Mapping System",
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
        sa.CheckConstraint(
            "reliability_score BETWEEN 0 AND 1", name=op.f("ck_centre_reliability_range")
        ),
        sa.CheckConstraint("serves_0_2 OR serves_3_6", name=op.f("ck_centre_serves_an_age_band")),
        sa.ForeignKeyConstraint(
            ["pipeline_run_id"],
            ["pipeline_run.id"],
            name=op.f("fk_centre_pipeline_run_id_pipeline_run"),
        ),
        sa.ForeignKeyConstraint(
            ["sector_code"], ["admin_unit.code"], name=op.f("fk_centre_sector_code_admin_unit")
        ),
        sa.ForeignKeyConstraint(
            ["verified_by"], ["user_account.id"], name=op.f("fk_centre_verified_by_user_account")
        ),
        sa.PrimaryKeyConstraint("code", name=op.f("pk_centre")),
        sa.UniqueConstraint("ncda_ref", name=op.f("uq_centre_ncda_ref")),
    )
    op.create_geospatial_index(
        "idx_centre_location",
        "centre",
        ["location"],
        unique=False,
        postgresql_using="gist",
        postgresql_ops={},
    )
    op.create_index(op.f("ix_centre_pipeline_run_id"), "centre", ["pipeline_run_id"], unique=False)
    op.create_index(op.f("ix_centre_sector_code"), "centre", ["sector_code"], unique=False)
    op.create_table(
        "coverage_snapshot",
        sa.Column("id", sa.Uuid(), nullable=False, comment="Row id"),
        sa.Column("area_code", sa.String(length=64), nullable=False, comment="Sector"),
        sa.Column("week_start", sa.Date(), nullable=False, comment="Monday of the week"),
        sa.Column(
            "model_version_id",
            sa.String(length=64),
            nullable=False,
            comment="Coverage model that produced the row",
        ),
        sa.Column(
            "children_covered",
            sa.Integer(),
            nullable=False,
            comment="Children 0 to 6 with a place within the catchment",
        ),
        sa.Column(
            "children_uncovered",
            sa.Integer(),
            nullable=False,
            comment="Children 0 to 6 without a reachable place",
        ),
        sa.Column(
            "overcrowded_centres",
            sa.Integer(),
            nullable=False,
            comment="Centres with attendance above capacity",
        ),
        sa.Column(
            "catchment_minutes",
            sa.SmallInteger(),
            nullable=False,
            comment="Walking time used for the catchment",
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
            ["area_code"],
            ["admin_unit.code"],
            name=op.f("fk_coverage_snapshot_area_code_admin_unit"),
        ),
        sa.ForeignKeyConstraint(
            ["model_version_id"],
            ["model_version.id"],
            name=op.f("fk_coverage_snapshot_model_version_id_model_version"),
        ),
        sa.ForeignKeyConstraint(
            ["pipeline_run_id"],
            ["pipeline_run.id"],
            name=op.f("fk_coverage_snapshot_pipeline_run_id_pipeline_run"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_coverage_snapshot")),
    )
    op.create_index(
        op.f("ix_coverage_snapshot_area_code"), "coverage_snapshot", ["area_code"], unique=False
    )
    op.create_index(
        op.f("ix_coverage_snapshot_pipeline_run_id"),
        "coverage_snapshot",
        ["pipeline_run_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_coverage_snapshot_week_start"), "coverage_snapshot", ["week_start"], unique=False
    )
    op.create_geospatial_table(
        "demand_signal",
        sa.Column("id", sa.Uuid(), nullable=False, comment="Id"),
        sa.Column(
            "kind",
            sa.Enum(
                "empty_search",
                "centre_request",
                name="demandkind",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
            comment="empty_search | centre_request",
        ),
        sa.Column(
            "grid_cell",
            sa.String(length=32),
            nullable=False,
            comment="500 m cell id in EPSG:32735: 'E{easting}N{northing}'",
        ),
        sa.Column(
            "cell_centre",
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
            comment="Centre of the cell, EPSG:4326",
        ),
        sa.Column(
            "sector_code",
            sa.String(length=64),
            nullable=False,
            comment="Sector containing the cell centre",
        ),
        sa.Column(
            "age_band",
            sa.String(length=8),
            nullable=True,
            comment="Age band searched for: 0_2 | 3_6",
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
            comment="Origin of the signal",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="When the row was written",
        ),
        sa.ForeignKeyConstraint(
            ["sector_code"],
            ["admin_unit.code"],
            name=op.f("fk_demand_signal_sector_code_admin_unit"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_demand_signal")),
    )
    op.create_geospatial_index(
        "idx_demand_signal_cell_centre",
        "demand_signal",
        ["cell_centre"],
        unique=False,
        postgresql_using="gist",
        postgresql_ops={},
    )
    op.create_index(
        op.f("ix_demand_signal_grid_cell"), "demand_signal", ["grid_cell"], unique=False
    )
    op.create_index(
        op.f("ix_demand_signal_sector_code"), "demand_signal", ["sector_code"], unique=False
    )
    op.create_table(
        "need_estimate",
        sa.Column("id", sa.Uuid(), nullable=False, comment="Row id"),
        sa.Column(
            "area_code",
            sa.String(length=64),
            nullable=False,
            comment="Sector for district deep dives, district for the national map",
        ),
        sa.Column(
            "model_version_id",
            sa.String(length=64),
            nullable=False,
            comment="Model that produced the estimate",
        ),
        sa.Column(
            "children_0_2_estimate",
            sa.Integer(),
            nullable=False,
            comment="Children aged 0 to 2, point estimate",
        ),
        sa.Column(
            "children_0_2_low",
            sa.Integer(),
            nullable=False,
            comment="Children aged 0 to 2, lower bound",
        ),
        sa.Column(
            "children_0_2_high",
            sa.Integer(),
            nullable=False,
            comment="Children aged 0 to 2, upper bound",
        ),
        sa.Column(
            "children_3_6_estimate",
            sa.Integer(),
            nullable=False,
            comment="Children aged 3 to 6, point estimate",
        ),
        sa.Column(
            "children_3_6_low",
            sa.Integer(),
            nullable=False,
            comment="Children aged 3 to 6, lower bound",
        ),
        sa.Column(
            "children_3_6_high",
            sa.Integer(),
            nullable=False,
            comment="Children aged 3 to 6, upper bound",
        ),
        sa.Column(
            "stunting_risk_estimate",
            sa.Float(),
            nullable=False,
            comment="Share of under-5s at risk of stunting",
        ),
        sa.Column(
            "stunting_risk_low", sa.Float(), nullable=False, comment="Stunting risk, lower bound"
        ),
        sa.Column(
            "stunting_risk_high", sa.Float(), nullable=False, comment="Stunting risk, upper bound"
        ),
        sa.Column(
            "mothers_barrier_share_estimate",
            sa.Float(),
            nullable=False,
            comment="Share of mothers of under-3s who report childcare as a barrier to work",
        ),
        sa.Column(
            "mothers_barrier_share_low",
            sa.Float(),
            nullable=False,
            comment="Mothers' childcare barrier, lower bound",
        ),
        sa.Column(
            "mothers_barrier_share_high",
            sa.Float(),
            nullable=False,
            comment="Mothers' childcare barrier, upper bound",
        ),
        sa.Column(
            "top_drivers",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            comment="Up to five drivers: [{feature, label_en, label_rw, contribution}]",
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
        sa.CheckConstraint(
            "children_0_2_low <= children_0_2_estimate AND children_0_2_estimate <= children_0_2_high",
            name=op.f("ck_need_estimate_children_0_2_range_ordered"),
        ),
        sa.CheckConstraint(
            "children_3_6_low <= children_3_6_estimate AND children_3_6_estimate <= children_3_6_high",
            name=op.f("ck_need_estimate_children_3_6_range_ordered"),
        ),
        sa.CheckConstraint(
            "mothers_barrier_share_low <= mothers_barrier_share_estimate AND mothers_barrier_share_estimate <= mothers_barrier_share_high",
            name=op.f("ck_need_estimate_mothers_barrier_share_range_ordered"),
        ),
        sa.CheckConstraint(
            "stunting_risk_low <= stunting_risk_estimate AND stunting_risk_estimate <= stunting_risk_high",
            name=op.f("ck_need_estimate_stunting_risk_range_ordered"),
        ),
        sa.ForeignKeyConstraint(
            ["area_code"], ["admin_unit.code"], name=op.f("fk_need_estimate_area_code_admin_unit")
        ),
        sa.ForeignKeyConstraint(
            ["model_version_id"],
            ["model_version.id"],
            name=op.f("fk_need_estimate_model_version_id_model_version"),
        ),
        sa.ForeignKeyConstraint(
            ["pipeline_run_id"],
            ["pipeline_run.id"],
            name=op.f("fk_need_estimate_pipeline_run_id_pipeline_run"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_need_estimate")),
    )
    op.create_index(
        op.f("ix_need_estimate_area_code"), "need_estimate", ["area_code"], unique=False
    )
    op.create_index(
        op.f("ix_need_estimate_pipeline_run_id"), "need_estimate", ["pipeline_run_id"], unique=False
    )
    op.create_table(
        "scenario",
        sa.Column("id", sa.Uuid(), nullable=False, comment="Id"),
        sa.Column(
            "district_code", sa.String(length=64), nullable=False, comment="District being planned"
        ),
        sa.Column(
            "name", sa.String(length=120), nullable=False, comment="Label shown in comparisons"
        ),
        sa.Column("budget_rwf", sa.BigInteger(), nullable=False, comment="Budget in RWF"),
        sa.Column(
            "weight_stunting",
            sa.Float(),
            nullable=False,
            comment="Policy weight on high stunting risk",
        ),
        sa.Column(
            "weight_readiness",
            sa.Float(),
            nullable=False,
            comment="Policy weight on uncovered 3 to 6 year olds",
        ),
        sa.Column(
            "weight_jobs",
            sa.Float(),
            nullable=False,
            comment="Policy weight on mothers' childcare barrier",
        ),
        sa.Column(
            "constraints",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            comment="Extra constraints: {excluded_site_ids, max_actions_per_sector}",
        ),
        sa.Column(
            "is_baseline",
            sa.Boolean(),
            nullable=False,
            comment="True for the largest-population-first comparison run",
        ),
        sa.Column(
            "model_version_id", sa.String(length=64), nullable=False, comment="Optimizer version"
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
            comment="simulated when any input record is simulated",
        ),
        sa.Column("created_by", sa.Uuid(), nullable=False, comment="Planner who ran it"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="When the row was written",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["user_account.id"], name=op.f("fk_scenario_created_by_user_account")
        ),
        sa.ForeignKeyConstraint(
            ["district_code"],
            ["admin_unit.code"],
            name=op.f("fk_scenario_district_code_admin_unit"),
        ),
        sa.ForeignKeyConstraint(
            ["model_version_id"],
            ["model_version.id"],
            name=op.f("fk_scenario_model_version_id_model_version"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_scenario")),
    )
    op.create_index(op.f("ix_scenario_district_code"), "scenario", ["district_code"], unique=False)
    op.create_table(
        "alert",
        sa.Column("id", sa.Uuid(), nullable=False, comment="Id"),
        sa.Column("centre_code", sa.String(length=32), nullable=False, comment="Centre concerned"),
        sa.Column("week_start", sa.Date(), nullable=False, comment="Week the signal fired"),
        sa.Column(
            "kind",
            sa.Enum(
                "attendance_drop",
                "missing_report",
                "overcrowding",
                "wash",
                "closure_risk",
                name="alertkind",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
            comment="attendance_drop | missing_report | overcrowding | wash | closure_risk",
        ),
        sa.Column(
            "severity",
            sa.Enum(
                "info",
                "warning",
                "critical",
                name="alertseverity",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
            comment="info | warning | critical",
        ),
        sa.Column("reason_en", sa.Text(), nullable=False, comment="Reason in English"),
        sa.Column("reason_rw", sa.Text(), nullable=False, comment="Reason in Kinyarwanda"),
        sa.Column(
            "evidence",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            comment="Numbers the rule used, e.g. {attendance, baseline_mean, z_score}",
        ),
        sa.Column(
            "rule",
            sa.String(length=48),
            nullable=False,
            comment="Rule id inside the early-warning model",
        ),
        sa.Column(
            "model_version_id",
            sa.String(length=64),
            nullable=False,
            comment="Early-warning version",
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
            comment="Origin of the reports the alert was computed from",
        ),
        sa.Column(
            "status",
            sa.Enum(
                "open",
                "acknowledged",
                "resolved",
                name="alertstatus",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
            comment="open | acknowledged | resolved",
        ),
        sa.Column("assigned_to", sa.Uuid(), nullable=True, comment="Officer following up"),
        sa.Column("resolution_note", sa.Text(), nullable=True, comment="What was done"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="When the row was written",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="Last status change",
        ),
        sa.ForeignKeyConstraint(
            ["assigned_to"], ["user_account.id"], name=op.f("fk_alert_assigned_to_user_account")
        ),
        sa.ForeignKeyConstraint(
            ["centre_code"], ["centre.code"], name=op.f("fk_alert_centre_code_centre")
        ),
        sa.ForeignKeyConstraint(
            ["model_version_id"],
            ["model_version.id"],
            name=op.f("fk_alert_model_version_id_model_version"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_alert")),
        sa.UniqueConstraint("centre_code", "week_start", "kind", name="one_per_kind"),
    )
    op.create_index(op.f("ix_alert_centre_code"), "alert", ["centre_code"], unique=False)
    op.create_index(op.f("ix_alert_week_start"), "alert", ["week_start"], unique=False)
    op.create_geospatial_table(
        "candidate_site",
        sa.Column("id", sa.String(length=32), nullable=False, comment="Site code"),
        sa.Column(
            "kind",
            sa.Enum(
                "village",
                "school",
                "centre_upgrade",
                "centre_support",
                name="candidatekind",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
            comment="village | school | centre_upgrade | centre_support",
        ),
        sa.Column(
            "name", sa.String(length=160), nullable=False, comment="Village, school or centre name"
        ),
        sa.Column(
            "sector_code", sa.String(length=64), nullable=False, comment="Sector of the site"
        ),
        sa.Column(
            "centre_code",
            sa.String(length=32),
            nullable=True,
            comment="Existing centre for upgrade and support sites",
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
            comment="Site location, EPSG:4326",
        ),
        sa.Column(
            "unit_cost_band",
            sa.Enum(
                "low",
                "medium",
                "high",
                name="costband",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
            comment="Cost band looked up in unit_cost",
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
        sa.CheckConstraint(
            "(kind IN ('centre_upgrade', 'centre_support')) = (centre_code IS NOT NULL)",
            name=op.f("ck_candidate_site_centre_kinds_have_centre"),
        ),
        sa.ForeignKeyConstraint(
            ["centre_code"], ["centre.code"], name=op.f("fk_candidate_site_centre_code_centre")
        ),
        sa.ForeignKeyConstraint(
            ["pipeline_run_id"],
            ["pipeline_run.id"],
            name=op.f("fk_candidate_site_pipeline_run_id_pipeline_run"),
        ),
        sa.ForeignKeyConstraint(
            ["sector_code"],
            ["admin_unit.code"],
            name=op.f("fk_candidate_site_sector_code_admin_unit"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_candidate_site")),
    )
    op.create_geospatial_index(
        "idx_candidate_site_location",
        "candidate_site",
        ["location"],
        unique=False,
        postgresql_using="gist",
        postgresql_ops={},
    )
    op.create_index(
        op.f("ix_candidate_site_pipeline_run_id"),
        "candidate_site",
        ["pipeline_run_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_candidate_site_sector_code"), "candidate_site", ["sector_code"], unique=False
    )
    op.create_table(
        "weekly_report",
        sa.Column("id", sa.Uuid(), nullable=False, comment="Report id"),
        sa.Column("centre_code", sa.String(length=32), nullable=False, comment="Reporting centre"),
        sa.Column("week_start", sa.Date(), nullable=False, comment="Monday of the reported week"),
        sa.Column(
            "enrolled_0_2_female",
            sa.Integer(),
            nullable=False,
            comment="Girls aged 0 to 2 enrolled",
        ),
        sa.Column(
            "enrolled_0_2_male", sa.Integer(), nullable=False, comment="Boys aged 0 to 2 enrolled"
        ),
        sa.Column(
            "enrolled_3_6_female",
            sa.Integer(),
            nullable=False,
            comment="Girls aged 3 to 6 enrolled",
        ),
        sa.Column(
            "enrolled_3_6_male", sa.Integer(), nullable=False, comment="Boys aged 3 to 6 enrolled"
        ),
        sa.Column(
            "avg_daily_attendance",
            sa.Integer(),
            nullable=False,
            comment="Average number of children present per open day",
        ),
        sa.Column(
            "waiting_list", sa.Integer(), nullable=False, comment="Children waiting for a place"
        ),
        sa.Column(
            "caregivers_present",
            sa.Integer(),
            nullable=False,
            comment="Caregivers present on a typical day",
        ),
        sa.Column(
            "days_open",
            sa.SmallInteger(),
            nullable=False,
            comment="Days the centre opened this week, 0 to 6",
        ),
        sa.Column(
            "days_meal_served",
            sa.SmallInteger(),
            nullable=False,
            comment="Days a meal was served, 0 to 6",
        ),
        sa.Column(
            "wash_available",
            sa.Boolean(),
            nullable=False,
            comment="Water and handwashing were available all week",
        ),
        sa.Column(
            "referrals_growth_monitoring",
            sa.Integer(),
            nullable=False,
            comment="Children referred to growth monitoring this week",
        ),
        sa.Column(
            "children_with_disability",
            sa.Integer(),
            nullable=False,
            comment="Enrolled children with a known disability",
        ),
        sa.Column(
            "main_problem",
            sa.Enum(
                "none",
                "no_food",
                "no_water",
                "caregiver_absent",
                "building_damage",
                "weather",
                "other",
                name="mainproblem",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
            comment="none | no_food | no_water | caregiver_absent | building_damage | weather | other",
        ),
        sa.Column(
            "channel",
            sa.Enum(
                "web",
                "offline",
                "sms",
                "assisted",
                name="reportchannel",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
            comment="web | offline | sms | assisted",
        ),
        sa.Column(
            "quality_flags",
            sa.ARRAY(sa.String(length=32)),
            nullable=False,
            comment="Validation flags. Flagged reports are kept and shown, never silently accepted",
        ),
        sa.Column(
            "submitted_by",
            sa.Uuid(),
            nullable=True,
            comment="Account that submitted or entered the report",
        ),
        sa.Column(
            "submitted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="When the server received it",
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
        sa.CheckConstraint(
            "avg_daily_attendance <= enrolled_0_2_female + enrolled_0_2_male + enrolled_3_6_female + enrolled_3_6_male",
            name=op.f("ck_weekly_report_attendance_le_enrolled"),
        ),
        sa.CheckConstraint(
            "children_with_disability <= enrolled_0_2_female + enrolled_0_2_male + enrolled_3_6_female + enrolled_3_6_male",
            name=op.f("ck_weekly_report_disability_le_enrolled"),
        ),
        sa.CheckConstraint(
            "days_meal_served <= days_open", name=op.f("ck_weekly_report_meals_le_days_open")
        ),
        sa.CheckConstraint(
            "extract(isodow from week_start) = 1", name=op.f("ck_weekly_report_week_starts_monday")
        ),
        sa.ForeignKeyConstraint(
            ["centre_code"], ["centre.code"], name=op.f("fk_weekly_report_centre_code_centre")
        ),
        sa.ForeignKeyConstraint(
            ["pipeline_run_id"],
            ["pipeline_run.id"],
            name=op.f("fk_weekly_report_pipeline_run_id_pipeline_run"),
        ),
        sa.ForeignKeyConstraint(
            ["submitted_by"],
            ["user_account.id"],
            name=op.f("fk_weekly_report_submitted_by_user_account"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_weekly_report")),
        sa.UniqueConstraint("centre_code", "week_start", name="one_per_week"),
    )
    op.create_index(
        op.f("ix_weekly_report_centre_code"), "weekly_report", ["centre_code"], unique=False
    )
    op.create_index(
        op.f("ix_weekly_report_pipeline_run_id"), "weekly_report", ["pipeline_run_id"], unique=False
    )
    op.create_index(
        op.f("ix_weekly_report_week_start"), "weekly_report", ["week_start"], unique=False
    )
    op.create_table(
        "recommendation",
        sa.Column("id", sa.Uuid(), nullable=False, comment="Id"),
        sa.Column("scenario_id", sa.Uuid(), nullable=False, comment="Scenario"),
        sa.Column("rank", sa.Integer(), nullable=False, comment="1 is the strongest suggestion"),
        sa.Column(
            "action",
            sa.Enum(
                "build",
                "upgrade",
                "support",
                name="action",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
            comment="build | upgrade | support",
        ),
        sa.Column("site_id", sa.String(length=32), nullable=False, comment="Target site or centre"),
        sa.Column(
            "children_reached",
            sa.Integer(),
            nullable=False,
            comment="Uncovered children 0 to 6 who gain a reachable place",
        ),
        sa.Column(
            "reached_low", sa.Integer(), nullable=False, comment="Children reached, lower bound"
        ),
        sa.Column(
            "reached_high", sa.Integer(), nullable=False, comment="Children reached, upper bound"
        ),
        sa.Column(
            "high_risk_children_reached",
            sa.Integer(),
            nullable=False,
            comment="Children reached in high stunting-risk areas",
        ),
        sa.Column(
            "mothers_under3_reached",
            sa.Integer(),
            nullable=False,
            comment="Mothers of under-3s in the catchment who report childcare as a barrier",
        ),
        sa.Column("cost_rwf", sa.BigInteger(), nullable=False, comment="Expected cost in RWF"),
        sa.Column(
            "score", sa.Float(), nullable=False, comment="Weighted benefit per RWF used to rank"
        ),
        sa.Column(
            "drivers",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            comment="Top reasons: [{feature, label_en, label_rw, contribution}]",
        ),
        sa.Column(
            "sources",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            comment="Inputs used: [{table, source, reference_year, origin}]",
        ),
        sa.Column(
            "status",
            sa.Enum(
                "proposed",
                "approved",
                "edited",
                "rejected",
                name="recommendationstatus",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
            comment="proposed | approved | edited | rejected",
        ),
        sa.CheckConstraint(
            "reached_low <= children_reached AND children_reached <= reached_high",
            name=op.f("ck_recommendation_reached_range_ordered"),
        ),
        sa.ForeignKeyConstraint(
            ["scenario_id"],
            ["scenario.id"],
            name=op.f("fk_recommendation_scenario_id_scenario"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["site_id"],
            ["candidate_site.id"],
            name=op.f("fk_recommendation_site_id_candidate_site"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_recommendation")),
    )
    op.create_index(
        op.f("ix_recommendation_scenario_id"), "recommendation", ["scenario_id"], unique=False
    )
    op.create_table(
        "decision",
        sa.Column("id", sa.Uuid(), nullable=False, comment="Id"),
        sa.Column("recommendation_id", sa.Uuid(), nullable=False, comment="Recommendation"),
        sa.Column("user_id", sa.Uuid(), nullable=False, comment="Person who decided"),
        sa.Column(
            "verdict",
            sa.Enum(
                "approve",
                "edit",
                "reject",
                name="verdict",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
            comment="approve | edit | reject",
        ),
        sa.Column(
            "reason_code",
            sa.Enum(
                "no_land",
                "already_funded",
                "access_problem",
                "community_objection",
                "other",
                name="rejectionreason",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=True,
            comment="no_land | already_funded | access_problem | community_objection | other",
        ),
        sa.Column("reason_text", sa.Text(), nullable=True, comment="Free-text explanation"),
        sa.Column(
            "edits",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Changed fields for an edit: {field: {from, to}}",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="When the row was written",
        ),
        sa.CheckConstraint(
            "reason_code <> 'other' OR length(trim(reason_text)) > 0",
            name=op.f("ck_decision_other_has_text"),
        ),
        sa.CheckConstraint(
            "verdict <> 'reject' OR reason_code IS NOT NULL",
            name=op.f("ck_decision_reject_has_reason"),
        ),
        sa.ForeignKeyConstraint(
            ["recommendation_id"],
            ["recommendation.id"],
            name=op.f("fk_decision_recommendation_id_recommendation"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["user_account.id"], name=op.f("fk_decision_user_id_user_account")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_decision")),
    )
    op.create_index(
        op.f("ix_decision_recommendation_id"), "decision", ["recommendation_id"], unique=False
    )
    op.execute(AUDIT_GUARD)


def downgrade() -> None:
    op.execute("DROP TRIGGER audit_log_no_truncate ON audit_log")
    op.execute("DROP TRIGGER audit_log_no_update ON audit_log")
    op.execute("DROP FUNCTION audit_log_append_only()")
    op.drop_index(op.f("ix_decision_recommendation_id"), table_name="decision")
    op.drop_table("decision")
    op.drop_index(op.f("ix_recommendation_scenario_id"), table_name="recommendation")
    op.drop_table("recommendation")
    op.drop_index(op.f("ix_weekly_report_week_start"), table_name="weekly_report")
    op.drop_index(op.f("ix_weekly_report_pipeline_run_id"), table_name="weekly_report")
    op.drop_index(op.f("ix_weekly_report_centre_code"), table_name="weekly_report")
    op.drop_table("weekly_report")
    op.drop_index(op.f("ix_candidate_site_sector_code"), table_name="candidate_site")
    op.drop_index(op.f("ix_candidate_site_pipeline_run_id"), table_name="candidate_site")
    op.drop_geospatial_index(
        "idx_candidate_site_location",
        table_name="candidate_site",
        postgresql_using="gist",
        column_name="location",
    )
    op.drop_geospatial_table("candidate_site")
    op.drop_index(op.f("ix_alert_week_start"), table_name="alert")
    op.drop_index(op.f("ix_alert_centre_code"), table_name="alert")
    op.drop_table("alert")
    op.drop_index(op.f("ix_scenario_district_code"), table_name="scenario")
    op.drop_table("scenario")
    op.drop_index(op.f("ix_need_estimate_pipeline_run_id"), table_name="need_estimate")
    op.drop_index(op.f("ix_need_estimate_area_code"), table_name="need_estimate")
    op.drop_table("need_estimate")
    op.drop_index(op.f("ix_demand_signal_sector_code"), table_name="demand_signal")
    op.drop_index(op.f("ix_demand_signal_grid_cell"), table_name="demand_signal")
    op.drop_geospatial_index(
        "idx_demand_signal_cell_centre",
        table_name="demand_signal",
        postgresql_using="gist",
        column_name="cell_centre",
    )
    op.drop_geospatial_table("demand_signal")
    op.drop_index(op.f("ix_coverage_snapshot_week_start"), table_name="coverage_snapshot")
    op.drop_index(op.f("ix_coverage_snapshot_pipeline_run_id"), table_name="coverage_snapshot")
    op.drop_index(op.f("ix_coverage_snapshot_area_code"), table_name="coverage_snapshot")
    op.drop_table("coverage_snapshot")
    op.drop_index(op.f("ix_centre_sector_code"), table_name="centre")
    op.drop_index(op.f("ix_centre_pipeline_run_id"), table_name="centre")
    op.drop_geospatial_index(
        "idx_centre_location", table_name="centre", postgresql_using="gist", column_name="location"
    )
    op.drop_geospatial_table("centre")
    op.drop_index(op.f("ix_area_indicator_pipeline_run_id"), table_name="area_indicator")
    op.drop_index(op.f("ix_area_indicator_indicator"), table_name="area_indicator")
    op.drop_index(op.f("ix_area_indicator_area_code"), table_name="area_indicator")
    op.drop_table("area_indicator")
    op.drop_index(op.f("ix_unit_cost_pipeline_run_id"), table_name="unit_cost")
    op.drop_table("unit_cost")
    op.drop_index(op.f("ix_saved_search_user_id"), table_name="saved_search")
    op.drop_geospatial_index(
        "idx_saved_search_cell_centre",
        table_name="saved_search",
        postgresql_using="gist",
        column_name="cell_centre",
    )
    op.drop_geospatial_table("saved_search")
    op.drop_index(op.f("ix_refresh_token_user_id"), table_name="refresh_token")
    op.drop_table("refresh_token")
    op.drop_table("model_version")
    op.drop_index(op.f("ix_audit_log_entity_id"), table_name="audit_log")
    op.drop_index(op.f("ix_audit_log_actor_id"), table_name="audit_log")
    op.drop_index(op.f("ix_audit_log_action"), table_name="audit_log")
    op.drop_table("audit_log")
    op.drop_index(op.f("ix_admin_unit_pipeline_run_id"), table_name="admin_unit")
    op.drop_index(op.f("ix_admin_unit_parent_code"), table_name="admin_unit")
    op.drop_index(op.f("ix_admin_unit_level"), table_name="admin_unit")
    op.drop_geospatial_index(
        "idx_admin_unit_geom_medium",
        table_name="admin_unit",
        postgresql_using="gist",
        column_name="geom_medium",
    )
    op.drop_geospatial_index(
        "idx_admin_unit_geom_coarse",
        table_name="admin_unit",
        postgresql_using="gist",
        column_name="geom_coarse",
    )
    op.drop_geospatial_index(
        "idx_admin_unit_geom", table_name="admin_unit", postgresql_using="gist", column_name="geom"
    )
    op.drop_geospatial_index(
        "idx_admin_unit_centroid",
        table_name="admin_unit",
        postgresql_using="gist",
        column_name="centroid",
    )
    op.drop_geospatial_table("admin_unit")
    op.drop_table("user_account")
    op.drop_index(op.f("ix_pipeline_run_pipeline"), table_name="pipeline_run")
    op.drop_table("pipeline_run")
    op.drop_index(op.f("ix_otp_challenge_phone"), table_name="otp_challenge")
    op.drop_table("otp_challenge")
    op.drop_table("data_source")
