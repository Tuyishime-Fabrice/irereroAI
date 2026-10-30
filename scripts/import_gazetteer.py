"""Import administrative P-codes from the OCHA COD-AB gazetteer into the reviewed crosswalks.

    uv run --with openpyxl python scripts/import_gazetteer.py rwa_gazetteer_rphc2012_v2.xlsx

Writes data/reference/pcodes_cod_ab.csv (province, district and sector codes and names) and
fills nisr_sector_code / nisr_district_code in the crosswalks by exact name match within the
district (case and spacing only, as everywhere else). The COD-AB codes are the NISR codes
prefixed with RW (sector RW1101 is NISR 1101), which is what the COD-AB boundary files carry,
so the official boundaries can be loaded once they are in data/raw/boundaries/.

Stops, changing nothing, if any sector or district does not match exactly. The reviewed
column is left as it is: a person still confirms each row.
"""

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
REFERENCE = ROOT / "data" / "reference"
SOURCE = "OCHA COD-AB Rwanda gazetteer (RPHC 2012 v2), via HDX"


def _key(text: object) -> str:
    return " ".join(str(text).split()).casefold()


def pcodes(path: Path) -> pd.DataFrame:
    sheets = pd.read_excel(path, sheet_name=["ADM1", "ADM2", "ADM3"], dtype=str)
    adm1 = sheets["ADM1"].dropna(subset=["ADM1_PCODE"])
    adm2 = sheets["ADM2"].dropna(subset=["ADM2_PCODE"])
    adm3 = sheets["ADM3"].dropna(subset=["ADM3_PCODE"])
    frames = [
        pd.DataFrame({"level": "province", "pcode": adm1.ADM1_PCODE, "name": adm1.ADM1_EN,
                      "parent_pcode": "RW", "district": "", "alt_name": ""}),
        pd.DataFrame({"level": "district", "pcode": adm2.ADM2_PCODE, "name": adm2.ADM2_EN,
                      "parent_pcode": adm2.ADM1_PCODE, "district": adm2.ADM2_EN, "alt_name": ""}),
        pd.DataFrame({"level": "sector", "pcode": adm3.ADM3_PCODE, "name": adm3.ADM3_EN,
                      "parent_pcode": adm3.ADM2_PCODE, "district": adm3.ADM2_EN,
                      "alt_name": adm3.ADM3ALT1EN.fillna("")}),
    ]  # fmt: skip
    out = pd.concat(frames, ignore_index=True).assign(source=SOURCE)
    if out.pcode.duplicated().any():
        sys.exit(f"duplicate P-codes: {out.pcode[out.pcode.duplicated()].tolist()[:10]}")
    counts = out.level.value_counts().to_dict()
    if counts != {"sector": 416, "district": 30, "province": 5}:
        sys.exit(f"expected 5 provinces, 30 districts and 416 sectors, got {counts}")
    return out


def main(path: Path) -> None:
    codes = pcodes(path)
    sectors = codes[codes.level == "sector"]
    districts = codes[codes.level == "district"]
    by_sector = {(_key(r.district), _key(r.name)): r.pcode for r in sectors.itertuples()}
    by_district = {_key(r.name): r.pcode for r in districts.itertuples()}

    # Match the canonical rows (source "*"); rows for other sources' spellings take the code
    # of the same geo_id.
    xw = pd.read_csv(REFERENCE / "sector_name_crosswalk.csv", dtype=str).fillna("")
    canon = xw[xw.source == "*"]
    sector_code = {
        g: by_sector.get((_key(d), _key(s)))
        for g, d, s in zip(canon.geo_id, canon.source_district, canon.source_sector, strict=True)
    }
    missing = [g for g, code in sector_code.items() if code is None]
    dx = pd.read_csv(REFERENCE / "district_name_crosswalk.csv", dtype=str).fillna("")
    dcanon = dx[dx.source == "*"]
    district_code = {
        g: by_district.get(_key(d))
        for g, d in zip(dcanon.geo_id, dcanon.source_district, strict=True)
    }
    missing += [g for g, code in district_code.items() if code is None]
    missing += [g for g in set(xw.geo_id) - set(sector_code)] + [
        g for g in set(dx.geo_id) - set(district_code)
    ]
    if missing:
        sys.exit(f"no exact gazetteer match, nothing written: {missing[:20]}")

    codes.to_csv(REFERENCE / "pcodes_cod_ab.csv", index=False)
    xw["nisr_sector_code"] = xw.geo_id.map(sector_code)
    xw.loc[xw.source == "*", "note"] = (
        "geoBoundaries spelling; code from the COD-AB gazetteer by exact name match"
    )
    xw.to_csv(REFERENCE / "sector_name_crosswalk.csv", index=False)
    dx["nisr_district_code"] = dx.geo_id.map(district_code)
    dx.to_csv(REFERENCE / "district_name_crosswalk.csv", index=False)
    print(
        f"{len(xw)} sector and {len(dx)} district codes written; review the rows and set reviewed"
    )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(Path(sys.argv[1]))
