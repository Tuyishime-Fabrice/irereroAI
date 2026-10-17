"""Every load is one pipeline_run row: its input files with checksums, row counts and checks.

So every loaded row can be traced back to the files and checks that produced it.
"""

import hashlib
import subprocess
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import Engine, insert, update

from irerero_contract.enums import Origin, RunStatus
from irerero_contract.tables import PipelineRun

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = REPO_ROOT / "data" / "raw"


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    detail: str


def file_fingerprint(path: Path) -> dict[str, Any]:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return {
        "path": path.relative_to(REPO_ROOT).as_posix()
        if path.is_relative_to(REPO_ROOT)
        else path.name,
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
