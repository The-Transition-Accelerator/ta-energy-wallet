"""Annualized capital cost computation using PMT (payment) function."""
from __future__ import annotations

import numpy as np
import pandas as pd


def annualized_capital(
    purchase_cost: pd.Series,
    discount_rate: pd.Series,
    life_years: pd.Series,
) -> pd.Series:
    """Compute annualized capital cost.

    Uses the standard PMT formula:
        payment = cost * rate / (1 - (1 + rate)^{-life})

    When cost is 0, returns 0 regardless of other inputs.
    When life is <= 0, returns 0 (guards against bad data).

    Parameters
    ----------
    purchase_cost : Series  – upfront cost ($)
    discount_rate : Series  – annual discount rate (decimal, e.g. 0.03)
    life_years    : Series  – expected useful life (years)

    Returns
    -------
    Series of annual payment amounts (positive = cost).
    """
    cost = purchase_cost.values
    rate = discount_rate.values
    life = life_years.values

    result = np.zeros_like(cost, dtype=float)

    # valid (nonzero) rate case
    safe_pos_rate = (cost != 0) & (life > 0) & (rate > 0)
    r = rate[safe_pos_rate]
    n = life[safe_pos_rate]
    pv = cost[safe_pos_rate]
    result[safe_pos_rate] = pv * r / (1.0 - np.power(1.0 + r, -n))

    # zero rate case -> straight-line annualization
    safe_zero_rate = (cost != 0) & (life > 0) & (rate == 0)
    result[safe_zero_rate] = cost[safe_zero_rate] / life[safe_zero_rate]

    return pd.Series(result, index=purchase_cost.index)
