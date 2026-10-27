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
from irerero.ui.i18n import t

ASSETS = ROOT / "app" / "assets"
# Streamlit Community Cloud runs apps from /mount/src and draws its own buttons over the
# top right corner, so the account button moves left of them there.
ON_COMMUNITY_CLOUD = str(ROOT).startswith("/mount/src/")
LOGO = ASSETS / "logo.png"
LOGO_LIGHT = ASSETS / "logo-light.png"
ICON = ASSETS / "icon.png"
ICON_LIGHT = ASSETS / "icon-light.png"

# --- tokens -------------------------------------------------------------------------------
# Brand: navy for navigation and headings, teal for actions and positive indicators, gold for
# targets. TEAL (brand) passes 3:1 for icons, tracks and chart marks; TEAL_700 carries filled
# buttons, the active nav item and teal text (5.3:1 with white).
NAVY = "#0B2E50"
NAVY_900 = NAVY  # sidebar
NAVY_700 = "#14406B"
TEAL = "#169B83"
TEAL_700 = "#0F7A67"
GOLD = "#ECA837"
GOLD_700 = "#8A5A00"
INK = "#0F1B2A"
SLATE = "#5B6B7C"
SLATE_300 = "#CBD5E1"
BORDER = "#DDE3EA"
SURFACE = "#FFFFFF"
CANVAS = "#F4F7FB"
SIM_RED = "#B42318"
FOCUS = NAVY  # focus ring on light surfaces; gold on the navy sidebar

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
    "UNCLEAR": ("slate", "Unclear"),
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
# Spacing follows an 8px scale (--s1 8px ... --s4 32px). Cards pad 20px; Streamlit's own gap
# between blocks and columns is 16px. Sizes are in px so they do not drift with the root size.
CSS = f"""
<style>
  :root {{
    --ir-navy: {NAVY}; --ir-teal: {TEAL}; --ir-teal-700: {TEAL_700}; --ir-gold: {GOLD};
    --ir-ink: {INK}; --ir-slate: {SLATE}; --ir-border: {BORDER}; --ir-canvas: {CANVAS};
    --s1: 8px; --s2: 16px; --s3: 24px; --s4: 32px;
    --ir-radius: 12px; --ir-radius-sm: 8px;
    --ir-shadow: 0 1px 2px rgba(16,24,40,.05);
    --ir-sidebar: 248px;
  }}
  .stApp {{ background: {CANVAS}; color: {INK}; }}
  .stApp h1, .stApp h2, .stApp h3, .stApp h4 {{ color: {NAVY}; letter-spacing: -.01em; }}
  header[data-testid="stHeader"] {{ background: transparent; }}
  .block-container, [data-testid="stMainBlockContainer"] {{
    padding: var(--s3) var(--s4) 48px; max-width: 1440px;
  }}

  /* sidebar: 248px, one icon column, 40px rows */
  section[data-testid="stSidebar"][data-collapsed="false"] {{
    width: var(--ir-sidebar) !important; min-width: var(--ir-sidebar) !important;
    max-width: var(--ir-sidebar) !important;
  }}
  section[data-testid="stSidebar"] {{ border-right: 0; }}
  section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {{ padding: 0 0 var(--s3); }}
  section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {{
    padding: var(--s2) var(--s2) var(--s3);
  }}
  section[data-testid="stSidebar"] [data-testid="stSidebarHeader"] {{ padding: var(--s2) var(--s2) var(--s1); margin: 0; }}
  section[data-testid="stSidebar"] [data-testid="stSidebarNav"] {{ padding: 0 var(--s1); }}
  [data-testid="stSidebarLogo"], [data-testid="stHeaderLogo"] {{ height: 32px; max-width: 180px; }}
  section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a {{
    border-radius: var(--ir-radius-sm); margin: 2px 0; padding: 0 12px; min-height: 40px;
    gap: 12px; align-items: center;
  }}
  /* Kinyarwanda names are longer: menu entries wrap instead of being cut (English fits as is) */
  [data-testid="stSidebarNav"] a [data-testid="stMarkdownContainer"],
  [data-testid="stSidebarNav"] a [data-testid="stMarkdownContainer"] p,
  [data-testid="stNavSectionHeader"] > span,
  [data-testid="stNavSectionHeader"] [data-testid="stMarkdownContainer"],
  [data-testid="stNavSectionHeader"] [data-testid="stMarkdownContainer"] p {{
    white-space: normal; overflow: visible; text-overflow: clip;
  }}
  section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a span {{
    color: #D6E2EE; font-weight: 500; font-size: 14px;
  }}
  section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a:hover {{
    background: rgba(255,255,255,.08);
  }}
  section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[aria-current="page"] {{
    background: {TEAL_700}; box-shadow: inset 3px 0 0 {TEAL};
  }}
  section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[aria-current="page"] span {{
    color: #fff; font-weight: 600;
  }}
  [data-testid="stNavSectionHeader"] {{ padding: 0 12px; margin-top: var(--s2); }}
  [data-testid="stNavSectionHeader"] p, [data-testid="stNavSectionHeader"] span {{
    color: #A9BCD0 !important; font-size: 12px; font-weight: 600; text-transform: uppercase;
    letter-spacing: .08em;
  }}
  section[data-testid="stSidebar"] [data-testid="stSidebarNavSeparator"] {{
    border-color: rgba(255,255,255,.12);
  }}
  section[data-testid="stSidebar"] header [data-testid="stSidebarNavSeparator"] {{ display:none; }}
  section[data-testid="stSidebar"] [role="radiogroup"] label {{ min-height: 32px; align-items: center; }}
  section[data-testid="stSidebar"] [role="radiogroup"] label p {{ font-size: 14px; }}
  section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {{ color: #D6E2EE; }}
  .ir-side-label {{
    color: #A9BCD0; font-size: 12px; font-weight: 600; text-transform: uppercase;
    letter-spacing: .08em; margin: var(--s1) 0 4px;
  }}
  .ir-side-note {{ color: #A9BCD0; font-size: 12px; line-height: 1.45; }}

  /* focus: always visible, 2px, never colour alone */
  .stApp a:focus-visible, .stApp button:focus-visible, .stApp [role="radio"]:focus-visible,
  .stApp [role="switch"]:focus-visible, .stApp [role="slider"]:focus-visible,
  .stApp [role="tab"]:focus-visible, .stApp summary:focus-visible,
  .stApp input:focus-visible, .stApp textarea:focus-visible {{
    outline: 2px solid {FOCUS} !important; outline-offset: 2px;
  }}
  .stApp [data-baseweb="select"] > div:focus-within {{
    outline: 2px solid {FOCUS}; outline-offset: 1px;
  }}
  section[data-testid="stSidebar"] a:focus-visible, section[data-testid="stSidebar"] button:focus-visible,
  section[data-testid="stSidebar"] [role="radio"]:focus-visible,
  section[data-testid="stSidebar"] [data-baseweb="select"] > div:focus-within {{
    outline: 2px solid {GOLD} !important; outline-offset: 2px;
  }}

  /* widgets: labels stay readable when a control is locked to the user's area */
  .stApp [data-testid="stWidgetLabel"] {{ min-height: 24px; }}
  .stApp [data-testid="stWidgetLabel"] p {{ font-size: 14px; font-weight: 500; color: {INK}; }}
  .stApp [data-testid="stSelectbox"] input[data-disabled="true"],
  .stApp [data-testid="stSelectbox"] input:disabled {{
    color: {SLATE}; -webkit-text-fill-color: {SLATE}; opacity: 1;
  }}
  .stApp [data-baseweb="select"] > div {{ min-height: 40px; }}
  .stButton button, .stDownloadButton button, .stFormSubmitButton button {{
    border-radius: var(--ir-radius-sm); font-weight: 600; min-height: 40px; padding: 0 var(--s2);
  }}
  .stApp [data-testid="stPageLink"] a {{ min-height: 32px; padding: 0 4px; }}
  .stApp [data-testid="stPageLink"] a p {{ color: {TEAL_700}; font-weight: 600; font-size: 14px; }}
  [data-testid="stDataFrame"] {{ border-radius: var(--ir-radius-sm); overflow: hidden; }}
  .stApp [data-testid="stExpander"] details {{
    background: {SURFACE}; border-color: {BORDER}; border-radius: var(--ir-radius-sm);
  }}
  .stApp [data-testid="stTabs"] [role="tab"] {{ min-height: 40px; }}

  /* body text inside cards: 14px, one line height, 8px between paragraphs */
  .stApp [class*="st-key-ir-"] [data-testid="stMarkdownContainer"] p,
  .stApp [class*="st-key-ir-"] [data-testid="stMarkdownContainer"] li {{
    font-size: 14px; line-height: 1.55;
  }}
  .stApp [class*="st-key-ir-"] [data-testid="stMarkdownContainer"] p {{ margin-bottom: 8px; }}
  .stApp [class*="st-key-ir-"] [data-testid="stMarkdownContainer"] h4 {{
    font-size: 16px; font-weight: 600; padding: 4px 0 0;
  }}
  ul.ir-list {{ margin: 0 0 4px; padding-left: 20px; }}
  ul.ir-list li {{ margin: 0 0 6px; }}
  .ir-sub {{ color: {INK}; font-size: 14px; font-weight: 600; margin: 8px 0 4px; }}
  ol.ir-sources {{ margin: 0; padding-left: 0; list-style: none; color: {SLATE};
    font-size: 13px; line-height: 1.6; }}

  /* Streamlit alerts in the notice style */
  .stApp [data-testid="stAlert"] [data-testid="stAlertContainer"] {{
    border-radius: var(--ir-radius-sm); padding: 10px 14px;
  }}
  .stApp [data-testid="stAlert"] [data-testid="stMarkdownContainer"] p {{
    font-size: 14px; line-height: 1.5; margin: 0;
  }}

  /* cards: every keyed container (theme.panel) is a white card, 20px padding */
  .stApp [class*="st-key-ir-"] {{
    background: {SURFACE}; border: 1px solid {BORDER}; border-radius: var(--ir-radius);
    box-shadow: var(--ir-shadow); padding: 20px; box-sizing: border-box;
  }}
  .stApp [class*="st-key-ir-"] [class*="st-key-ir-"] {{ box-shadow: none; padding: var(--s2); }}

  /* one row, one height: cards in the same row of columns fill the row */
  [data-testid="stColumn"] > [data-testid="stVerticalBlock"] {{ height: 100%; }}
  [data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [data-testid="stLayoutWrapper"]:last-child:has(> [class*="st-key-ir-"]) {{
    flex: 1 1 auto;
  }}
  [data-testid="stLayoutWrapper"] > [class*="st-key-ir-"] {{ height: 100%; }}
  [data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"]:has(.ir-fill) {{
    flex: 1 1 auto;
  }}
  [data-testid="stElementContainer"]:has(.ir-fill) > div,
  [data-testid="stElementContainer"]:has(.ir-fill) > div > div,
  [data-testid="stMarkdownContainer"]:has(> .ir-fill) {{ height: 100%; }}

  /* top bar: one line, the breadcrumb and a small account button */
  .stApp .st-key-topbar, .stApp .st-key-topbar-cloud {{
    gap: var(--s2); min-height: 32px; padding-bottom: var(--s1);
    border-bottom: 1px solid {BORDER}; margin-bottom: var(--s1); flex-wrap: nowrap;
  }}
  /* Community Cloud overlays Share, star and edit at the top right of the app */
  .stApp .st-key-topbar-cloud {{ padding-right: 168px; }}
  .ir-crumbs {{ color: {SLATE}; font-size: 13px; min-width: 0; flex: 1;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
  .ir-crumbs span {{ margin-right: 6px; }}
  .ir-crumbs .sep {{ color: {SLATE_300}; }}
  .ir-crumbs .here {{ color: {INK}; font-weight: 600; }}
  .ir-crumbs .app {{ color: {SLATE}; font-weight: 600; letter-spacing: .08em;
    text-transform: uppercase; font-size: 12px; margin-right: 10px; }}
  /* the account button: a navy circle with the role's initials; it opens the account card */
  .stApp .st-key-account button {{ width: 32px; height: 32px; min-height: 32px; padding: 0;
    border-radius: 50%; border: 0; background: {NAVY}; color: #fff; font-weight: 700;
    font-size: 12px; transition: box-shadow .15s; }}
  .stApp .st-key-account button p {{ font-size: 12px; font-weight: 700; color: #fff; }}
  .stApp .st-key-account button div[aria-hidden="true"] {{ display: none; }}
  .stApp .st-key-account button:hover {{ box-shadow: 0 0 0 3px #D6E2EE; color: #fff; }}
  .stApp .st-key-account button:focus-visible {{ box-shadow: 0 0 0 3px {TEAL_700}; }}
  [data-testid="stPopoverBody"]:has(.ir-account) {{ width: 280px !important;
    min-width: 0 !important; max-width: calc(100vw - 32px) !important; }}
  .ir-account {{ line-height: 1.4; margin-bottom: 4px; }}
  .ir-account b {{ display: block; color: {INK}; font-size: 14px; font-weight: 600; }}
  .ir-account span {{ display: block; color: {SLATE}; font-size: 13px; }}
  .ir-account .note {{ margin-top: 8px; padding-top: 8px; border-top: 1px solid {BORDER};
    font-size: 12px; }}
  .stApp [data-testid="stMarkdownContainer"] h1.ir-title {{
    font-size: 32px; font-weight: 700; color: {NAVY}; margin: 0; padding: 0;
    letter-spacing: -.02em; line-height: 1.2; text-wrap: balance;
  }}
  .ir-subtitle {{ color: {SLATE}; font-size: 15px; line-height: 1.5; margin: 4px 0 4px; }}
  .ir-tag {{ display: inline-block; vertical-align: middle; margin-left: 12px; font-size: 12px;
    font-weight: 600; padding: 2px 8px; border-radius: 999px; letter-spacing: 0; }}

  /* notices: compact, one style, icon + words */
  .ir-notice {{ display: flex; gap: 10px; align-items: flex-start; font-size: 13px;
    line-height: 1.5; padding: 10px 14px; border-radius: var(--ir-radius-sm); border: 1px solid; }}
  .ir-notice .ir-icon {{ flex: none; margin-top: 1px; }}
  .ir-scope {{ background: #EEF6F3; border-color: #CFE7E0; color: {INK}; }}
  .ir-scope .ir-icon {{ color: {TEAL_700}; }}
  .ir-banner {{ background: #FEF3F2; border-color: #F5C2BC; color: #7A271A;
    box-shadow: inset 3px 0 0 {SIM_RED}; }}
  .ir-banner .ir-icon {{ color: {SIM_RED}; }}
  .ir-callout {{ border-radius: var(--ir-radius); padding: var(--s2) 20px; border: 1px solid; }}
  .ir-target {{ background: #FDF6E7; border-color: #F3DDB0; display: flex; gap: var(--s2);
    align-items: center; }}
  .ir-target .ico {{ color: {GOLD_700}; flex: none; display: flex; }}
  .ir-target .label {{ font-weight: 600; color: {INK}; font-size: 14px; }}
  .ir-target .detail {{ color: {SLATE}; font-size: 13px; }}
  .ir-target .value {{ font-weight: 700; color: {NAVY}; font-size: 24px; line-height: 1.2;
    margin-top: 2px; white-space: nowrap; }}

  /* badges, pills, chips: always a word */
  .ir-badge {{ display: inline-block; padding: 1px 6px; border-radius: 4px;
    font-size: 11px; font-weight: 700; letter-spacing: .04em; vertical-align: middle;
    line-height: 1.5; white-space: nowrap; }}
  .ir-sim {{ background: {SIM_RED}; color: #fff; }}
  .ir-status {{ background: #E6EDF3; color: {NAVY}; font-weight: 600; }}
  .ir-pill {{ display: inline-block; padding: 2px 8px; border-radius: 6px; font-size: 12px;
    font-weight: 600; white-space: nowrap; line-height: 1.5; }}
  .ir-chip {{ display: inline-block; border-radius: 999px; padding: 2px 10px; font-size: 12px;
    font-weight: 600; color: #fff; }}
  .ir-num {{ border-bottom: 1px dotted {SLATE}; cursor: help; }}
  .ir-note {{ color: {SLATE}; font-size: 13px; line-height: 1.5; }}

  /* KPI cards: icon + label, value, detail, then source and status pinned to the bottom */
  .ir-kpi, .ir-card {{ background: {SURFACE}; border: 1px solid {BORDER};
    border-radius: var(--ir-radius); padding: 20px; display: flex; flex-direction: column;
    height: 100%; box-sizing: border-box; box-shadow: var(--ir-shadow); min-width: 0; }}
  .ir-kpi .head {{ display: flex; gap: 12px; align-items: center; min-height: 40px;
    margin-bottom: 12px; }}
  .ir-kpi .ico {{ width: 40px; height: 40px; border-radius: 10px; display: flex; flex: none;
    align-items: center; justify-content: center; }}
  .ir-kpi .label, .ir-card .label {{ color: {INK}; font-size: 14px; font-weight: 600;
    line-height: 1.35; }}
  .ir-kpi .value, .ir-card .value {{ color: {NAVY}; font-size: 28px; font-weight: 700;
    line-height: 1.15; letter-spacing: -.02em; font-variant-numeric: tabular-nums;
    overflow-wrap: anywhere; }}
  .ir-kpi .detail, .ir-card .range {{ color: {SLATE}; font-size: 13px; line-height: 1.45;
    margin-top: 4px; }}
  .ir-kpi .src, .ir-card .src {{ color: {SLATE}; font-size: 12px; line-height: 1.4;
    margin-top: auto; padding-top: 12px; display: flex; flex-wrap: wrap; gap: 4px 8px;
    align-items: center; }}
  .ir-card {{ padding: var(--s2); }}
  .ir-card .label {{ color: {SLATE}; font-weight: 500; }}
  .ir-card .value {{ font-size: 24px; margin-top: 4px; }}
  .ir-alert {{ height: 100%; box-sizing: border-box; display: flex; flex-direction: column;
    gap: var(--s1); }}
  .ir-alert .title {{ display: flex; gap: var(--s1); align-items: center; font-weight: 700;
    font-size: 16px; }}
  .ir-alert .body {{ color: {INK}; font-size: 14px; line-height: 1.5; }}
  .ir-alert .also {{ color: {INK}; font-size: 13px; line-height: 1.5; margin-top: var(--s1);
    padding-top: var(--s1); border-top: 1px solid rgba(15,27,42,.08); }}

  /* stat strip: a headline figure split into cells (Action plans banner) */
  .ir-strip {{ display: grid; grid-template-columns: minmax(260px, 2fr) repeat(3, minmax(140px, 1fr));
    gap: var(--s2); align-items: center; }}
  .ir-strip .lead {{ display: flex; gap: var(--s2); align-items: center; }}
  .ir-strip .lead b {{ color: {NAVY}; font-size: 18px; font-weight: 700; line-height: 1.3;
    display: block; }}
  .ir-strip .cell {{ border-left: 1px solid #CFE7E0; padding-left: var(--s2); }}
  .ir-strip .cell .v {{ color: {NAVY}; font-size: 24px; font-weight: 700; line-height: 1.2;
    font-variant-numeric: tabular-nums; }}

  /* panel headers */
  .ir-panel-head {{ display: flex; justify-content: space-between; align-items: flex-start;
    gap: 12px; }}
  .ir-panel-head h3 {{ margin: 0; padding: 0; font-size: 18px; font-weight: 600; line-height: 1.35;
    color: {NAVY}; display: flex; gap: var(--s1); align-items: center; }}
  .ir-panel-head h3 svg.ir-icon {{ margin-right: 8px; vertical-align: -3px; flex: none; }}
  .ir-panel-head p {{ margin: 4px 0 0; color: {SLATE}; font-size: 13px; line-height: 1.45; }}

  /* tables: wrap headers instead of hiding columns */
  .ir-table-wrap {{ overflow-x: auto; border: 1px solid {BORDER}; border-radius: var(--ir-radius-sm); }}
  table.ir-table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
  table.ir-table th {{ background: #F7F9FB; color: {INK}; font-weight: 600; font-size: 12px;
    text-align: left; padding: 10px 12px; border-bottom: 1px solid {BORDER};
    line-height: 1.3; vertical-align: bottom; }}
  table.ir-table td {{ padding: 10px 12px; border-bottom: 1px solid #EEF2F6; color: {INK};
    vertical-align: middle; line-height: 1.45; }}
  table.ir-table tr:last-child td {{ border-bottom: 0; }}
  table.ir-table tbody tr:hover td {{ background: #FAFCFD; }}
  table.ir-table .num {{ text-align: right; font-variant-numeric: tabular-nums;
    white-space: nowrap; }}
  table.ir-table th.num {{ white-space: normal; }}
  table.ir-table .strong {{ font-weight: 600; }}
  table.ir-table .muted {{ color: {SLATE}; }}
  table.ir-table code {{ font-size: 12px; background: #EEF2F6; color: {INK}; padding: 1px 6px;
    border-radius: 4px; white-space: nowrap; }}

  /* factor bars */
  .ir-bar-row {{ display: grid; grid-template-columns: 40px 1fr 42%; gap: 12px;
    align-items: center; padding: 10px 0; border-bottom: 1px solid #EEF2F6; }}
  .ir-bar-row:last-child {{ border-bottom: 0; }}
  .ir-bar-row .ico {{ width: 36px; height: 36px; border-radius: 10px; display: flex;
    align-items: center; justify-content: center; }}
  .ir-bar-row .name {{ font-weight: 600; color: {INK}; font-size: 14px; }}
  .ir-bar-row .sub {{ color: {SLATE}; font-size: 12px; line-height: 1.4; }}
  .ir-bar-track {{ background: #EEF2F6; border-radius: 6px; height: 10px; position: relative; }}
  .ir-bar-fill {{ height: 10px; border-radius: 6px; }}
  .ir-bar-mark {{ position: absolute; top: -4px; width: 2px; height: 18px; background: {SLATE};
    left: 75%; }}
  .ir-bar-val {{ font-size: 12px; color: {INK}; margin-top: 4px; font-weight: 600; }}

  /* timeline */
  .ir-timeline {{ margin: 0; padding: 0; list-style: none; }}
  .ir-timeline li {{ display: grid; grid-template-columns: 14px 1fr; gap: 10px;
    padding: var(--s1) 0; border-bottom: 1px solid #EEF2F6; }}
  .ir-timeline li:last-child {{ border-bottom: 0; }}
  .ir-timeline .dot {{ width: 10px; height: 10px; border-radius: 50%; margin-top: 6px; }}
  .ir-timeline .when {{ color: {SLATE}; font-size: 12px; }}
  .ir-timeline .what {{ color: {INK}; font-size: 14px; font-weight: 600; }}
  .ir-timeline .why {{ color: {SLATE}; font-size: 13px; }}

  .ir-empty {{ text-align: center; color: {SLATE}; padding: var(--s3) var(--s2); font-size: 14px;
    display: flex; flex-direction: column; align-items: center; gap: var(--s1); }}
  .ir-empty .ir-icon {{ color: #9AA8B7; }}

  /* motion: few, short, and only where it says something. Entrances play when an element first
     appears (a new screen, a new result); Streamlit keeps unchanged elements on a rerun, so they
     do not replay when a slider moves. */
  @keyframes ir-rise {{ from {{ opacity: 0; transform: translateY(6px); }}
    to {{ opacity: 1; transform: none; }} }}
  @keyframes ir-fade {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
  @keyframes ir-grow {{ from {{ transform: scaleX(0); }} to {{ transform: scaleX(1); }} }}
  .ir-title, .ir-subtitle {{ animation: ir-fade .25s ease-out both; }}
  .stApp [class*="st-key-ir-"], .ir-kpi {{ animation: ir-rise .32s cubic-bezier(.2,.8,.2,1) both; }}
  .stApp [class*="st-key-ir-"] [class*="st-key-ir-"] {{ animation: none; }}
  [data-testid="stColumn"]:nth-child(2) .ir-kpi {{ animation-delay: .05s; }}
  [data-testid="stColumn"]:nth-child(3) .ir-kpi {{ animation-delay: .1s; }}
  [data-testid="stColumn"]:nth-child(4) .ir-kpi {{ animation-delay: .15s; }}
  /* bars grow to their value, so the eye reads the length, not just the end state */
  .ir-bar-fill {{ transform-origin: left; animation: ir-grow .7s cubic-bezier(.2,.8,.2,1) .1s both;
    transition: width .5s cubic-bezier(.2,.8,.2,1); }}  /* another sector: bars move, not jump */
  .ir-bar-row:nth-child(2) .ir-bar-fill {{ animation-delay: .16s; }}
  .ir-bar-row:nth-child(3) .ir-bar-fill {{ animation-delay: .22s; }}
  .ir-bar-row:nth-child(4) .ir-bar-fill {{ animation-delay: .28s; }}
  .ir-bar-row:nth-child(5) .ir-bar-fill {{ animation-delay: .34s; }}
  /* the result of an action (saved, refused, suggested) arrives visibly */
  .stApp [data-testid="stAlert"] {{ animation: ir-rise .28s cubic-bezier(.2,.8,.2,1) both; }}
  /* a decision just recorded: its entry glows once. Two identical animations alternate, so the
     glow restarts on the next decision even though Streamlit reuses the list item. */
  @keyframes ir-fresh-a {{ from {{ background: #D5EFE7; }} to {{ background: transparent; }} }}
  @keyframes ir-fresh-b {{ from {{ background: #D5EFE7; }} to {{ background: transparent; }} }}
  .ir-timeline li.ir-fresh-a {{ animation: ir-fresh-a 2s ease-out; }}
  .ir-timeline li.ir-fresh-b {{ animation: ir-fresh-b 2s ease-out; }}
  /* controls answer the pointer */
  .stButton button, .stDownloadButton button, .stFormSubmitButton button {{
    transition: background-color .15s ease, border-color .15s ease, box-shadow .15s ease,
      transform .1s ease;
  }}
  .stButton button:hover, .stDownloadButton button:hover, .stFormSubmitButton button:hover {{
    box-shadow: 0 2px 6px rgba(16,24,40,.12);
  }}
  .stButton button:active, .stDownloadButton button:active, .stFormSubmitButton button:active {{
    transform: scale(.98); box-shadow: none;
  }}
  section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a {{
    transition: background-color .15s ease;
  }}
  table.ir-table td {{ transition: background-color .12s ease; }}
  @media (prefers-reduced-motion: reduce) {{
    .stApp *, .stApp *::before, .stApp *::after {{
      animation: none !important; transition: none !important;
    }}
  }}
  @media print {{
    .stApp * {{ animation: none !important; transition: none !important; }}
  }}

  /* --- IrereroAI assistant ------------------------------------------------------------ */
  .ir-sr {{ position: absolute !important; width: 1px; height: 1px; padding: 0; margin: -1px;
    overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; border: 0; }}
  .stApp [class*="st-key-ir-"].st-key-ir-hero {{ padding: 0; overflow: hidden;
    background: linear-gradient(90deg, #E8EEF5 0%, #F3F6FA 40%, {SURFACE} 100%); }}
  [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .ir-hero-art) {{ gap: 0; flex-wrap: nowrap; }}
  [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .ir-hero-art) > [data-testid="stColumn"]:first-child {{
    flex: 0 0 min(380px, 33%) !important; min-width: 0 !important; }}
  [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .ir-hero-art) > [data-testid="stColumn"]:last-child {{ flex: 1 1 0 !important; min-width: 0 !important; }}
  .ir-hero-art {{ height: 100%; min-height: 300px; background-repeat: no-repeat;
    background-size: cover; background-position: 30% 40%;
    -webkit-mask-image: linear-gradient(90deg, #000 60%, transparent 100%);
    mask-image: linear-gradient(90deg, #000 60%, transparent 100%); }}
  [data-testid="stMarkdownContainer"]:has(> .ir-hero-art) {{ margin-bottom: 0; }}
  .stApp .st-key-hero-body {{ padding: 20px 20px 16px 4px; }}
  .st-key-ir-hero .ir-target .value {{ font-size: clamp(17px, 1.5vw, 20px); white-space: normal; }}
  .st-key-ir-hero .ir-target {{ gap: 12px; padding: 14px 16px; }}
  .ir-greet {{ margin: 4px 0 2px; }}
  .ir-greet .hello {{ color: {SLATE}; font-size: 14px; }}
  .ir-greet .ask {{ color: {NAVY}; font-size: 22px; font-weight: 700; line-height: 1.25; }}
  .ir-greet .sub {{ color: {SLATE}; font-size: 14px; line-height: 1.5; display: flex;
    flex-wrap: wrap; align-items: center; gap: 4px 12px; }}
  .ir-greet .who {{ font-size: 12px; color: {INK}; border: 1px solid {BORDER};
    border-radius: 999px; padding: 1px 10px; background: {SURFACE}; }}

  /* notices: one at a time; auto-rotation pauses on hover or focus and stops once chosen */
  .ir-notices {{ display: flex; flex-direction: column; gap: var(--s1); height: 100%; }}
  .ir-slides {{ display: grid; flex: 1; }}
  .ir-slide {{ grid-area: 1 / 1; display: flex; gap: 10px; align-items: flex-start;
    padding: 12px 14px; border-radius: var(--ir-radius-sm); border: 1px solid #CFE7E0;
    background: #EEF6F3; color: {INK}; font-size: 13px; line-height: 1.5;
    opacity: 0; visibility: hidden; transition: opacity .35s ease, visibility .35s; }}
  .ir-slide.warn {{ background: #FEF3F2; border-color: #F5C2BC; color: #7A271A;
    box-shadow: inset 3px 0 0 {SIM_RED}; }}
  .ir-slide-ico {{ color: {TEAL_700}; flex: none; display: flex; margin-top: 1px; }}
  .ir-slide.warn .ir-slide-ico {{ color: {SIM_RED}; }}
  .ir-notices.single .s1,
  .ir-notices:not(:has(input:checked)) .s1,
  #irn-1:checked ~ .ir-slides .s1, #irn-2:checked ~ .ir-slides .s2 {{
    opacity: 1; visibility: visible; }}
  .ir-notice-tabs {{ display: flex; flex-wrap: wrap; gap: var(--s1); }}
  .ir-notice-tabs label {{ display: inline-flex; align-items: center; gap: 6px;
    min-height: 28px; padding: 2px 12px; border-radius: 999px; border: 1px solid {BORDER};
    background: {SURFACE}; color: {SLATE}; font-size: 12px; font-weight: 600;
    cursor: pointer; }}
  .ir-notice-tabs .dot {{ width: 8px; height: 8px; border-radius: 50%; background: {SLATE_300}; }}
  .ir-notices:not(:has(input:checked)) .t1,
  #irn-1:checked ~ .ir-notice-tabs .t1 {{ color: {INK}; border-color: {TEAL_700}; }}
  .ir-notices:not(:has(input:checked)) .t1 .dot,
  #irn-1:checked ~ .ir-notice-tabs .t1 .dot {{ background: {TEAL_700}; }}
  #irn-2:checked ~ .ir-notice-tabs .t2 {{ color: {INK}; border-color: {SIM_RED}; }}
  #irn-2:checked ~ .ir-notice-tabs .t2 .dot {{ background: {SIM_RED}; }}
  #irn-1:focus-visible ~ .ir-notice-tabs .t1, #irn-2:focus-visible ~ .ir-notice-tabs .t2 {{
    outline: 2px solid {FOCUS}; outline-offset: 2px; }}
  @media (prefers-reduced-motion: no-preference) {{
    .ir-notices:not(:has(input:checked)) .s1 {{ animation: irn-show-a 16s infinite; }}
    .ir-notices:not(:has(input:checked)) .s2 {{ animation: irn-show-b 16s infinite; }}
    .ir-notices:not(:has(input:checked)) .t1 {{ animation: irn-tab-a 16s infinite; }}
    .ir-notices:not(:has(input:checked)) .t2 {{ animation: irn-tab-b 16s infinite; }}
    .ir-notices:not(:has(input:checked)) .t1 .dot {{ animation: irn-dot-a 16s infinite; }}
    .ir-notices:not(:has(input:checked)) .t2 .dot {{ animation: irn-dot-b 16s infinite; }}
    .ir-notices:hover *, .ir-notices:focus-within * {{ animation-play-state: paused !important; }}
  }}
  @keyframes irn-show-a {{ 0%, 46% {{ opacity: 1; visibility: visible; }}
    50%, 96% {{ opacity: 0; visibility: hidden; }} 100% {{ opacity: 1; visibility: visible; }} }}
  @keyframes irn-show-b {{ 0%, 46% {{ opacity: 0; visibility: hidden; }}
    50%, 96% {{ opacity: 1; visibility: visible; }} 100% {{ opacity: 0; visibility: hidden; }} }}
  @keyframes irn-tab-a {{ 0%, 48% {{ color: {INK}; border-color: {TEAL_700}; }}
    50%, 98% {{ color: {SLATE}; border-color: {BORDER}; }} }}
  @keyframes irn-tab-b {{ 0%, 48% {{ color: {SLATE}; border-color: {BORDER}; }}
    50%, 98% {{ color: {INK}; border-color: {SIM_RED}; }} }}
  @keyframes irn-dot-a {{ 0%, 48% {{ background: {TEAL_700}; }} 50%, 98% {{ background: {SLATE_300}; }} }}
  @keyframes irn-dot-b {{ 0%, 48% {{ background: {SLATE_300}; }} 50%, 98% {{ background: {SIM_RED}; }} }}

  /* question box and conversation */
  .stApp [data-testid="stChatInput"] > div {{ border-radius: var(--ir-radius);
    border: 1px solid {BORDER}; background: {SURFACE}; box-shadow: var(--ir-shadow); }}
  .stApp [data-testid="stChatInput"]:focus-within > div {{ border-color: {NAVY};
    box-shadow: 0 0 0 1px {NAVY}; }}
  .stApp [data-testid="stChatInput"] textarea {{ font-size: 15px; }}
  .stApp [data-testid="stChatInputSubmitButton"] {{ background: {TEAL_700}; color: #fff;
    border-radius: var(--ir-radius-sm); }}
  .stApp [data-testid="stChatInputSubmitButton"] svg {{ color: #fff; fill: #fff; }}
  .stApp [data-testid="stChatInputSubmitButton"]:disabled {{ background: #DDE3EA;
    color: {SLATE}; }}
  .stApp [data-testid="stChatInputSubmitButton"]:disabled svg {{ color: {SLATE}; fill: {SLATE}; }}
  .stApp [data-testid="stChatMessage"] {{ padding: 12px 14px; border-radius: var(--ir-radius);
    gap: 12px; margin-bottom: var(--s1); background: {SURFACE}; border: 1px solid {BORDER}; }}
  .stApp [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarCustom"]) {{
    background: #EEF2F7; border-color: #EEF2F7; }}
  .stApp [data-testid="stChatMessageAvatarCustom"] {{ background: {NAVY}; color: #fff;
    border-radius: 50%; }}
  .stApp [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] p,
  .stApp [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] li {{
    font-size: 14px; line-height: 1.6; }}
  .ir-typing {{ display: flex; align-items: center; gap: 6px; color: {SLATE}; font-size: 13px;
    min-height: 24px; }}
  .ir-typing span {{ width: 6px; height: 6px; border-radius: 50%; background: {TEAL};
    animation: ir-blink 1.2s infinite both; }}
  .ir-typing span:nth-child(2) {{ animation-delay: .2s; }}
  .ir-typing span:nth-child(3) {{ animation-delay: .4s; margin-right: 4px; }}
  @keyframes ir-blink {{ 0%, 80%, 100% {{ opacity: .25; }} 40% {{ opacity: 1; }} }}
  @media (prefers-reduced-motion: reduce) {{ .ir-typing span {{ animation: none; opacity: .6; }} }}
  .stApp .st-key-ask-entry {{ display: flex; justify-content: flex-end; }}
  .stApp [data-testid="stDialog"] [role="dialog"] {{ border-radius: var(--ir-radius); }}

  /* a collapsed sidebar leaves the logo and the open button floating over the page: give
     their band the page colour, so content scrolls under a bar instead of through the logo */
  .stApp:has(section[data-testid="stSidebar"][data-collapsed="true"]) header[data-testid="stHeader"] {{
    background: {CANVAS}; box-shadow: 0 1px 0 {BORDER};
  }}
  .stApp:has(section[data-testid="stSidebar"][data-collapsed="true"]) .block-container,
  .stApp:has(section[data-testid="stSidebar"][data-collapsed="true"]) [data-testid="stMainBlockContainer"] {{
    padding-top: 64px;
  }}

  /* chart legends in HTML, so they wrap on a phone instead of being clipped */
  .ir-legend {{ display: flex; flex-wrap: wrap; gap: 4px 16px; margin: 4px 0 0; font-size: 12px;
    color: {INK}; align-items: center; }}
  .ir-legend span {{ display: inline-flex; align-items: center; gap: 6px; }}
  .ir-legend i {{ display: inline-block; width: 18px; height: 0; border-top: 3px solid; }}
  .ir-legend i.dash {{ border-top-style: dashed; }}
  .ir-legend i.diamond {{ width: 9px; height: 9px; border: 0; transform: rotate(45deg); }}

  /* laptop: a little less cell padding so wide tables (the sector ranking) fit at 1280px */
  @media (max-width: 1366px) {{
    table.ir-table th, table.ir-table td {{ padding-left: 10px; padding-right: 10px; }}
  }}
  /* tablet: KPI rows go 2 by 2 and side-by-side panels stack */
  @media (max-width: 1180px) {{
    .block-container, [data-testid="stMainBlockContainer"] {{ padding-left: var(--s3); padding-right: var(--s3); }}
    [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .ir-kpi) {{ flex-wrap: wrap; }}
    [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .ir-kpi) > [data-testid="stColumn"] {{
      flex: 1 1 calc(50% - 8px) !important; min-width: calc(50% - 8px) !important;
    }}
    [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [data-testid="stLayoutWrapper"] > [class*="st-key-ir-"]) {{
      flex-wrap: wrap;
    }}
    [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [data-testid="stLayoutWrapper"] > [class*="st-key-ir-"]) > [data-testid="stColumn"] {{
      flex: 1 1 100% !important; min-width: 100% !important;
    }}
    .ir-strip {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }}
    .ir-target .value {{ font-size: 20px; }}
  }}
  @media (max-width: 900px) {{
    /* the scene becomes a band across the top, fading into the panel below */
    [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .ir-hero-art) {{ flex-wrap: wrap; }}
    [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .ir-hero-art) > [data-testid="stColumn"]:first-child,
    [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .ir-hero-art) > [data-testid="stColumn"]:last-child {{
      flex: 1 1 100% !important; min-width: 100% !important; }}
    .ir-hero-art {{ min-height: 260px; background-position: 50% 22%;
      -webkit-mask-image: linear-gradient(180deg, #000 72%, transparent 100%);
      mask-image: linear-gradient(180deg, #000 72%, transparent 100%); }}
    .stApp .st-key-hero-body {{ padding: 0 16px 16px; }}
    .ir-strip .lead {{ grid-column: 1 / -1; }}
    .ir-strip .cell:nth-child(2) {{ border-left: 0; padding-left: 0; }}
  }}
  /* narrow phones: zoom in on the robot so it fills the width */
  @media (max-width: 480px) {{
    .ir-hero-art {{ min-height: 300px; background-size: 165% auto; background-position: 62% 12%; }}
  }}
  /* phone: 16px gutters, one column, smaller title */
  @media (max-width: 640px) {{
    .block-container, [data-testid="stMainBlockContainer"] {{
      padding: var(--s3) var(--s2) var(--s4);
    }}
    [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .ir-kpi) > [data-testid="stColumn"] {{
      flex: 1 1 100% !important; min-width: 100% !important;
    }}
    .stApp [data-testid="stMarkdownContainer"] h1.ir-title {{ font-size: 28px; }}
    .ir-subtitle {{ font-size: 15px; }}
    .ir-kpi .value {{ font-size: 26px; }}
    .stApp [class*="st-key-ir-"] {{ padding: var(--s2); }}
    .ir-crumbs .app {{ display: none; }}
    .stApp .st-key-topbar-cloud {{ padding-right: 112px; }}
    .ir-bar-row {{ grid-template-columns: 36px 1fr; }}
    .ir-bar-row > div:last-child {{ grid-column: 1 / -1; }}
    .ir-strip {{ grid-template-columns: 1fr 1fr; }}
    .ir-strip .cell {{ border-left: 0; padding-left: 0; }}
    .ir-greet .ask {{ font-size: 20px; }}
    .stApp .st-key-ask-entry {{ justify-content: flex-start; }}
    table.ir-table {{ font-size: 13px; }}
    table.ir-table th, table.ir-table td {{ padding: var(--s1) 10px; }}
    /* rank and name stay in view while the other columns scroll sideways */
    table.ir-pin th:nth-child(-n+2), table.ir-pin td:nth-child(-n+2) {{ position: sticky;
      z-index: 1; box-sizing: border-box; background: {SURFACE}; }}
    table.ir-pin th:nth-child(-n+2) {{ background: #F7F9FB; }}
    table.ir-pin th:first-child, table.ir-pin td:first-child {{ left: 0; width: 56px;
      min-width: 56px; max-width: 56px; }}
    table.ir-pin th:nth-child(2), table.ir-pin td:nth-child(2) {{ left: 56px;
      box-shadow: inset -1px 0 0 {BORDER}; }}
  }}
</style>
"""


