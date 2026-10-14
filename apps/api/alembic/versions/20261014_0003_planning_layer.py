"""planning layer: one planner role, centre feed fields, no weekly reports or alerts

IrereroAI becomes a planning layer over the NCDA ECD Mapping System. Weekly reports, alerts,
caregiver, officer, analyst and admin accounts and parent sign-in are removed; centres carry
the latest enrolment from the centre feed; coverage is precomputed per catchment step.

Every Phase 1 database holds simulated demo data only. This migration refuses to run on a
database with official or partner data. Otherwise it clears the demo rows, which the old
accounts, reports and alerts would not fit, and the build pipeline reseeds.

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geometry
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DATA_TABLES = (
    "admin_unit",
    "area_indicator",
    "audit_log",
    "candidate_site",
    "centre",
    "coverage_snapshot",
    "data_source",
    "decision",
    "demand_signal",
    "model_version",
    "need_estimate",
    "pipeline_run",
    "planning_default",
    "recommendation",
    "refresh_token",
    "scenario",
    "unit_cost",
    "user_account",
)
AUDIT_TRIGGERS = """
CREATE TRIGGER audit_log_no_update BEFORE UPDATE OR DELETE ON audit_log
    FOR EACH ROW EXECUTE FUNCTION audit_log_append_only();
CREATE TRIGGER audit_log_no_truncate BEFORE TRUNCATE ON audit_log
    FOR EACH STATEMENT EXECUTE FUNCTION audit_log_append_only();
