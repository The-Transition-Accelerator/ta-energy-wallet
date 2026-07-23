"""Step 5: Utility bill perspective — cost breakdown by energy type."""
from __future__ import annotations

import logging

import numpy as np
import polars as pl

from .errors import EnergyTypeAnalysisError

logger = logging.getLogger(__name__)

VEHICLE_SLOTS = (1, 2)
SUFFIXES = ("base", "alt")


def _safe_col(df: pl.DataFrame, col: str) -> pl.Series:
    if col in df.columns:
        return df[col]
    return pl.Series(col, np.zeros(len(df)))


def compute_utility_bill_perspective(step4_output: pl.DataFrame) -> pl.DataFrame:
    df = step4_output
    n_rows = len(df)
    logger.info("Step 5: computing utility bill perspective for %d rows.", n_rows)

    new_cols: dict[str, pl.Series] = {}

    for sfx in SUFFIXES:
        logger.debug("  Computing utility bill for '%s' configuration.", sfx)

        elec = _safe_col(df, f"hvac_{sfx}_heating_electric_cost")
        elec = elec + _safe_col(df, f"hvac_{sfx}_cooling_cost")
        elec = elec + _safe_col(df, f"dhw_{sfx}_electric_cost")
        elec = elec + _safe_col(df, f"other_{sfx}_electricity_cost")
        elec = elec + _safe_col(df, f"other_{sfx}_electricity_fixed_charge")
        for slot in VEHICLE_SLOTS:
            elec = elec + _safe_col(df, f"vehicle_{slot}_{sfx}_ev_cost_home")
        new_cols[f"utility_bill_electricity_{sfx}"] = elec

        ng = _safe_col(df, f"hvac_{sfx}_heating_gas_cost")
        ng = ng + _safe_col(df, f"dhw_{sfx}_gas_cost")
        ng = ng + _safe_col(df, f"other_{sfx}_natural_gas_cost")
        ng = ng + _safe_col(df, f"other_{sfx}_natural_gas_fixed_charge")
        new_cols[f"utility_bill_natural_gas_{sfx}"] = ng

        oil = _safe_col(df, f"hvac_{sfx}_heating_oil_cost")
        oil = oil + _safe_col(df, f"dhw_{sfx}_oil_cost")
        new_cols[f"utility_bill_oil_{sfx}"] = oil

        propane = _safe_col(df, f"hvac_{sfx}_heating_propane_cost")
        propane = propane + _safe_col(df, f"dhw_{sfx}_propane_cost")
        new_cols[f"utility_bill_propane_{sfx}"] = propane

        wood = _safe_col(df, f"hvac_{sfx}_heating_wood_cost")
        wood = wood + _safe_col(df, f"dhw_{sfx}_wood_cost")
        new_cols[f"utility_bill_wood_{sfx}"] = wood

        gasoline = pl.Series("_", np.zeros(n_rows))
        for slot in VEHICLE_SLOTS:
            gasoline = gasoline + _safe_col(df, f"vehicle_{slot}_{sfx}_gas_cost")
        new_cols[f"utility_bill_gasoline_{sfx}"] = gasoline

        public_ev = pl.Series("_", np.zeros(n_rows))
        for slot in VEHICLE_SLOTS:
            public_ev = public_ev + _safe_col(df, f"vehicle_{slot}_{sfx}_ev_cost_public")
        new_cols[f"utility_bill_public_ev_charging_{sfx}"] = public_ev

        # Reconciliation
        capital = pl.Series("_", np.zeros(n_rows))
        for slot in VEHICLE_SLOTS:
            capital = capital + _safe_col(df, f"vehicle_{slot}_{sfx}_annual_capital")
        capital = capital + _safe_col(df, f"hvac_{sfx}_annual_capital")
        capital = capital + _safe_col(df, f"dhw_{sfx}_annual_capital")
        capital = capital + _safe_col(df, f"other_{sfx}_panel_annual_capital")

        maintenance = pl.Series("_", np.zeros(n_rows))
        for slot in VEHICLE_SLOTS:
            maintenance = maintenance + _safe_col(df, f"vehicle_{slot}_{sfx}_annual_maintenance")
        maintenance = maintenance + _safe_col(df, f"hvac_{sfx}_annual_maintenance")
        maintenance = maintenance + _safe_col(df, f"dhw_{sfx}_annual_maintenance")

        bill_total = elec + ng + oil + propane + wood + gasoline + public_ev
        energy_wallet = _safe_col(df, f"energy_wallet_{sfx}")

        if energy_wallet.sum() != 0:
            full_total = bill_total + capital + maintenance
            max_diff = (full_total - energy_wallet).abs().max()
            if max_diff > 0.01:
                logger.warning(
                    "Step 5 reconciliation warning (%s): max difference between "
                    "utility bill + capital + maintenance and energy wallet total = %.4f",
                    sfx,
                    max_diff,
                )

        new_cols[f"utility_bill_total_{sfx}"] = bill_total

    for category in [
        "electricity", "natural_gas", "oil", "propane", "wood",
        "gasoline", "public_ev_charging", "total",
    ]:
        base_key = f"utility_bill_{category}_base"
        alt_key = f"utility_bill_{category}_alt"
        if base_key in new_cols and alt_key in new_cols:
            new_cols[f"utility_bill_{category}_diff"] = new_cols[alt_key] - new_cols[base_key]

    new_df = pl.DataFrame(
        {col: series.rename(col) for col, series in new_cols.items()}
    )
    df = pl.concat([df, new_df], how="horizontal")

    logger.info("Step 5 complete: utility bill perspective columns added.")
    return df