def _altair_theme() -> None:
    import altair as alt

    def theme() -> dict[str, Any]:
        return {
            "config": {
                "font": "Inter, sans-serif",
                "background": "transparent",
                # room for the last x label and the target labels, so nothing is clipped
                "padding": {"left": 4, "right": 20, "top": 8, "bottom": 4},
                "view": {"stroke": None},
                "axis": {
                    "labelColor": SLATE,
                    "titleColor": SLATE,
                    "titleFontWeight": 500,
                    "gridColor": "#EEF2F6",
                    "domainColor": SLATE_300,
                    "tickColor": SLATE_300,
                    "labelFontSize": 12,
                    "titleFontSize": 12,
                    "labelPadding": 6,
                },
                "legend": {
                    "labelColor": INK,
                    "titleColor": SLATE,
                    "labelFontSize": 12,
                    "symbolSize": 120,
                    "symbolStrokeWidth": 3,
                },
                "range": {"category": list(SERIES)},
            }
        }

    try:
        alt.theme.register("irerero", enable=True)(theme)
    except AttributeError:  # older Altair
        alt.themes.register("irerero", theme)
        alt.themes.enable("irerero")


# Dark appearance, chosen in the account menu. The page is drawn inverted with its hues kept, so
# every colour keeps its meaning (teal stays teal, red stays red) and no screen needs its own
# dark styles. What must show its real colours is turned back: photos, maps and the swatches of
# map legends, and the sidebar, which is dark already.
DARK_CSS = """<style>
  @media screen {  /* printing, e.g. the district brief, stays light */
    html { filter: invert(1) hue-rotate(180deg); background: #FFFFFF; }
    img, video, .ir-hero-art, .ir-swatch, [data-testid="stDeckGlJsonChart"],
    section[data-testid="stSidebar"] { filter: invert(1) hue-rotate(180deg); }
    section[data-testid="stSidebar"] img { filter: none; }
  }
</style>"""


