"""Cached reads for the app. The first start builds the tables from the demo bundle (or the
real files), so a fresh deployment needs no manual step."""

import json

import pandas as pd
import streamlit as st
from sqlalchemy import Engine, func, select

from irerero.config import PROCESSED
from irerero.data import bundle
from irerero.db.models import Estimate2026
from irerero.db.session import engine
from irerero.db.store import read
from irerero.plan import frame as plan_frame


@st.cache_resource
def eng() -> Engine:
    return engine()


BUILT_FROM = PROCESSED / ".built_from"  # the data bundle the tables were built from


def _built(e: Engine) -> bool:
    with e.connect() as conn:
        count = conn.execute(select(func.count()).select_from(Estimate2026)).scalar_one()
    source = BUILT_FROM.read_text() if BUILT_FROM.exists() else ""
    return count > 0 and (PROCESSED / "sectors.geojson").exists() and source == bundle.fingerprint()


def _secrets() -> dict:
    try:
        return dict(st.secrets)
    except Exception:  # no secrets file in this deployment
        return {}


@st.cache_resource(show_spinner="Loading the private data bundle...")
def _fetch_bundle(sha256: str | None) -> str:
    """Once per server process and bundle. A failure is not cached: the next visit retries."""
    return bundle.sync(_secrets())


@st.cache_resource(show_spinner="Loading the school list...")
def _fetch_schools(path: str | None) -> str:
    """Once per server process and path; a failure is not cached."""
    return bundle.sync_schools(_secrets())


def ensure_built() -> None:
    if st.session_state.get("_built"):
        return
    e = eng()
    settings = bundle.settings(_secrets())
    try:
        _fetch_bundle(settings["IRERERO_DATA_SHA256"])
    except bundle.BundleError as error:
        st.warning(f"The private data bundle was not used: {error}. The app shows what it has.")
    try:
        _fetch_schools(settings["IRERERO_SCHOOLS_PATH"] or settings["IRERERO_SCHOOLS_URL"])
    except bundle.BundleError as error:
        st.warning(f"The school list was not loaded: {error}. Distances keep their stand-in.")
    if not _built(e):
        from irerero.pipeline.build import build

        with st.spinner("First start: building the analysis tables (about a minute)..."):
            build(eng=e)
        BUILT_FROM.write_text(bundle.fingerprint())
        st.cache_data.clear()
    from irerero.pipeline.app_seed import seed

    seed(e)
    from irerero.learn import triggers

    triggers.run(e, diagnosis_now(target()))
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
def schools() -> tuple[list[dict], dict]:
    """(school points the distance layer used, the loader's report)."""
    points = PROCESSED / "schools.geojson"
    report = PROCESSED / "schools_report.json"
    if not points.exists():
        return [], {}
    features = json.loads(points.read_text())["features"]
    rows = [
        {"lon": f["geometry"]["coordinates"][0], "lat": f["geometry"]["coordinates"][1],
         **f["properties"]}
        for f in features
    ]  # fmt: skip
    return rows, json.loads(report.read_text()) if report.exists() else {}


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
