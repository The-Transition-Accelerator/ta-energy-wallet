from __future__ import annotations

from typing import Dict

import pandas as pd

from .errors import InputParameterJoinError
from .lookup import LookupPlan, build_lookup_plan
from .required import REQUIRED_INPUT_PARAMETERS
from .spec import InputParameterTableSpec
from .validate import validate_final_model_input_table

_REQUIRED_SET: set[str] = set(REQUIRED_INPUT_PARAMETERS)


def _execute_passthrough_join(
    merged: pd.DataFrame,
    name: str,
    table: pd.DataFrame,
    spec: InputParameterTableSpec,
) -> pd.DataFrame:
    """Attach a passthrough table using the original single-join approach."""
    missing_join = [c for c in spec.join_cols if c not in table.columns]
    if missing_join:
        raise InputParameterJoinError(
            f"{name}: missing declared join columns in table: {missing_join}"
        )

    # Columns that can be used to match current merged rows.
    effective_join_cols = [c for c in spec.join_cols if c in merged.columns]
    unavailable_join_cols = [c for c in spec.join_cols if c not in merged.columns]
    invalid_unavailable = [
        c for c in unavailable_join_cols if c != "year" and "scenario" not in c.lower()
    ]
    if invalid_unavailable:
        raise InputParameterJoinError(
            f"{name}: join columns not available in expanded archetypes: {invalid_unavailable}"
        )

    collision_cols = [c for c in spec.input_value_cols if c in merged.columns]
    if collision_cols:
        raise InputParameterJoinError(
            f"{name}: input value columns already exist in merged output: {collision_cols}"
        )

    if effective_join_cols:
        merged = merged.merge(table, on=effective_join_cols, how="left", indicator=True)
    else:
        merged = merged.merge(table, how="cross", indicator=True)

    unmatched = merged[merged["_merge"] == "left_only"]
    if not unmatched.empty:
        sample_cols = effective_join_cols if effective_join_cols else merged.columns[:5].tolist()
        sample = unmatched[sample_cols].head(10)
        raise InputParameterJoinError(
            f"{name}: missing input data coverage for some expanded archetype rows. "
            f"Sample unmatched keys:\n{sample}"
        )
    merged = merged.drop(columns=["_merge"])
    return merged


def _expand_unsuffixed_value_cols(
    merged: pd.DataFrame,
    spec: InputParameterTableSpec,
) -> pd.DataFrame:
    """Duplicate unsuffixed value columns into ``_base`` and ``_alt`` copies.

    When a passthrough table has a value column like ``heating_load_annual``
    (no ``_base``/``_alt`` suffix) and the required-parameter registry expects
    ``heating_load_annual_base`` and ``heating_load_annual_alt``, duplicate the
    column so that downstream calculations can reference both variants.

    Shared parameters (``discount_rate``, ``cost_*``, etc.) are left untouched
    because the required-parameter registry lists them without suffixes.
    """
    for col in spec.input_value_cols:
        # Skip columns that already carry a suffix
        if col.endswith("_base") or col.endswith("_alt"):
            continue
        # Only duplicate if the suffixed version is a required parameter
        col_base = f"{col}_base"
        col_alt = f"{col}_alt"
        if col_base in _REQUIRED_SET and col in merged.columns:
            merged[col_base] = merged[col]
            merged[col_alt] = merged[col]
            merged = merged.drop(columns=[col])
    return merged