"""


def _clear_demo_data(extra_tables: tuple[str, ...]) -> None:
    real = (
        op.get_bind()
        .execute(
            sa.text("SELECT count(*) FROM pipeline_run WHERE origin IN ('official', 'partner')")
        )
        .scalar_one()
    )
    if real:
        raise RuntimeError(
            "This database holds official or partner data. Migrate it by hand: "
            "revision 0003 removes accounts, weekly reports and alerts."
        )
    op.execute("DROP TRIGGER audit_log_no_update ON audit_log")
    op.execute("DROP TRIGGER audit_log_no_truncate ON audit_log")
    op.execute(f"TRUNCATE {', '.join(DATA_TABLES + extra_tables)} CASCADE")
    op.execute(AUDIT_TRIGGERS)


def _replace_check(table: str, name: str, column: str, values: Sequence[str]) -> None:
    op.drop_constraint(op.f(name), table, type_="check")
    listed = ", ".join(f"'{v}'" for v in values)
    op.create_check_constraint(op.f(name), table, f"{column} IN ({listed})")


def upgrade() -> None:
    _clear_demo_data(("alert", "weekly_report", "otp_challenge", "saved_search"))

    op.drop_index(op.f("ix_weekly_report_week_start"), table_name="weekly_report")
    op.drop_index(op.f("ix_weekly_report_pipeline_run_id"), table_name="weekly_report")
    op.drop_index(op.f("ix_weekly_report_centre_code"), table_name="weekly_report")
    op.drop_table("weekly_report")
    op.drop_index(op.f("ix_alert_week_start"), table_name="alert")
    op.drop_index(op.f("ix_alert_centre_code"), table_name="alert")
    op.drop_table("alert")
    op.drop_index(op.f("ix_saved_search_user_id"), table_name="saved_search")
    op.drop_geospatial_index(
        "idx_saved_search_cell_centre",
        table_name="saved_search",
        postgresql_using="gist",
        column_name="cell_centre",
    )
    op.drop_geospatial_table("saved_search")
    op.drop_index(op.f("ix_otp_challenge_phone"), table_name="otp_challenge")
    op.drop_table("otp_challenge")

    op.add_column(
        "centre",
        sa.Column(
            "water_available",
            sa.Boolean(),
            nullable=False,
            comment="Has safe drinking water and handwashing on site",
        ),
    )
    op.add_column(
        "centre",
        sa.Column(
            "enrolment",
            sa.Integer(),
            nullable=False,
            comment="Children enrolled, from the latest attendance feed record",
        ),
    )
    op.add_column(
        "centre",
        sa.Column(
            "enrolment_as_of",
            sa.Date(),
            nullable=False,
            comment="Date of the attendance feed record the enrolment comes from",
        ),
    )
    op.create_check_constraint(op.f("ck_centre_enrolment_min"), "centre", "enrolment >= 0")
    op.alter_column(
        "centre",
        "verified",
        existing_type=sa.Boolean(),
        comment="Marked verified in the NCDA ECD Mapping System",
        existing_comment="A sector officer has checked the centre in person",
        existing_nullable=False,
    )
    op.drop_constraint(op.f("fk_centre_verified_by_user_account"), "centre", type_="foreignkey")
    op.drop_column("centre", "reliability_score")
    op.drop_column("centre", "verified_at")
    op.drop_column("centre", "verified_by")

    op.alter_column(
        "coverage_snapshot",
        "overcrowded_centres",
        existing_type=sa.Integer(),
        comment="Centres with enrolment above capacity",
        existing_comment="Centres with attendance above capacity",
        existing_nullable=False,
    )
    op.drop_index(op.f("ix_coverage_snapshot_week_start"), table_name="coverage_snapshot")
    op.drop_column("coverage_snapshot", "week_start")
    op.create_unique_constraint(
        op.f("uq_coverage_snapshot_area_code"),
        "coverage_snapshot",
        ["area_code", "catchment_minutes"],
    )

    op.alter_column(
        "demand_signal",
        "age_band",
        existing_type=sa.String(length=8),
        comment="Age band the parent needs a place for: 0_2 | 3_6",
        existing_comment="Age band searched for: 0_2 | 3_6",
        existing_nullable=True,
    )
    op.drop_column("demand_signal", "kind")

    op.drop_constraint(op.f("uq_user_account_phone"), "user_account", type_="unique")
    op.drop_column("user_account", "scope_level")
    op.drop_column("user_account", "scope_code")
    op.drop_column("user_account", "totp_secret")
    op.drop_column("user_account", "phone")
    op.add_column(
        "user_account",
        sa.Column(
            "district_code",
            sa.String(length=64),
            nullable=False,
            comment="District the planner plans for",
        ),
    )
    op.create_foreign_key(
        op.f("fk_user_account_district_code_admin_unit"),
        "user_account",
        "admin_unit",
        ["district_code"],
        ["code"],
    )
    op.alter_column(
        "user_account",
        "email",
        existing_type=sa.String(length=254),
        nullable=False,
        comment="Login",
        existing_comment="Staff login",
    )
    op.alter_column(
        "user_account",
        "password_hash",
        existing_type=sa.String(length=255),
        nullable=False,
        existing_comment="Argon2id hash",
    )
    _replace_check("user_account", "ck_user_account_role", "role", ["district_planner"])
    _replace_check("audit_log", "ck_audit_log_role", "actor_role", ["district_planner"])
    _replace_check(
        "model_version",
        "ck_model_version_enginecomponent",
        "component",
        ["need", "coverage", "optimizer", "explainer"],
    )

    op.drop_constraint(
        op.f("fk_planning_default_updated_by_user_account"), "planning_default", type_="foreignkey"
    )
    op.drop_column("planning_default", "updated_by")


def downgrade() -> None:
    _clear_demo_data(())

    op.add_column(
        "planning_default",
        sa.Column("updated_by", sa.Uuid(), nullable=True, comment="Analyst who last changed it"),
    )
    op.create_foreign_key(
        op.f("fk_planning_default_updated_by_user_account"),
        "planning_default",
        "user_account",
        ["updated_by"],
        ["id"],
    )

    _replace_check(
        "model_version",
        "ck_model_version_enginecomponent",
        "component",
        ["need", "coverage", "optimizer", "early_warning", "explainer"],
    )
    _replace_check(
        "audit_log",
        "ck_audit_log_role",
        "actor_role",
        ["parent", "caregiver", "sector_officer", "district_planner", "national_analyst", "admin"],
    )
    _replace_check(
        "user_account",
        "ck_user_account_role",
        "role",
        ["parent", "caregiver", "sector_officer", "district_planner", "national_analyst", "admin"],
    )
    op.alter_column(
        "user_account",
        "password_hash",
        existing_type=sa.String(length=255),
        nullable=True,
        existing_comment="Argon2id hash",
    )
    op.alter_column(
        "user_account",
        "email",
        existing_type=sa.String(length=254),
        nullable=True,
        comment="Staff login",
        existing_comment="Login",
    )
    op.drop_constraint(
        op.f("fk_user_account_district_code_admin_unit"), "user_account", type_="foreignkey"
    )
    op.drop_column("user_account", "district_code")
    op.add_column(
        "user_account",
        sa.Column(
            "phone",
            sa.String(length=16),
            nullable=True,
            comment="E.164 phone, parent and caregiver login",
        ),
    )
    op.add_column(
        "user_account",
        sa.Column(
            "totp_secret",
            sa.String(length=64),
            nullable=True,
            comment="TOTP secret. Required for admins",
        ),
    )
    op.add_column(
        "user_account",
        sa.Column(
            "scope_code",
            sa.String(length=64),
            nullable=True,
            comment="Centre code or admin unit code the account may see",
        ),
    )
    op.add_column(
        "user_account",
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
    )
    op.create_unique_constraint(op.f("uq_user_account_phone"), "user_account", ["phone"])
    op.create_check_constraint(
        op.f("ck_user_account_has_login"), "user_account", "email IS NOT NULL OR phone IS NOT NULL"
    )
    op.create_check_constraint(
        op.f("ck_user_account_scope"),
        "user_account",
        "(scope_level IN ('none', 'national')) = (scope_code IS NULL)",
    )

    op.add_column(
        "demand_signal",
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
    )
    op.alter_column(
        "demand_signal",
        "age_band",
        existing_type=sa.String(length=8),
        comment="Age band searched for: 0_2 | 3_6",
        existing_comment="Age band the parent needs a place for: 0_2 | 3_6",
        existing_nullable=True,
    )

    op.drop_constraint(op.f("uq_coverage_snapshot_area_code"), "coverage_snapshot", type_="unique")
    op.add_column(
        "coverage_snapshot",
        sa.Column("week_start", sa.Date(), nullable=False, comment="Monday of the week"),
    )
    op.create_index(
        op.f("ix_coverage_snapshot_week_start"), "coverage_snapshot", ["week_start"], unique=False
    )
    op.alter_column(
        "coverage_snapshot",
        "overcrowded_centres",
        existing_type=sa.Integer(),
        comment="Centres with attendance above capacity",
        existing_comment="Centres with enrolment above capacity",
        existing_nullable=False,
    )

    op.add_column(
        "centre",
        sa.Column(
            "verified_by", sa.Uuid(), nullable=True, comment="Officer who verified the centre"
        ),
    )
    op.add_column(
        "centre",
        sa.Column(
            "verified_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=True,
            comment="When the last verification happened",
        ),
    )
    op.add_column(
        "centre",
        sa.Column(
            "reliability_score",
            sa.Float(),
            nullable=False,
            comment="0 to 1. Share of the last 12 weeks reported on time without quality flags",
        ),
    )
    op.create_check_constraint(
        op.f("ck_centre_reliability_range"), "centre", "reliability_score BETWEEN 0 AND 1"
    )
    op.create_foreign_key(
        op.f("fk_centre_verified_by_user_account"),
        "centre",
        "user_account",
        ["verified_by"],
        ["id"],
    )
    op.alter_column(
        "centre",
        "verified",
        existing_type=sa.Boolean(),
        comment="A sector officer has checked the centre in person",
        existing_comment="Marked verified in the NCDA ECD Mapping System",
        existing_nullable=False,
    )
    op.drop_constraint(op.f("ck_centre_enrolment_min"), "centre", type_="check")
    op.drop_column("centre", "enrolment_as_of")
    op.drop_column("centre", "enrolment")
    op.drop_column("centre", "water_available")

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
    op.create_index(op.f("ix_saved_search_user_id"), "saved_search", ["user_id"], unique=False)
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
    op.create_geospatial_index(
        "idx_saved_search_cell_centre",
        "saved_search",
        ["cell_centre"],
        unique=False,
        postgresql_using="gist",
        postgresql_ops={},
    )
