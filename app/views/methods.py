"""Screen 8. Data and methods: sources, definitions, status legend, model card, validation,
limitations, and the simulated NCDA supply connector."""

import pandas as pd
import streamlit as st

from irerero.config import (
    CAREGIVER_RATIO_HIGH,
    CAREGIVER_RATIO_LOW,
    CHILDREN_PER_ROOM,
    CONFORMAL_COVERAGE,
    DEFINITION,
    FAR_SHARE,
    NCDA_DISPLAY_SETTING,
    SIMULATED,
    STATUSES,
    TARGET_2027,
    TARGET_2029,
    WALKING_DISTANCE_KM,
    WEAK_FACTOR,
)
from irerero.data.registry import DATASETS
from irerero.diagnose.features import LABELS
from irerero.diagnose.peer import MODEL_LABELS
from irerero.track import forecast
from irerero.ui import data, theme

theme.header(
    "Data & methods",
    "Where every number comes from, and how far to trust it.",
    crumbs=["Rwanda", "Data & methods"],
    assistant="methods",
)

STATUS_MEANING = {
    "observed": "Counted directly in a census, yearbook or administrative record.",
    "published estimate": "An estimate published by its producer (projections, survey rates).",
    "model estimate": "Computed by IrereroAI from observed and published inputs.",
    "user input": "Entered by a person in the app (targets, weights, decisions, check-ins).",
    "provisional": "Built on real but partial records (a school list that is not the full "
    "register). Shown and labelled; never read as complete coverage.",
    "simulated": "Invented stand-in while the real file is missing. Never a real value; left "
    "out of exports by default.",
}
loaded = data.sources()
run = data.table("model_run")
SHORT_MODEL = {
    "linear": "Linear",
    "lightgbm": "LightGBM",
    "district_mean": "District mean",
    "province_mean": "Province mean",
}
file_sets = [d for d in DATASETS if d.files]
real_n = sum(bool(loaded.loaded.get(d.key, False)) for d in file_sets)
k1, k2, k3, k4 = st.columns(4)
with k1:
    theme.kpi("Datasets with real files", f"{real_n} of {len(file_sets)}", "Data layer", None, None,
              "the rest use labelled stand-ins", "database", "teal")  # fmt: skip
with k2:
    units = data.table("geo_unit")
    sector_units = units[units.level == "sector"]
    coded = int(sector_units.nisr_code.notna().sum())
    if bool(loaded.loaded.get("boundaries", False)):
        theme.kpi("Sectors with real boundaries", str(len(sector_units)),
                  "COD-AB boundaries (NISR via HDX)", "2022", "observed",
                  f"{coded} with official NISR codes", "pin", "navy")  # fmt: skip
    else:
        theme.kpi("Sectors with real boundaries", str(len(sector_units)),
                  "geoBoundaries (CC BY 4.0)", "2023", "published estimate",
                  f"{coded} with NISR codes from the COD-AB gazetteer, to review" if coded
                  else "real shapes, NISR codes to add", "pin", "navy")  # fmt: skip
with k3:
    if len(run):
        best = run[run.chosen].iloc[0]
        theme.kpi("Peer model", SHORT_MODEL.get(best.model_id, best.model_id), "Leave-one-district-out CV",
                  None, "model estimate", f"{MODEL_LABELS[best.model_id]} · MAE {best.metrics['mae_pp']} pts · R² {best.metrics['r2']}",
                  "chart", "blue")  # fmt: skip
with k4:
    theme.kpi("Statuses in use", str(len(STATUSES)), "Provenance", None, None,
              "every number carries one", "shield", "gold")  # fmt: skip
with theme.panel(key="methods"):
    tabs = st.tabs(
        ["Sources", "Definitions", "Model card", "Validation", "Limitations", "NCDA connector"]
    )

