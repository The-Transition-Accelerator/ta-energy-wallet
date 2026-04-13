"""Step 5: Utility bill perspective — cost breakdown by energy type.

Consumes intermediate columns produced by Step 4 (energy wallet calculations)
and aggregates them into utility-bill categories so costs can be viewed from
the perspective of which bill (electricity, natural gas, gasoline, etc.) they
appear on.
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from .errors import EnergyTypeAnalysisError

logger = logging.getLogger(__name__)

VEHICLE_SLOTS = (1, 2)
SUFFIXES = ("base", "alt")


def _safe_col(df: pd.DataFrame, col: str) -> pd.Series:
    """Get a column or return zeros if it doesn't exist."""
    if col in df.columns:
        return df[col]
    return pd.Series(0.0, index=df.index)


def compute_utility_bill_perspective(step4_output: pd.DataFrame) -> pd.DataFrame:
    """Compute Step 5: utility bill perspective cost breakdown.

    Takes the output of Step 4 (with all intermediate cost columns) and
    produces per-energy-type cost aggregations for base and alt configurations.

    Output columns (for each suffix in {base, alt}):
    - utility_bill_electricity_{s}: HVAC electric heating + cooling + DHW electric
      + other electricity + home EV charging (both slots).
      Includes electricity fixed charge. Excludes public EV charging.
    - utility_bill_natural_gas_{s}: HVAC gas heating + DHW gas + other NG + NG fixed charge
    - utility_bill_oil_{s}: HVAC oil heating + DHW oil
    - utility_bill_propane_{s}: HVAC propane heating + DHW propane
    - utility_bill_wood_{s}: HVAC wood heating + DHW wood
    - utility_bill_gasoline_{s}: Vehicle gasoline costs (both slots)
    - utility_bill_public_ev_charging_{s}: L2 + fast charging costs (both slots)

    Capital and maintenance costs are NOT output columns (they are not utility
    bills). They are computed internally for reconciliation verification only.

    Parameters
    ----------
    step4_output : DataFrame
        Output of Step 4 with all intermediate columns.

    Returns
    -------
    DataFrame with original columns plus utility bill breakdown columns.

    Raises
    ------
    EnergyTypeAnalysisError
        If required Step 4 intermediate columns are missing or totals don't reconcile.
    """
    df = step4_output.copy()
    n_rows = len(df)
    logger.info("Step 5: computing utility bill perspective for %d rows.", n_rows)

    for sfx in SUFFIXES:
        logger.debug("  Computing utility bill for '%s' configuration.", sfx)

        # ---- Electricity ----
        # HVAC electric heating + cooling
        elec = _safe_col(df, f"hvac_{sfx}_heating_electric_cost")
        elec = elec + _safe_col(df, f"hvac_{sfx}_cooling_cost")

        # DHW electric
        elec = elec + _safe_col(df, f"dhw_{sfx}_electric_cost")

        # Other household electricity
        elec = elec + _safe_col(df, f"other_{sfx}_electricity_cost")

        # Electricity fixed charge
        elec = elec + _safe_col(df, f"other_{sfx}_electricity_fixed_charge")

        # Home EV charging (both vehicle slots)
        for slot in VEHICLE_SLOTS:
            elec = elec + _safe_col(df, f"vehicle_{slot}_{sfx}_ev_cost_home")

        df[f"utility_bill_electricity_{sfx}"] = elec

        # ---- Natural Gas ----
        ng = _safe_col(df, f"hvac_{sfx}_heating_gas_cost")
        ng = ng + _safe_col(df, f"dhw_{sfx}_gas_cost")
        ng = ng + _safe_col(df, f"other_{sfx}_natural_gas_cost")
        ng = ng + _safe_col(df, f"other_{sfx}_natural_gas_fixed_charge")
        df[f"utility_bill_natural_gas_{sfx}"] = ng

        # ---- Oil ----
        oil = _safe_col(df, f"hvac_{sfx}_heating_oil_cost")
        oil = oil + _safe_col(df, f"dhw_{sfx}_oil_cost")
        df[f"utility_bill_oil_{sfx}"] = oil

        # ---- Propane ----
        propane = _safe_col(df, f"hvac_{sfx}_heating_propane_cost")
        propane = propane + _safe_col(df, f"dhw_{sfx}_propane_cost")
        df[f"utility_bill_propane_{sfx}"] = propane

        # ---- Wood ----
        wood = _safe_col(df, f"hvac_{sfx}_heating_wood_cost")
        wood = wood + _safe_col(df, f"dhw_{sfx}_wood_cost")
        df[f"utility_bill_wood_{sfx}"] = wood

        # ---- Gasoline ----
        gasoline = pd.Series(0.0, index=df.index)
        for slot in VEHICLE_SLOTS:
            gasoline = gasoline + _safe_col(df, f"vehicle_{slot}_{sfx}_gas_cost")
        df[f"utility_bill_gasoline_{sfx}"] = gasoline

        # ---- Public EV Charging (L2 + fast) ----
        public_ev = pd.Series(0.0, index=df.index)
        for slot in VEHICLE_SLOTS:
            public_ev = public_ev + _safe_col(df, f"vehicle_{slot}_{sfx}_ev_cost_public")
        df[f"utility_bill_public_ev_charging_{sfx}"] = public_ev

        # ---- Reconciliation check ----
        # Compute capital and maintenance locally for cross-step verification
        # (not output columns — they are not utility bills)
        capital = pd.Series(0.0, index=df.index)
        for slot in VEHICLE_SLOTS:
            capital = capital + _safe_col(df, f"vehicle_{slot}_{sfx}_annual_capital")
        capital = capital + _safe_col(df, f"hvac_{sfx}_annual_capital")
        capital = capital + _safe_col(df, f"dhw_{sfx}_annual_capital")
        capital = capital + _safe_col(df, f"other_{sfx}_panel_annual_capital")

        maintenance = pd.Series(0.0, index=df.index)
        for slot in VEHICLE_SLOTS:
            maintenance = maintenance + _safe_col(df, f"vehicle_{slot}_{sfx}_annual_maintenance")
        maintenance = maintenance + _safe_col(df, f"hvac_{sfx}_annual_maintenance")
        maintenance = maintenance + _safe_col(df, f"dhw_{sfx}_annual_maintenance")

        bill_total = elec + ng + oil + propane + wood + gasoline + public_ev
        energy_wallet = _safe_col(df, f"energy_wallet_{sfx}")

        if energy_wallet.sum() != 0:
            full_total = bill_total + capital + maintenance
            max_diff = np.abs(full_total - energy_wallet).max()
            if max_diff > 0.01:  # tolerance for floating point
                logger.warning(
                    "Step 5 reconciliation warning (%s): max difference between "
                    "utility bill + capital + maintenance and energy wallet total = %.4f",
                    sfx,
                    max_diff,
                )

        df[f"utility_bill_total_{sfx}"] = bill_total

    # ---- Comparison metrics for utility bill perspective ----
    # Utility bill categories use utility_bill_ prefix
    for category in [
        "electricity", "natural_gas", "oil", "propane", "wood",
        "gasoline", "public_ev_charging", "total",
    ]:
        base_col = f"utility_bill_{category}_base"
        alt_col = f"utility_bill_{category}_alt"
        if base_col in df.columns and alt_col in df.columns:
            diff = df[alt_col] - df[base_col]
            df[f"utility_bill_{category}_diff"] = diff

    logger.info("Step 5 complete: utility bill perspective columns added.")
    return df
