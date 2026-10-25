"""District brief: every number with its source, reference period and status, as one long table
that feeds the page, the CSV and the PDF.

Exports leave out simulated values unless asked, and then label them. Counts of children under
10 are shown as "fewer than 10".
"""

import pandas as pd

from irerero.config import SIMULATED, SUPPRESS_BELOW

COUNT_INDICATORS = {"children_3_5", "attending", "places"}
COLUMNS = ["geo_id", "area", "indicator", "value", "unit", "source", "period", "status"]
SOURCE_ESTIMATE = "IrereroAI 2026 estimate (census 2022, NISR projections, MINEDUC)"
SOURCE_STANDARDS = "IrereroAI from the National ECD Standards (2024)"
SOURCE_DISTANCE = "IrereroAI distance layer (OSM schools and roads)"
SOURCE_DIAGNOSIS = "IrereroAI bottleneck rules"
SOURCE_TREND = "IrereroAI trend of MINEDUC yearbooks 2020/21-2024/25"


def sector_rows(ranked: pd.DataFrame) -> pd.DataFrame:
    """Long rows for each sector of a ranked planning table (from plan.frame.ranked) joined
    with its diagnosis (bottleneck)."""
    rows = []
    for r in ranked.itertuples():
        status = r.status
        rows += [
            (
                r.geo_id,
                r.name,
                "priority_rank",
                r.rank,
                "rank",
                "IrereroAI priority index",
                "2026",
                "model estimate" if status != SIMULATED else SIMULATED,
            ),
            (
                r.geo_id,
                r.name,
                "children_3_5",
                r.children_3_5,
                "children",
                SOURCE_ESTIMATE,
                "2026",
                status,
            ),
            (
                r.geo_id,
                r.name,
                "children_3_5_low",
                r.low,
                "children",
                SOURCE_ESTIMATE,
                "2026",
                status,
            ),
            (
                r.geo_id,
                r.name,
                "children_3_5_high",
                r.high,
                "children",
                SOURCE_ESTIMATE,
                "2026",
                status,
            ),
            (
                r.geo_id,
                r.name,
                "attendance_rate",
                round(r.attendance_rate, 4),
                "share",
                SOURCE_ESTIMATE,
                "2026",
                status,
            ),
            (r.geo_id, r.name, "places", r.places, "places", SOURCE_STANDARDS, "2026", status),
            (r.geo_id, r.name, "rooms", r.rooms, "rooms", SOURCE_STANDARDS, "2026", status),
            (
                r.geo_id,
                r.name,
                "caregivers_low",
                r.caregivers_low,
                "caregivers",
                SOURCE_STANDARDS,
                "2026",
                status,
            ),
            (
                r.geo_id,
                r.name,
                "caregivers_high",
                r.caregivers_high,
                "caregivers",
                SOURCE_STANDARDS,
                "2026",
                status,
            ),
            (r.geo_id, r.name, "far_share", r.far_share, "share", SOURCE_DISTANCE, "2026", status),
        ]
        if hasattr(r, "bottleneck"):
            rows.append(
                (
                    r.geo_id,
                    r.name,
                    "bottleneck",
                    r.bottleneck,
                    "category",
                    SOURCE_DIAGNOSIS,
                    "2026",
                    status,
                )
            )
    return pd.DataFrame(rows, columns=COLUMNS)


def district_rows(geo_id: str, name: str, summary: pd.Series, status: str) -> pd.DataFrame:
    rows = [
        (
            geo_id,
            name,
            "enrolment_rate_latest",
            round(summary.latest, 4),
            "share",
            "MINEDUC yearbook / NISR projection",
            "2024/25",
            status,
        ),
        (
            geo_id,
            name,
            "enrolment_rate_2028_29",
            round(summary.projected, 4),
            "share",
            SOURCE_TREND,
            "2028/29",
            status,
        ),
        (
            geo_id,
            name,
            "enrolment_rate_2028_29_low",
            round(summary.low, 4),
            "share",
            SOURCE_TREND,
            "2028/29",
            status,
        ),
        (
            geo_id,
            name,
            "enrolment_rate_2028_29_high",
            round(summary.high, 4),
            "share",
            SOURCE_TREND,
            "2028/29",
            status,
        ),
        (
            geo_id,
            name,
            "status_2028_29",
            summary.status,
            "category",
            SOURCE_TREND,
            "2028/29",
            status,
        ),
    ]
    return pd.DataFrame(rows, columns=COLUMNS)


