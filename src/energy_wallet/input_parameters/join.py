from __future__ import annotations

from typing import Dict

import polars as pl

from .errors import InputParameterJoinError
from .lookup import LookupPlan, build_lookup_plan
from .required import REQUIRED_INPUT_PARAMETERS
from .spec import InputParameterTableSpec
from .validate import validate_final_model_input_table

_REQUIRED_SET: set[str] = set(REQUIRED_INPUT_PARAMETERS)


def _execute_passthrough_join(
    merged: pl.DataFrame,
    name: str,
    table: pl.DataFrame,
    spec: InputParameterTableSpec,
) -> pl.DataFrame:
    missing_join = [c for c in spec.join_cols if c not in table.columns]
    if missing_join:
        raise InputParameterJoinError(
            f"{name}: missing declared join columns in table: {missing_join}"
        )

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
        result = merged.join(table, on=effective_join_cols, how="left")
        unmatched = merged.join(table.select(effective_join_cols).unique(), on=effective_join_cols, how="anti")
    else:
        result = merged.join(table, how="cross")
        unmatched = pl.DataFrame()

    if len(unmatched) > 0:
        sample_cols = effective_join_cols if effective_join_cols else merged.columns[:5]
        sample = unmatched.select(sample_cols).head(10)
        raise InputParameterJoinError(
            f"{name}: missing input data coverage for some expanded archetype rows. "
            f"Sample unmatched keys:\n{sample}"
        )
    return result


def _expand_unsuffixed_value_cols(
    merged: pl.DataFrame,
    spec: InputParameterTableSpec,
) -> pl.DataFrame:
    new_cols = []
    drop_cols = []
    for col in spec.input_value_cols:
        if col.endswith("_base") or col.endswith("_alt"):
            continue
        col_base = f"{col}_base"
        col_alt = f"{col}_alt"
        if col_base in _REQUIRED_SET and col in merged.columns:
            new_cols.append(pl.col(col).alias(col_base))
            new_cols.append(pl.col(col).alias(col_alt))
            drop_cols.append(col)

    if new_cols:
        merged = merged.with_columns(new_cols).drop(drop_cols)
    return merged


def _execute_multi_lookup(
    merged: pl.DataFrame,
    name: str,
    table: pl.DataFrame,
    plan: LookupPlan,
    spec: InputParameterTableSpec,
) -> pl.DataFrame:
    for lookup_spec in plan.lookups:
        input_table = table.clone()

        join_rename = {}
        for input_col, expanded_col in lookup_spec.join_col_mapping.items():
            if input_col != expanded_col:
                join_rename[input_col] = expanded_col
        if join_rename:
            input_table = input_table.rename(join_rename)

        expanded_join_cols = list(lookup_spec.join_col_mapping.values())

        effective_join_cols = [c for c in expanded_join_cols if c in merged.columns]
        if not effective_join_cols:
            raise InputParameterJoinError(
                f"{name}: no effective join columns for lookup "
                f"(suffix={lookup_spec.suffix}). "
                f"Expected columns: {expanded_join_cols}"
            )

        output_col_names = list(lookup_spec.value_col_rename.values())
        collision_cols = [c for c in output_col_names if c in merged.columns]
        if collision_cols:
            raise InputParameterJoinError(
                f"{name}: output value columns already exist in merged output: "
                f"{collision_cols}"
            )

        input_value_cols_in_table = list(lookup_spec.value_col_rename.keys())
        merge_cols = effective_join_cols + input_value_cols_in_table

        missing_in_table = [c for c in merge_cols if c not in input_table.columns]
        if missing_in_table:
            raise InputParameterJoinError(
                f"{name}: columns missing from input table after rename: "
                f"{missing_in_table}"
            )

        merge_table = input_table.select(merge_cols).unique(subset=effective_join_cols)

        pre_len = len(merged)
        result = merged.join(merge_table, on=effective_join_cols, how="left")

        unmatched_count = merged.join(
            merge_table.select(effective_join_cols).unique(),
            on=effective_join_cols,
            how="anti",
        ).height
        if unmatched_count > 0:
            sample = merged.join(
                merge_table.select(effective_join_cols).unique(),
                on=effective_join_cols,
                how="anti",
            ).select(effective_join_cols).head(10)
            raise InputParameterJoinError(
                f"{name} (suffix={lookup_spec.suffix}): missing input data coverage. "
                f"Sample unmatched keys:\n{sample}"
            )
        merged = result

        if len(merged) != pre_len:
            raise InputParameterJoinError(
                f"{name} (suffix={lookup_spec.suffix}): row count changed during "
                f"lookup join (before={pre_len}, after={len(merged)}). "
                f"This suggests duplicate keys in the input table."
            )

        merged = merged.rename(lookup_spec.value_col_rename)

    return merged


def attach_input_parameters(
    expanded_archetypes: pl.DataFrame,
    tables: Dict[str, pl.DataFrame],
    specs: Dict[str, InputParameterTableSpec],
    *,
    validate: bool = True,
) -> pl.DataFrame:
    if not tables:
        raise InputParameterJoinError("No input parameter tables provided.")
    if set(tables.keys()) != set(specs.keys()):
        raise InputParameterJoinError("Tables/specs keys mismatch.")

    merged = expanded_archetypes
    expanded_columns = set(expanded_archetypes.columns)

    table_order = sorted(
        specs.keys(),
        key=lambda name: (len(specs[name].join_cols), len(tables[name])),
    )

    for name in table_order:
        spec = specs[name]
        table = tables[name]

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

        expanded_columns = set(merged.columns)

    if validate:
        validate_final_model_input_table(merged)

    return merged
