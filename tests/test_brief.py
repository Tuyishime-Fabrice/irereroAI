"""Exports: simulated values are excluded by default and labelled when included; small counts
are suppressed; every exported value has a source, period and status."""

import io

import pandas as pd

from irerero import brief
from irerero.config import SIMULATED

ROWS = pd.DataFrame(
    [
        ("S1", "A", "children_3_5", 1200, "children", "src", "2026", "model estimate"),
        ("S1", "A", "places", 7, "places", "src", "2026", "model estimate"),
        ("S1", "A", "children_3_5_low", 4, "children", "src", "2026", "model estimate"),
        ("S1", "A", "rooms", 3, "rooms", "src", "2026", "model estimate"),
        ("S2", "B", "children_3_5", 900, "children", "src", "2026", SIMULATED),
    ],
    columns=brief.COLUMNS,
)


def test_simulated_values_excluded_by_default():
    out = brief.export(ROWS)
    assert SIMULATED not in set(out.status)
    assert "S2" not in set(out.geo_id)


def test_simulated_values_labelled_when_included():
    out = brief.export(ROWS, include_simulated=True)
    sim = out[out.status == SIMULATED]
    assert len(sim) == 1
    assert (sim.simulated == "SIMULATED").all()
    assert (out[out.status != SIMULATED].simulated == "").all()


def test_small_counts_suppressed_but_not_rooms():
    out = brief.export(ROWS).set_index("indicator").value
    assert out["places"] == "fewer than 10"
    assert out["children_3_5_low"] == "fewer than 10"
    assert out["children_3_5"] == 1200
    assert out["rooms"] == 3  # not a count of children


def test_csv_says_what_it_contains():
    text = brief.to_csv(ROWS).decode()
    assert text.startswith("# IrereroAI district brief")
    assert "Simulated values are excluded" in text
    frame = pd.read_csv(io.StringIO(text), comment="#")
    assert {"source", "period", "status"} <= set(frame.columns)
    assert frame.source.notna().all() and frame.status.notna().all()


def test_brief_from_built_tables(tables):
    from irerero.plan.frame import ranked

    est = tables["estimate_2026"].merge(
        tables["geo_unit"][["geo_id", "name", "parent_id"]], on="geo_id"
    )
    est = est[est.parent_id == "D-MUHANGA"].assign(poverty=0.3, expected=float("nan"))
    result, _ = ranked(est, 0.65, {"volume": 1}, stability=False)
    rows = brief.sector_rows(result)
    assert len(rows) == 10 * len(result)
    assert brief.export(rows).empty  # demo build: everything is simulated
    assert len(brief.export(rows, include_simulated=True)) == len(rows)


def test_pdf_renders():
    out = brief.pdf(
        "District brief: Test", ["Line [1]"], pd.DataFrame({"A": [1]}), ["[1] src"], True
    )
    assert out[:4] == b"%PDF"
