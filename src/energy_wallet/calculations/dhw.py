"""Domestic hot water (DHW) system cost calculations."""
from __future__ import annotations

from typing import Dict

import numpy as np
import pandas as pd

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
    df: pd.DataFrame,
    suffix: str,
) -> Dict[str, pd.Series]:
    """Compute DHW costs for one configuration side (base or alt).

    Same pattern as HVAC heating: load × proportion / efficiency × price for each fuel.

    Parameters
    ----------
    df     : DataFrame with all Step 3 model input columns.
    suffix : "base" or "alt".

    Returns
    -------
    Dict mapping intermediate column names to their computed Series.
    """
    sfx = suffix

    # --- Capital ---
    equip_cost = df[f"dhw_equipment_cost_{sfx}"]
    life = df[f"dhw_assumed_life_{sfx}"]
    discount_rate = df["discount_rate"]
    annual_capital = annualized_capital(equip_cost, discount_rate, life)

    # --- O&M ---
    annual_maint = df[f"dhw_maintenance_cost_annual_{sfx}"]

    # --- Fuel costs ---
    dhw_load = df[f"dhw_load_annual_{sfx}"]

    fuel_cost_total = pd.Series(0.0, index=df.index)
    intermediates: Dict[str, pd.Series] = {}

    for fuel in FUELS:
        prop = df[f"dhw_system_proportion_{fuel}_{sfx}"]
        eff = df[f"dhw_system_efficiency_{fuel}_{sfx}"]
        price = df[FUEL_PRICE_MAP[fuel]]

        energy = np.where(prop > 0, dhw_load * prop / eff, 0.0)
        cost = energy * price

        intermediates[f"dhw_{sfx}_{fuel}_energy_gj"] = pd.Series(energy, index=df.index)
        intermediates[f"dhw_{sfx}_{fuel}_cost"] = pd.Series(cost, index=df.index)
        fuel_cost_total = fuel_cost_total + cost

    # --- Total ---
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