def _execute_multi_lookup(
    merged: pd.DataFrame,
    name: str,
    table: pd.DataFrame,
    plan: LookupPlan,
    spec: InputParameterTableSpec,
) -> pd.DataFrame:
    """Execute all lookup specs from a multi-lookup plan.

    For each LookupSpec in the plan:
      1. Take a copy of the input table.
      2. Rename the input table's join columns per the spec's join_col_mapping.
      3. Left-join the renamed table to the merged DataFrame.
      4. Check for unmatched rows.
      5. Rename value columns per the spec's value_col_rename.
      6. Add just the renamed value columns to the main merged DataFrame.
    """
    for lookup_spec in plan.lookups:
        # Build the renamed input table for this lookup
        input_table = table.copy()

        # Rename join columns in the input table to match expanded column names
        join_rename = {}
        for input_col, expanded_col in lookup_spec.join_col_mapping.items():
            if input_col != expanded_col:
                join_rename[input_col] = expanded_col
        if join_rename:
            input_table = input_table.rename(columns=join_rename)

        # The join keys are the expanded column names (values of the mapping)
        expanded_join_cols = list(lookup_spec.join_col_mapping.values())

        # Filter to effective join cols (those present in merged)
        effective_join_cols = [c for c in expanded_join_cols if c in merged.columns]
        if not effective_join_cols:
            raise InputParameterJoinError(
                f"{name}: no effective join columns for lookup "
                f"(suffix={lookup_spec.suffix}). "
                f"Expected columns: {expanded_join_cols}"
            )

        # Check for collision with already-present output columns
        output_col_names = list(lookup_spec.value_col_rename.values())
        collision_cols = [c for c in output_col_names if c in merged.columns]
        if collision_cols:
            raise InputParameterJoinError(
                f"{name}: output value columns already exist in merged output: "
                f"{collision_cols}"
            )

        # Select only the join cols + value cols from the input table for the merge
        input_value_cols_in_table = list(lookup_spec.value_col_rename.keys())
        merge_cols = effective_join_cols + input_value_cols_in_table

        # Ensure all merge cols exist in the input table
        missing_in_table = [c for c in merge_cols if c not in input_table.columns]
        if missing_in_table:
            raise InputParameterJoinError(
                f"{name}: columns missing from input table after rename: "
                f"{missing_in_table}"
            )

        merge_table = input_table[merge_cols].copy()

        # Deduplicate merge table on join keys to avoid row explosion
        # (an input table may have duplicate rows for the same key combination)
        if merge_table.duplicated(subset=effective_join_cols).any():
            merge_table = merge_table.drop_duplicates(subset=effective_join_cols)

        # Perform the left join
        pre_len = len(merged)
        merged = merged.merge(
            merge_table,
            on=effective_join_cols,
            how="left",
            indicator=True,
        )

        # Check for unmatched rows
        unmatched = merged[merged["_merge"] == "left_only"]
        if not unmatched.empty:
            sample = unmatched[effective_join_cols].head(10)
            raise InputParameterJoinError(
                f"{name} (suffix={lookup_spec.suffix}): missing input data coverage. "
                f"Sample unmatched keys:\n{sample}"
            )
        merged = merged.drop(columns=["_merge"])

        # Verify row count didn't change
        if len(merged) != pre_len:
            raise InputParameterJoinError(
                f"{name} (suffix={lookup_spec.suffix}): row count changed during "
                f"lookup join (before={pre_len}, after={len(merged)}). "
                f"This suggests duplicate keys in the input table."
            )

        # Rename value columns to their final output names
        merged = merged.rename(columns=lookup_spec.value_col_rename)

    return merged


def attach_input_parameters(
    expanded_archetypes: pd.DataFrame,
    tables: Dict[str, pd.DataFrame],
    specs: Dict[str, InputParameterTableSpec],
    *,
    validate: bool = True,
) -> pd.DataFrame:
    """Attach Step 3 input parameter tables to expanded archetypes.

    For each table:
      1. Build a LookupPlan via ``build_lookup_plan()``.
      2. If ``plan.is_passthrough``: use the original single-join approach.
      3. If multi-lookup: execute each LookupSpec in sequence.
      4. After all tables: validate the final output.
    """
    if not tables:
        raise InputParameterJoinError("No input parameter tables provided.")
    if set(tables.keys()) != set(specs.keys()):
        raise InputParameterJoinError("Tables/specs keys mismatch.")

    merged = expanded_archetypes.copy()
    expanded_columns = set(expanded_archetypes.columns)

    table_order = sorted(
        specs.keys(),
        key=lambda name: (len(specs[name].join_cols), len(tables[name])),
    )

    for name in table_order:
        spec = specs[name]
        table = tables[name].copy()

        # Build the lookup plan
        plan = build_lookup_plan(
            table_name=name,
            input_join_cols=[
                    c for c in spec.join_cols
                    if "scenario" not in c.lower()
                    and (c != spec.year_col or c in expanded_columns)
                ],
            input_value_cols=spec.input_value_cols,
            expanded_columns=expanded_columns,
        )

        if plan.is_passthrough:
            merged = _execute_passthrough_join(merged, name, table, spec)
            merged = _expand_unsuffixed_value_cols(merged, spec)
        else:
            merged = _execute_multi_lookup(merged, name, table, plan, spec)

        # Update expanded_columns so later tables can join on columns
        # introduced by earlier tables (e.g. year from a cross-joined table).
        expanded_columns = set(merged.columns)

    if validate:
        validate_final_model_input_table(merged)

    return merged
