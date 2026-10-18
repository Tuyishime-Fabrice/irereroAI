"""Completion certificate as a one-page PDF (fpdf2). It certifies course completion, which
measures course knowledge, not teaching quality."""

from datetime import datetime

from fpdf import FPDF

from irerero.config import ROOT

LOGO = ROOT / "app" / "assets" / "logo.png"


def pdf(
    name: str,
    centre: str,
    course_en: str,
    course_rw: str,
    source: str,
    on: datetime,
    simulated: bool = True,
) -> bytes:
    doc = FPDF(orientation="L", format="A4")
    doc.set_auto_page_break(False)
    doc.add_page()
    doc.set_draw_color(3, 54, 101)
    doc.set_line_width(1.2)
    doc.rect(10, 10, 277, 190)
    if LOGO.exists():
        doc.image(str(LOGO), x=103, y=20, w=90)
    doc.set_text_color(3, 54, 101)
    doc.set_font("Helvetica", "B", 26)
    doc.set_xy(10, 70)
    doc.cell(277, 12, "Certificate of completion", align="C")
    doc.set_font("Helvetica", "", 13)
    doc.set_text_color(15, 27, 42)
    doc.set_xy(10, 90)
    doc.cell(277, 8, "This certifies that", align="C")
    doc.set_font("Helvetica", "B", 18)
    doc.set_xy(10, 100)
    doc.cell(277, 10, name, align="C")
    doc.set_font("Helvetica", "", 13)
    doc.set_xy(10, 113)
    doc.cell(277, 8, f"of {centre} completed the IrereroAI course", align="C")
    doc.set_font("Helvetica", "B", 16)
    doc.set_text_color(24, 151, 122)
    doc.set_xy(10, 124)
    doc.cell(277, 9, course_en, align="C")
    doc.set_font("Helvetica", "I", 12)
    doc.set_xy(10, 134)
    doc.cell(277, 7, course_rw, align="C")
    doc.set_text_color(91, 107, 124)
    doc.set_font("Helvetica", "", 10)
    doc.set_xy(10, 150)
    doc.cell(277, 6, f"Completed on {on:%d %B %Y}. Course adapted from: {source}.", align="C")
    doc.set_xy(10, 158)
    doc.cell(277, 6, "The quiz measures course knowledge, not teaching quality.", align="C")
    if simulated:
        doc.set_xy(10, 180)
        doc.set_text_color(180, 35, 24)
        doc.cell(277, 6, "Demo certificate for a fictional caregiver (SIMULATED).", align="C")
    return bytes(doc.output())
