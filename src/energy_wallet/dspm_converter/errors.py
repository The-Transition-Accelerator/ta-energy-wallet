"""Exception hierarchy for the DSPM-to-Energy-Wallet converter."""

from __future__ import annotations


class DSPMConverterError(Exception):
    """Base exception for all converter errors."""


class DSPMDataError(DSPMConverterError):
    """Missing or malformed DSPM data file."""


class DSPMValidationError(DSPMConverterError):
    """Post-build validation failure (e.g., join-key mismatch)."""
