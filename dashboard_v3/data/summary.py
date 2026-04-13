"""Population-weighted statistics and weight renormalization.

Ported from dashboard/summary.py and dashboard/charts.py — no Streamlit dependency.
"""

from __future__ import annotations

from collections import OrderedDict

import numpy as np
import pandas as pd

from dashboard_v3.data.constants import DIMENSION_COLUMNS, WEIGHT_COL

# ---------------------------------------------------------------------------
# Weighted statistics
# ---------------------------------------------------------------------------


def weighted_mean(values: pd.Series, weights: pd.Series) -> float:
    """NaN-safe population-weighted mean."""
    mask = values.notna() & weights.notna()
    v = values[mask].to_numpy(dtype=float)
    w = weights[mask].to_numpy(dtype=float)
    total = w.sum()
    if len(v) == 0 or total == 0:
        return float("nan")
    return float(np.average(v, weights=w))


def weighted_median(values: pd.Series, weights: pd.Series) -> float:
    """Weighted median using linear interpolation."""
    return weighted_percentile(values, weights, 0.5)


def weighted_percentile(
    values: pd.Series,
    weights: pd.Series,
    q: float,
) -> float:
    """Weighted percentile (0-1) using linear interpolation."""
    mask = values.notna() & weights.notna()
    v = values[mask].to_numpy(dtype=float)
    w = weights[mask].to_numpy(dtype=float)
    if len(v) == 0 or w.sum() == 0:
        return float("nan")
    order = np.argsort(v)
    v, w = v[order], w[order]
    cumw = np.cumsum(w)
    cumw_norm = cumw / cumw[-1]
    idx = int(np.argmax(cumw_norm >= q))
    if idx == 0:
        return float(v[0])
    lower_cum = cumw_norm[idx - 1]
    upper_cum = cumw_norm[idx]
    if upper_cum == lower_cum:
        return float(v[idx])
    frac = (q - lower_cum) / (upper_cum - lower_cum)
    return float(v[idx - 1] + frac * (v[idx] - v[idx - 1]))


# ---------------------------------------------------------------------------
# Mandatory groupby detection
# ---------------------------------------------------------------------------


def detect_mandatory_groupby(df: pd.DataFrame) -> list[str]:
    """Detect year + scn_* columns that must be used for grouping."""
    cols = []
    if "year" in df.columns:
        cols.append("year")
    for c in df.columns:
        if c.startswith("scn_"):
            cols.append(c)
    return cols


# ---------------------------------------------------------------------------
# Available dimensions in a DataFrame
# ---------------------------------------------------------------------------


def available_dimensions(df: pd.DataFrame) -> OrderedDict[str, str]:
    """Return the subset of DIMENSION_COLUMNS that exist in df."""
    return OrderedDict(
        (col, label)
        for col, label in DIMENSION_COLUMNS.items()
        if col in df.columns
    )


# ---------------------------------------------------------------------------
# Weight renormalization
# ---------------------------------------------------------------------------


def renormalize_weights(
    df: pd.DataFrame,
    weight_col: str = WEIGHT_COL,
) -> pd.DataFrame:
    """Renormalize population weights to sum to 1.0 within each year+scenario group.

    After filtering, the original weights no longer sum to 1.0. This function
    rescales them so population-share interpretations remain valid.
    """
    df = df.copy()
    group_cols = [c for c in detect_mandatory_groupby(df) if c in df.columns]
    if not group_cols:
        total = df[weight_col].sum()
        if total > 0:
            df[weight_col] = df[weight_col] / total
        return df

    group_sums = df.groupby(group_cols)[weight_col].transform("sum")
    df[weight_col] = np.where(group_sums > 0, df[weight_col] / group_sums, 0.0)
    return df


# ---------------------------------------------------------------------------
# Weighted aggregation helper
# ---------------------------------------------------------------------------


def weighted_mean_by_group(
    df: pd.DataFrame,
    metric_col: str,
    group_cols: list[str],
    weight_col: str = WEIGHT_COL,
) -> pd.DataFrame:
    """Compute population-weighted mean of metric_col for each group."""
    records = []
    for name, grp in df.groupby(group_cols, sort=True):
        if not isinstance(name, tuple):
            name = (name,)
        row = dict(zip(group_cols, name))
        row[metric_col] = weighted_mean(grp[metric_col], grp[weight_col])
        records.append(row)
    return pd.DataFrame(records)


# ---------------------------------------------------------------------------
# Filter application
# ---------------------------------------------------------------------------


def apply_filters(
    df: pd.DataFrame,
    filters: dict[str, list],
) -> pd.DataFrame:
    """Apply a dict of {column: [selected_values]} filters to a DataFrame."""
    mask = pd.Series(True, index=df.index)
    for col, values in filters.items():
        if col in df.columns and values:
            mask = mask & df[col].isin(values)
    return df[mask].copy()
