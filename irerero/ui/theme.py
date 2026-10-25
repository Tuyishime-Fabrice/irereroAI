"""IrereroAI design system: brand tokens, page chrome and the components every screen uses.

Navy for navigation and headings, teal for actions and selection, gold for targets, white
cards on a light blue-grey workspace. Colour never carries meaning alone: every status, pill
and legend also says it in words.
"""

import re
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from html import escape
from typing import Any

import streamlit as st

from irerero.config import DEFINITION, ROOT, SIMULATED

ASSETS = ROOT / "app" / "assets"
LOGO = ASSETS / "logo.png"
LOGO_LIGHT = ASSETS / "logo-light.png"
ICON = ASSETS / "icon.png"
ICON_LIGHT = ASSETS / "icon-light.png"

# --- tokens -------------------------------------------------------------------------------
NAVY = "#033665"
NAVY_900 = "#0B2D4F"  # sidebar
TEAL = "#18977A"
TEAL_700 = "#12785F"
GOLD = "#ECA837"
GOLD_700 = "#A86A06"
INK = "#0F1B2A"
SLATE = "#5B6B7C"
SLATE_300 = "#CBD5E1"
BORDER = "#E2E8F0"
SURFACE = "#FFFFFF"
CANVAS = "#F4F7FA"
SIM_RED = "#B42318"

# Chart series (validated with the dataviz palette checks: lightness band, chroma, CVD and
# contrast all pass on white). Used in this order; never cycled.
SERIES = ("#2F6DB5", "#139A7C", "#C4850F")
SERIES_MUTED = "#8A98A8"
# Sequential map ramp, light to dark (green-blue, monotonic lightness).
RAMP = ("#E0F3EE", "#A8DCCB", "#5DB8A8", "#2B8A9A", "#0E5A84")

TONES = {
    "teal": ("#E3F4EF", TEAL_700),
    "navy": ("#E6EEF7", NAVY),
    "gold": ("#FDF3E0", GOLD_700),
    "rose": ("#FCE8E6", SIM_RED),
    "blue": ("#E7F0FB", "#245A99"),
    "purple": ("#F1ECFB", "#5E4596"),
    "slate": ("#EEF2F6", "#3F4E5F"),
}
# Pills: tinted background, dark text of the same hue, and always a word.
PILLS = {
    "SUPPLY": ("rose", "Supply"),
    "DEMAND": ("gold", "Demand"),
    "CAPACITY": ("blue", "Capacity"),
    "WELLBEING": ("purple", "Wellbeing"),
    "NONE": ("teal", "At target"),
    "on track": ("teal", "On track"),
    "at risk": ("gold", "At risk"),
    "off track": ("rose", "Off track"),
    "stable": ("teal", "Stable"),
    "depends on weights": ("gold", "Depends on weights"),
    "rarely top 3": ("slate", "Rarely top 3"),
    "pending": ("slate", "Pending"),
    "approved": ("teal", "Approved"),
    "edited": ("blue", "Edited"),
    "rejected": ("rose", "Rejected"),
    "planned": ("slate", "Planned"),
    "funded": ("blue", "Funded"),
    "done": ("teal", "Done"),
    "required": ("navy", "Required"),
    "recommended": ("gold", "Suggested"),
    "completed": ("teal", "Completed"),
    "set aside": ("slate", "Set aside"),
    "High": ("rose", "High"),
    "Medium": ("gold", "Medium"),
    "Low": ("teal", "Low"),
}

