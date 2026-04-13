"""Population-weighted averaging and envelope bin aggregation."""

from __future__ import annotations

import logging
from typing import Dict, List, Sequence

import numpy as np
import pandas as pd

from .errors import DSPMDataError

logger = logging.getLogger(__name__)


def weighted_average(
    values: Sequence[float],
    weights: Sequence[float],
) -> float:
    """Compute a weighted average with a zero-guard.

    If total weight is zero (e.g., zero HDD or CDD), returns 0.0
    instead of raising a division-by-zero error.
    """
    total_weight = sum(weights)
    if total_weight == 0:
        return 0.0
    return sum(v * w for v, w in zip(values, weights)) / total_weight


def aggregate_envelope_bins(
    building_stock: pd.DataFrame,
    envelope_bin_groups: Dict[str, List[int]],
    group_by: List[str],
    load_cols: List[str],
    weight_col: str = "building_genome_qty",
) -> pd.DataFrame:
    """Collapse envelope bins into groups via population-weighted averaging.

    Parameters
    ----------
    building_stock : DataFrame
        Filtered building stock with ``building_envelope_bin`` column.
    envelope_bin_groups : dict
        e.g. ``{"poor": [-5, -4, -3], "average": [-2, -1], "good": [1, 2, 3, 4, 5]}``
    group_by : list of str
        Columns to group by BEFORE envelope grouping (e.g., climate_zone, building_type).
    load_cols : list of str
        Load columns to average (e.g., load_heating_annual_kwh).
    weight_col : str
        Population weight column.

    Returns
    -------
    DataFrame with columns: group_by + ["envelope_tier"] + load_cols + [weight_col]
    """
    # Build bin → group mapping
    bin_to_group: Dict[int, str] = {}
    for group_name, bins in envelope_bin_groups.items():
        for b in bins:
            bin_to_group[b] = group_name

    df = building_stock.copy()
    df["envelope_tier"] = df["building_envelope_bin"].map(bin_to_group)

    # Drop unmapped bins
    unmapped = df[df["envelope_tier"].isna()]["building_envelope_bin"].unique()
    if len(unmapped) > 0:
        logger.warning(
            "Dropping %d envelope bins not in any group: %s",
            len(unmapped),
            sorted(unmapped),
        )
        df = df.dropna(subset=["envelope_tier"])

    full_group = group_by + ["envelope_tier"]

    rows = []
    for keys, grp in df.groupby(full_group, sort=True):
        if not isinstance(keys, tuple):
            keys = (keys,)
        total_weight = grp[weight_col].sum()
        if total_weight == 0:
            logger.debug(
                "Skipping empty envelope group: %s",
                dict(zip(full_group, keys)),
            )
            continue
        row = dict(zip(full_group, keys))
        for col in load_cols:
            row[col] = (grp[col] * grp[weight_col]).sum() / total_weight
        row[weight_col] = total_weight
        rows.append(row)

    result = pd.DataFrame(rows)
    logger.info(
        "Envelope aggregation: %d input rows → %d grouped rows",
        len(df),
        len(result),
    )
    return result


def compute_population_shares(
    df: pd.DataFrame,
    group_cols: List[str],
    within_cols: List[str],
    weight_col: str = "building_genome_qty",
) -> pd.DataFrame:
    """Compute population shares within groups.

    For each unique combination of ``within_cols``, compute each
    ``group_cols`` combination's share of total population.

    Returns DataFrame with group_cols + within_cols + ["population_share"].
    """
    all_cols = within_cols + group_cols
    counts = df.groupby(all_cols, sort=True)[weight_col].sum().reset_index()
    if within_cols:
        totals = counts.groupby(within_cols, sort=True)[weight_col].transform("sum")
    else:
        totals = counts[weight_col].sum()
    counts["population_share"] = counts[weight_col] / totals
    return counts[all_cols + ["population_share"]]
