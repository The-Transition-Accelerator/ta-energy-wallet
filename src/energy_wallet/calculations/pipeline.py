"""Step 4 orchestrator: compute full energy wallet for base and alt configurations."""
from __future__ import annotations

import logging
from typing import Dict

import numpy as np
import pandas as pd

from .errors import CalculationError
from .vehicle import compute_vehicle_slot_costs
from .hvac import compute_hvac_costs
from .dhw import compute_dhw_costs
from .other import compute_other_costs

logger = logging.getLogger(__name__)

VEHICLE_SLOTS = (1, 2)
SUFFIXES = ("base", "alt")


def compute_energy_wallet(model_inputs: pd.DataFrame) -> pd.DataFrame:
    """Compute the full energy wallet cost model (Step 4).

    Takes the output of Step 3 (model_inputs with all parameters attached)
    and computes annualized costs for every component, then aggregates
    into total energy wallet costs for base and alt configurations.

    Parameters
    ----------
    model_inputs : DataFrame
        Step 3 output with all archetype + input parameter columns.

    Returns
    -------
    DataFrame
        Original columns plus all intermediate and summary cost columns.

    Raises
    ------
    CalculationError
        If required columns are missing or calculations produce invalid results.
    """
    df = model_inputs.copy()
    n_rows = len(df)
    logger.info("Step 4: computing energy wallet for %d archetype rows.", n_rows)

    all_intermediates: Dict[str, pd.Series] = {}

    for sfx in SUFFIXES:
        logger.debug("  Computing costs for '%s' configuration.", sfx)

        # --- Vehicles (2 slots) ---
        vehicle_totals = pd.Series(0.0, index=df.index)
        for slot in VEHICLE_SLOTS:
            try:
                slot_results = compute_vehicle_slot_costs(df, slot=slot, suffix=sfx)
            except KeyError as exc:
                raise CalculationError(
                    f"Missing column for vehicle slot {slot} ({sfx}): {exc}"
                ) from exc
            all_intermediates.update(slot_results)
            vehicle_totals = vehicle_totals + slot_results[f"vehicle_{slot}_{sfx}_total_cost"]
        all_intermediates[f"vehicles_{sfx}_total_cost"] = vehicle_totals

        # --- HVAC ---
        try:
            hvac_results = compute_hvac_costs(df, suffix=sfx)
        except KeyError as exc:
            raise CalculationError(
                f"Missing column for HVAC ({sfx}): {exc}"
            ) from exc
        all_intermediates.update(hvac_results)

        # --- DHW ---
        try:
            dhw_results = compute_dhw_costs(df, suffix=sfx)
        except KeyError as exc:
            raise CalculationError(
                f"Missing column for DHW ({sfx}): {exc}"
            ) from exc
        all_intermediates.update(dhw_results)

        # --- Other (other energy + fixed charges + panel upgrade) ---
        try:
            other_results = compute_other_costs(df, suffix=sfx)
        except KeyError as exc:
            raise CalculationError(
                f"Missing column for other costs ({sfx}): {exc}"
            ) from exc
        all_intermediates.update(other_results)

        # --- Grand total for this configuration ---
        energy_wallet = (
            vehicle_totals
            + hvac_results[f"hvac_{sfx}_total_cost"]
            + dhw_results[f"dhw_{sfx}_total_cost"]
            + other_results[f"other_{sfx}_total_cost"]
        )
        all_intermediates[f"energy_wallet_{sfx}"] = energy_wallet

    # --- Domain sub-totals ---
    for sfx in SUFFIXES:
        all_intermediates[f"energy_wallet_vehicle_{sfx}"] = all_intermediates[f"vehicles_{sfx}_total_cost"]
        all_intermediates[f"energy_wallet_home_{sfx}"] = (
            all_intermediates[f"hvac_{sfx}_total_cost"]
            + all_intermediates[f"dhw_{sfx}_total_cost"]
            + all_intermediates[f"other_{sfx}_total_cost"]
        )

    # --- Comparison metrics ---
    base_total = all_intermediates["energy_wallet_base"]
    alt_total = all_intermediates["energy_wallet_alt"]

    diff_absolute = alt_total - base_total
    all_intermediates["energy_wallet_diff_absolute"] = diff_absolute

    # Percent difference: (alt - base) / base * 100
    # Guard against division by zero where base = 0
    diff_pct = np.where(
        base_total != 0,
        diff_absolute / base_total * 100.0,
        0.0,
    )
    all_intermediates["energy_wallet_diff_percent"] = pd.Series(
        diff_pct, index=df.index
    )

    all_intermediates["energy_wallet_vehicle_diff_absolute"] = (
        all_intermediates["energy_wallet_vehicle_alt"] - all_intermediates["energy_wallet_vehicle_base"]
    )
    all_intermediates["energy_wallet_home_diff_absolute"] = (
        all_intermediates["energy_wallet_home_alt"] - all_intermediates["energy_wallet_home_base"]
    )

    # --- Attach all intermediates to the output DataFrame ---
    # Use pd.concat to avoid fragmentation warnings from repeated column insertion.
    intermediates_df = pd.DataFrame(
        {col: series.values for col, series in all_intermediates.items()},
        index=df.index,
    )
    df = pd.concat([df, intermediates_df], axis=1)

    logger.info(
        "Step 4 complete: %d cost columns added, %d total columns.",
        len(all_intermediates),
        len(df.columns),
    )
    return df
