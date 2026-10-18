"""Pick the real file when it is present, otherwise the demo copy, and say which."""

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from irerero.config import DEMO, RAW, SIMULATED
from irerero.data.spec import Dataset


@dataclass(frozen=True)
class Loaded:
    frame: pd.DataFrame
    status: str
    """The dataset's status when its real file was read; 'simulated' for the demo copy."""
    real: bool
    files: tuple[Path, ...]


def folder(dataset: Dataset, raw: Path = RAW) -> tuple[Path, bool]:
    """(folder to read, real?). Real files win; the demo bundle stands in."""
    if dataset.present(raw):
        return dataset.folder(raw), True
    return DEMO / dataset.key, False


def status(dataset: Dataset, real: bool) -> str:
    return dataset.status if real else SIMULATED