def setup() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
    if st.session_state.get("dark", False):
        st.markdown(DARK_CSS, unsafe_allow_html=True)
    st.logo(str(LOGO_LIGHT), icon_image=str(ICON_LIGHT), size="large")
    _altair_theme()


def _switch_language() -> None:
    from irerero.ui import i18n

    st.session_state["lang"] = i18n.EN if i18n.lang() == i18n.RW else i18n.RW


def _switch_theme() -> None:
    st.session_state["dark"] = not st.session_state.get("dark", False)


def topbar(crumbs: Sequence[str]) -> None:
    from irerero.ui import i18n
    from irerero.ui.roles import ROLE_LABELS, current

    user = current()
    parts = [f'<span class="app">{escape(t("ECD planning · Rwanda"))}</span>']
    shown = [c for c in crumbs if c]
    for i, crumb in enumerate(shown):
        if i:
            parts.append('<span class="sep" aria-hidden="true">›</span>')
        attrs = ' class="here" aria-current="page"' if i == len(shown) - 1 else ""
        parts.append(f"<span{attrs}>{escape(t(crumb))}</span>")
    words = [w for w in ROLE_LABELS[user.role].split() if w[0].isalpha()]
    initials = "".join(w[0] for w in words[:2]).upper()
    role = i18n.role(user.role, ROLE_LABELS[user.role])
    area = user.district_id or t("All districts")
    area = area.removeprefix("D-").title() if user.district_id else area
    with st.container(
        horizontal=True,
        vertical_alignment="center",
        key="topbar-cloud" if ON_COMMUNITY_CLOUD else "topbar",
    ):
        st.markdown(
            f'<nav class="ir-crumbs" aria-label="Breadcrumb">{"".join(parts)}</nav>',
            unsafe_allow_html=True,
            width="stretch",
        )
        # the account button: details, then the language and the light or dark appearance
        with st.popover(initials, help=f"{role} · {area}", key="account"):
            st.markdown(
                f'<div class="ir-account"><b>{escape(role)}</b>'
                f"<span>{escape(area)} · {escape(t('demo account'))}</span>"
                f'<span class="note">'
                f"{escape(t('Fictional user. Switch role under Demo role in the sidebar.'))}"
                "</span></div>",
                unsafe_allow_html=True,
            )
            rw = i18n.lang() == i18n.RW
            dark = st.session_state.get("dark", False)
            st.button(
                "English" if rw else "Ikinyarwanda",
                key="pref-lang",
                icon=":material/translate:",
                on_click=_switch_language,
                width="stretch",
            )
            st.button(
                t("Light mode") if dark else t("Dark mode"),
                key="pref-theme",
                icon=":material/light_mode:" if dark else ":material/dark_mode:",
                on_click=_switch_theme,
                width="stretch",
            )
            if rw:
                st.markdown(f'<div class="ir-note">{escape(i18n.DRAFT_NOTE)}</div>',
                            unsafe_allow_html=True)  # fmt: skip


