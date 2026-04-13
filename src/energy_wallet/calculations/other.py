"""Other energy costs, fixed charges, and panel upgrade calculations."""
from __future__ import annotations

from typing import Dict

import numpy as np
import pandas as pd

from .annualize import annualized_capital


def compute_other_costs(
    df: pd.DataFrame,
    suffix: str,
) -> Dict[str, pd.Series]:
    """Compute other residential costs for one configuration side (base or alt).

    Includes:
    - Other electricity and natural gas usage costs
    - Monthly fixed charges (electricity always; NG only if gas is used)
    - Annualized panel upgrade cost

    Parameters
    ----------
    df     : DataFrame with all Step 3 model input columns.
    suffix : "base" or "alt".

    Returns
    -------
    Dict mapping intermediate column names to their computed Series.
    """
    sfx = suffix

    # --- Other energy usage ---
    other_elec_cost = df[f"other_electricity_annual_{sfx}"] * df["cost_electricity_home"]
    other_ng_cost = df[f"other_natural_gas_annual_{sfx}"] * df["cost_natural_gas_home"]

    # --- Fixed charges ---
    elec_fixed = df["electricity_fixed_charge_monthly"] * 12.0

    # NG fixed charge: only applied if this config uses any natural gas
    uses_gas = (
        (df[f"heating_system_proportion_gas_{sfx}"] > 0)
        | (df[f"dhw_system_proportion_gas_{sfx}"] > 0)
        | (df[f"other_natural_gas_annual_{sfx}"] > 0)
    )
    ng_fixed = df["natural_gas_fixed_charge_monthly"] * 12.0 * uses_gas.astype(float)

    # --- Panel upgrade (annualized) ---
    panel_cost = df[f"panel_upgrade_cost_{sfx}"]
    panel_life = df[f"panel_assumed_life_{sfx}"]
    discount_rate = df["discount_rate"]
    panel_annual = annualized_capital(panel_cost, discount_rate, panel_life)

    # --- Total ---
    total = other_elec_cost + other_ng_cost + elec_fixed + ng_fixed + panel_annual

    prefix = f"other_{sfx}"
    return {
        f"{prefix}_electricity_cost": other_elec_cost,
        f"{prefix}_natural_gas_cost": other_ng_cost,
        f"{prefix}_electricity_fixed_charge": elec_fixed,
        f"{prefix}_natural_gas_fixed_charge": ng_fixed,
        f"{prefix}_panel_annual_capital": panel_annual,
        f"{prefix}_total_cost": total,
    }
