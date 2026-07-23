"""Vehicle cost calculations for one slot (1 or 2) and one configuration (base or alt)."""
from __future__ import annotations

from typing import Dict

import numpy as np
import polars as pl

from .annualize import annualized_capital


def compute_vehicle_slot_costs(
    df: pl.DataFrame,
    slot: int,
    suffix: str,
) -> Dict[str, pl.Series]:
    s = str(slot)
    sfx = suffix

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

    price_gas = df["cost_gasoline"]
    price_elec_home = df["cost_electricity_home"]
    price_elec_l2 = df["cost_electricity_level2"]
    price_elec_fast = df["cost_electricity_fast"]

    annual_capital = annualized_capital(purchase_cost, discount_rate, life)
    annual_maint = maint_per_km * vkt

    gas_energy = eff_gas * vkt
    gas_cost = gas_energy * price_gas

    ev_energy_kwh = eff_elec * vkt
    ev_f = ev_factor.to_numpy()
    ev_kwh = ev_energy_kwh.to_numpy()
    ev_energy_kwh_derated = np.where(ev_f > 0, ev_kwh / ev_f, 0.0)
    ev_energy_gj = pl.Series("_", ev_energy_kwh_derated * 0.0036)

    weighted_ev_price = (
        pct_home * price_elec_home
        + pct_l2 * price_elec_l2
        + pct_fast * price_elec_fast
    )
    ev_cost = ev_energy_gj * weighted_ev_price

    ev_cost_home = ev_energy_gj * pct_home * price_elec_home
    ev_cost_public = ev_energy_gj * (pct_l2 * price_elec_l2 + pct_fast * price_elec_fast)

    fuel_cost = gas_cost + ev_cost
    total = annual_capital + annual_maint + fuel_cost

    prefix = f"vehicle_{s}_{sfx}"
    return {
        f"{prefix}_annual_capital": annual_capital,
        f"{prefix}_annual_maintenance": annual_maint,
        f"{prefix}_gas_energy_gj": gas_energy,
        f"{prefix}_gas_cost": gas_cost,
        f"{prefix}_ev_energy_gj": ev_energy_gj,
        f"{prefix}_ev_cost": ev_cost,
        f"{prefix}_ev_cost_home": ev_cost_home,
        f"{prefix}_ev_cost_public": ev_cost_public,
        f"{prefix}_fuel_cost": fuel_cost,
        f"{prefix}_total_cost": total,
    }
