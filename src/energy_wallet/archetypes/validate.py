from __future__ import annotations
import pandas as pd
from .errors import ArchetypeTableError
from .spec import ArchetypeTableSpec
from energy_wallet.validation.common import (
    require_numeric_series,
    require_series_between,
    require_share_sums_to_one,
)


def validate_table(df: pd.DataFrame, spec: ArchetypeTableSpec, tolerance: float = 1e-3) -> None:
    # shares exist + numeric
    if spec.share_col not in df.columns:
        raise ArchetypeTableError(f"{spec.path.name}: missing share column '{spec.share_col}'")

    shares = df[spec.share_col]
    require_numeric_series(
        shares,
        source_name=spec.path.name,
        error_cls=ArchetypeTableError,
    )

    if ((shares < 0) | (shares > 1)).any():
        bad = df.loc[(shares < 0) | (shares > 1), [spec.share_col]].head(5)
        require_series_between(
            shares,
            lower=0.0,
            upper=1.0,
            source_name=spec.path.name,
            error_cls=ArchetypeTableError,
            message=(
                f"{spec.path.name}: shares must be between 0 and 1. Examples:\n{bad}"
            ),
        )

    # sum-to-1 within conditioning (+ year if present)
    group_cols = list(spec.conditioning_cols)
    if spec.year_col:
        group_cols.append(spec.year_col)

    require_share_sums_to_one(
        df,
        share_col=spec.share_col,
        group_cols=group_cols,
        tolerance=tolerance,
        source_name=spec.path.name,
        error_cls=ArchetypeTableError,
    )
