"""Shared dtype optimization for memory-efficient DataFrames.

Downcasts float64 → float32 after CSV loading. Float32 provides ~7 decimal
digits of precision, more than sufficient for energy cost calculations in
$/year.
"""
from __future__ import annotations

import polars as pl


def optimize_dtypes(df: pl.DataFrame) -> pl.DataFrame:
    """Downcast a Polars DataFrame's numeric columns to memory-efficient dtypes.

    - Float64 → Float32
    - Int64 year column → Int16
    """
    casts = []
    for col in df.columns:
        dtype = df[col].dtype
        if dtype == pl.Float64:
            casts.append(pl.col(col).cast(pl.Float32))
        elif dtype == pl.Int64 and col == "year":
            casts.append(pl.col(col).cast(pl.Int16))

    if casts:
        return df.with_columns(casts)
    return df