def header(
    title: str,
    subtitle: str | None = None,
    simulated: bool = False,
    crumbs: Sequence[str] | None = None,
    aside: str | None = None,
    tag: str | None = None,
    assistant: str | None = None,
    hero: bool = False,
) -> None:
    """Top bar, page title and subtitle, an optional right-hand callout (HTML) or the "Ask
    IrereroAI" button for page `assistant`, the scope line and, when needed, the
    simulated-data notice. With `hero`, a role's home screen: the assistant's hero (which
    carries the notices) above the title instead of the button."""
    topbar(crumbs or [title])
    tag_html = (
        f'<span class="ir-tag" style="background:#FCE8E6;color:{SIM_RED}">{escape(tag)}</span>'
        if tag
        else ""
    )
    head = f'<h1 class="ir-title">{escape(t(title))}{tag_html}</h1>' + (
        f'<p class="ir-subtitle">{escape(t(subtitle))}</p>' if subtitle else ""
    )
    if hero and assistant:
        from irerero.ui import assistant as ask
        from irerero.ui.roles import current

        ask.hero(current(), simulated, page=assistant)
        st.markdown(head, unsafe_allow_html=True)
        return
    if aside:
        left, right = st.columns([3, 2], vertical_alignment="center")
        left.markdown(head, unsafe_allow_html=True)
        right.markdown(aside, unsafe_allow_html=True)
    elif assistant:
        from irerero.ui import assistant as ask

        left, right = st.columns([4, 1], vertical_alignment="center", gap="medium")
        left.markdown(head, unsafe_allow_html=True)
        with right, st.container(key="ask-entry"):
            ask.entry(assistant)
    else:
        st.markdown(head, unsafe_allow_html=True)
    definition()
    if simulated:
        simulated_banner()


