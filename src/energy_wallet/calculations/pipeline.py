"""Step 4 orchestrator: compute full energy wallet for base and alt configurations."""
from __future__ import annotations

import logging
from typing import Dict

import numpy as np
import polars as pl

from .errors import CalculationError
from .vehicle import compute_vehicle_slot_costs
from .hvac import compute_hvac_costs
from .dhw import compute_dhw_costs
from .other import compute_other_costs

logger = logging.getLogger(__name__)

VEHICLE_SLOTS = (1, 2)
SUFFIXES = ("base", "alt")


def compute_energy_wallet(model_inputs: pl.DataFrame) -> pl.DataFrame:
    df = model_inputs
    n_rows = len(df)
    logger.info("Step 4: computing energy wallet for %d archetype rows.", n_rows)

    all_intermediates: Dict[str, pl.Series] = {}

    for sfx in SUFFIXES:
        logger.debug("  Computing costs for '%s' configuration.", sfx)

        vehicle_totals = pl.Series("_", np.zeros(n_rows))
        for slot in VEHICLE_SLOTS:
            try:
                slot_results = compute_vehicle_slot_costs(df, slot=slot, suffix=sfx)
            except (KeyError, pl.exceptions.ColumnNotFoundError) as exc:
                raise CalculationError(
                    f"Missing column for vehicle slot {slot} ({sfx}): {exc}"
                ) from exc
            all_intermediates.update(slot_results)
            vehicle_totals = vehicle_totals + slot_results[f"vehicle_{slot}_{sfx}_total_cost"]
        all_intermediates[f"vehicles_{sfx}_total_cost"] = vehicle_totals

        try:
            hvac_results = compute_hvac_costs(df, suffix=sfx)
        except (KeyError, pl.exceptions.ColumnNotFoundError) as exc:
            raise CalculationError(
                f"Missing column for HVAC ({sfx}): {exc}"
            ) from exc
        all_intermediates.update(hvac_results)

        try:
            dhw_results = compute_dhw_costs(df, suffix=sfx)
        except (KeyError, pl.exceptions.ColumnNotFoundError) as exc:
            raise CalculationError(
                f"Missing column for DHW ({sfx}): {exc}"
            ) from exc
        all_intermediates.update(dhw_results)

        try:
            other_results = compute_other_costs(df, suffix=sfx)
        except (KeyError, pl.exceptions.ColumnNotFoundError) as exc:
            raise CalculationError(
                f"Missing column for other costs ({sfx}): {exc}"
            ) from exc
        all_intermediates.update(other_results)

        energy_wallet = (
            vehicle_totals
            + hvac_results[f"hvac_{sfx}_total_cost"]
            + dhw_results[f"dhw_{sfx}_total_cost"]
            + other_results[f"other_{sfx}_total_cost"]
        )
        all_intermediates[f"energy_wallet_{sfx}"] = energy_wallet

    for sfx in SUFFIXES:
        all_intermediates[f"energy_wallet_vehicle_{sfx}"] = all_intermediates[f"vehicles_{sfx}_total_cost"]
        all_intermediates[f"energy_wallet_home_{sfx}"] = (
            all_intermediates[f"hvac_{sfx}_total_cost"]
            + all_intermediates[f"dhw_{sfx}_total_cost"]
            + all_intermediates[f"other_{sfx}_total_cost"]
        )

    base_total = all_intermediates["energy_wallet_base"]
    alt_total = all_intermediates["energy_wallet_alt"]

    diff_absolute = alt_total - base_total
    all_intermediates["energy_wallet_diff_absolute"] = diff_absolute

    base_arr = base_total.to_numpy()
    diff_arr = diff_absolute.to_numpy()
    diff_pct = np.where(base_arr != 0, diff_arr / base_arr * 100.0, 0.0)
    all_intermediates["energy_wallet_diff_percent"] = pl.Series("_", diff_pct)

    all_intermediates["energy_wallet_vehicle_diff_absolute"] = (
        all_intermediates["energy_wallet_vehicle_alt"] - all_intermediates["energy_wallet_vehicle_base"]
    )
    all_intermediates["energy_wallet_home_diff_absolute"] = (
        all_intermediates["energy_wallet_home_alt"] - all_intermediates["energy_wallet_home_base"]
    )

    intermediates_df = pl.DataFrame(
        {col: series.rename(col) for col, series in all_intermediates.items()}
    )
    df = pl.concat([df, intermediates_df], how="horizontal")

    logger.info(
        "Step 4 complete: %d cost columns added, %d total columns.",
        len(all_intermediates),
        len(df.columns),
    )
    return df