# Stroke icons (24px grid, drawn with currentColor).
ICONS = {
    "users": '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/>'
    '<path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    "target": '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/>'
    '<circle cx="12" cy="12" r="2"/>',
    "chart": '<path d="M3 3v18h18"/><path d="M18 17V9"/><path d="M13 17V5"/><path d="M8 17v-3"/>',
    "school": '<path d="M3 21h18"/><path d="M5 21V7l7-4 7 4v14"/><path d="M9 21v-6h6v6"/>',
    "pin": '<path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/>',
    "alert": '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/>'
    '<path d="M12 9v4"/><path d="M12 17h.01"/>',
    "book": '<path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/>'
    '<path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>',
    "check": '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><path d="m9 11 3 3L22 4"/>',
    "clock": '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>',
    "home": '<path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><path d="M9 22V12h6v10"/>',
    "route": '<circle cx="6" cy="19" r="3"/><path d="M9 19h8.5a3.5 3.5 0 0 0 0-7h-11a3.5 3.5 0 0 1 0-7H15"/>'
    '<circle cx="18" cy="5" r="3"/>',
    "trend": '<path d="m22 7-8.5 8.5-5-5L2 17"/><path d="M16 7h6v6"/>',
    "heart": '<path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74'
    '-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"/>',
    "droplet": '<path d="M12 22a7 7 0 0 0 7-7c0-2-1-3.9-3-5.5s-3.5-4-4-6.5c-.5 2.5-2 4.9-4 6.5C6 11.1 5 13'
    ' 5 15a7 7 0 0 0 7 7z"/>',
    "coins": '<circle cx="8" cy="8" r="6"/><path d="M18.09 10.37A6 6 0 1 1 10.34 18"/>'
    '<path d="M7 6h1v4"/>',
    "clipboard": '<rect width="8" height="4" x="8" y="2" rx="1"/><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2'
    ' 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><path d="M9 14h6"/><path d="M9 18h6"/>',
    "bell": '<path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/>',
    "database": '<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14a9 3 0 0 0 18 0V5"/>'
    '<path d="M3 12a9 3 0 0 0 18 0"/>',
    "info": '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>',
    "shield": '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1'
    'c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/>',
    "rooms": '<rect width="18" height="18" x="3" y="3" rx="2"/><path d="M3 9h18"/><path d="M9 21V9"/>',
    "cap": '<path d="M22 10 12 5 2 10l10 5 10-5z"/><path d="M6 12v5c3 3 9 3 12 0v-5"/>',
    "layers": '<path d="m12 2 10 5-10 5L2 7z"/><path d="m2 17 10 5 10-5"/><path d="m2 12 10 5 10-5"/>',
    "scale": '<path d="m16 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"/><path d="m2 16 3-8 3 8c-.87.65'
    '-1.92 1-3 1s-2.13-.35-3-1Z"/><path d="M7 21h10"/><path d="M12 3v18"/><path d="M3 7h2c2 0 5-1 7-2'
    ' 2 1 5 2 7 2h2"/>',
}


def icon(name: str, size: int = 20, stroke: float = 2) -> str:
    return (
        f'<svg class="ir-icon" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
        f'stroke="currentColor" stroke-width="{stroke}" stroke-linecap="round" '
        f'stroke-linejoin="round" aria-hidden="true">{ICONS[name]}</svg>'
    )


