"""Annualized capital cost computation using PMT (payment) function."""
from __future__ import annotations

import numpy as np
import polars as pl


def annualized_capital(
    purchase_cost: pl.Series,
    discount_rate: pl.Series,
    life_years: pl.Series,
) -> pl.Series:
    cost = purchase_cost.to_numpy()
    rate = discount_rate.to_numpy()
    life = life_years.to_numpy()

    result = np.zeros_like(cost, dtype=float)

    safe_pos_rate = (cost != 0) & (life > 0) & (rate > 0)
    r = rate[safe_pos_rate]
    n = life[safe_pos_rate]
    pv = cost[safe_pos_rate]
    result[safe_pos_rate] = pv * r / (1.0 - np.power(1.0 + r, -n))

    safe_zero_rate = (cost != 0) & (life > 0) & (rate == 0)
    result[safe_zero_rate] = cost[safe_zero_rate] / life[safe_zero_rate]

    return pl.Series(purchase_cost.name, result)