with tabs[0]:
    st.markdown("#### Status legend")
    for status in STATUSES:
        st.markdown(f"{theme.badge(status)} {STATUS_MEANING[status]}", unsafe_allow_html=True)
    st.markdown("#### Datasets")
    rows = []
    for d in DATASETS:
        state = (
            "real file"
            if d.key in loaded.index and bool(loaded.loaded.get(d.key))
            else ("parameters" if not d.files else "simulated stand-in")
        )
        if d.key == "boundaries" and not bool(loaded.loaded.get(d.key, False)):
            state = "geoBoundaries (real shapes, no NISR codes)"
        if d.key == "learn_simulation":
            state = "simulated"
        rows.append(
            {
                "Dataset": d.title,
                "Publisher": d.publisher,
                "Level": d.level,
                "Period": d.reference_period,
                "Licence": d.licence,
                "Used by": "; ".join(d.used_by),
                "In this build": state,
            }
        )
    state_pill = {
        "real file": ("approved", "Real file"),
        "simulated stand-in": ("rejected", "Simulated stand-in"),
        "simulated": ("rejected", "Simulated"),
        "parameters": ("planned", "Parameters"),
    }
    st.markdown(
        theme.table(
            rows,
            [
                theme.Col("Dataset", "Dataset", strong=True),
                theme.Col("Publisher", "Publisher"),
                theme.Col("Period", "Period"),
                theme.Col("Licence", "Licence"),
                theme.Col("Used by", "Used by", fmt=lambda v, r: f"<span class='muted'>{v}</span>"),
                theme.Col(
                    "In this build",
                    "In this build",
                    fmt=lambda v, r: (
                        theme.pill(*state_pill[v])
                        if v in state_pill
                        else theme.pill("edited", "Real shapes")
                    ),
                ),
            ],
        ),
        unsafe_allow_html=True,
    )
    theme.note(
        "File names, formats and required columns for each dataset are in DATA_SOURCES.md. "
        "Put a real file in data/raw/<dataset>/ and rebuild; nothing else changes."
    )
    _, school_report = data.schools()
    if school_report.get("features") is not None:
        missing = {k: v for k, v in school_report.get("missing_properties", {}).items() if v}
        st.markdown(
            f"**School locations** {theme.badge(school_report.get('status'))}  \n"
            f"{school_report.get('loaded', 0)} of {school_report['features']} records loaded "
            f"and used by the distance layer; {school_report.get('invalid_coordinates', 0)} with "
            f"coordinates outside Rwanda or not numbers and {school_report.get('missing_geometry', 0)}"
            f" without a point (left out, never guessed); {school_report.get('duplicate_points', 0)}"
            f" sharing another school's coordinates; missing properties: "
            f"{', '.join(f'{k} ({v})' for k, v in missing.items()) or 'none'}."
            + (f" Errors: {'; '.join(school_report['errors'])}." if school_report.get("errors")
               else ""),
            unsafe_allow_html=True,
        )  # fmt: skip
        if school_report.get("status") == "provisional":
            mapped = school_report.get("osm_points")
            theme.note(
                (
                    f"A provisional list: {mapped} schools mapped in OpenStreetMap plus the "
                    f"{school_report['mineduc_points'] - school_report['mineduc_same_site']} "
                    "standalone pre-primary schools from MINEDUC that are not at an OSM school's "
                    f"site ({school_report['mineduc_same_site']} are, counted once). "
                    if mapped is not None
                    else "A provisional list: only standalone pre-primary schools. "
                )
                + "The share of children more than 1 km from a listed school is an upper bound, "
                "and it is not used as evidence in the bottleneck rules; a missing school is not "
                "proof of no school."
            )

with tabs[1]:
    estimates = data.table("estimate_2026")
    method = estimates.method.iat[0] if len(estimates) else "not built"
    st.markdown(f"**Scope.** {DEFINITION}")
    st.markdown(
        f"""
- **Children aged 3 to 5 (2026):** NISR's projected children aged 3 to 5 per district (from
  the single-age tables; otherwise the projected population × the census 3-5 share), split
  across sectors by WorldPop under-5 (× census age ratio) or, while WorldPop is missing, by
  census sector shares. Range from the projection range and the disagreement between the two
  splits. Method in use: *{method}*.
- **Attending (2026):** the sector's census 2022 attendance rate. The app can move it by the
  district's change in MINEDUC pupils per child since 2021/22 (`MINEDUC_TREND_ON_CENSUS`),
  but this is off: the census rate (53.7% in 2022) and MINEDUC's gross rate barely agree by
  district (correlation 0.3 to 0.4), and pupils grew 52% in 2022/23 alone. TRACK shows
  MINEDUC's own rate. Counts from different sources are never added together.
- **Census counts from sample records:** when the census arrives as sample records of
  children aged 3 to 5 with population weights (not printed Table 2.5), each sector's count is
  the sum of the weights, so it is a model estimate. Sectors resting on fewer than 100
  sampled children carry about ±10 points of uncertainty on their attendance rate.
- **Places** = max(0, ceil(t × P) − A); **rooms** = ceil(places / {CHILDREN_PER_ROOM.value:g});
  **caregivers** between places / {CAREGIVER_RATIO_HIGH.value:g} and places /
  {CAREGIVER_RATIO_LOW.value:g}. {CHILDREN_PER_ROOM.citation}.
- **Far from school:** share of children more than {WALKING_DISTANCE_KM.value:g} km from a
  school with pre-primary, along roads where OSM roads reach most children, otherwise
  straight-line (indicative).
- **Priority index:** weighted percentile ranks of volume (places needed), equity (share not
  attending), peer gap (below the peer model's expectation) and poverty, within the district.
  Rank stability: share of 500 Dirichlet weight draws in which a sector stays in the top 3.
- **Bottlenecks:** SUPPLY (large gap and at least {FAR_SHARE:.0%} of children beyond 1 km),
  DEMAND (school nearby, attendance below the peer interval), CAPACITY (district teacher
  ratios or qualifications in the worst quarter), WELLBEING (stunting or water and
  sanitation in the worst quarter), NONE (at or above target). Factor scores are national
  percentiles; {WEAK_FACTOR:.2f} marks the worst quarter.
- **Enrolment rate (TRACK):** MINEDUC pre-primary pupils / children aged 3 to 5; a gross
  rate. Targets: {TARGET_2027.value:.1%} by 2026/27 and {TARGET_2029.value:.0%} by 2028/29
  ({TARGET_2029.citation}).
"""
    )

