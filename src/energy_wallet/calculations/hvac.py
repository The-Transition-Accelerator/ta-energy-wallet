"""HVAC system cost calculations for one configuration (base or alt)."""
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


def compute_hvac_costs(
    df: pl.DataFrame,
    suffix: str,
) -> Dict[str, pl.Series]:
    sfx = suffix

    equip_cost = df[f"hvac_equipment_cost_{sfx}"]
    life = df[f"hvac_assumed_life_{sfx}"]
    discount_rate = df["discount_rate"]
    annual_capital = annualized_capital(equip_cost, discount_rate, life)

    annual_maint = df[f"hvac_maintenance_cost_annual_{sfx}"]

    heating_load = df[f"heating_load_annual_{sfx}"]

    n = len(df)
    heating_cost_total = pl.Series("_", np.zeros(n))
    intermediates: Dict[str, pl.Series] = {}

    for fuel in FUELS:
        prop = df[f"heating_system_proportion_{fuel}_{sfx}"]
        eff = df[f"heating_system_efficiency_{fuel}_{sfx}"]
        price = df[FUEL_PRICE_MAP[fuel]]

        energy_arr = np.where(
            prop.to_numpy() > 0,
            heating_load.to_numpy() * prop.to_numpy() / eff.to_numpy(),
            0.0,
        )
        energy = pl.Series("_", energy_arr)
        cost = energy * price

        intermediates[f"hvac_{sfx}_heating_{fuel}_energy_gj"] = energy
        intermediates[f"hvac_{sfx}_heating_{fuel}_cost"] = cost
        heating_cost_total = heating_cost_total + cost

    cooling_load = df[f"cooling_load_annual_{sfx}"]
    cooling_eff = df[f"cooling_system_efficiency_{sfx}"]
    cooling_energy_arr = np.where(
        cooling_eff.to_numpy() > 0,
        cooling_load.to_numpy() / cooling_eff.to_numpy(),
        0.0,
    )
    cooling_energy = pl.Series("_", cooling_energy_arr)
    cooling_cost = cooling_energy * df["cost_electricity_home"]

    total = annual_capital + annual_maint + heating_cost_total + cooling_cost

    prefix = f"hvac_{sfx}"
    result = {
        f"{prefix}_annual_capital": annual_capital,
        f"{prefix}_annual_maintenance": annual_maint,
        f"{prefix}_heating_cost": heating_cost_total,
        f"{prefix}_cooling_energy_gj": cooling_energy,
        f"{prefix}_cooling_cost": cooling_cost,
        f"{prefix}_total_cost": total,
    }
    result.update(intermediates)
    return result
