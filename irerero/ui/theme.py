"""Brand, layout and the provenance badges every screen uses."""

from html import escape

import streamlit as st

from irerero.config import (
    DEFINITION,
    GOLD,
    GREEN,
    INK,
    MUTED,
    NAVY,
    ROOT,
    SIMULATED,
    SIMULATED_RED,
)

ASSETS = ROOT / "app" / "assets"
LOGO = ASSETS / "logo.png"
ICON = ASSETS / "icon.png"

CSS = f"""
<style>
  h1, h2, h3 {{ color: {NAVY}; }}
  .block-container {{ padding-top: 2rem; max-width: 1280px; }}
  .ir-definition {{
    border-left: 4px solid {GREEN}; background: #F2F6F9; padding: .5rem .8rem;
    font-size: .85rem; color: {INK}; margin-bottom: .8rem; border-radius: 0 6px 6px 0;
  }}
  .ir-badge {{
    display: inline-block; padding: 0 .45rem; border-radius: 4px; font-size: .72rem;
    font-weight: 700; letter-spacing: .03em; vertical-align: middle; line-height: 1.5;
  }}
  .ir-sim {{ background: {SIMULATED_RED}; color: #fff; }}
  .ir-status {{ background: #E6EDF3; color: {NAVY}; font-weight: 600; }}
  .ir-card {{
    border: 1px solid #DCE3EA; border-radius: 8px; padding: .7rem .9rem; height: 100%;
    background: #fff;
  }}
  .ir-card .label {{ color: {MUTED}; font-size: .8rem; }}
  .ir-card .value {{ color: {NAVY}; font-size: 1.55rem; font-weight: 700; line-height: 1.25; }}
  .ir-card .range {{ color: {MUTED}; font-size: .8rem; }}
  .ir-card .src {{ color: {MUTED}; font-size: .72rem; margin-top: .3rem; }}
  .ir-num {{ border-bottom: 1px dotted {MUTED}; cursor: help; }}
  .ir-banner {{
    border: 2px solid {SIMULATED_RED}; color: {SIMULATED_RED}; border-radius: 6px;
    padding: .4rem .7rem; font-size: .85rem; margin-bottom: .8rem; background: #FEF3F2;
  }}
  .ir-chip {{
    display: inline-block; border-radius: 999px; padding: .05rem .55rem; font-size: .78rem;
    font-weight: 600; color: #fff;
  }}
  .ir-note {{ color: {MUTED}; font-size: .8rem; }}
  .ir-gold {{ color: {GOLD}; }}
  @media (max-width: 640px) {{
    .block-container {{ padding-left: 1rem; padding-right: 1rem; }}
    .ir-card .value {{ font-size: 1.25rem; }}
  }}
</style>
"""


def setup() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
    st.logo(str(LOGO), icon_image=str(ICON), size="large")


def header(title: str, subtitle: str | None = None, simulated: bool = False) -> None:
    st.title(title)
    if subtitle:
        st.caption(subtitle)
    definition()
    if simulated:
        simulated_banner()


def definition() -> None:
    st.markdown(
        f'<div class="ir-definition"><b>Scope.</b> {escape(DEFINITION)} Census, MINEDUC and '
        "NCDA enrolment figures are never added together.</div>",
        unsafe_allow_html=True,
    )


def simulated_banner() -> None:
    st.markdown(
        '<div class="ir-banner"><span class="ir-badge ir-sim">SIMULATED</span> Some values on '
        "this screen are simulated stand-ins for data files not yet loaded. They show the "
        "method, not the real situation, and are left out of exports by default.</div>",
        unsafe_allow_html=True,
    )


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


def card(
    label: str,
    value: str,
    source: str,
    period: str | None,
    status: str | None,
    detail: str | None = None,
) -> None:
    tip = escape(provenance(source, period, status), quote=True)
    detail_html = f'<div class="range">{escape(detail)}</div>' if detail else ""
    st.markdown(
        f'<div class="ir-card" title="{tip}"><div class="label">{escape(label)}</div>'
        f'<div class="value">{escape(value)}</div>{detail_html}'
        f'<div class="src">{escape(provenance(source, period, None))} {badge(status)}</div></div>',
        unsafe_allow_html=True,
    )


def chip(text: str, colour: str) -> str:
    """Coloured label that always carries its text, never colour alone."""
    return f'<span class="ir-chip" style="background:{colour}">{escape(text)}</span>'


def note(text: str) -> None:
    st.markdown(f'<div class="ir-note">{escape(text)}</div>', unsafe_allow_html=True)


def fmt_int(x: float | None) -> str:
    return "–" if x is None or x != x else f"{round(x):,}"


def fmt_pct(x: float | None, digits: int = 0) -> str:
    return "–" if x is None or x != x else f"{x * 100:.{digits}f}%"


def ordinal(n: int) -> str:
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"
