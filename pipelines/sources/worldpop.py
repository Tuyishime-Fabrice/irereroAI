"""WorldPop under-5 population: where children live inside each pilot sector."""

import uuid
from pathlib import Path

from sqlalchemy import Connection, text

from irerero_contract.enums import Origin
from pipelines.config import PILOT_DISTRICTS
from pipelines.runs import CheckResult
from pipelines.sources.areas import write_indicators
from pipelines.sources.base import Loader, LoadReport
from pipelines.sources.rasters import masked, open_raster, sectors
from pipelines.sources.readers import SchemaError
from pipelines.sources.spec import Dataset, ExpectedFile

# Under 5 = age group 0 (under 1) plus age group 1 (1 to 4), girls and boys.
FILES = (
    ("rwa_f_0_2020_constrained_UNadj.tif", "Girls under 1"),
    ("rwa_f_1_2020_constrained_UNadj.tif", "Girls aged 1 to 4"),
    ("rwa_m_0_2020_constrained_UNadj.tif", "Boys under 1"),
    ("rwa_m_1_2020_constrained_UNadj.tif", "Boys aged 1 to 4"),
)
CELLS = text(
    """
    INSERT INTO population_cell (id, sector_code, location, share, source, reference_year,
        origin, pipeline_run_id)
    SELECT sector || ':' || 'E' || cx::bigint || 'N' || cy::bigint, sector,
        ST_Transform(ST_SetSRID(ST_MakePoint(cx + 250, cy + 250), 32735), 4326),
        sum(people) / sum(sum(people)) OVER (PARTITION BY sector),
        :source, :year, :origin, :run_id
    FROM (
        SELECT sector, people,
            floor(ST_X(ST_Transform(ST_SetSRID(ST_MakePoint(lon, lat), 4326), 32735)) / 500)
                * 500 AS cx,
            floor(ST_Y(ST_Transform(ST_SetSRID(ST_MakePoint(lon, lat), 4326), 32735)) / 500)
                * 500 AS cy
        FROM worldpop_stage
    ) p
    GROUP BY sector, cx, cy
    HAVING sum(people) > 0
    """
)


class WorldPop(Loader):
    dataset = Dataset(
        key="worldpop",
        title="WorldPop age and sex structures, constrained, 100 m, 2020 (UN adjusted)",
        publisher="WorldPop, University of Southampton",
        access="Open download",
        url="https://hub.worldpop.org/project/categories?id=8",
        licence="CC BY 4.0",
        origin=Origin.PUBLIC,
        reference_year=2020,
        files=tuple(ExpectedFile(name, "geotiff", what) for name, what in FILES),
        columns=(),
        level="raster",
        joins_on="Pixels summed into 500 m cells inside each pilot sector",
        used_by=(
            "coverage: where children live inside each sector",
            "catchments and the optimizer",
        ),
        produces=("population_cell", "area_indicator: population_under5"),
        fallback="Children spread evenly over each sector's area on the 500 m grid",
        notes=(
            "Only where children live is taken from WorldPop; how many comes from the census "
            "or the need model. Rename the files to these names if your download differs.",
        ),
    )

    def load(self, conn: Connection, folder: Path, run_id: uuid.UUID) -> LoadReport:
        conn.execute(
            text(
                "CREATE TEMP TABLE worldpop_stage (sector text, lon float, lat float, "
                "people float) ON COMMIT DROP"
            )
        )
        totals: dict[str, float] = {}
        shape = None
        for name, _ in FILES:
            with open_raster(folder / name) as source:
                if source.crs.to_epsg() != 4326:
                    raise SchemaError(f"{name}: expected WorldPop's EPSG:4326 grid")
                if shape is not None and (source.width, source.height) != shape:
                    raise SchemaError(f"{name}: the four WorldPop files must share one grid")
                shape = (source.width, source.height)
                for code, geometry in sectors(conn, PILOT_DISTRICTS):
                    try:
                        band, window = masked(source, geometry)
                    except ValueError:
                        continue
                    rows_idx, cols_idx = band.nonzero()
                    rows = []
                    for row, col in zip(rows_idx.tolist(), cols_idx.tolist(), strict=True):
                        people = float(band[row, col])
                        if people <= 0:
                            continue
                        lon, lat = window @ (col + 0.5, row + 0.5)
                        rows.append({"sector": code, "lon": lon, "lat": lat, "people": people})
                    if rows:
                        conn.execute(
                            text(
                                "INSERT INTO worldpop_stage VALUES (:sector, :lon, :lat, :people)"
                            ),
                            rows,
                        )
                    totals[code] = totals.get(code, 0.0) + sum(r["people"] for r in rows)
        if not totals:
            raise SchemaError("WorldPop files do not cover the pilot district")
        meta = {
            "source": self.dataset.title,
            "year": self.dataset.reference_year,
            "origin": self.dataset.origin.value,
            "run_id": run_id,
        }
        cells = conn.execute(CELLS, meta).rowcount
        written = write_indicators(
            conn,
            self.dataset,
            self.dataset.reference_year or 0,
            run_id,
            [
                (code, "population_under5", total, None, None, None)
                for code, total in totals.items()
            ],
        )
        return LoadReport(
            {"population_cell": cells, "area_indicator": written},
            [
                CheckResult("sectors_covered", len(totals) > 0, f"{len(totals)} pilot sectors"),
                CheckResult("cells_written", cells > 0, f"{cells} cells of 500 m"),
            ],
        )
