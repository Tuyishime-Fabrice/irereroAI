"""Optional covariates: rainfall, elevation and slope, night-time lights, as sector means."""

import math
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any

from sqlalchemy import Connection

from irerero_contract.enums import Origin
from pipelines.config import PILOT_DISTRICTS
from pipelines.runs import CheckResult
from pipelines.sources.areas import write_indicators
from pipelines.sources.base import Loader, LoadReport
from pipelines.sources.rasters import zonal_mean
from pipelines.sources.spec import Dataset, ExpectedFile

if TYPE_CHECKING:
    import numpy as np
    from rasterio.io import DatasetReader

COVARIATE_USE = (
    "need model (Phase 2): covariate for small-area estimates",
    "need map: sector details",
)


class _RasterMean(Loader):
    indicator: str

    def load(self, conn: Connection, folder: Path, run_id: uuid.UUID) -> LoadReport:
        means = zonal_mean(conn, folder / self.dataset.files[0].name, PILOT_DISTRICTS)
        return _write(conn, self.dataset, run_id, {self.indicator: means})


def _write(
    conn: Connection, dataset: Dataset, run_id: uuid.UUID, values: dict[str, dict[str, float]]
) -> LoadReport:
    rows = [
        (area, indicator, value, None, None, None)
        for indicator, by_area in values.items()
        for area, value in by_area.items()
    ]
    written = write_indicators(conn, dataset, dataset.reference_year or 0, run_id, rows)
    sectors = len({area for by_area in values.values() for area in by_area})
    return LoadReport(
        {"area_indicator": written},
        [CheckResult("sectors_covered", sectors > 0, f"{sectors} pilot sectors covered")],
    )


class Chirps(_RasterMean):
    indicator = "rainfall_mm_annual"
    dataset = Dataset(
        key="chirps",
        title="CHIRPS rainfall, annual total",
        publisher="Climate Hazards Center, UC Santa Barbara",
        access="Open download",
        url="https://www.chc.ucsb.edu/data/chirps",
        licence="CC BY 4.0 (public domain dedication for the data)",
        origin=Origin.PUBLIC,
        reference_year=2024,
        files=(ExpectedFile("chirps_annual_mm.tif", "geotiff", "Annual rainfall in mm"),),
        columns=(),
        level="raster",
        joins_on="Pixels averaged inside each pilot sector",
        used_by=COVARIATE_USE,
        produces=("area_indicator: rainfall_mm_annual",),
        fallback="Not used until loaded",
        optional=True,
    )


def _slope_degrees(band: "np.ndarray", source: "DatasetReader", window: Any) -> "np.ndarray":
    """Slope from elevation. Pixel sizes in degrees are converted to metres at the window's
    latitude, which is accurate enough across one district."""
    import numpy as np

    dx, dy = abs(window.a), abs(window.e)
    if source.crs.is_geographic:
        latitude = window.f + window.e * band.shape[0] / 2
        dy = dy * 111_320
        dx = dx * 111_320 * math.cos(math.radians(latitude))
    filled = band.filled(np.nan).astype(float)
    grad_y, grad_x = np.gradient(filled, dy, dx)
    slope = np.degrees(np.arctan(np.hypot(grad_x, grad_y)))
    return np.ma.masked_invalid(np.ma.array(slope, mask=band.mask))


class Srtm(Loader):
    dataset = Dataset(
        key="srtm",
        title="SRTM elevation, 30 m",
        publisher="NASA / USGS",
        access="Open download",
        url="https://earthexplorer.usgs.gov",
        licence="Public domain",
        origin=Origin.PUBLIC,
        reference_year=2000,
        files=(ExpectedFile("srtm_elevation_m.tif", "geotiff", "Elevation in metres"),),
        columns=(),
        level="raster",
        joins_on="Pixels averaged inside each pilot sector",
        used_by=COVARIATE_USE,
        produces=("area_indicator: elevation_m_mean, slope_deg_mean",),
        fallback="Not used until loaded",
        optional=True,
    )

    def load(self, conn: Connection, folder: Path, run_id: uuid.UUID) -> LoadReport:
        path = folder / self.dataset.files[0].name
        return _write(
            conn,
            self.dataset,
            run_id,
            {
                "elevation_m_mean": zonal_mean(conn, path, PILOT_DISTRICTS),
                "slope_deg_mean": zonal_mean(conn, path, PILOT_DISTRICTS, _slope_degrees),
            },
        )


class Viirs(_RasterMean):
    indicator = "night_lights_mean"
    dataset = Dataset(
        key="viirs",
        title="VIIRS night-time lights, annual composite",
        publisher="Earth Observation Group, Colorado School of Mines",
        access="Open download (free registration)",
        url="https://eogdata.mines.edu/products/vnl/",
        licence="CC BY 4.0",
        origin=Origin.PUBLIC,
        reference_year=2024,
        files=(ExpectedFile("viirs_radiance.tif", "geotiff", "Average radiance, nW/cm2/sr"),),
        columns=(),
        level="raster",
        joins_on="Pixels averaged inside each pilot sector",
        used_by=COVARIATE_USE,
        produces=("area_indicator: night_lights_mean",),
        fallback="Not used until loaded",
        optional=True,
    )
