"""Vehicle cost calculations for one slot (1 or 2) and one configuration (base or alt)."""
from __future__ import annotations

from typing import Dict

import numpy as np
import pandas as pd

from .annualize import annualized_capital


def compute_vehicle_slot_costs(
    df: pd.DataFrame,
    slot: int,
    suffix: str,
) -> Dict[str, pd.Series]:
    """Compute all cost components for one vehicle slot and one config side.

    Parameters
    ----------
    df     : DataFrame with all Step 3 model input columns.
    slot   : 1 or 2.
    suffix : "base" or "alt".

    Returns
    -------
    Dict mapping intermediate column names to their computed Series.
    """
    s = str(slot)
    sfx = suffix

    # --- Input columns ---
    purchase_cost = df[f"vehicle_{s}_purchase_cost_{sfx}"]
    life = df[f"vehicle_{s}_assumed_life_{sfx}"]
    maint_per_km = df[f"vehicle_{s}_maintenance_cost_per_km_{sfx}"]
    eff_gas = df[f"vehicle_{s}_efficiency_gas_{sfx}"]
    eff_elec = df[f"vehicle_{s}_efficiency_electric_{sfx}"]
    ev_factor = df[f"ev_{s}_efficiency_factor_{sfx}"]
    pct_home = df[f"ev_{s}_pct_charged_home_{sfx}"]
    pct_l2 = df[f"ev_{s}_pct_charged_level2_{sfx}"]
    pct_fast = df[f"ev_{s}_pct_charged_fast_{sfx}"]
    vkt = df[f"vkt_{s}_annual_{sfx}"]
    discount_rate = df["discount_rate"]

    # Shared fuel prices
    price_gas = df["cost_gasoline"]
    price_elec_home = df["cost_electricity_home"]
    price_elec_l2 = df["cost_electricity_level2"]
    price_elec_fast = df["cost_electricity_fast"]

    # --- Annualized capital ---
    annual_capital = annualized_capital(purchase_cost, discount_rate, life)

    # --- Annual maintenance ---
    annual_maint = maint_per_km * vkt

    # --- Gasoline energy and cost ---
    # vehicle_efficiency_gas is in GJ/km
    gas_energy = eff_gas * vkt  # GJ
    gas_cost = gas_energy * price_gas

    # --- EV energy and cost ---
    # vehicle_efficiency_electric is in kWh/km; convert to GJ: kWh * 0.0036
    ev_energy_kwh = eff_elec * vkt  # kWh
    # Apply climate derating (divide by factor; factor <= 1 increases consumption)
    ev_energy_kwh_derated = np.where(
        ev_factor > 0,
        ev_energy_kwh / ev_factor,
        0.0,
    )
    ev_energy_gj = ev_energy_kwh_derated * 0.0036  # convert kWh to GJ

    # Weighted electricity price across charging locations
    weighted_ev_price = (
        pct_home * price_elec_home
        + pct_l2 * price_elec_l2
        + pct_fast * price_elec_fast
    )
    ev_cost = ev_energy_gj * weighted_ev_price

    # --- EV cost breakdown by charging location (for Step 5 utility bill) ---
    ev_cost_home = ev_energy_gj * pct_home * price_elec_home
    ev_cost_public = ev_energy_gj * (pct_l2 * price_elec_l2 + pct_fast * price_elec_fast)

    # --- Totals ---
    fuel_cost = gas_cost + ev_cost
    total = annual_capital + annual_maint + fuel_cost

    prefix = f"vehicle_{s}_{sfx}"
    return {
        f"{prefix}_annual_capital": annual_capital,
        f"{prefix}_annual_maintenance": annual_maint,
        f"{prefix}_gas_energy_gj": pd.Series(gas_energy, index=df.index),
        f"{prefix}_gas_cost": gas_cost,
        f"{prefix}_ev_energy_gj": pd.Series(ev_energy_gj, index=df.index),
        f"{prefix}_ev_cost": pd.Series(ev_cost, index=df.index),
        f"{prefix}_ev_cost_home": pd.Series(ev_cost_home, index=df.index),
        f"{prefix}_ev_cost_public": pd.Series(ev_cost_public, index=df.index),
        f"{prefix}_fuel_cost": fuel_cost,
        f"{prefix}_total_cost": total,
    }
