"""Name and category mapping between DSPM and Energy Wallet conventions."""

from __future__ import annotations

from typing import Dict

import pandas as pd

from .errors import DSPMValidationError


def map_hvac_names(
    df: pd.DataFrame,
    hvac_name_map: Dict[str, str],
    config_id_col: str = "equipment_config_id",
) -> pd.DataFrame:
    """Add an ``ew_hvac_name`` column by mapping DSPM config IDs."""
    df = df.copy()
    df["ew_hvac_name"] = df[config_id_col].map(hvac_name_map)
    unmapped = df[df["ew_hvac_name"].isna()][config_id_col].unique()
    if len(unmapped) > 0:
        raise DSPMValidationError(
            f"Unmapped HVAC config IDs: {sorted(unmapped)}. "
            f"Add them to the HVAC name map."
        )
    return df


def map_dhw_names(
    df: pd.DataFrame,
    dhw_name_map: Dict[str, str],
    config_id_col: str = "equipment_config_id",
) -> pd.DataFrame:
    """Add an ``ew_dhw_name`` column by mapping DSPM config IDs."""
    df = df.copy()
    df["ew_dhw_name"] = df[config_id_col].map(dhw_name_map)
    unmapped = df[df["ew_dhw_name"].isna()][config_id_col].unique()
    if len(unmapped) > 0:
        raise DSPMValidationError(
            f"Unmapped DHW config IDs: {sorted(unmapped)}. "
            f"Add them to the DHW name map."
        )
    return df


def map_climate_zones(
    df: pd.DataFrame,
    climate_zone_map: Dict[str, str],
    col: str = "climate_zone",
) -> pd.DataFrame:
    """Rename climate zone values (e.g., '5' → 'CZ_5')."""
    df = df.copy()
    # Handle potential int/str mismatch
    str_map = {str(k): v for k, v in climate_zone_map.items()}
    original_values = df[col].astype(str)
    df[col] = original_values.map(str_map)
    unmapped_mask = df[col].isna()
    if unmapped_mask.any():
        unmapped_vals = sorted(original_values[unmapped_mask].unique())
        raise DSPMValidationError(
            f"Unmapped climate zones: {unmapped_vals}. "
            f"Add them to the climate zone map."
        )
    return df


def map_fuel_name(dspm_fuel: str, fuel_name_map: Dict[str, str]) -> str:
    """Map a single DSPM fuel name to EW fuel category."""
    mapped = fuel_name_map.get(dspm_fuel)
    if mapped is None:
        raise DSPMValidationError(
            f"Unknown DSPM fuel name '{dspm_fuel}'. "
            f"Add it to the fuel name map. Known: {sorted(fuel_name_map.keys())}"
        )
    return mapped


# The five EW fuel categories in canonical order
EW_FUELS = ("gas", "electric", "oil", "propane", "wood")