with tabs[2]:
    if run.empty:
        st.info("The peer model has not run.")
    else:
        chosen = run[run.chosen].iloc[0]
        m = chosen.metrics
        st.markdown(
            f"**Peer benchmark model.** Chosen: **{MODEL_LABELS[chosen.model_id]}**"
            + (" (fallback: no model beat the district average)" if m.get("fallback") else "")
        )
        st.markdown(
            "- **Purpose:** expected attendance of children aged 3 to 5 for a sector, given "
            "sectors like it, to spot where attendance is lower than its peers.\n"
            "- **Target:** census 2022 attendance rate (observed), one row per sector "
            f"({m.get('n_sectors')} sectors, {m.get('n_districts')} districts).\n"
            f"- **Features:** {', '.join(LABELS.get(f, f) for f in m.get('features', []))}.\n"
            "- **Validation:** leave-one-district-out cross-validation; the simplest model "
            "within 1 point of the best MAE is kept.\n"
            f"- **Intervals:** split-conformal at {CONFORMAL_COVERAGE:.0%} from out-of-fold "
            f"residuals: ±{m.get('interval_halfwidth_pp')} points.\n"
            "- **Use:** a screening aid for planners. Drivers are associations, not causes. "
            "Not for judging individual centres or staff.\n"
            "- **Not for:** causal claims, child-level decisions, or ranking caregivers."
        )
        if m.get("importance_pp"):
            imp = pd.DataFrame(
                {
                    "Feature": [LABELS.get(k, k) for k in m["importance_pp"]],
                    "Mean contribution (points)": list(m["importance_pp"].values()),
                }
            )
            st.dataframe(imp, hide_index=True, width="stretch")

with tabs[3]:
    if not run.empty:
        st.markdown("**Peer model: leave-one-district-out cross-validation**")
        table = pd.DataFrame(
            [
                {
                    "Model": MODEL_LABELS[r.model_id],
                    "MAE (points)": r.metrics["mae_pp"],
                    "Weighted MAE (points)": r.metrics["weighted_mae_pp"],
                    "R²": r.metrics["r2"],
                    "Chosen": "yes" if r.chosen else "",
                }
                for r in run.itertuples()
            ]
        )
        st.dataframe(table, hide_index=True, width="stretch")
        m = run[run.chosen].iloc[0].metrics
        moran = m.get("residual_moran", {})
        st.markdown(
            f"- Interval coverage: **{m.get('coverage', 0):.1%}** (target "
            f"{CONFORMAL_COVERAGE:.0%}); by area: "
            + ", ".join(f"{k} {v:.0%}" for k, v in m.get("coverage_by_area", {}).items())
            + "\n"
            "- Error by area (MAE, points): "
            + ", ".join(f"{k} {v}" for k, v in m.get("mae_by_area", {}).items())
            + "\n"
            "- Error by province (MAE, points): "
            + ", ".join(f"{k} {v}" for k, v in m.get("mae_by_province", {}).items())
            + "\n"
            f"- Moran's I of residuals: **{moran.get('morans_i')}** (p = {moran.get('p_value')}; "
            f"expected under no clustering {moran.get('expected')}). A positive, significant "
            "value means neighbouring sectors share something the features miss."
        )
    summary = forecast.summary(data.table("forecast")).drop(index=forecast.NATIONAL)
    st.markdown("**2029 trend: back-test** (fit 2020/21-2023/24, predict 2024/25)")
    st.markdown(
        f"- Mean absolute error: **{summary.backtest_error_pp.abs().mean():.2f} points** across "
        f"30 districts; observed value inside the 80% range for "
        f"**{summary.backtest_inside.mean():.0%}** of districts."
    )
    if (data.table("model_output").status == "simulated").any():
        st.warning(
            "The peer model's validation above is computed on simulated inputs: it tests the "
            "method, not the real-world accuracy."
        )
    if (data.table("forecast").status == "simulated").any():
        st.warning(
            "The trend back-test runs on the simulated yearbook series: it tests the method, "
            "not the real-world accuracy."
        )

