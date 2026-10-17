"""Raster helpers. rasterio and numpy are imported only when a raster file is present.

Install them with `uv sync --extra geo`; the build says so if they are missing.
"""

import json
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any

from sqlalchemy import Connection, text

from pipelines.sources.readers import SchemaError

if TYPE_CHECKING:
    import numpy as np
    from rasterio.io import DatasetReader

PILOT_SECTORS = text(
    "SELECT code, ST_AsGeoJSON(geom) AS geometry FROM admin_unit "
    "WHERE level = 'sector' AND parent_code = ANY(:districts) ORDER BY code"
)


def require_geo() -> None:
    try:
        import numpy  # noqa: F401
        import rasterio  # noqa: F401
    except ImportError as error:
        raise SchemaError(
            "Raster files need the geo extras: run `uv sync --extra geo` and build again"
        ) from error


@contextmanager
def open_raster(path: Path) -> Iterator["DatasetReader"]:
    require_geo()
    import rasterio

    try:
        with rasterio.open(path) as source:
            if source.crs is None:
                raise SchemaError(f"{path.name}: the raster has no coordinate reference system")
            yield source
    except rasterio.errors.RasterioIOError as error:
        raise SchemaError(f"{path.name}: not a readable GeoTIFF ({error})") from error


def sectors(conn: Connection, districts: Sequence[str]) -> list[tuple[str, dict[str, Any]]]:
    return [
        (row.code, json.loads(row.geometry))
        for row in conn.execute(PILOT_SECTORS, {"districts": list(districts)})
    ]


def masked(source: "DatasetReader", geometry: dict[str, Any]) -> tuple["np.ndarray", Any]:
    """Pixels inside the geometry (others masked) and the window's affine transform."""
    import rasterio.mask
    import rasterio.warp

    shape = rasterio.warp.transform_geom("EPSG:4326", source.crs, geometry)
    data, transform = rasterio.mask.mask(
        source, [shape], crop=True, filled=False, all_touched=False
    )
    return data[0], transform


def zonal_mean(
    conn: Connection,
    path: Path,
    districts: Sequence[str],
    transform_band: Callable[["np.ndarray", "DatasetReader", Any], "np.ndarray"] | None = None,
) -> dict[str, float]:
    """Mean of valid pixels per pilot sector."""
    out: dict[str, float] = {}
    with open_raster(path) as source:
        for code, geometry in sectors(conn, districts):
            try:
                band, window = masked(source, geometry)
            except ValueError:
                continue  # the sector lies outside the raster
            if transform_band is not None:
                band = transform_band(band, source, window)
            if band.count() > 0:
                out[code] = float(band.mean())
    if not out:
        raise SchemaError(f"{path.name}: the raster does not cover the pilot district")
    return out
