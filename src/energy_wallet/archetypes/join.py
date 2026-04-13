from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

import pandas as pd

from .errors import ArchetypeJoinError, ArchetypeTableError
from .spec import ArchetypeTableSpec


def _toposort_tables(
    specs: Dict[str, ArchetypeTableSpec],
    tables: Optional[Dict[str, pd.DataFrame]] = None,
) -> List[str]:
    """
    Topologically sort tables so that a table's conditioning columns are available
    before it is merged.

    Dependency rule:
      - A table introduces `new_var_col`
      - A table depends on any conditioning col that is introduced by some other table
      - Conditioning cols that are never introduced by any table are treated as exogenous.
        (We treat `year` as exogenous too; it is handled specially during merging.)

    Optimization:
      - Among "ready" tables at each step, prefer the smallest table first to
        reduce intermediate blow-up.
    """
    introduced_by: Dict[str, str] = {}
    for name, spec in specs.items():
        introduced_by[spec.new_var_col] = name

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
        raise ArchetypeJoinError(
            "Cannot resolve table merge order (cycle or unresolved dependencies).\n"
            f"Remaining tables with deps: {cycle_info}"
        )

    return ordered


def _cross_join(left: pd.DataFrame, right: pd.DataFrame) -> pd.DataFrame:
    left = left.copy()
    right = right.copy()
    left["_tmp_key"] = 1
    right["_tmp_key"] = 1
    out = left.merge(right, on="_tmp_key", how="inner")
    return out.drop(columns=["_tmp_key"])


def _distinct_years(df: pd.DataFrame, year_col: str = "year") -> pd.DataFrame:
    return df[[year_col]].drop_duplicates().sort_values(year_col).reset_index(drop=True)


def _validate_combined(
    df: pd.DataFrame,
    weight_col: str,
    year_col: str = "year",
    tolerance: float = 1e-3,
) -> None:
    """
    Combined archetype validation (Step 1.4):
      - weights > 0
      - no duplicate archetype combos (including year if present)
      - weights sum to 1 (± tol) for each year if year exists, else overall sum to 1
    """
    if weight_col not in df.columns:
        raise ArchetypeJoinError(f"Combined output missing weight column '{weight_col}'")

    if (df[weight_col] <= 0).any():
        bad = df[df[weight_col] <= 0].head(5)
        raise ArchetypeJoinError(
            f"Combined output contains non-positive weights in '{weight_col}'. "
            f"Sample rows:\n{bad}"
        )

    # Determine the "archetype id" columns: everything except provenance shares + weight
    ignore = {weight_col}
    for c in df.columns:
        if c.endswith("__share"):
            ignore.add(c)

    id_cols = [c for c in df.columns if c not in ignore]

    # Duplicates check
    if df.duplicated(subset=id_cols).any():
        dup = df[df.duplicated(subset=id_cols, keep=False)].head(10)
        raise ArchetypeJoinError(
            "Duplicate archetype combinations found in combined output. "
            f"ID columns: {id_cols}\nSample duplicates:\n{dup}"
        )

    # Sum-to-1 check
    if year_col in df.columns:
        sums = df.groupby(year_col, observed=True)[weight_col].sum()
        bad_years = sums[(sums - 1.0).abs() > tolerance]
        if not bad_years.empty:
            raise ArchetypeJoinError(
                f"Combined weights do not sum to 1 within tolerance ({tolerance}) for some years. "
                f"Bad years:\n{bad_years}"
            )
    else:
        total = float(df[weight_col].sum())
        if abs(total - 1.0) > tolerance:
            raise ArchetypeJoinError(
                f"Combined weights do not sum to 1 within tolerance ({tolerance}). "
                f"Total={total}"
            )


def merge_archetypes(
    tables: Dict[str, pd.DataFrame],
    specs: Dict[str, ArchetypeTableSpec],
    *,
    weight_col_out: str = "population_weight",
    keep_provenance_shares: bool = False,
    tolerance: float = 1e-3,
    validate: bool = True,
) -> pd.DataFrame:
    """
    Combine N archetype tables into a full archetype universe.

    Rules:
      - If a table has no conditioning cols -> Cartesian product (cross join).
      - If a table has conditioning cols -> inner join on those cols.
      - If a table has a 'year' column:
          * If merged doesn't yet have year, merged is expanded across the table's years first.
          * If merged already has year, year becomes part of the join key.
      - If a table does NOT have year but merged does, the table applies to all years (no join on year).
      - Final weight = product of each table's population_share (multiplicative).

    Inputs:
      tables/specs: keyed by table name (e.g. file stem)
      specs[name].share_col is expected to be 'population_share' (or whatever you set)
    """
    if not tables:
        raise ArchetypeJoinError("No archetype tables provided.")
    if set(tables.keys()) != set(specs.keys()):
        raise ArchetypeJoinError("Tables/specs keys mismatch.")

    order = _toposort_tables(specs, tables=tables)

    merged: Optional[pd.DataFrame] = None

    for name in order:
        df = tables[name]
        spec = specs[name]

        share_col = spec.share_col
        if share_col not in df.columns:
            raise ArchetypeJoinError(f"{name}: missing share column '{share_col}'")

        # Rename share column to keep provenance and avoid collisions
        share_name = f"{name}__share"
        cur = df.copy().rename(columns={share_col: share_name})

        # -----------------------
        # First table initializes
        # -----------------------
        if merged is None:
            merged = cur
            merged[weight_col_out] = merged[share_name]
            continue

        # -----------------------
        # Year handling
        # -----------------------
        cur_has_year = spec.year_col is not None and spec.year_col in cur.columns
        merged_has_year = "year" in merged.columns

        if cur_has_year and not merged_has_year:
            # Earlier tables were time-invariant; expand merged across all years
            years = _distinct_years(cur, year_col="year")
            merged = _cross_join(merged, years)

        # Decide join keys:
        join_cols = list(spec.conditioning_cols)

        # If both have year, enforce consistency by joining on it too
        if cur_has_year and "year" in merged.columns:
            join_cols = join_cols + ["year"]

        # Conditioning columns must already exist in merged
        missing = [c for c in join_cols if c not in merged.columns]
        if missing:
            raise ArchetypeJoinError(
                f"{name}: conditioning columns not available yet: {missing}. "
                "This usually means you conditioned on a variable never introduced by any archetype file, "
                "or the dependency ordering cannot be satisfied."
            )

        # -----------------------
        # Join
        # -----------------------
        if not join_cols:
            merged = _cross_join(merged, cur)
        else:
            merged = merged.merge(cur, on=join_cols, how="inner")

        # Multiply weights
        merged[weight_col_out] = merged[weight_col_out] * merged[share_name]

    assert merged is not None

    # Optionally drop per-table share columns
    if not keep_provenance_shares:
        drop_cols = [c for c in merged.columns if c.endswith("__share")]
        merged = merged.drop(columns=drop_cols)

    # Optional validation of combined output
    if validate:
        _validate_combined(
            merged,
            weight_col=weight_col_out,
            year_col="year",
            tolerance=tolerance,
        )

    return merged
