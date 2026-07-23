from __future__ import annotations

from typing import Type

import polars as pl


def require_columns_present(
    df: pl.DataFrame,
    columns: list[str],
    *,
    source_name: str,
    error_cls: Type[Exception],
) -> None:
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise error_cls(f"{source_name}: missing expected columns {missing}")


def require_numeric_series(
    series: pl.Series,
    *,
    source_name: str,
    error_cls: Type[Exception],
) -> None:
    if not series.dtype.is_numeric():
        raise error_cls(f"{source_name}: '{series.name}' must be numeric")


def require_series_between(
    series: pl.Series,
    *,
    lower: float,
    upper: float,
    source_name: str,
    error_cls: Type[Exception],
    message: str | None = None,
) -> None:
    if ((series < lower) | (series > upper)).any():
        if message is not None:
            raise error_cls(message)
        raise error_cls(
            f"{source_name}: '{series.name}' must be between {lower} and {upper}"
        )


def require_share_sums_to_one(
    df: pl.DataFrame,
    *,
    share_col: str,
    group_cols: list[str],
    tolerance: float,
    source_name: str,
    error_cls: Type[Exception],
    grouped_message_prefix: str = "shares must sum to 1.0",
    overall_message_prefix: str = "shares must sum to 1.0",
) -> None:
    if group_cols:
        sums = df.group_by(group_cols).agg(pl.col(share_col).sum())
        bad = sums.filter((pl.col(share_col) - 1.0).abs() > tolerance)
        if len(bad) > 0:
            example = bad.head(10)
            raise error_cls(
                f"{source_name}: {grouped_message_prefix} within each group of "
                f"{group_cols} (+/-{tolerance}). Examples:\n{example}"
            )
    else:
        total = df[share_col].sum()
        if abs(total - 1.0) > tolerance:
            raise error_cls(
                f"{source_name}: {overall_message_prefix} (+/-{tolerance}). Got {total}."
            )


def require_no_duplicates(
    df: pl.DataFrame,
    *,
    subset: list[str],
    source_name: str,
    error_cls: Type[Exception],
    message_prefix: str = "duplicate rows for keys",
) -> None:
    if df.select(subset).is_duplicated().any():
        dup = df.filter(df.select(subset).is_duplicated()).head(10)
        raise error_cls(f"{source_name}: {message_prefix} {subset}. Examples:\n{dup}")
