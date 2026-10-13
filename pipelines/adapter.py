"""The ingestion contract every data source implements.

An adapter moves one source from files in data/raw/<adapter name>/ into contract tables, in
four steps: extract, validate, align_to_sector, load. `run_adapter` executes the steps inside
one pipeline_run record so every loaded row can be traced back to its files and checks.
"""

import hashlib
import subprocess
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, ClassVar

from sqlalchemy import Connection, Engine, insert, update

from irerero_contract.enums import Origin, RunStatus
from irerero_contract.tables import PipelineRun

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = REPO_ROOT / "data" / "raw"


@dataclass(frozen=True)
class ExpectedFile:
    pattern: str
    description: str


@dataclass(frozen=True)
class CheckSpec:
    name: str
    description: str


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class AdapterSpec:
    name: str
    title: str
    publisher: str
    reference_year: int | None
    origin: Origin
    licence: str
    url: str | None
    expected_files: tuple[ExpectedFile, ...]
    target_tables: tuple[str, ...]
    checks: tuple[CheckSpec, ...]
    indicators: tuple[str, ...] = ()
    notes: str = ""


class ChecksFailedError(RuntimeError):
    def __init__(self, results: list[CheckResult]) -> None:
        failed = ", ".join(r.name for r in results if not r.passed)
        super().__init__(f"checks failed: {failed}")
        self.results = results


class SourceAdapter[RawT, AlignedT](ABC):
    spec: ClassVar[AdapterSpec]

    @abstractmethod
    def extract(self, raw_dir: Path) -> RawT:
        """Read the expected files. No transformation beyond parsing."""

    @abstractmethod
    def validate(self, raw: RawT) -> list[CheckResult]:
        """Run every check in spec.checks. Loading stops if any fails."""

    @abstractmethod
    def align_to_sector(self, raw: RawT, conn: Connection) -> AlignedT:
        """Map records to admin_unit codes (or centres), keeping intervals and sample sizes."""

    @abstractmethod
    def load(self, aligned: AlignedT, conn: Connection, run_id: uuid.UUID) -> dict[str, int]:
        """Write to spec.target_tables with provenance; return rows written per table."""


class PlannedAdapter(SourceAdapter[Any, Any]):
    """A Phase 2 source: specified and registered, not implemented yet."""

    def _not_yet(self) -> NotImplementedError:
        return NotImplementedError(
            f"{self.spec.name} is a Phase 2 adapter; see docs/PHASE2_HANDOFF.md"
        )

    def extract(self, raw_dir: Path) -> Any:
        raise self._not_yet()

    def validate(self, raw: Any) -> list[CheckResult]:
        raise self._not_yet()

    def align_to_sector(self, raw: Any, conn: Connection) -> Any:
        raise self._not_yet()

    def load(self, aligned: Any, conn: Connection, run_id: uuid.UUID) -> dict[str, int]:
        raise self._not_yet()


def file_fingerprint(path: Path) -> dict[str, Any]:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return {
        "path": path.relative_to(REPO_ROOT).as_posix(),
        "sha256": digest,
        "bytes": path.stat().st_size,
    }


def code_version() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],  # noqa: S607
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


@dataclass
class RunRecorder:
    """Writes the pipeline_run row in its own transactions, so a failed run stays on record."""

    engine: Engine
    pipeline: str
    origin: Origin
    id: uuid.UUID = field(default_factory=uuid.uuid4)

    def start(self, inputs: list[dict[str, Any]]) -> uuid.UUID:
        with self.engine.begin() as conn:
            conn.execute(
                insert(PipelineRun).values(
                    id=self.id,
                    pipeline=self.pipeline,
                    origin=self.origin,
                    status=RunStatus.RUNNING,
                    started_at=datetime.now(UTC),
                    code_version=code_version(),
                    inputs=inputs,
                    row_counts={},
                    checks=[],
                )
            )
        return self.id

    def finish(
        self, status: RunStatus, row_counts: dict[str, int], checks: list[CheckResult]
    ) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                update(PipelineRun)
                .where(PipelineRun.id == self.id)
                .values(
                    status=status,
                    finished_at=datetime.now(UTC),
                    row_counts=row_counts,
                    checks=[
                        {"name": c.name, "passed": c.passed, "detail": c.detail} for c in checks
                    ],
                )
            )


def run_adapter(adapter: SourceAdapter[Any, Any], engine: Engine) -> uuid.UUID:
    """Run one adapter. Loaded rows commit together, or not at all."""
    raw_dir = RAW_DIR / adapter.spec.name
    inputs = [file_fingerprint(p) for p in sorted(raw_dir.rglob("*")) if p.is_file()]
    recorder = RunRecorder(engine, adapter.spec.name, adapter.spec.origin)
    run_id = recorder.start(inputs)
    results: list[CheckResult] = []
    try:
        raw = adapter.extract(raw_dir)
        results = adapter.validate(raw)
        if not all(r.passed for r in results):
            raise ChecksFailedError(results)
        with engine.begin() as conn:
            aligned = adapter.align_to_sector(raw, conn)
            counts = adapter.load(aligned, conn, run_id)
    except Exception:
        recorder.finish(RunStatus.FAILED, {}, results)
        raise
    recorder.finish(RunStatus.SUCCEEDED, counts, results)
    return run_id
