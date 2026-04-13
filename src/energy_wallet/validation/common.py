from __future__ import annotations

from typing import Type

import numpy as np
import pandas as pd


def require_columns_present(
    df: pd.DataFrame,
    columns: list[str],
    *,
    source_name: str,
    error_cls: Type[Exception],
) -> None:
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise error_cls(f"{source_name}: missing expected columns {missing}")


def require_numeric_series(
    series: pd.Series,
    *,
    source_name: str,
    error_cls: Type[Exception],
) -> None:
    if not np.issubdtype(series.dtype, np.number):
        raise error_cls(f"{source_name}: '{series.name}' must be numeric")


def require_series_between(
    series: pd.Series,
    *,
    lower: float,
    upper: float,
    source_name: str,
    error_cls: Type[Exception],
    message: str | None = None,
) -> None:
    out_of_bounds = (series < lower) | (series > upper)
    if out_of_bounds.any():
        if message is not None:
            raise error_cls(message)
        raise error_cls(
            f"{source_name}: '{series.name}' must be between {lower} and {upper}"
        )


def require_share_sums_to_one(
    df: pd.DataFrame,
    *,
    share_col: str,
    group_cols: list[str],
    tolerance: float,
    source_name: str,
    error_cls: Type[Exception],
    grouped_message_prefix: str = "shares must sum to 1.0",
    overall_message_prefix: str = "shares must sum to 1.0",
) -> None:
    shares = df[share_col]
    if group_cols:
        sums = df.groupby(group_cols, dropna=False, observed=True)[share_col].sum()
        bad = sums[(sums - 1.0).abs() > tolerance]
        if not bad.empty:
            example = bad.head(10)
            raise error_cls(
                f"{source_name}: {grouped_message_prefix} within each group of "
                f"{group_cols} (+/-{tolerance}). Examples:\n{example}"
            )
    else:
        total = float(shares.sum())
        if abs(total - 1.0) > tolerance:
            raise error_cls(
                f"{source_name}: {overall_message_prefix} (+/-{tolerance}). Got {total}."
            )


def require_no_duplicates(
    df: pd.DataFrame,
    *,
    subset: list[str],
    source_name: str,
    error_cls: Type[Exception],
    message_prefix: str = "duplicate rows for keys",
) -> None:
    if df.duplicated(subset=subset).any():
        dup = df[df.duplicated(subset=subset, keep=False)].head(10)
        raise error_cls(f"{source_name}: {message_prefix} {subset}. Examples:\n{dup}")
