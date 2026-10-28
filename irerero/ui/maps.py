"""Choropleth maps with pydeck. Colours come from the brand's sequential ramp (one hue family,
light to dark, so order survives colour-blindness and greyscale) and every map has a text
legend; tooltips carry the value, source and status."""

import copy
from collections.abc import Callable, Mapping
from html import escape

import numpy as np
import pydeck as pdk
import streamlit as st

from irerero.ui.theme import RAMP

VIRIDIS = list(RAMP)  # low -> high
NO_DATA = "#D0D5DB"
POINT = "#B54708"  # school points: orange, apart from the green-blue ramp
VIEW = pdk.ViewState(latitude=-1.95, longitude=29.9, zoom=7.2, min_zoom=6, max_zoom=13)


def _rgb(hex_colour: str, alpha: int = 210) -> list[int]:
    h = hex_colour.lstrip("#")
    return [int(h[i : i + 2], 16) for i in (0, 2, 4)] + [alpha]


def bins(values: Mapping[str, float], k: int = 5) -> list[float]:
    data = np.array([v for v in values.values() if v == v])
    if len(data) == 0:
        return []
    edges = np.unique(np.quantile(data, np.linspace(0, 1, k + 1)))
    return edges.tolist()


def _bin(value: float, edges: list[float]) -> int:
    if len(edges) < 2:
        return 0
    return int(min(np.searchsorted(edges, value, side="right") - 1, len(edges) - 2))


def choropleth(
    geojson: dict,
    values: Mapping[str, float],
    label: str,
    fmt: Callable[[float], str],
    tooltip: Mapping[str, str] | None = None,
    colours: Mapping[str, str] | None = None,
    view: pdk.ViewState | None = None,
    height: int = 460,
    key: str | None = None,
    points: list[dict] | None = None,
    edges: list[float] | None = None,
) -> None:
    """Colour features by value (quantile bins unless fixed `edges` are given), or by a given
    colour per geo_id. `points` (dicts with lon, lat, name and extra) are drawn on top, e.g.
    school locations."""
    data = copy.deepcopy(geojson)
    edges = edges or bins(values)
    palette = VIRIDIS[: max(1, len(edges) - 1)]
    keep = []
    for feature in data["features"]:
        geo_id = feature["properties"]["geo_id"]
        if geo_id not in values and (colours is None or geo_id not in colours):
            continue
        value = values.get(geo_id, float("nan"))
        if colours is not None and geo_id in colours:
            colour = colours[geo_id]
        elif value == value:
            colour = palette[_bin(value, edges)]
        else:
            colour = NO_DATA
        feature["properties"]["fill"] = _rgb(colour)
        feature["properties"]["value_text"] = fmt(value) if value == value else "no data"
        feature["properties"]["extra"] = (tooltip or {}).get(geo_id, "")
        keep.append(feature)
    data["features"] = keep
    layer = pdk.Layer(
        "GeoJsonLayer",
        data,
        pickable=True,
        stroked=True,
        filled=True,
        get_fill_color="properties.fill",
        get_line_color=[255, 255, 255, 255],
        line_width_min_pixels=0.6,
        auto_highlight=True,
    )
    layers = [layer]
    if points:
        layers.append(
            pdk.Layer(
                "ScatterplotLayer",
                [
                    {**p, "value_text": p.get("value_text", ""), "position": [p["lon"], p["lat"]]}
                    for p in points
                ],
                pickable=True,
                get_position="position",
                get_fill_color=_rgb(POINT, 235),
                get_line_color=[255, 255, 255, 255],
                stroked=True,
                line_width_min_pixels=1,
                radius_min_pixels=3,
                radius_max_pixels=7,
                get_radius=250,
            )
        )
    deck = pdk.Deck(
        layers=layers,
        initial_view_state=view or VIEW,
        map_style="light",
        tooltip={
            "html": f"<b>{{name}}</b><br/>{label}: {{value_text}}<br/>{{extra}}",
            "style": {"fontSize": "12px", "fontFamily": "Inter, sans-serif"},
        },
    )
    st.pydeck_chart(deck, height=height, key=key)
    if colours is None and len(edges) >= 2:
        legend(
            [(palette[i], f"{fmt(edges[i])}–{fmt(edges[i + 1])}") for i in range(len(palette))],
            f"{label} (lighter = lower)",
        )


def legend(items: list[tuple[str, str]], title: str) -> None:
    """Swatches with dark text beside each colour, so no reading depends on colour alone."""
    swatches = "".join(
        f'<span style="display:inline-flex;align-items:center;gap:6px;margin:4px 16px 4px 0;'
        f'font-size:12px;color:#0F1B2A"><span class="ir-swatch" style="width:12px;height:12px;'
        "border-radius:3px;"
        f'background:{colour};border:1px solid rgba(15,27,42,.2)"></span>{escape(text)}</span>'
        for colour, text in items
    )
    st.markdown(
        f'<div role="group" aria-label="{escape(title, quote=True)}"><div class="ir-note" '
        f'style="margin-bottom:2px">{escape(title)}</div>{swatches}</div>',
        unsafe_allow_html=True,
    )


def view_for(geojson: dict, ids: set[str]) -> pdk.ViewState:
    """Centre and zoom on the features in `ids`."""
    xs, ys = [], []

    def walk(coords: list) -> None:
        if coords and isinstance(coords[0], (int, float)):
            xs.append(coords[0])
            ys.append(coords[1])
        else:
            for c in coords:
                walk(c)

    for f in geojson["features"]:
        if f["properties"]["geo_id"] in ids:
            walk(f["geometry"]["coordinates"])
    if not xs:
        return VIEW
    span = max(max(xs) - min(xs), max(ys) - min(ys), 0.05)
    zoom = float(np.clip(np.log2(360 / span) - 0.6, 6, 12))
    return pdk.ViewState(
        latitude=(min(ys) + max(ys)) / 2, longitude=(min(xs) + max(xs)) / 2, zoom=zoom
    )
