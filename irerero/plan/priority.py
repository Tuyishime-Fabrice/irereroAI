"""Priority index: weighted percentile ranks of four components, and how stable the ranking
is when the weights move.

    volume    places needed to reach the target (children)
    equity    share of children aged 3 to 5 not attending
    peer_gap  how far attendance falls below the peer model's expectation (DIAGNOSE)
    poverty   poverty rate, sector if published, otherwise the district's

Each component is ranked within the sectors being compared (one district, or the country), so
the index says "higher priority than x% of these sectors", not an absolute need.
"""

from collections.abc import Mapping

import numpy as np
import pandas as pd

from irerero.config import COMPONENTS, SEED, STABILITY_CONCENTRATION, STABILITY_DRAWS, STABILITY_TOP


def percentiles(components: pd.DataFrame) -> pd.DataFrame:
    """Percentile rank of each component (0 to 1, higher = more need). Columns that are all
    missing are dropped."""
    usable = [c for c in COMPONENTS if c in components and components[c].notna().any()]
    return components[usable].rank(pct=True, method="average").fillna(0.5)


def normalise(weights: Mapping[str, float], available: list[str]) -> dict[str, float]:
    """Weights over the available components, summing to 1. A missing component's weight is
    shared out in proportion."""
    kept = {c: max(0.0, float(weights.get(c, 0.0))) for c in available}
    total = sum(kept.values())
    if total == 0:
        return {c: 1 / len(available) for c in available}
    return {c: w / total for c, w in kept.items()}


def score(pct: pd.DataFrame, weights: Mapping[str, float]) -> pd.Series:
    w = normalise(weights, list(pct.columns))
    return sum(pct[c] * w[c] for c in pct.columns).rename("score")  # type: ignore[return-value]


def rank(pct: pd.DataFrame, weights: Mapping[str, float]) -> pd.Series:
    return score(pct, weights).rank(ascending=False, method="first").astype(int).rename("rank")


def stability(
    pct: pd.DataFrame,
    weights: Mapping[str, float],
    draws: int = STABILITY_DRAWS,
    concentration: float = STABILITY_CONCENTRATION,
    top: int = STABILITY_TOP,
    seed: int = SEED,
) -> pd.Series:
    """Share of Dirichlet weight draws around `weights` in which each sector stays in the top
    `top`. 1.0 = in the top whatever the exact weights; near 0 = only with these weights."""
    w = normalise(weights, list(pct.columns))
    alpha = np.array([w[c] for c in pct.columns]) * concentration + 1e-3
    samples = np.random.default_rng(seed).dirichlet(alpha, size=draws)
    scores = pct.to_numpy() @ samples.T  # sectors x draws
    k = min(top, len(pct))
    order = np.argsort(-scores, axis=0, kind="stable")[:k]
    counts = np.zeros(len(pct))
    np.add.at(counts, order.ravel(), 1)
    return pd.Series(counts / draws, index=pct.index, name="stability")


def stability_label(share: float) -> str:
    if share >= 0.8:
        return "stable"
    if share >= 0.4:
        return "depends on weights"
    return "rarely top 3"
