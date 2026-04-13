"""HVAC system cost calculations for one configuration (base or alt)."""
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


def compute_hvac_costs(
    df: pd.DataFrame,
    suffix: str,
) -> Dict[str, pd.Series]:
    """Compute HVAC costs for one configuration side (base or alt).

    Includes:
    - Annualized capital cost
    - Annual maintenance
    - Heating fuel costs (5 fuels: gas, electric, oil, propane, wood)
    - Cooling energy cost (always electric)

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
    equip_cost = df[f"hvac_equipment_cost_{sfx}"]
    life = df[f"hvac_assumed_life_{sfx}"]
    discount_rate = df["discount_rate"]
    annual_capital = annualized_capital(equip_cost, discount_rate, life)

    # --- O&M ---
    annual_maint = df[f"hvac_maintenance_cost_annual_{sfx}"]

    # --- Heating fuel costs ---
    heating_load = df[f"heating_load_annual_{sfx}"]

    heating_cost_total = pd.Series(0.0, index=df.index)
    intermediates: Dict[str, pd.Series] = {}

    for fuel in FUELS:
        prop = df[f"heating_system_proportion_{fuel}_{sfx}"]
        eff = df[f"heating_system_efficiency_{fuel}_{sfx}"]
        price = df[FUEL_PRICE_MAP[fuel]]

        # Energy consumed = load × proportion / efficiency
        # Only calculate where proportion > 0 to avoid division by zero
        energy = np.where(prop > 0, heating_load * prop / eff, 0.0)
        cost = energy * price

        intermediates[f"hvac_{sfx}_heating_{fuel}_energy_gj"] = pd.Series(energy, index=df.index)
        intermediates[f"hvac_{sfx}_heating_{fuel}_cost"] = pd.Series(cost, index=df.index)
        heating_cost_total = heating_cost_total + cost

    # --- Cooling cost (always electric) ---
    cooling_load = df[f"cooling_load_annual_{sfx}"]
    cooling_eff = df[f"cooling_system_efficiency_{sfx}"]
    cooling_energy = np.where(cooling_eff > 0, cooling_load / cooling_eff, 0.0)
    cooling_cost = cooling_energy * df["cost_electricity_home"]

    # --- Totals ---
    total = annual_capital + annual_maint + heating_cost_total + cooling_cost

    prefix = f"hvac_{sfx}"
    result = {
        f"{prefix}_annual_capital": annual_capital,
        f"{prefix}_annual_maintenance": annual_maint,
        f"{prefix}_heating_cost": heating_cost_total,
        f"{prefix}_cooling_energy_gj": pd.Series(cooling_energy, index=df.index),
        f"{prefix}_cooling_cost": pd.Series(cooling_cost, index=df.index),
        f"{prefix}_total_cost": total,
    }
    result.update(intermediates)
    return result
