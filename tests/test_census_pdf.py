"""The Table 2.5 parser, on a synthetic profile laid out like the published ones."""

from fpdf import FPDF

from irerero.data.sources.census_pdf import TABLES, parse_profiles, parse_table

ROWS = [
    ("Byumba", "4,210", "1,302", "2,908"),
    ("Kageyo", "2,045", "411", "1,634"),
    ("Gicumbi", "6,255", "1,713", "4,542"),
]


def profile(path):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=10)
    pdf.cell(0, 8, "Introduction", new_x="LMARGIN", new_y="NEXT")
    pdf.add_page()
    pdf.cell(
        0, 8, "Table 2.5: Children aged 3-5 by nursery attendance", new_x="LMARGIN", new_y="NEXT"
    )
    with pdf.table() as table:
        header = table.row()
        for text in ("Sector", "Total", "Attending", "Never attended"):
            header.cell(text)
        for values in ROWS:
            row = table.row()
            for value in values:
                row.cell(value)
    pdf.output(str(path))
    return path


def test_parse_table_reads_rows_and_page(tmp_path):
    table = parse_table(profile(tmp_path / "Gicumbi.pdf"), TABLES[0])
    assert table.name.tolist() == ["Byumba", "Kageyo", "Gicumbi"]
    assert table.children_3_5.tolist() == [4210, 2045, 6255]
    assert table.children_3_5_attending.tolist() == [1302, 411, 1713]
    assert table.children_3_5_never_attended.tolist() == [2908, 1634, 4542]
    assert set(table.source_page) == {"p.2"}


def test_parse_profiles_splits_sectors_from_district_total(tmp_path):
    out = parse_profiles([profile(tmp_path / "Gicumbi.pdf")], tmp_path / "interim")
    sectors = (out / "census_2022_sectors.csv").read_text()
    districts = (out / "census_2022_districts.csv").read_text()
    assert "Byumba" in sectors
    assert "Gicumbi,6255" in districts
    assert "Byumba" not in districts
