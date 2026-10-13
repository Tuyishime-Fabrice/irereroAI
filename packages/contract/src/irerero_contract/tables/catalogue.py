import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from irerero_contract.base import Base, created_at_column, enum_type, new_uuid
from irerero_contract.enums import EngineComponent, Origin, RunStatus, SourceStatus


class DataSource(Base):
    """Catalogue of every source the platform uses or will use, and its status today."""

    __tablename__ = "data_source"

    id: Mapped[str] = mapped_column(
        String(48), primary_key=True, comment="Adapter name, e.g. census_2022"
    )
    name: Mapped[str] = mapped_column(String(160), comment="Human-readable source name")
    publisher: Mapped[str] = mapped_column(String(120), comment="Publishing institution")
    reference_year: Mapped[int | None] = mapped_column(SmallInteger, comment="Year described")
    origin: Mapped[Origin] = mapped_column(enum_type(Origin), comment="Origin once loaded")
    status: Mapped[SourceStatus] = mapped_column(
        enum_type(SourceStatus), comment="loaded | simulated_stand_in | planned"
    )
    licence: Mapped[str] = mapped_column(String(160), comment="Licence or access terms")
    url: Mapped[str | None] = mapped_column(String(300), comment="Where the source is published")
    feeds: Mapped[list[str]] = mapped_column(
        JSONB, comment="Tables or indicators this source feeds", info={"items": {"type": "string"}}
    )


class PipelineRun(Base):
    """One execution of an adapter or the demo generator, with its checks."""

    __tablename__ = "pipeline_run"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid, comment="Run id")
    pipeline: Mapped[str] = mapped_column(
        String(48), index=True, comment="Adapter or generator name, e.g. demo_generator"
    )
    origin: Mapped[Origin] = mapped_column(enum_type(Origin), comment="Origin of the rows loaded")
    status: Mapped[RunStatus] = mapped_column(
        enum_type(RunStatus), comment="running | succeeded | failed"
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), comment="Start time")
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), comment="End time"
    )
    code_version: Mapped[str] = mapped_column(String(64), comment="Git commit or package version")
    inputs: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, comment="Input files with sha256 and size: [{path, sha256, bytes}]"
    )
    row_counts: Mapped[dict[str, int]] = mapped_column(
        JSONB, comment="Rows written per table", info={"additionalProperties": {"type": "integer"}}
    )
    checks: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, comment="Checks run: [{name, passed, detail}]"
    )


class ModelVersion(Base):
    """A versioned engine component. Phase 1 baselines and Phase 2 trained models live here."""

    __tablename__ = "model_version"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, comment="Version id, e.g. need-baseline-1"
    )
    component: Mapped[EngineComponent] = mapped_column(
        enum_type(EngineComponent),
        comment="need | coverage | optimizer | early_warning | explainer",
    )
    description: Mapped[str] = mapped_column(Text, comment="What the model does, in plain words")
    params: Mapped[dict[str, Any]] = mapped_column(JSONB, comment="Parameters and thresholds")
    metrics: Mapped[dict[str, Any]] = mapped_column(
        JSONB, comment="Evaluation metrics. Empty for rule-based baselines"
    )
    trained_on_run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("pipeline_run.id"), comment="Pipeline run that produced the training data"
    )
    created_at: Mapped[datetime] = created_at_column()
