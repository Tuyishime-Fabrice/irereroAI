"""WorldPop age and sex structures: children under 5 on a 100 m grid."""

from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

from irerero.config import PUBLISHED, RAW
from irerero.data.spec import Dataset

FILES = (
    "rwa_f_0_2020_constrained_UNadj.tif",
    "rwa_f_1_2020_constrained_UNadj.tif",
    "rwa_m_0_2020_constrained_UNadj.tif",
    "rwa_m_1_2020_constrained_UNadj.tif",
)
DATASET = Dataset(
    key="worldpop",
    title="WorldPop age and sex structures, constrained, 100 m, 2020 (UN adjusted)",
    publisher="WorldPop, University of Southampton",
    files=FILES,
    format="GeoTIFF, EPSG:4326",
    columns=(),
    level="100 m grid",
    reference_period="2020",
    licence="CC BY 4.0",
    url="https://hub.worldpop.org/project/categories?id=8",
    used_by=("PLAN: where children live inside each sector (2026 estimate, distance layer)",),
    status=PUBLISHED,
    fallback="Sector shares of the census 3-5 count; the distance layer spreads children evenly",
    notes=("Age group 0 is under 1 and group 1 is 1 to 4; both sexes are summed.",),
)


def under5_by_sector(sectors: gpd.GeoDataFrame, raw: Path = RAW) -> pd.Series | None:
    """WorldPop under-5 total per sector geo_id, or None while the rasters are missing."""
    if not DATASET.present(raw):
        return None
    from rasterstats import zonal_stats

    total = np.zeros(len(sectors))
    for name in FILES:
        stats = zonal_stats(sectors.geometry, str(DATASET.folder(raw) / name), stats="sum")
        total += np.array([s["sum"] or 0.0 for s in stats])
    return pd.Series(total, index=sectors.geo_id.to_numpy())


def pixels(geometry: object, raw: Path = RAW) -> pd.DataFrame | None:
    """(lon, lat, children) of every under-5 pixel inside a geometry, or None if missing."""
    if not DATASET.present(raw):
        return None
    import rasterio
    import rasterio.mask

    frames = []
    for name in FILES:
        with rasterio.open(DATASET.folder(raw) / name) as source:
            data, transform = rasterio.mask.mask(source, [geometry], crop=True, filled=False)
            band = data[0]
            rows, cols = np.nonzero(~np.ma.getmaskarray(band) & (band.filled(0) > 0))
            lons, lats = rasterio.transform.xy(transform, rows, cols)
            frames.append(pd.DataFrame({"lon": lons, "lat": lats, "children": band[rows, cols]}))
    merged = pd.concat(frames)
    return merged.groupby(["lon", "lat"], as_index=False).children.sum()
