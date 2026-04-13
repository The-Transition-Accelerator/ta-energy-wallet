"""Unit conversion constants and helpers for DSPM → EW conversion."""

from __future__ import annotations

# Energy
KWH_TO_GJ: float = 0.0036
GJ_TO_KWH: float = 1.0 / KWH_TO_GJ  # 277.777...


def kwh_to_gj(kwh: float) -> float:
    """Convert kilowatt-hours to gigajoules."""
    return kwh * KWH_TO_GJ


def gj_to_kwh(gj: float) -> float:
    """Convert gigajoules to kilowatt-hours."""
    return gj * GJ_TO_KWH