with tabs[4]:
    st.markdown(
        """
- **Census attendance may leave out home-based ECD.** The gap is the formal pre-primary gap.
- **Five yearbook points make a short trend.** The 2029 range assumes the trend continues;
  policy changes, fee changes or a new data series can break it.
- **Children aged 3 to 5 to 2029** come from NISR's single-age projections when they are
  loaded; otherwise the 3-5 share is held at its 2022 value, and falling fertility would make
  2029 children (and places needed) overstated.
- **Attendance in 2026 is the 2022 census rate.** Enrolment has grown since (MINEDUC's gross
  rate rose from 35% in 2021/22 to 65% in 2024/25), so places needed may be overstated where it
  grew. The two rates measure different things: the gross rate counts over-age pupils.
- **The 2029 trend runs through a jump:** pupils rose 52% in 2022/23, so the straight-line
  trend is steep and reaches the 100% cap in many districts; read "on track" with the latest
  observed rate beside it.
- **OSM does not say which schools have pre-primary.** Distance uses all schools and
  kindergartens; where roads are thin, straight-line distance understates the walk.
- **District context.** Capacity and stunting are district values applied to every sector.
- **Peer model drivers are associations.** A sector's features explain its expected value; they
  do not say what would change attendance.
- **LEARN data are simulated** for the Muhanga pilot. The quiz measures course knowledge, not
  teaching quality. Caregivers are never ranked.
- **Kinyarwanda labels and course titles are drafts** awaiting review by a native speaker.
- **Every value in this demo build that comes from a missing file is simulated**, labelled, and
  excluded from exports by default.
- **The IrereroAI assistant is a language model.** It answers from this dashboard's figures and
  labels their status, but it can still misread or misstate them: check an answer against the
  screen before using it. It reads aggregates only and cannot change plans or data.
"""
    )

with tabs[5]:
    st.markdown(
        "IrereroAI complements NCDA's ECD Mapping System. It reads an extract in the "
        "`supply_extract` schema: one row per centre with its type, location, capacity, "
        "enrolment and caregivers. Centres are joined to sectors through the reviewed crosswalk. "
        "They are not added to the distance layer, which measures distance to formal pre-primary "
        "schools (most mapped services are home-based ECD)."
    )
    on = st.toggle("Show the NCDA connector", value=False)
    if on:
        extract = data.table("supply_extract")
        names = data.table("geo_unit").set_index("geo_id").name
        real = extract[extract.status != SIMULATED]
        if len(real) and not data.setting_on(NCDA_DISPLAY_SETTING):
            theme.note(
                f"The NCDA extract is loaded ({len(real):,} active services) but not shown here: "
                f"set {NCDA_DISPLAY_SETTING} to on once the NCDA data-sharing agreement allows "
                "public display."
            )
            extract = extract[extract.status == SIMULATED]
        for status, part in extract.groupby("status", sort=False):
            label = (
                "Muhanga demonstration centres (seed 2026)"
                if status == SIMULATED
                else (f"NCDA extract, as of {part.as_of.max()}")
            )
            st.markdown(
                f"{theme.badge(status)} {label} · {len(part):,} centres · ids unique: "
                f"{part.centre_id.is_unique} · joined to sectors: {part.geo_id.notna().mean():.0%}",
                unsafe_allow_html=True,
            )
            by_sector = part.groupby("geo_id").agg(
                centres=("centre_id", "count"),
                capacity=("capacity", lambda s: s.sum(min_count=1)),
                enrolled=("enrolled_3_5", lambda s: s.sum(min_count=1)),
                enrolled_3_6=("enrolled_3_6", lambda s: s.sum(min_count=1)),
                caregivers=("caregivers", lambda s: s.sum(min_count=1)),
            )
            by_sector["free places"] = (by_sector.capacity - by_sector.enrolled).clip(lower=0)
            by_sector = by_sector.dropna(axis=1, how="all")  # a column the source does not have
            by_sector.index = [names.get(g, g) for g in by_sector.index]
            st.dataframe(
                by_sector.rename_axis("Sector").reset_index(), hide_index=True, width="stretch"
            )
        theme.note(
            "Free places in mapped centres show where existing supply could absorb children "
            "before new rooms are built; the NCDA extract has no capacity, so it shows none. It "
            "counts children aged 3 to 6. NCDA enrolment is shown separately and never added to "
            "census or MINEDUC counts."
        )
