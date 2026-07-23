"""Domestic hot water (DHW) system cost calculations."""
from __future__ import annotations

from typing import Dict

import numpy as np
import polars as pl

from .annualize import annualized_capital

FUELS = ("gas", "electric", "oil", "propane", "wood")

FUEL_PRICE_MAP = {
    "gas": "cost_natural_gas_home",
    "electric": "cost_electricity_home",
    "oil": "cost_oil_home",
    "propane": "cost_propane_home",
    "wood": "cost_wood_home",
}


def compute_dhw_costs(
    df: pl.DataFrame,
    suffix: str,
) -> Dict[str, pl.Series]:
    sfx = suffix

    equip_cost = df[f"dhw_equipment_cost_{sfx}"]
    life = df[f"dhw_assumed_life_{sfx}"]
    discount_rate = df["discount_rate"]
    annual_capital = annualized_capital(equip_cost, discount_rate, life)

    annual_maint = df[f"dhw_maintenance_cost_annual_{sfx}"]

    dhw_load = df[f"dhw_load_annual_{sfx}"]

    n = len(df)
    fuel_cost_total = pl.Series("_", np.zeros(n))
    intermediates: Dict[str, pl.Series] = {}

    for fuel in FUELS:
        prop = df[f"dhw_system_proportion_{fuel}_{sfx}"]
        eff = df[f"dhw_system_efficiency_{fuel}_{sfx}"]
        price = df[FUEL_PRICE_MAP[fuel]]

        energy_arr = np.where(
            prop.to_numpy() > 0,
            dhw_load.to_numpy() * prop.to_numpy() / eff.to_numpy(),
            0.0,
        )
        energy = pl.Series("_", energy_arr)
        cost = energy * price

        intermediates[f"dhw_{sfx}_{fuel}_energy_gj"] = energy
        intermediates[f"dhw_{sfx}_{fuel}_cost"] = cost
        fuel_cost_total = fuel_cost_total + cost

    total = annual_capital + annual_maint + fuel_cost_total

    prefix = f"dhw_{sfx}"
    result = {
        f"{prefix}_annual_capital": annual_capital,
        f"{prefix}_annual_maintenance": annual_maint,
        f"{prefix}_fuel_cost": fuel_cost_total,
        f"{prefix}_total_cost": total,
    }
    result.update(intermediates)
    return result
