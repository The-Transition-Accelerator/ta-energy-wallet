from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import polars as pl

from .errors import ArchetypeJoinError, ArchetypeTableError
from .spec import ArchetypeTableSpec


def _toposort_tables(
    specs: Dict[str, ArchetypeTableSpec],
    tables: Optional[Dict[str, pl.DataFrame]] = None,
) -> List[str]:
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


def _validate_combined(
    df: pl.DataFrame,
    weight_col: str,
    year_col: str = "year",
    tolerance: float = 1e-3,
) -> None:
    if weight_col not in df.columns:
        raise ArchetypeJoinError(f"Combined output missing weight column '{weight_col}'")

    if (df[weight_col] <= 0).any():
        bad = df.filter(pl.col(weight_col) <= 0).head(5)
        raise ArchetypeJoinError(
            f"Combined output contains non-positive weights in '{weight_col}'. "
            f"Sample rows:\n{bad}"
        )

    ignore = {weight_col}
    for c in df.columns:
        if c.endswith("__share"):
            ignore.add(c)
    id_cols = [c for c in df.columns if c not in ignore]

    if df.select(id_cols).is_duplicated().any():
        dup = df.filter(df.select(id_cols).is_duplicated()).head(10)
        raise ArchetypeJoinError(
            "Duplicate archetype combinations found in combined output. "
            f"ID columns: {id_cols}\nSample duplicates:\n{dup}"
        )

    if year_col in df.columns:
        sums = df.group_by(year_col).agg(pl.col(weight_col).sum())
        bad_years = sums.filter((pl.col(weight_col) - 1.0).abs() > tolerance)
        if len(bad_years) > 0:
            raise ArchetypeJoinError(
                f"Combined weights do not sum to 1 within tolerance ({tolerance}) for some years. "
                f"Bad years:\n{bad_years}"
            )
    else:
        total = df[weight_col].sum()
        if abs(total - 1.0) > tolerance:
            raise ArchetypeJoinError(
                f"Combined weights do not sum to 1 within tolerance ({tolerance}). "
                f"Total={total}"
            )


def merge_archetypes(
    tables: Dict[str, pl.DataFrame],
    specs: Dict[str, ArchetypeTableSpec],
    *,
    weight_col_out: str = "population_weight",
    keep_provenance_shares: bool = False,
    tolerance: float = 1e-3,
    validate: bool = True,
) -> pl.DataFrame:
    if not tables:
        raise ArchetypeJoinError("No archetype tables provided.")
    if set(tables.keys()) != set(specs.keys()):
        raise ArchetypeJoinError("Tables/specs keys mismatch.")

    order = _toposort_tables(specs, tables=tables)

    merged: Optional[pl.DataFrame] = None

    for name in order:
        df = tables[name]
        spec = specs[name]

        share_col = spec.share_col
        if share_col not in df.columns:
            raise ArchetypeJoinError(f"{name}: missing share column '{share_col}'")

        share_name = f"{name}__share"
        cur = df.rename({share_col: share_name})

        if merged is None:
            merged = cur.with_columns(pl.col(share_name).alias(weight_col_out))
            continue

        cur_has_year = spec.year_col is not None and spec.year_col in cur.columns
        merged_has_year = "year" in merged.columns

        if cur_has_year and not merged_has_year:
            years = cur.select("year").unique().sort("year")
            merged = merged.join(years, how="cross")

        join_cols = list(spec.conditioning_cols)
        if cur_has_year and "year" in merged.columns:
            join_cols = join_cols + ["year"]

        missing = [c for c in join_cols if c not in merged.columns]
        if missing:
            raise ArchetypeJoinError(
                f"{name}: conditioning columns not available yet: {missing}. "
                "This usually means you conditioned on a variable never introduced by any archetype file, "
                "or the dependency ordering cannot be satisfied."
            )

        if not join_cols:
            merged = merged.join(cur, how="cross")
        else:
            merged = merged.join(cur, on=join_cols, how="inner")

        merged = merged.with_columns(
            (pl.col(weight_col_out) * pl.col(share_name)).alias(weight_col_out)
        )

    assert merged is not None

    if not keep_provenance_shares:
        drop_cols = [c for c in merged.columns if c.endswith("__share")]
        merged = merged.drop(drop_cols)

    if validate:
        _validate_combined(
            merged,
            weight_col=weight_col_out,
            year_col="year",
            tolerance=tolerance,
        )

    return merged
