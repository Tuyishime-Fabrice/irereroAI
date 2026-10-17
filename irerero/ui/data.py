"""Cached reads for the app. The first start builds the tables from the demo bundle (or the
real files), so a fresh deployment needs no manual step."""

import json

import pandas as pd
import streamlit as st
from sqlalchemy import Engine, func, select

from irerero.config import PROCESSED
from irerero.db.models import Estimate2026
from irerero.db.session import engine
from irerero.db.store import read
from irerero.plan import frame as plan_frame


@st.cache_resource
def eng() -> Engine:
    return engine()


def _built(e: Engine) -> bool:
    with e.connect() as conn:
        count = conn.execute(select(func.count()).select_from(Estimate2026)).scalar_one()
    return count > 0 and (PROCESSED / "sectors.geojson").exists()


def ensure_built() -> None:
    if st.session_state.get("_built"):
        return
    e = eng()
    if not _built(e):
        from irerero.pipeline.build import build

        with st.spinner("First start: building the analysis tables (about a minute)..."):
            build(eng=e)
        st.cache_data.clear()
    from irerero.pipeline.app_seed import seed

    seed(e)
    st.session_state["_built"] = True


@st.cache_data(show_spinner=False)
def table(name: str) -> pd.DataFrame:
    return read(eng(), name)


@st.cache_data(show_spinner=False)
def sectors() -> pd.DataFrame:
    return plan_frame.sectors(eng())


@st.cache_data(show_spinner=False)
def geojson(level: str) -> dict:
    return json.loads((PROCESSED / f"{level}s.geojson").read_text())


@st.cache_data(show_spinner=False)
def sources() -> pd.DataFrame:
    return read(eng(), "source").set_index("source_id")


def source_title(source_id: str) -> str:
    frame = sources()
    return str(frame.title.get(source_id, source_id)) if len(frame) else source_id


def districts() -> dict[str, str]:
    units = table("geo_unit")
    rows = units[units.level == "district"].sort_values("name")
    return dict(zip(rows.geo_id, rows.name, strict=True))


def clear() -> None:
    st.cache_data.clear()


def training_completion() -> dict[str, float]:
    """Share of caregivers per district who completed their required LEARN courses."""
    from irerero.learn import progress

    return progress.completion_by_district(eng())


@st.cache_data(show_spinner=False)
def diagnosis(target: float, completion: tuple[tuple[str, float], ...] = ()) -> pd.DataFrame:
    from irerero.diagnose import live

    return live.frame(
        table("observation"),
        table("geo_unit"),
        table("estimate_2026"),
        table("model_output"),
        table("model_run"),
        target,
        dict(completion) or None,
    ).merge(table("geo_unit")[["geo_id", "name", "district"]], on="geo_id", how="left")


def diagnosis_now(target: float) -> pd.DataFrame:
    return diagnosis(target, tuple(sorted(training_completion().items())))


def target() -> float:
    from irerero.config import TARGET_2029

    return st.session_state.get("target_pct", round(TARGET_2029.value * 100)) / 100
