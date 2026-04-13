"""DSPM-to-Energy-Wallet data converter.

Reads a DSPM data library and produces Energy Wallet input files
(archetypes and input parameters).
"""

from __future__ import annotations

from .pipeline import run_pipeline

__all__ = ["run_pipeline"]
