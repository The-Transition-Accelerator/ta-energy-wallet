"""Fuel proportion conversion: DSPM primary+secondary fuel → EW 5-fuel vector.

Produces [gas, electric, oil, propane, wood] summing to 1.0 for each HVAC config.
Climate-zone-specific: uses degree-day temperature weights for dual-fuel systems.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

import pandas as pd

from .efficiency import HEATING_TEMPS, _cap_col, estimate_heating_temp_weights
from .aggregation import weighted_average
from .mapping import EW_FUELS, map_fuel_name

logger = logging.getLogger(__name__)


def compute_fuel_proportions(
    row: pd.Series,
    fuel_name_map: Dict[str, str],
    temp_weights: Optional[List[float]] = None,
) -> Dict[str, float]:
    """Compute EW fuel proportion vector for one HVAC config.

    For single-fuel systems: 100% goes to the primary fuel.
    For dual-fuel systems: uses temperature weights (if provided) or
    capacity weights to compute load sharing across temperature bins.
    """
    proportions = {fuel: 0.0 for fuel in EW_FUELS}

    primary_fuel_dspm = row["equipment_primary_energy_source"]
    primary_fuel_ew = map_fuel_name(primary_fuel_dspm, fuel_name_map)

    has_secondary = pd.notna(row.get("equipment_secondary_energy_source"))
    load_share_str = str(row.get("load_share_primary", "1"))

    if not has_secondary or load_share_str == "1":
        proportions[primary_fuel_ew] = 1.0
        return proportions

    secondary_fuel_dspm = row["equipment_secondary_energy_source"]
    secondary_fuel_ew = map_fuel_name(secondary_fuel_dspm, fuel_name_map)

    if load_share_str == "Varies":
        min_temp = float(row.get("min_temp_primary", -999))
        primary_load: float = 0.0
        secondary_load: float = 0.0

        for i, temp in enumerate(HEATING_TEMPS):
            cap_p = float(row.get(_cap_col(temp, "primary"), 0) or 0)
            cap_s = float(row.get(_cap_col(temp, "secondary"), 0) or 0)
            tw = temp_weights[i] if temp_weights else 1.0

            if temp < min_temp:
                secondary_load += cap_s * tw
            else:
                primary_load += cap_p * tw

        total = primary_load + secondary_load
        if total > 0:
            proportions[primary_fuel_ew] += primary_load / total
            proportions[secondary_fuel_ew] += secondary_load / total
        else:
            proportions[primary_fuel_ew] += 0.5
            proportions[secondary_fuel_ew] += 0.5
    else:
        share_p = float(load_share_str)
        proportions[primary_fuel_ew] += share_p
        proportions[secondary_fuel_ew] += 1.0 - share_p

    return proportions


def compute_all_fuel_proportions_by_cz(
    hvac_specs: pd.DataFrame,
    cz_design_temps: Dict[str, Tuple[float, float]],
    fuel_name_map: Dict[str, str],
) -> pd.DataFrame:
    """Compute fuel proportion vectors for all HVAC configs x climate zones.

    Parameters
    ----------
    hvac_specs : DataFrame
        HVAC spec rows.
    cz_design_temps : dict
        {climate_zone: (design_temp_heat, design_temp_cool)} per CZ.
    fuel_name_map : dict
        DSPM fuel name → EW fuel name.

    Returns
    -------
    DataFrame with columns:
        climate_zone, equipment_config_id,
        proportion_gas, proportion_electric, proportion_oil,
        proportion_propane, proportion_wood
    """
    results = []
    for cz, (dt_heat, _dt_cool) in sorted(cz_design_temps.items()):
        heat_weights = estimate_heating_temp_weights(dt_heat)

        for _, row in hvac_specs.iterrows():
            config_id = row["equipment_config_id"]
            props = compute_fuel_proportions(row, fuel_name_map, heat_weights)
            result = {
                "climate_zone": cz,
                "equipment_config_id": config_id,
            }
            for fuel in EW_FUELS:
                result[f"proportion_{fuel}"] = props[fuel]
            results.append(result)

    df = pd.DataFrame(results)

    # Validate proportions sum to 1.0
    prop_cols = [f"proportion_{f}" for f in EW_FUELS]
    sums = df[prop_cols].sum(axis=1)
    bad = sums[~sums.between(0.999, 1.001)]
    if len(bad) > 0:
        logger.warning(
            "Fuel proportions don't sum to 1.0 for %d rows: %s",
            len(bad),
            bad.to_dict(),
        )

    logger.info(
        "Computed fuel proportions for %d HVAC configs x %d climate zones = %d rows",
        len(hvac_specs),
        len(cz_design_temps),
        len(df),
    )
    return df
