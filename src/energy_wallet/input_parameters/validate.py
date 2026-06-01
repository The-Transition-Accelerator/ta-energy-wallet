from __future__ import annotations

import numpy as np
import pandas as pd

from .errors import InputParameterTableError
from .required import REQUIRED_INPUT_PARAMETERS
from .spec import InputParameterTableSpec
from energy_wallet.validation.common import (
    require_columns_present,
    require_no_duplicates,
    require_numeric_series,
)


def validate_input_parameter_table(df: pd.DataFrame, spec: InputParameterTableSpec) -> None:
    """Validate one input parameter table (Step 3 table-level rules).

    For tech-type tables (no _base/_alt suffixes on value columns), proportion
    and efficiency checks still apply to the raw column names.
    """
    require_columns_present(
        df,
        spec.join_cols + spec.input_value_cols,
        source_name=spec.path.name,
        error_cls=InputParameterTableError,
    )

    if not spec.input_value_cols:
        raise InputParameterTableError(f"{spec.path.name}: table must contain one or more input value columns")

    for col in spec.input_value_cols:
        series = df[col]
        require_numeric_series(
            series,
            source_name=spec.path.name,
            error_cls=InputParameterTableError,
        )
        if series.isna().any():
            raise InputParameterTableError(f"{spec.path.name}: input column '{col}' contains missing values")
        if col == "discount_rate":
            if (series <= 0).any():
                raise InputParameterTableError(
                    f"{spec.path.name}: 'discount_rate' must be strictly positive"
                )
        else:
            if (series < 0).any():
                raise InputParameterTableError(
                    f"{spec.path.name}: input column '{col}' must be non-negative"
                )

        if ("_proportion_" in col or "ev_pct_charged_" in col or "pct_charged_" in col) and (
            (series < 0).any() or (series > 1).any()
        ):
            raise InputParameterTableError(
                f"{spec.path.name}: proportion column '{col}' must be between 0 and 1"
            )

    _validate_efficiency_vs_proportions(df, source_name=spec.path.name)

    # Reject duplicate dimension keys in one table.
    if spec.join_cols:
        require_no_duplicates(
            df,
            subset=spec.join_cols,
            source_name=spec.path.name,
            error_cls=InputParameterTableError,
        )
    elif len(df) != 1:
        raise InputParameterTableError(
            f"{spec.path.name}: table with no join columns must have exactly one row"
        )


def validate_cross_table_parameter_registry(
    specs: list[InputParameterTableSpec],
    *,
    required_parameters: tuple[str, ...] = REQUIRED_INPUT_PARAMETERS,
    strict: bool = False,
) -> None:
    """Validate duplicate/missing required parameters across all input tables.

    When *strict* is False (default for Phase 3B), multi-lookup tables are
    excluded from the missing-parameter check because their raw value columns
    don't yet have the final _base/_alt/_slot names.  The primary coverage
    validation happens at the final output level via
    ``validate_final_model_input_table``.
    """
    seen: dict[str, str] = {}
    duplicates: dict[str, list[str]] = {}

    for spec in specs:
        for col in spec.input_value_cols:
            if col in seen:
                duplicates.setdefault(col, [seen[col]]).append(spec.path.name)
            else:
                seen[col] = spec.path.name

    if duplicates:
        raise InputParameterTableError(
            f"Duplicate input parameter columns across tables: {duplicates}"
        )

    if strict:
        missing_required = [p for p in required_parameters if p not in seen]
        if missing_required:
            raise InputParameterTableError(
                f"Missing required input parameters: {missing_required[:20]}"
            )


def validate_final_model_input_table(
    model_input_df: pd.DataFrame,
    *,
    required_parameters: tuple[str, ...] = REQUIRED_INPUT_PARAMETERS,
) -> None:
    """Validate final joined Step 3 output table."""
    missing_cols = [p for p in required_parameters if p not in model_input_df.columns]
    if missing_cols:
        raise InputParameterTableError(
            f"Final model input table is missing required parameters: {missing_cols[:20]}"
        )

    req_cols = list(required_parameters)
    if model_input_df[req_cols].isna().any().any():
        raise InputParameterTableError("Final model input table contains missing parameter values")

    # Validate assumed_life >= 1 to avoid division by zero in annualization.
    life_cols = [c for c in model_input_df.columns if "assumed_life" in c]
    for col in life_cols:
        if (model_input_df[col] < 1).any():
            raise InputParameterTableError(
                f"Final model input table has assumed_life < 1 in column '{col}'"
            )

    proportion_cols = [
        c for c in model_input_df.columns
        if "_proportion_" in c or "pct_charged_" in c
    ]
    for col in proportion_cols:
        s = model_input_df[col]
        if (s < 0).any() or (s > 1).any():
            raise InputParameterTableError(
                f"Final model input table has out-of-range proportion column '{col}'"
            )

    _validate_efficiency_vs_proportions(model_input_df, source_name="final model input table")

    # EV charging sums: per slot and suffix.
    for n in (1, 2):
        for suffix in ("base", "alt"):
            cols = [
                f"ev_{n}_pct_charged_home_{suffix}",
                f"ev_{n}_pct_charged_level2_{suffix}",
                f"ev_{n}_pct_charged_fast_{suffix}",
            ]
            if all(c in model_input_df.columns for c in cols):
                sums = model_input_df[cols].sum(axis=1)
                active_mask = pd.Series([True] * len(model_input_df), index=model_input_df.index)
                eff_col = f"vehicle_{n}_efficiency_electric_{suffix}"
                if eff_col in model_input_df.columns:
                    active_mask = model_input_df[eff_col] > 0
                bad = active_mask & ((sums - 1.0).abs() > 1e-3)
                if bad.any():
                    raise InputParameterTableError(
                        f"Final model input table violates EV charging share sum=1 "
                        f"for slot {n}, '{suffix}'"
                    )

    # Heating/DHW fuel proportion sums.
    systems = ("heating_system", "dhw_system")
    fuels = ("gas", "electric", "oil", "propane", "wood")
    for system in systems:
        for suffix in ("base", "alt"):
            cols = [f"{system}_proportion_{fuel}_{suffix}" for fuel in fuels]
            if all(c in model_input_df.columns for c in cols):
                sums = model_input_df[cols].sum(axis=1)
                bad = (sums - 1.0).abs() > 1e-3
                if bad.any():
                    raise InputParameterTableError(
                        f"Final model input table violates {system} fuel proportion sum=1 for '{suffix}'"
                    )


