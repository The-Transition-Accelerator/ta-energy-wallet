"""COP curve collapse: DSPM temperature-dependent COP → annual efficiency.

Uses degree-day-weighted averaging across temperature points from hvac_specs.csv.
For dual-fuel systems with load_share='Varies', the primary system operates above
min_temp_primary and the secondary below it.

Climate-zone-specific weighting uses design heating temperatures to approximate
how much time each CZ spends at each outdoor temperature.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .aggregation import weighted_average

logger = logging.getLogger(__name__)

# Temperature points in hvac_specs.csv columns
HEATING_TEMPS: List[float] = [
    -45, -40, -35, -30, -25, -20, -15, -10, -8.3, -5, 0,
    5, 8.3, 10, 15, 18, 20, 25, 30, 35, 40, 45,
]

COOLING_TEMPS: List[float] = [5, 8.3, 10, 15, 18, 20, 25, 30, 35, 40, 45]

BALANCE_TEMP: float = 18.0


def _cop_col(temp: float, system: str, mode: str = "heating") -> str:
    """Build column name like 'heating_cop_neg_10_primary'."""
    if temp < 0:
        t_str = f"neg_{abs(temp)}"
    else:
        t_str = str(temp)
    t_str = t_str.replace(".0", "").replace(".", ".")
    return f"{mode}_cop_{t_str}_{system}"


def _cap_col(temp: float, system: str, mode: str = "heating") -> str:
    """Build column name like 'heating_cap_neg_10_primary'."""
    if temp < 0:
        t_str = f"neg_{abs(temp)}"
    else:
        t_str = str(temp)
    t_str = t_str.replace(".0", "").replace(".", ".")
    return f"{mode}_cap_{t_str}_{system}"


def estimate_heating_temp_weights(design_temp_heat: float) -> List[float]:
    """Estimate relative heating hours at each HEATING_TEMPS point.

    Uses a linear degree-day proxy: weight at each temperature is
    proportional to (balance_temp - temp), representing the degree-day
    contribution at that outdoor temperature. Temps below the design
    heating temperature get zero weight (rarely reached), and temps
    above the balance point (18C) also get zero (no heating needed).

    For a cold CZ (low design_temp), more of the curve is included.
    For a mild CZ, weights concentrate near the balance point.
    """
    weights = []
    for temp in HEATING_TEMPS:
        if temp < design_temp_heat:
            weights.append(0.0)
        elif temp > BALANCE_TEMP:
            weights.append(0.0)
        else:
            weights.append(max(0.0, BALANCE_TEMP - temp))
    return weights


def estimate_cooling_temp_weights(design_temp_cool: float) -> List[float]:
    """Estimate relative cooling hours at each COOLING_TEMPS point.

    Weight at each temperature proportional to (temp - balance_temp).
    Temps below the balance point get zero. Temps above design cooling
    temperature get capped weight.
    """
    weights = []
    for temp in COOLING_TEMPS:
        if temp < BALANCE_TEMP:
            weights.append(0.0)
        else:
            weights.append(max(0.0, temp - BALANCE_TEMP))
    return weights


def compute_heating_efficiency(
    row: pd.Series,
    temp_weights: Optional[List[float]] = None,
) -> float:
    """Compute annual-average heating efficiency for one HVAC config.

    If temp_weights is provided, uses degree-day-based weighting instead
    of capacity weighting. This makes the result climate-zone-specific.
    """
    load_share_str = str(row.get("load_share_primary", "1"))
    min_temp_primary = row.get("min_temp_primary", -999)
    has_secondary = pd.notna(row.get("equipment_secondary_energy_source"))

    cops: List[float] = []
    caps: List[float] = []

    for i, temp in enumerate(HEATING_TEMPS):
        cop_p = float(row.get(_cop_col(temp, "primary"), 0) or 0)
        cap_p = float(row.get(_cap_col(temp, "primary"), 0) or 0)

        tw = temp_weights[i] if temp_weights else None

        if not has_secondary or load_share_str == "1":
            cops.append(cop_p)
            caps.append(tw if tw is not None else cap_p)
        elif load_share_str == "Varies":
            cop_s = float(row.get(_cop_col(temp, "secondary"), 0) or 0)
            cap_s = float(row.get(_cap_col(temp, "secondary"), 0) or 0)

            if pd.notna(min_temp_primary) and temp < float(min_temp_primary):
                cops.append(cop_s)
                caps.append(tw if tw is not None else cap_s)
            else:
                cops.append(cop_p)
                caps.append(tw if tw is not None else cap_p)
        else:
            share_p = float(load_share_str)
            cop_s = float(row.get(_cop_col(temp, "secondary"), 0) or 0)
            cap_s = float(row.get(_cap_col(temp, "secondary"), 0) or 0)

            effective_cop = cop_p * share_p + cop_s * (1 - share_p)
            effective_cap = cap_p * share_p + cap_s * (1 - share_p)
            cops.append(effective_cop)
            caps.append(tw if tw is not None else effective_cap)

    return weighted_average(cops, caps)


def compute_cooling_efficiency(
    row: pd.Series,
    temp_weights: Optional[List[float]] = None,
) -> float:
    """Compute annual-average cooling efficiency for one HVAC config.

    Returns 0 if the system has no cooling capability.
    """
    has_cooling = row.get("has_cooling", 0)
    if not has_cooling or has_cooling == 0:
        return 0.0

    cops: List[float] = []
    caps: List[float] = []

    for i, temp in enumerate(COOLING_TEMPS):
        cop = float(row.get(_cop_col(temp, "primary", mode="cooling"), 0) or 0)
        cap = float(row.get(_cap_col(temp, "primary", mode="cooling"), 0) or 0)
        tw = temp_weights[i] if temp_weights else None
        cops.append(cop)
        caps.append(tw if tw is not None else cap)

    return weighted_average(cops, caps)


def compute_primary_secondary_efficiencies(
    row: pd.Series,
    temp_weights: Optional[List[float]] = None,
) -> Tuple[float, float]:
    """Compute separate primary and secondary heating efficiencies.

    For single-fuel systems, returns (primary_eff, 0.0).
    For dual-fuel systems, returns efficiencies computed independently
    for the temperature bins where each system operates.
    """
    load_share_str = str(row.get("load_share_primary", "1"))
    min_temp_primary = row.get("min_temp_primary", -999)
    has_secondary = pd.notna(row.get("equipment_secondary_energy_source"))

    if not has_secondary or load_share_str == "1":
        return compute_heating_efficiency(row, temp_weights), 0.0

    primary_cops: List[float] = []
    primary_caps: List[float] = []
    secondary_cops: List[float] = []
    secondary_caps: List[float] = []

    for i, temp in enumerate(HEATING_TEMPS):
        cop_p = float(row.get(_cop_col(temp, "primary"), 0) or 0)
        cap_p = float(row.get(_cap_col(temp, "primary"), 0) or 0)
        cop_s = float(row.get(_cop_col(temp, "secondary"), 0) or 0)
        cap_s = float(row.get(_cap_col(temp, "secondary"), 0) or 0)
        tw = temp_weights[i] if temp_weights else None

        if load_share_str == "Varies":
            if pd.notna(min_temp_primary) and temp < float(min_temp_primary):
                secondary_cops.append(cop_s)
                secondary_caps.append(tw if tw is not None else cap_s)
            else:
                primary_cops.append(cop_p)
                primary_caps.append(tw if tw is not None else cap_p)
        else:
            primary_cops.append(cop_p)
            primary_caps.append(tw if tw is not None else cap_p)
            secondary_cops.append(cop_s)
            secondary_caps.append(tw if tw is not None else cap_s)

    primary_eff = weighted_average(primary_cops, primary_caps)
    secondary_eff = weighted_average(secondary_cops, secondary_caps)

    return primary_eff, secondary_eff


def compute_all_efficiencies_by_cz(
    hvac_specs: pd.DataFrame,
    cz_design_temps: Dict[str, Tuple[float, float]],
) -> pd.DataFrame:
    """Compute heating and cooling efficiencies for all HVAC configs x climate zones.

    Parameters
    ----------
    hvac_specs : DataFrame
        HVAC spec rows with COP/capacity columns.
    cz_design_temps : dict
        {climate_zone: (design_temp_heat, design_temp_cool)} per CZ.

    Returns
    -------
    DataFrame with columns:
        climate_zone, equipment_config_id, heating_efficiency, cooling_efficiency,
        primary_heating_efficiency, secondary_heating_efficiency
    """
    results = []
    for cz, (dt_heat, dt_cool) in sorted(cz_design_temps.items()):
        heat_weights = estimate_heating_temp_weights(dt_heat)
        cool_weights = estimate_cooling_temp_weights(dt_cool)

        for _, row in hvac_specs.iterrows():
            config_id = row["equipment_config_id"]
            heat_eff = compute_heating_efficiency(row, heat_weights)
            cool_eff = compute_cooling_efficiency(row, cool_weights)
            primary_eff, secondary_eff = compute_primary_secondary_efficiencies(
                row, heat_weights
            )
            results.append({
                "climate_zone": cz,
                "equipment_config_id": config_id,
                "heating_efficiency": heat_eff,
                "cooling_efficiency": cool_eff,
                "primary_heating_efficiency": primary_eff,
                "secondary_heating_efficiency": secondary_eff,
            })

    df = pd.DataFrame(results)
    logger.info(
        "Computed efficiencies for %d HVAC configs x %d climate zones = %d rows",
        len(hvac_specs),
        len(cz_design_temps),
        len(df),
    )
    return df