# --- page chrome --------------------------------------------------------------------------
CSS = f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
  :root {{
    --ir-navy: {NAVY}; --ir-teal: {TEAL}; --ir-gold: {GOLD}; --ir-ink: {INK};
    --ir-slate: {SLATE}; --ir-border: {BORDER}; --ir-canvas: {CANVAS};
    --ir-font: Inter, "Source Sans Pro", system-ui, -apple-system, "Segoe UI", sans-serif;
  }}
  .stApp, .stApp p, .stApp li, .stApp label, .stApp input, .stApp textarea, .stApp button,
  .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp td, .stApp th,
  .stApp [data-testid="stMarkdownContainer"], .stApp [data-baseweb="select"] {{
    font-family: var(--ir-font);
  }}
  .stApp h1, .stApp h2, .stApp h3, .stApp h4 {{ color: {NAVY}; letter-spacing: -.01em; }}
  .stApp h3 {{ font-size: 1.15rem; font-weight: 700; }}
  header[data-testid="stHeader"] {{ background: transparent; }}
  .block-container {{ padding-top: 1.2rem; padding-bottom: 3rem; max-width: 1360px; }}

  /* sidebar */
  section[data-testid="stSidebar"] {{ border-right: 0; }}
  section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a {{
    border-radius: 8px; margin: 1px 0; padding: .3rem .7rem; min-height: 2.3rem;
  }}
  [data-testid="stSidebarLogo"], [data-testid="stHeaderLogo"] {{ height: 2.4rem; max-width: 13rem; }}
  [data-testid="stNavSectionHeader"] p {{ color: #9FB3C8 !important; font-size: .72rem;
    font-weight: 600; text-transform: uppercase; letter-spacing: .08em; }}
  section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a span {{
    color: #D6E2EE; font-weight: 500;
  }}
  section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a:hover {{
    background: rgba(255,255,255,.07);
  }}
  section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[aria-current="page"] {{
    background: {TEAL};
  }}
  section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[aria-current="page"] span {{
    color: #fff; font-weight: 600;
  }}
  section[data-testid="stSidebar"] [data-testid="stSidebarNavSeparator"] {{
    border-color: rgba(255,255,255,.12);
  }}
  section[data-testid="stSidebar"] header [data-testid="stSidebarNavSeparator"] {{ display:none; }}
  .ir-side-label {{
    color: #9FB3C8; font-size: .72rem; font-weight: 600; text-transform: uppercase;
    letter-spacing: .08em; margin: .2rem 0 .3rem;
  }}
  .ir-side-note {{ color: #9FB3C8; font-size: .75rem; line-height: 1.4; }}

  /* cards: every bordered container is a white card */
  .stApp [class*="st-key-ir-"] {{
    background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 12px;
    box-shadow: 0 1px 2px rgba(16,24,40,.04); padding: 1rem 1.1rem;
  }}
  .stApp [class*="st-key-ir-"] [class*="st-key-ir-"] {{ box-shadow: none; }}
  .stApp [data-testid="stExpander"] details {{
    background: {SURFACE}; border-color: {BORDER}; border-radius: 10px;
  }}
  .stButton button, .stDownloadButton button, .stFormSubmitButton button {{
    border-radius: 8px; font-weight: 600;
  }}
  .stButton button:focus-visible, .stDownloadButton button:focus-visible {{
    outline: 2px solid {GOLD}; outline-offset: 2px;
  }}
  [data-testid="stDataFrame"] {{ border-radius: 10px; overflow: hidden; }}

  /* top bar and page header */
  .ir-topbar {{
    display: flex; align-items: center; justify-content: space-between; gap: 1rem;
    padding: .2rem 0 .9rem; border-bottom: 1px solid {BORDER}; margin-bottom: 1rem;
  }}
  .ir-crumbs {{ color: {SLATE}; font-size: .85rem; display: flex; flex-wrap: wrap; gap: .35rem;
    align-items: center; }}
  .ir-crumbs .sep {{ color: {SLATE_300}; }}
  .ir-crumbs .here {{ color: {INK}; font-weight: 600; }}
  .ir-crumbs .app {{ color: {SLATE}; font-weight: 600; letter-spacing: .08em;
    text-transform: uppercase; font-size: .74rem; margin-right: .4rem; }}
  .ir-user {{ display: flex; align-items: center; gap: .7rem; white-space: nowrap; }}
  .ir-user .bell {{ color: {SLATE}; position: relative; display: flex; }}
  .ir-avatar {{ width: 34px; height: 34px; border-radius: 50%; background: {NAVY};
    color: #fff; display: flex; align-items: center; justify-content: center;
    font-weight: 700; font-size: .8rem; }}
  .ir-user .who {{ line-height: 1.15; }}
  .ir-user .who b {{ color: {INK}; font-size: .86rem; display: block; }}
  .ir-user .who span {{ color: {SLATE}; font-size: .76rem; }}
  .stApp h1.ir-title {{ padding: 0 !important; }}
  .ir-title {{ font-size: 1.95rem; font-weight: 800; color: {NAVY}; margin: 0;
    letter-spacing: -.02em; line-height: 1.15; }}
  .ir-subtitle {{ color: {SLATE}; font-size: 1.05rem; margin: .3rem 0 .2rem; }}
  .ir-tag {{ display: inline-block; vertical-align: middle; margin-left: .6rem; font-size: .75rem;
    font-weight: 600; padding: .15rem .55rem; border-radius: 999px; }}

  /* notices */
  .ir-scope {{ display: flex; gap: .55rem; align-items: flex-start; background: #EEF5F3;
    border: 1px solid #CFE7E0; color: {INK}; font-size: .82rem; padding: .5rem .75rem;
    border-radius: 10px; margin: .7rem 0 .5rem; }}
  .ir-scope .ir-icon {{ color: {TEAL_700}; flex: none; margin-top: 1px; }}
  .ir-banner {{ display: flex; gap: .55rem; align-items: flex-start; background: #FEF3F2;
    border: 1px solid #F5C2BC; border-left: 4px solid {SIM_RED}; color: #7A271A;
    font-size: .82rem; padding: .5rem .75rem; border-radius: 10px; margin: .2rem 0 .8rem; }}
  .ir-banner .ir-icon {{ color: {SIM_RED}; flex: none; margin-top: 1px; }}
  .ir-callout {{ border-radius: 12px; padding: .9rem 1rem; border: 1px solid; }}

  /* badges, pills, chips */
  .ir-badge {{ display: inline-block; padding: .05rem .45rem; border-radius: 4px;
    font-size: .68rem; font-weight: 700; letter-spacing: .04em; vertical-align: middle;
    line-height: 1.5; }}
  .ir-sim {{ background: {SIM_RED}; color: #fff; }}
  .ir-status {{ background: #E6EDF3; color: {NAVY}; font-weight: 600; }}
  .ir-pill {{ display: inline-block; padding: .12rem .6rem; border-radius: 6px; font-size: .8rem;
    font-weight: 600; white-space: nowrap; line-height: 1.5; }}
  .ir-chip {{ display: inline-block; border-radius: 999px; padding: .08rem .6rem; font-size: .78rem;
    font-weight: 600; color: #fff; }}
  .ir-num {{ border-bottom: 1px dotted {SLATE}; cursor: help; }}
  .ir-note {{ color: {SLATE}; font-size: .8rem; line-height: 1.45; }}

  /* KPI cards */
  .ir-kpi {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 12px;
    padding: 1rem 1.1rem; display: flex; gap: .9rem; align-items: flex-start; height: 100%;
    box-shadow: 0 1px 2px rgba(16,24,40,.04); }}
  .ir-kpi .ico {{ width: 42px; height: 42px; border-radius: 50%; display: flex; flex: none;
    align-items: center; justify-content: center; }}
  .ir-kpi .label {{ color: {INK}; font-size: .86rem; font-weight: 600; }}
  .ir-kpi .value {{ color: {NAVY}; font-size: 1.65rem; font-weight: 800; line-height: 1.15;
    letter-spacing: -.02em; margin: .1rem 0; }}
  .ir-kpi .detail {{ color: {SLATE}; font-size: .8rem; }}
  .ir-kpi .src {{ color: {SLATE}; font-size: .7rem; margin-top: .35rem; }}
  .ir-card {{ border: 1px solid {BORDER}; border-radius: 12px; padding: .8rem 1rem;
    height: 100%; background: {SURFACE}; }}
  .ir-card .label {{ color: {SLATE}; font-size: .8rem; }}
  .ir-card .value {{ color: {NAVY}; font-size: 1.55rem; font-weight: 800; line-height: 1.25; }}
  .ir-card .range {{ color: {SLATE}; font-size: .8rem; }}
  .ir-card .src {{ color: {SLATE}; font-size: .72rem; margin-top: .3rem; }}

  /* panel headers */
  .ir-panel-head {{ display: flex; justify-content: space-between; align-items: flex-start;
    gap: .8rem; margin-bottom: .4rem; }}
  .ir-panel-head h3 {{ margin: 0; padding: 0; font-size: 1.12rem; font-weight: 700;
    color: {NAVY}; display: flex; gap: .5rem; align-items: center; }}
  .ir-panel-head h3 .ir-icon {{ margin-right: .45rem; flex: none; }}
  .ir-panel-head p {{ margin: .15rem 0 0; color: {SLATE}; font-size: .85rem; }}

  /* tables */
  .ir-table-wrap {{ overflow-x: auto; border: 1px solid {BORDER}; border-radius: 10px; }}
  table.ir-table {{ width: 100%; border-collapse: collapse; font-size: .88rem; }}
  table.ir-table th {{ background: #F7F9FB; color: {INK}; font-weight: 600; font-size: .8rem;
    text-align: left; padding: .6rem .5rem; border-bottom: 1px solid {BORDER};
    vertical-align: bottom; }}
  table.ir-table td {{ padding: .55rem .5rem; border-bottom: 1px solid #EEF2F6; color: {INK};
    vertical-align: middle; }}
  table.ir-table tr:last-child td {{ border-bottom: 0; }}
  table.ir-table tr:hover td {{ background: #FAFCFD; }}
  table.ir-table .num {{ text-align: right; font-variant-numeric: tabular-nums;
    white-space: nowrap; }}
  table.ir-table .strong {{ font-weight: 600; }}
  table.ir-table .muted {{ color: {SLATE}; }}

  /* factor bars */
  .ir-bar-row {{ display: grid; grid-template-columns: 40px 1fr 42%; gap: .7rem;
    align-items: center; padding: .55rem 0; border-bottom: 1px solid #EEF2F6; }}
  .ir-bar-row:last-child {{ border-bottom: 0; }}
  .ir-bar-row .ico {{ width: 36px; height: 36px; border-radius: 10px; display: flex;
    align-items: center; justify-content: center; }}
  .ir-bar-row .name {{ font-weight: 600; color: {INK}; font-size: .9rem; }}
  .ir-bar-row .sub {{ color: {SLATE}; font-size: .76rem; }}
  .ir-bar-track {{ background: #EEF2F6; border-radius: 6px; height: 12px; position: relative; }}
  .ir-bar-fill {{ height: 12px; border-radius: 6px; }}
  .ir-bar-mark {{ position: absolute; top: -3px; width: 2px; height: 18px; background: {SLATE};
    left: 75%; }}
  .ir-bar-val {{ font-size: .78rem; color: {INK}; margin-top: .2rem; font-weight: 600; }}

  /* timeline */
  .ir-timeline {{ margin: 0; padding: 0; list-style: none; }}
  .ir-timeline li {{ display: grid; grid-template-columns: 14px 1fr; gap: .6rem;
    padding: .45rem 0; }}
  .ir-timeline .dot {{ width: 10px; height: 10px; border-radius: 50%; margin-top: .35rem; }}
  .ir-timeline .when {{ color: {SLATE}; font-size: .75rem; }}
  .ir-timeline .what {{ color: {INK}; font-size: .86rem; font-weight: 600; }}
  .ir-timeline .why {{ color: {SLATE}; font-size: .8rem; }}

  .ir-empty {{ text-align: center; color: {SLATE}; padding: 1.4rem .8rem; font-size: .88rem; }}
  .ir-empty .ir-icon {{ color: {SLATE_300}; margin-bottom: .3rem; }}

  @media (max-width: 760px) {{
    .block-container {{ padding-left: 1rem; padding-right: 1rem; padding-top: 3.2rem; }}
    .ir-title {{ font-size: 1.55rem; }}
    .ir-kpi .value {{ font-size: 1.45rem; }}
    .ir-user .who {{ display: none; }}
    .ir-topbar {{ flex-wrap: wrap; }}
    .ir-bar-row {{ grid-template-columns: 36px 1fr; }}
    .ir-bar-row > div:last-child {{ grid-column: 1 / -1; }}
  }}
</style>
"""


def _altair_theme() -> None:
    import altair as alt

    def theme() -> dict[str, Any]:
        return {
            "config": {
                "font": "Inter, Source Sans Pro, sans-serif",
                "background": "transparent",
                "view": {"stroke": None},
                "axis": {
                    "labelColor": SLATE,
                    "titleColor": SLATE,
                    "titleFontWeight": 500,
                    "gridColor": "#EEF2F6",
                    "domainColor": SLATE_300,
                    "tickColor": SLATE_300,
                    "labelFontSize": 11,
                    "titleFontSize": 11,
                },
                "legend": {"labelColor": INK, "titleColor": SLATE, "labelFontSize": 11},
                "range": {"category": list(SERIES)},
            }
        }

    try:
        alt.theme.register("irerero", enable=True)(theme)
    except AttributeError:  # older Altair
        alt.themes.register("irerero", theme)
        alt.themes.enable("irerero")


def setup() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
    st.logo(str(LOGO_LIGHT), icon_image=str(ICON_LIGHT), size="large")
    _altair_theme()


def topbar(crumbs: Sequence[str]) -> None:
    from irerero.ui.roles import ROLE_LABELS, current

    user = current()
    parts = ['<span class="app">ECD planning · Rwanda</span>']
    for i, crumb in enumerate(crumbs):
        if i:
            parts.append('<span class="sep">›</span>')
        cls = "here" if i == len(crumbs) - 1 else ""
        parts.append(f'<span class="{cls}">{escape(crumb)}</span>')
    words = [w for w in ROLE_LABELS[user.role].split() if w[0].isalpha()]
    initials = "".join(w[0] for w in words[:2]).upper()
    area = user.district_id or "All districts"
    area = area.removeprefix("D-").title() if user.district_id else area
    st.markdown(
        f'<div class="ir-topbar"><div class="ir-crumbs">{"".join(parts)}</div>'
        f'<div class="ir-user"><span class="bell" title="Notifications">{icon("bell", 20)}</span>'
        f'<span class="ir-avatar" aria-hidden="true">{initials}</span>'
        f'<span class="who"><b>{escape(ROLE_LABELS[user.role])}</b>'
        f"<span>{escape(area)} · demo</span></span></div></div>",
        unsafe_allow_html=True,
    )


def header(
    title: str,
    subtitle: str | None = None,
    simulated: bool = False,
    crumbs: Sequence[str] | None = None,
    aside: str | None = None,
    tag: str | None = None,
) -> None:
    """Top bar, page title and subtitle, an optional right-hand callout (HTML), the scope line
    and, when needed, the simulated-data notice."""
    topbar(crumbs or [title])
    tag_html = (
        f'<span class="ir-tag" style="background:#FCE8E6;color:{SIM_RED}">{escape(tag)}</span>'
        if tag
        else ""
    )
    head = f'<h1 class="ir-title">{escape(title)}{tag_html}</h1>' + (
        f'<p class="ir-subtitle">{escape(subtitle)}</p>' if subtitle else ""
    )
    if aside:
        left, right = st.columns([3, 2], vertical_alignment="center")
        left.markdown(head, unsafe_allow_html=True)
        right.markdown(aside, unsafe_allow_html=True)
    else:
        st.markdown(head, unsafe_allow_html=True)
    definition()
    if simulated:
        simulated_banner()


def definition() -> None:
    st.markdown(
        f'<div class="ir-scope">{icon("info", 16)}<div><b>Scope.</b> {escape(DEFINITION)} '
        "Census, MINEDUC and NCDA enrolment figures are never added together.</div></div>",
        unsafe_allow_html=True,
    )


def simulated_banner() -> None:
    st.markdown(
        f'<div class="ir-banner">{icon("alert", 16)}<div><span class="ir-badge ir-sim">SIMULATED'
        "</span>&nbsp; Some values on this screen are simulated stand-ins for data files not yet "
        "loaded. They show the method, not the real situation, and are left out of exports by "
        "default.</div></div>",
        unsafe_allow_html=True,
    )


def target_callout(label: str, value: str, detail: str) -> str:
    """Gold target card for the page header aside."""
    return (
        f'<div class="ir-callout" style="background:#FDF6E7;border-color:#F3DDB0;display:flex;'
        f'gap:.9rem;align-items:center"><span style="color:{GOLD_700}">{icon("target", 34, 1.8)}'
        f'</span><div><div style="font-weight:700;color:{INK};font-size:.9rem">{escape(label)}</div>'
        f'<div style="color:{SLATE};font-size:.8rem">{escape(detail)}</div>'
        f'<div style="font-weight:800;color:{NAVY};font-size:1.35rem">{escape(value)}</div>'
        "</div></div>"
    )


# --- provenance ---------------------------------------------------------------------------
def badge(status: str | None) -> str:
    if status == SIMULATED:
        return '<span class="ir-badge ir-sim">SIMULATED</span>'
    if not status:
        return ""
    return f'<span class="ir-badge ir-status">{escape(status)}</span>'


def provenance(source: str, period: str | None, status: str | None) -> str:
    parts = [source]
    if period:
        parts.append(str(period))
    if status:
        parts.append(status)
    return " · ".join(parts)


def number(text: str, source: str, period: str | None, status: str | None) -> str:
    """A number with its source, reference year and status on hover, and a SIMULATED badge."""
    tip = escape(provenance(source, period, status), quote=True)
    sim = f" {badge(status)}" if status == SIMULATED else ""
    return f'<span class="ir-num" title="{tip}">{escape(text)}</span>{sim}'


# --- components ---------------------------------------------------------------------------
def kpi(
    label: str,
    value: str,
    source: str,
    period: str | None,
    status: str | None,
    detail: str | None = None,
    icon_name: str = "chart",
    tone: str = "teal",
) -> None:
    """KPI card: tinted icon, label, value, detail line, and source with status on hover."""
    bg, fg = TONES[tone]
    tip = escape(provenance(source, period, status), quote=True)
    detail_html = f'<div class="detail">{escape(detail)}</div>' if detail else ""
    st.markdown(
        f'<div class="ir-kpi" title="{tip}"><div class="ico" style="background:{bg};color:{fg}">'
        f'{icon(icon_name, 22)}</div><div style="min-width:0"><div class="label">{escape(label)}'
        f'</div><div class="value">{escape(value)}</div>{detail_html}'
        f'<div class="src">{escape(provenance(source, period, None))} {badge(status)}</div>'
        "</div></div>",
        unsafe_allow_html=True,
    )


def card(
    label: str,
    value: str,
    source: str,
    period: str | None,
    status: str | None,
    detail: str | None = None,
) -> None:
    """Compact metric card without an icon."""
    tip = escape(provenance(source, period, status), quote=True)
    detail_html = f'<div class="range">{escape(detail)}</div>' if detail else ""
    st.markdown(
        f'<div class="ir-card" title="{tip}"><div class="label">{escape(label)}</div>'
        f'<div class="value">{escape(value)}</div>{detail_html}'
        f'<div class="src">{escape(provenance(source, period, None))} {badge(status)}</div></div>',
        unsafe_allow_html=True,
    )


@contextmanager
def panel(
    title: str | None = None,
    subtitle: str | None = None,
    icon_name: str | None = None,
    right: str | None = None,
    key: str | None = None,
) -> Iterator[Any]:
    """A white card with a title row. Streamlit widgets go inside the `with` block. The key
    (from the title unless given) must be unique on the page."""
    slug = re.sub(r"[^a-z0-9]+", "-", (key or title or "panel").lower()).strip("-")
    with st.container(key=f"ir-{slug}") as box:
        if title:
            ico = f'<span style="color:{NAVY}">{icon(icon_name, 20)}</span>' if icon_name else ""
            sub = f"<p>{escape(subtitle)}</p>" if subtitle else ""
            st.markdown(
                f'<div class="ir-panel-head"><div><h3>{ico}{escape(title)}</h3>{sub}</div>'
                f"<div>{right or ''}</div></div>",
                unsafe_allow_html=True,
            )
        yield box


def pill(key: str, text: str | None = None) -> str:
    tone, label = PILLS.get(key, ("slate", key))
    bg, fg = TONES[tone]
    return (
        f'<span class="ir-pill" style="background:{bg};color:{fg}">{escape(text or label)}</span>'
    )


def chip(text: str, colour: str) -> str:
    """Solid label that always carries its text, never colour alone."""
    return f'<span class="ir-chip" style="background:{colour}">{escape(text)}</span>'


@dataclass
class Col:
    key: str
    label: str
    fmt: Any = None
    """Callable(value, row) -> HTML string. Defaults to escaped text."""
    num: bool = False
    strong: bool = False


def table(rows: list[dict[str, Any]], cols: Sequence[Col], empty: str = "No rows.") -> str:
    """An HTML table in the house style (pills and formatted numbers allowed in cells)."""
    if not rows:
        return empty_state(empty)
    head = "".join(f'<th class="{"num" if c.num else ""}">{escape(c.label)}</th>' for c in cols)
    body = []
    for row in rows:
        cells = []
        for c in cols:
            value = row.get(c.key)
            html = c.fmt(value, row) if c.fmt else escape("–" if value is None else str(value))
            classes = " ".join(
                x for x in ("num" if c.num else "", "strong" if c.strong else "") if x
            )
            cells.append(f'<td class="{classes}">{html}</td>')
        body.append(f"<tr>{''.join(cells)}</tr>")
    return (
        f'<div class="ir-table-wrap"><table class="ir-table"><thead><tr>{head}</tr></thead>'
        f"<tbody>{''.join(body)}</tbody></table></div>"
    )


def empty_state(text: str, icon_name: str = "clipboard") -> str:
    return f'<div class="ir-empty">{icon(icon_name, 28)}<div>{escape(text)}</div></div>'


@dataclass
class Bar:
    name: str
    sub: str
    value: float | None
    """0 to 1."""
    label: str
    icon_name: str
    tone: str
    colour: str = field(default=SERIES[0])


def bars(items: Sequence[Bar], marker: float | None = 0.75) -> str:
    """Horizontal bar list with icon, name, explanation, bar and value label."""
    out = []
    for b in items:
        bg, fg = TONES[b.tone]
        width = 0 if b.value is None or b.value != b.value else max(2, min(100, b.value * 100))
        mark = f'<div class="ir-bar-mark" style="left:{marker * 100:.0f}%"></div>' if marker else ""
        out.append(
            f'<div class="ir-bar-row"><div class="ico" style="background:{bg};color:{fg}">'
            f'{icon(b.icon_name, 20)}</div><div><div class="name">{escape(b.name)}</div>'
            f'<div class="sub">{escape(b.sub)}</div></div><div><div class="ir-bar-track">'
            f'<div class="ir-bar-fill" style="width:{width:.0f}%;background:{b.colour}"></div>'
            f'{mark}</div><div class="ir-bar-val">{escape(b.label)}</div></div></div>'
        )
    return "".join(out)


def timeline(items: Sequence[tuple[str, str, str, str]]) -> str:
    """(when, what, why, tone) entries, newest first."""
    if not items:
        return empty_state("Nothing recorded yet.", "clock")
    rows = "".join(
        f'<li><span class="dot" style="background:{TONES[tone][1]}"></span><div>'
        f'<div class="when">{escape(when)}</div><div class="what">{escape(what)}</div>'
        f'<div class="why">{escape(why)}</div></div></li>'
        for when, what, why, tone in items
    )
    return f'<ul class="ir-timeline">{rows}</ul>'


def note(text: str) -> None:
    st.markdown(f'<div class="ir-note">{escape(text)}</div>', unsafe_allow_html=True)


def side_label(text: str) -> None:
    st.markdown(f'<div class="ir-side-label">{escape(text)}</div>', unsafe_allow_html=True)


# --- formatting ---------------------------------------------------------------------------
def text(value: object) -> str:
    """A free-text cell from a DataFrame: missing values (None or NaN) become ''."""
    return value if isinstance(value, str) else ""


def fmt_int(x: float | None) -> str:
    return "–" if x is None or x != x else f"{round(x):,}"


def fmt_pct(x: float | None, digits: int = 0) -> str:
    return "–" if x is None or x != x else f"{x * 100:.{digits}f}%"


def ordinal(n: int) -> str:
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"
