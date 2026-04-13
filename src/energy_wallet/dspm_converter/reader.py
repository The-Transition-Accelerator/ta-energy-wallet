"""DSPM data file readers.

Each function loads one CSV from a DSPM data library,
optionally filtering by province.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional

import pandas as pd

from .errors import DSPMDataError

logger = logging.getLogger(__name__)


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise DSPMDataError(f"DSPM data file not found: {path}")
    df = pd.read_csv(path)
    logger.info("Loaded %s: %d rows", path.name, len(df))
    return df


def _filter_province(df: pd.DataFrame, province: str, filename: str) -> pd.DataFrame:
    if "province_territory" not in df.columns:
        raise DSPMDataError(f"{filename}: missing 'province_territory' column")
    filtered = df[df["province_territory"] == province].copy()
    if filtered.empty:
        raise DSPMDataError(
            f"{filename}: no rows for province '{province}'. "
            f"Available: {sorted(df['province_territory'].unique())}"
        )
    logger.info("Filtered %s to province %s: %d rows", filename, province, len(filtered))
    return filtered


def _filter_residential(
    df: pd.DataFrame, building_types: List[str], filename: str
) -> pd.DataFrame:
    if "building_type" in df.columns:
        keep_types = set(building_types) | {"all"}
        filtered = df[df["building_type"].isin(keep_types)].copy()
        logger.info(
            "Filtered %s to residential types %s: %d rows",
            filename,
            building_types,
            len(filtered),
        )
        return filtered
    return df


def load_building_stock(
    library_path: Path, province: Optional[str], building_types: List[str]
) -> pd.DataFrame:
    path = library_path / "building_stock_library.csv"
    df = _read_csv(path)
    if province is not None:
        df = _filter_province(df, province, path.name)
    df = _filter_residential(df, building_types, path.name)
    return df


def load_hvac_specs(library_path: Path) -> pd.DataFrame:
    path = library_path / "hvac_specs.csv"
    df = _read_csv(path)
    res = df[df["equipment_config_id"].str.contains("_res_", na=False)].copy()
    logger.info("Filtered hvac_specs to residential: %d rows", len(res))
    return res


def load_dhw_specs(library_path: Path) -> pd.DataFrame:
    path = library_path / "dhw_specs.csv"
    df = _read_csv(path)
    res = df[df["equipment_config_id"].str.contains("_res_", na=False)].copy()
    logger.info("Filtered dhw_specs to residential: %d rows", len(res))
    return res


def load_equipment_categorization(library_path: Path) -> pd.DataFrame:
    path = library_path / "equipment_categorization.csv"
    df = _read_csv(path)
    res = df[df["sector"] == "res"].copy() if "sector" in df.columns else df.copy()
    return res


def load_equipment_shares(
    library_path: Path, province: Optional[str], building_types: List[str]
) -> pd.DataFrame:
    path = library_path / "equipment_shares_base_year.csv"
    df = _read_csv(path)
    if province is not None:
        df = _filter_province(df, province, path.name)
    if "sector" in df.columns:
        df = df[df["sector"] == "res"].copy()
    df = _filter_residential(df, building_types, path.name)
    return df


def load_design_temperatures(library_path: Path) -> pd.DataFrame:
    path = library_path / "design_temperatures.csv"
    return _read_csv(path)


def load_building_envelope_bins(library_path: Path) -> pd.DataFrame:
    path = library_path / "building_envelope_bins.csv"
    return _read_csv(path)


def get_available_provinces(library_path: Path) -> List[str]:
    """Read building_stock_library.csv and return sorted list of provinces."""
    path = library_path / "building_stock_library.csv"
    df = _read_csv(path)
    return sorted(df["province_territory"].unique())
