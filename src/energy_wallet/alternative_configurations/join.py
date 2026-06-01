from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import pandas as pd

from .errors import AlternativeConfigJoinError
from .spec import AlternativeConfigTableSpec
from .validate import validate_expanded_output


def _toposort_tables(
    specs: Dict[str, AlternativeConfigTableSpec],
    tables: Optional[Dict[str, pd.DataFrame]] = None,
) -> List[str]:
    introduced_by: Dict[str, str] = {}
    for name, spec in specs.items():
        if spec.new_alt_var_col in introduced_by:
            prev = introduced_by[spec.new_alt_var_col]
            raise AlternativeConfigJoinError(
                f"Duplicate alt variable '{spec.new_alt_var_col}' introduced by both '{prev}' and '{name}'"
            )
        introduced_by[spec.new_alt_var_col] = name

    deps = {name: set() for name in specs}
    for name, spec in specs.items():
        for c in spec.conditioning_cols:
            if c in introduced_by:
                deps[name].add(introduced_by[c])

    remaining = set(specs.keys())
    ordered: List[str] = []

    def _size_key(t: str) -> Tuple[int, str]:
        if tables is None:
            return (0, t)
        return (len(tables[t]), t)

    ready = sorted([t for t in remaining if not deps[t]], key=_size_key)
    while ready:
        t = ready.pop(0)
        ordered.append(t)
        remaining.remove(t)
        for other in list(remaining):
            if t in deps[other]:
                deps[other].remove(t)
                if not deps[other]:
                    ready.append(other)
        ready.sort(key=_size_key)

    if remaining:
        cycle_info = {t: sorted(deps[t]) for t in remaining}
        raise AlternativeConfigJoinError(
            "Cannot resolve alternative table merge order (cycle or unresolved dependencies).\n"
            f"Remaining tables with deps: {cycle_info}"
        )

    return ordered


def merge_alternative_configurations(
    baseline_archetypes: pd.DataFrame,
    tables: Dict[str, pd.DataFrame],
    specs: Dict[str, AlternativeConfigTableSpec],
    *,
    baseline_weight_col: str = "population_weight",
    expanded_weight_col: str = "population_weight",
    keep_provenance_shares: bool = False,
    tolerance: float = 1e-3,
    validate: bool = True,
) -> pd.DataFrame:
    """Expand baseline archetypes with Step 2 alternative configuration tables."""
    if baseline_weight_col not in baseline_archetypes.columns:
        raise AlternativeConfigJoinError(
            f"Baseline archetypes missing weight column '{baseline_weight_col}'"
        )

    if not tables:
        raise AlternativeConfigJoinError("No alternative configuration tables provided.")

    if set(tables.keys()) != set(specs.keys()):
        raise AlternativeConfigJoinError("Tables/specs keys mismatch.")

    order = _toposort_tables(specs, tables=tables)

    merged = baseline_archetypes.copy()
    baseline_id_col = "__baseline_row_id"
    if baseline_id_col in merged.columns:
        raise AlternativeConfigJoinError(
            f"Reserved internal column already exists in baseline data: {baseline_id_col}"
        )

    merged[baseline_id_col] = range(len(merged))
    merged["__baseline_weight"] = merged[baseline_weight_col]
    if expanded_weight_col != baseline_weight_col:
        merged[expanded_weight_col] = merged[baseline_weight_col]

    scenario_cols_all: List[str] = []

    for name in order:
        cur = tables[name].copy()
        spec = specs[name]

        share_col = spec.share_col
        if share_col not in cur.columns:
            raise AlternativeConfigJoinError(f"{name}: missing share column '{share_col}'")

        share_name = f"{name}__share"
        cur = cur.rename(columns={share_col: share_name})

        if spec.new_alt_var_col in merged.columns:
            raise AlternativeConfigJoinError(
                f"{name}: new alternative variable '{spec.new_alt_var_col}' already exists in merged table"
            )

        join_cols = list(spec.conditioning_cols)
        for c in spec.scenario_cols:
            if c in merged.columns:
                join_cols.append(c)
            elif c not in scenario_cols_all:
                scenario_cols_all.append(c)

        cur_has_year = spec.year_col is not None and spec.year_col in cur.columns
        if cur_has_year and "year" in merged.columns:
            join_cols.append("year")

        missing_join_cols = [c for c in join_cols if c not in merged.columns]
        if missing_join_cols:
            raise AlternativeConfigJoinError(
                f"{name}: conditioning/join columns not available in merged baseline: {missing_join_cols}"
            )

        merged = merged.merge(cur, on=join_cols, how="left")

        unmatched = merged[share_name].isna()
        if unmatched.any():
            new_scenario_cols = [c for c in spec.scenario_cols if c not in join_cols]
            if new_scenario_cols:
                raise AlternativeConfigJoinError(
                    f"{name}: baseline archetypes have no matching entry but table "
                    f"introduces scenario columns {new_scenario_cols}. "
                    f"Add entries for all baseline values."
                )
            baseline_col = spec.new_alt_var_col.removeprefix("alt_")
            merged.loc[unmatched, spec.new_alt_var_col] = merged.loc[unmatched, baseline_col].values
            merged.loc[unmatched, share_name] = 1.0

        merged[expanded_weight_col] = merged[expanded_weight_col] * merged[share_name]

    if not keep_provenance_shares:
        drop_cols = [c for c in merged.columns if c.endswith("__share")]
        merged = merged.drop(columns=drop_cols)

    if validate:
        validate_expanded_output(
            merged,
            baseline_id_col=baseline_id_col,
            baseline_weight_col="__baseline_weight",
            expanded_weight_col=expanded_weight_col,
            scenario_cols=scenario_cols_all,
            year_col="year",
            tolerance=tolerance,
        )

    return merged