def definition() -> None:
    st.markdown(
        f'<div class="ir-notice ir-scope" role="note">{icon("info", 16)}<div><b>Scope.</b> '
        f"{escape(DEFINITION)} Census, MINEDUC and NCDA enrolment figures are never added "
        "together.</div></div>",
        unsafe_allow_html=True,
    )


def simulated_banner() -> None:
    st.markdown(
        f'<div class="ir-notice ir-banner" role="status">{icon("alert", 16)}<div>'
        '<span class="ir-badge ir-sim">SIMULATED</span>&nbsp; Some values on this screen are '
        "simulated stand-ins for data files not yet loaded. They show the method, not the real "
        "situation, and are left out of exports by default.</div></div>",
        unsafe_allow_html=True,
    )


def target_callout(label: str, value: str, detail: str) -> str:
    """Gold target card for the page header aside."""
    return (
        f'<div class="ir-callout ir-target"><span class="ico">{icon("target", 32, 1.8)}</span>'
        f'<div><div class="label">{escape(t(label))}</div>'
        f'<div class="detail">{escape(t(detail))}</div>'
        f'<div class="value">{escape(value)}</div></div></div>'
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
    """KPI card: tinted icon and label, value, detail line, and source with status pinned to
    the bottom so cards in a row line up. The full provenance is also on hover."""
    bg, fg = TONES[tone]
    tip = escape(provenance(source, period, status), quote=True)
    detail_html = f'<div class="detail">{escape(t(detail))}</div>' if detail else ""
    st.markdown(
        f'<div class="ir-kpi ir-fill" title="{tip}"><div class="head">'
        f'<div class="ico" style="background:{bg};color:{fg}">{icon(icon_name, 20)}</div>'
        f'<div class="label">{escape(t(label))}</div></div>'
        f'<div class="value">{escape(value)}</div>{detail_html}'
        f'<div class="src"><span>{escape(provenance(source, period, None))}</span>'
        f"{badge(status)}</div></div>",
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
    detail_html = f'<div class="range">{escape(t(detail))}</div>' if detail else ""
    st.markdown(
        f'<div class="ir-card ir-fill" title="{tip}"><div class="label">{escape(t(label))}</div>'
        f'<div class="value">{escape(value)}</div>{detail_html}'
        f'<div class="src"><span>{escape(provenance(source, period, None))}</span>'
        f"{badge(status)}</div></div>",
        unsafe_allow_html=True,
    )


def alert(title: str, body: str, tone: str = "rose", also: Sequence[tuple[str, str]] = ()) -> None:
    """A tinted callout that fills its column, e.g. the main bottleneck beside the KPIs. The
    icon and the title say the state; the tint only repeats it. `also` lists further
    (pill key, text) lines, e.g. the other bottlenecks with their actions."""
    bg, fg = TONES[tone]
    ico = "check" if tone == "teal" else "alert"
    more = "".join(f'<div class="also">{pill(key)} {escape(text)}</div>' for key, text in also)
    st.markdown(
        f'<div class="ir-callout ir-alert ir-fill" role="status" style="background:{bg};'
        f'border-color:{fg}40"><div class="title" style="color:{fg}">{icon(ico, 20)}'
        f'{escape(title)}</div><div class="body">{escape(body)}</div>{more}</div>',
        unsafe_allow_html=True,
    )


def stat_strip(lead_title: str, lead_note: str, cells: Sequence[tuple[str, str, str]]) -> None:
    """A target banner: an icon and headline, then (label, value, note HTML) cells."""
    body = "".join(
        f'<div class="cell"><div class="ir-note">{escape(t(label))}</div><div class="v">'
        f'{escape(value)}</div><div class="ir-note">{note}</div></div>'
        for label, value, note in cells
    )
    st.markdown(
        f'<div class="ir-callout ir-strip" style="background:#EEF6F3;border-color:#CFE7E0">'
        f'<div class="lead"><span style="color:{TEAL_700}">{icon("target", 36, 1.8)}</span>'
        f'<div><b>{escape(lead_title)}</b><div class="ir-note">{escape(lead_note)}</div></div>'
        f"</div>{body}</div>",
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
    (from the title unless given) must be unique on the page. Cards in the same row of
    columns stretch to the same height."""
    slug = re.sub(r"[^a-z0-9]+", "-", (key or title or "panel").lower()).strip("-")
    with st.container(key=f"ir-{slug}") as box:
        if title:
            ico = (
                f'<span style="color:{TEAL_700}">{icon(icon_name, 20)}</span>' if icon_name else ""
            )
            sub = f"<p>{escape(t(subtitle))}</p>" if subtitle else ""
            st.markdown(
                f'<div class="ir-panel-head"><div><h3>{ico}{escape(t(title))}</h3>{sub}</div>'
                f"<div>{right or ''}</div></div>",
                unsafe_allow_html=True,
            )
        yield box


def pill(key: str, text: str | None = None) -> str:
    tone, label = PILLS.get(key, ("slate", key))
    bg, fg = TONES[tone]
    return f'<span class="ir-pill" style="background:{bg};color:{fg}">{escape(t(text or label))}</span>'


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


def table(
    rows: list[dict[str, Any]], cols: Sequence[Col], empty: str = "No rows.", pin: bool = False
) -> str:
    """An HTML table in the house style (pills and formatted numbers allowed in cells). With
    `pin`, the first two columns (rank and name) stay in view on a phone while the rest scrolls
    sideways."""
    if not rows:
        return empty_state(empty)
    head = "".join(f'<th class="{"num" if c.num else ""}">{escape(t(c.label))}</th>' for c in cols)
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
        f'<div class="ir-table-wrap"><table class="ir-table{" ir-pin" if pin else ""}">'
        f"<thead><tr>{head}</tr></thead>"
        f"<tbody>{''.join(body)}</tbody></table></div>"
    )


def empty_state(text: str, icon_name: str = "clipboard") -> str:
    return f'<div class="ir-empty">{icon(icon_name, 28)}<div>{escape(t(text))}</div></div>'


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
            f'{icon(b.icon_name, 20)}</div><div><div class="name">{escape(t(b.name))}</div>'
            f'<div class="sub">{escape(t(b.sub))}</div></div><div><div class="ir-bar-track">'
            f'<div class="ir-bar-fill" style="width:{width:.0f}%;background:{b.colour}"></div>'
            f'{mark}</div><div class="ir-bar-val">{escape(b.label)}</div></div></div>'
        )
    return "".join(out)


def timeline(items: Sequence[tuple[str, str, str, str]], fresh: str = "") -> str:
    """(when, what, why, tone) entries, newest first. `fresh` ("a" or "b", alternating with
    each new entry) makes the newest entry glow once, for a decision just recorded."""
    if not items:
        return empty_state("Nothing recorded yet.", "clock")
    glow = f' class="ir-fresh-{fresh}"' if fresh in ("a", "b") else ""
    rows = "".join(
        f'<li{glow if i == 0 else ""}><span class="dot" style="background:{TONES[tone][1]}">'
        "</span><div>"
        f'<div class="when">{escape(when)}</div><div class="what">{escape(what)}</div>'
        f'<div class="why">{escape(why)}</div></div></li>'
        for i, (when, what, why, tone) in enumerate(items)
    )
    return f'<ul class="ir-timeline">{rows}</ul>'


def note(text: str) -> None:
    st.markdown(f'<div class="ir-note">{escape(text)}</div>', unsafe_allow_html=True)


def measure_note() -> None:
    """Which measure the target is applied to on PLAN and DIAGNOSE, and how it differs from
    the NST2 rate (TRACK and the brief use the NST2 measure)."""
    from irerero.config import TARGET_2029

    note(
        "Target applied to attendance of children aged 3 to 5 (census based). The NST2 "
        f"{fmt_pct(TARGET_2029.value)} is a gross enrolment rate (MINEDUC pupils, over-age "
        "included), so it can be reached with fewer places than shown here."
    )


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
