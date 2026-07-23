from __future__ import annotations

import polars as pl

from .errors import AlternativeConfigTableError
from .spec import AlternativeConfigTableSpec
from energy_wallet.validation.common import (
    require_numeric_series,
    require_share_sums_to_one,
)


def validate_table(df: pl.DataFrame, spec: AlternativeConfigTableSpec, *, tolerance: float = 1e-3) -> None:
    if spec.share_col not in df.columns:
        raise AlternativeConfigTableError(f"{spec.path.name}: missing share column '{spec.share_col}'")

    shares = df[spec.share_col]
    require_numeric_series(
        shares,
        source_name=spec.path.name,
        error_cls=AlternativeConfigTableError,
    )

    if ((shares < 0) | (shares > 1)).any():
        bad = df.filter((pl.col(spec.share_col) < 0) | (pl.col(spec.share_col) > 1)).head(5)
        raise AlternativeConfigTableError(
            f"{spec.path.name}: adoption shares must be between 0 and 1. Examples:\n{bad}"
        )

    if not spec.new_alt_var_col.startswith("alt_"):
        raise AlternativeConfigTableError(
            f"{spec.path.name}: new alternative column must start with 'alt_' (got '{spec.new_alt_var_col}')"
        )

    grouping_cols = list(spec.conditioning_cols) + list(spec.scenario_cols)
    if spec.year_col:
        grouping_cols.append(spec.year_col)

    if not grouping_cols:
        raise AlternativeConfigTableError(
            f"{spec.path.name}: Step 2 requires at least one conditioning variable"
        )

    require_share_sums_to_one(
        df,
        share_col=spec.share_col,
        group_cols=grouping_cols,
        tolerance=tolerance,
        source_name=spec.path.name,
        error_cls=AlternativeConfigTableError,
        grouped_message_prefix="adoption shares must sum to 1.0",
    )


def validate_expanded_output(
    expanded: pl.DataFrame,
    *,
    baseline_id_col: str,
    baseline_weight_col: str,
    expanded_weight_col: str,
    scenario_cols: list[str],
    year_col: str = "year",
    tolerance: float = 1e-3,
) -> None:
    if expanded_weight_col not in expanded.columns:
        raise AlternativeConfigTableError(
            f"Expanded output missing weight column '{expanded_weight_col}'"
        )

    if baseline_id_col not in expanded.columns:
        raise AlternativeConfigTableError(
            f"Expanded output missing baseline id column '{baseline_id_col}'"
        )

    if (expanded[expanded_weight_col] <= 0).any():
        raise AlternativeConfigTableError("Expanded output contains non-positive weights")

    if baseline_weight_col not in expanded.columns:
        raise AlternativeConfigTableError(
            f"Expanded output missing baseline weight column '{baseline_weight_col}'"
        )

    ignore_cols = {expanded_weight_col}
    for c in expanded.columns:
        if c.endswith("__share"):
            ignore_cols.add(c)
    id_cols = [c for c in expanded.columns if c not in ignore_cols]
    if expanded.select(id_cols).is_duplicated().any():
        raise AlternativeConfigTableError("Expanded output has duplicate archetype/scenario combinations")

    conservation_group_cols = [baseline_id_col] + list(scenario_cols)
    if year_col in expanded.columns:
        conservation_group_cols.append(year_col)

    grouped = expanded.group_by(conservation_group_cols).agg(
        pl.col(expanded_weight_col).sum().alias("actual"),
        pl.col(baseline_weight_col).first().alias("expected"),
    )
    bad = grouped.filter((pl.col("actual") - pl.col("expected")).abs() > tolerance)
    if len(bad) > 0:
        example = bad.head(10)
        raise AlternativeConfigTableError(
            "Expanded output violates baseline weight conservation. "
            f"Examples:\n{example}"
        )