def suppress_counts(values: pd.Series) -> pd.Series:
    """One column of counts of children: values below SUPPRESS_BELOW become "fewer than 10".
    The same rule for the long CSV rows and the PDF table."""
    small = pd.to_numeric(values, errors="coerce") < SUPPRESS_BELOW
    return values.astype(object).where(~small, f"fewer than {SUPPRESS_BELOW}")


def suppress(frame: pd.DataFrame) -> pd.DataFrame:
    """Counts of children below SUPPRESS_BELOW become "fewer than 10"."""
    out = frame.copy().astype({"value": object})
    counts = out.indicator.str.replace(r"_(low|high)$", "", regex=True).isin(COUNT_INDICATORS)
    out.loc[counts, "value"] = suppress_counts(out.loc[counts, "value"])
    return out


def export(frame: pd.DataFrame, include_simulated: bool = False) -> pd.DataFrame:
    """The table as exported: simulated rows dropped unless asked for, then labelled in a
    SIMULATED column; small counts suppressed."""
    out = frame if include_simulated else frame[frame.status != SIMULATED]
    out = suppress(out)
    if include_simulated:
        out = out.assign(simulated=(out.status == SIMULATED).map({True: "SIMULATED", False: ""}))
    return out.reset_index(drop=True)


def to_csv(frame: pd.DataFrame, include_simulated: bool = False) -> bytes:
    out = export(frame, include_simulated)
    header = "# IrereroAI district brief. Every value has its source, period and status. " + (
        "Simulated values are included and labelled SIMULATED.\n"
        if include_simulated
        else "Simulated values are excluded.\n"
    )
    return (header + out.to_csv(index=False)).encode("utf-8")


def pdf(
    title: str,
    lines: list[str],
    table: pd.DataFrame,
    notes: list[str],
    simulated: bool,
) -> bytes:
    """One A4 page: title, key numbers, the priority table, notes and sources."""
    from fpdf import FPDF

    from irerero.learn.certificate import LOGO

    def clean(text: object) -> str:
        return str(text).replace("\u2013", "-").replace("\u2014", "-").replace("\u00b7", "-")

    doc = FPDF(format="A4")
    doc.set_auto_page_break(True, margin=12)
    doc.add_page()
    if LOGO.exists():
        doc.image(str(LOGO), x=10, y=8, w=45)
    doc.set_xy(10, 22)
    doc.set_font("Helvetica", "B", 15)
    doc.set_text_color(3, 54, 101)
    doc.cell(0, 8, clean(title), new_x="LMARGIN", new_y="NEXT")
    if simulated:
        doc.set_font("Helvetica", "B", 9)
        doc.set_text_color(180, 35, 24)
        doc.multi_cell(
            0,
            5,
            "SIMULATED: this brief contains simulated stand-in values. They show "
            "the method, not the real situation.",
            new_x="LMARGIN",
            new_y="NEXT",
        )
    doc.set_text_color(15, 27, 42)
    doc.set_font("Helvetica", "", 9)
    for line in lines:
        doc.multi_cell(0, 5, clean(line), new_x="LMARGIN", new_y="NEXT")
    doc.ln(2)
    if len(table):
        doc.set_font("Helvetica", "B", 8)
        widths = [190 / len(table.columns)] * len(table.columns)
        for column, w in zip(table.columns, widths, strict=True):
            doc.cell(w, 6, clean(column), border=1)
        doc.ln()
        doc.set_font("Helvetica", "", 8)
        for row in table.itertuples(index=False):
            for value, w in zip(row, widths, strict=True):
                doc.cell(w, 5, clean(value)[:28], border=1)
            doc.ln()
    doc.ln(2)
    doc.set_font("Helvetica", "", 7)
    doc.set_text_color(91, 107, 124)
    for n in notes:
        doc.multi_cell(0, 4, clean(n), new_x="LMARGIN", new_y="NEXT")
    return bytes(doc.output())