def _validate_efficiency_vs_proportions(df: pd.DataFrame, *, source_name: str) -> None:
    """Validate that efficiency > 0 whenever the corresponding fuel proportion > 0.

    Handles both the old naming scheme (no slot numbers) and the new per-slot
    naming scheme (vehicle_{N}_efficiency_...).
    """
    fuels = ("gas", "electric", "oil", "propane", "wood")
    systems = ("heating_system", "dhw_system")

    # System fuel efficiencies: enforce >0 only when corresponding fuel proportion >0.
    for system in systems:
        for suffix in ("base", "alt"):
            for fuel in fuels:
                p_col = f"{system}_proportion_{fuel}_{suffix}"
                e_col = f"{system}_efficiency_{fuel}_{suffix}"
                if p_col in df.columns and e_col in df.columns:
                    active = df[p_col] > 0
                    bad = active & (df[e_col] <= 0)
                    if bad.any():
                        raise InputParameterTableError(
                            f"{source_name}: '{e_col}' must be > 0 whenever '{p_col}' > 0"
                        )

    # Also check raw (unsuffixed) columns for table-level validation
    for system in systems:
        for fuel in fuels:
            p_col = f"{system}_proportion_{fuel}"
            e_col = f"{system}_efficiency_{fuel}"
            if p_col in df.columns and e_col in df.columns:
                active = df[p_col] > 0
                bad = active & (df[e_col] <= 0)
                if bad.any():
                    raise InputParameterTableError(
                        f"{source_name}: '{e_col}' must be > 0 whenever '{p_col}' > 0"
                    )

    # Vehicle fuel efficiencies: per-slot naming (vehicle_{N}_efficiency_...)
    for n in (1, 2):
        for suffix in ("base", "alt"):
            gas_col = f"vehicle_{n}_efficiency_gas_{suffix}"
            elec_col = f"vehicle_{n}_efficiency_electric_{suffix}"
            if gas_col in df.columns and elec_col in df.columns:
                # Skip rows where both are zero ("none" vehicle type).
                either_active = (df[gas_col] > 0) | (df[elec_col] > 0)
                pairs = (
                    (gas_col, elec_col),
                    (elec_col, gas_col),
                )
                for primary, other in pairs:
                    active = either_active & (df[other] == 0)
                    bad = active & (df[primary] <= 0)
                    if bad.any():
                        raise InputParameterTableError(
                            f"{source_name}: '{primary}' must be > 0 for rows where "
                            f"it is the active vehicle fuel mode"
                        )

    # Legacy vehicle naming (no slot number) for table-level validation
    for suffix in ("base", "alt", ""):
        suffix_str = f"_{suffix}" if suffix else ""
        gas_col = f"vehicle_efficiency_gas{suffix_str}"
        elec_col = f"vehicle_efficiency_electric{suffix_str}"
        if gas_col in df.columns and elec_col in df.columns:
            # Skip rows where both are zero ("none" vehicle type).
            either_active = (df[gas_col] > 0) | (df[elec_col] > 0)
            pairs = (
                (gas_col, elec_col),
                (elec_col, gas_col),
            )
            for primary, other in pairs:
                active = either_active & (df[other] == 0)
                bad = active & (df[primary] <= 0)
                if bad.any():
                    raise InputParameterTableError(
                        f"{source_name}: '{primary}' must be > 0 for rows where "
                        f"it is the active vehicle fuel mode"
                    )

    # Remaining efficiency columns that are not fuel-switched should be strictly positive.
    skip_patterns = (
        "heating_system_efficiency_",
        "dhw_system_efficiency_",
        "cooling_system_efficiency",
        "vehicle_efficiency_gas",
        "vehicle_efficiency_electric",
    )
    # Also skip per-slot vehicle efficiency patterns
    for n in (1, 2):
        skip_patterns = skip_patterns + (
            f"vehicle_{n}_efficiency_gas",
            f"vehicle_{n}_efficiency_electric",
        )

    for col in [c for c in df.columns if "efficiency" in c]:
        if any(token in col for token in skip_patterns):
            continue
        if (df[col] <= 0).any():
            raise InputParameterTableError(f"{source_name}: non-positive efficiency column '{col}'")
