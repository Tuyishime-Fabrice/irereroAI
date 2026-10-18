"""Moran's I on model residuals: are errors clustered in space? A high, significant value means
neighbouring sectors share something the features miss."""

import geopandas as gpd
import numpy as np
import pandas as pd

from irerero.config import METRIC_CRS, SEED


def neighbours(sectors: gpd.GeoDataFrame, tolerance_m: float = 50) -> list[tuple[int, int]]:
    """Pairs of sectors that share a border (queen contiguity, with a small tolerance for the
    gaps that simplification leaves)."""
    metric = sectors.to_crs(METRIC_CRS).reset_index(drop=True)
    grown = gpd.GeoDataFrame(geometry=metric.buffer(tolerance_m), crs=METRIC_CRS)
    pairs = gpd.sjoin(grown, grown, predicate="intersects")
    pairs = pairs[pairs.index < pairs.index_right]
    return list(zip(pairs.index, pairs.index_right, strict=True))


def morans_i(
    values: np.ndarray, pairs: list[tuple[int, int]], permutations: int = 999, seed: int = SEED
) -> dict[str, float]:
    z = values - values.mean()
    i, j = np.array(pairs).T if pairs else (np.array([], int), np.array([], int))
    s0 = 2 * len(pairs)
    n = len(values)

    def stat(v: np.ndarray) -> float:
        return float(n / s0 * 2 * np.sum(v[i] * v[j]) / np.sum(v * v))

    observed = stat(z)
    rng = np.random.default_rng(seed)
    sims = np.array([stat(rng.permutation(z)) for _ in range(permutations)])
    p = (np.sum(np.abs(sims - sims.mean()) >= abs(observed - sims.mean())) + 1) / (permutations + 1)
    return {
        "morans_i": round(observed, 3),
        "p_value": round(float(p), 3),
        "expected": round(-1 / (n - 1), 4),
    }


def residual_moran(sectors: gpd.GeoDataFrame, residuals: pd.Series) -> dict[str, float]:
    frame = sectors.set_index("geo_id").loc[residuals.index].reset_index()
    return morans_i(residuals.to_numpy(float), neighbours(frame))
