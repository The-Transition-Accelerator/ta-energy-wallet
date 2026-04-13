"""Data loading utilities — CSV discovery, caching, and I/O.

Ported from dashboard/utils.py and dashboard/summary.py — no Streamlit dependency.
Read-only: write/delete functions removed from dashboard_v2 version.
"""

from __future__ import annotations

import functools
import os
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------


def project_root() -> Path:
    """Return the project root (parent of dashboard_v3/)."""
    return Path(__file__).resolve().parent.parent.parent


INPUTS_ROOT = project_root() / "inputs"
OUTPUTS_ROOT = project_root() / "outputs"
EXPECTED_SUBDIRS = {"archetypes", "alternative_configurations", "input_parameters"}

CATEGORY_LABELS = {
    "archetypes": "Archetypes",
    "alternative_configurations": "Alternative Configurations",
    "input_parameters": "Input Parameters",
}

# ---------------------------------------------------------------------------
# Input set discovery
# ---------------------------------------------------------------------------


def discover_input_sets() -> list[str]:
    """Return sorted names of valid input set directories."""
    if not INPUTS_ROOT.is_dir():
        return []
    sets = []
    for child in sorted(INPUTS_ROOT.iterdir()):
        if not child.is_dir():
            continue
        child_contents = {p.name for p in child.iterdir() if p.is_dir()}
        if child_contents & EXPECTED_SUBDIRS:
            sets.append(child.name)
    return sets


def discover_csv_files(input_set: str, category: str) -> list[str]:
    """Return sorted CSV filenames within a category directory."""
    cat_dir = INPUTS_ROOT / input_set / category
    if not cat_dir.is_dir():
        return []
    return sorted(f.name for f in cat_dir.glob("*.csv"))


def count_input_files(input_set: str) -> dict[str, int]:
    """Return dict of file counts per category."""
    return {
        cat: len(discover_csv_files(input_set, cat))
        for cat in EXPECTED_SUBDIRS
    }


# ---------------------------------------------------------------------------
# CSV I/O
# ---------------------------------------------------------------------------


def load_csv(path: str | Path) -> pd.DataFrame:
    """Read a CSV file into a DataFrame."""
    return pd.read_csv(path)


# ---------------------------------------------------------------------------
# Output loading with bounded cache
# ---------------------------------------------------------------------------


@functools.lru_cache(maxsize=2)
def load_step5_cached(path: str, mtime: float) -> pd.DataFrame:
    """Load step5 CSV with cache keyed on path + modification time.

    The mtime parameter ensures cache invalidation when the file changes.
    maxsize=2 bounds memory to ~2 scenario DataFrames at a time.
    """
    return pd.read_csv(path)


def load_step5(path: str | Path) -> pd.DataFrame:
    """Load step5 output CSV with caching."""
    path = str(path)
    mtime = os.path.getmtime(path)
    return load_step5_cached(path, mtime)


# ---------------------------------------------------------------------------
# Scenario discovery
# ---------------------------------------------------------------------------


def discover_scenarios() -> list[dict]:
    """Discover completed scenarios from outputs/ directory.

    Returns list of dicts with keys: name, path, has_metadata.
    Checks for scenario.json (preferred) or step5_utility_bills.csv (fallback).
    """
    import json

    if not OUTPUTS_ROOT.is_dir():
        return []
    scenarios = []
    for child in sorted(OUTPUTS_ROOT.iterdir()):
        if not child.is_dir():
            continue
        meta_path = child / "scenario.json"
        step5_path = child / "step5_utility_bills.csv"
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text())
                scenarios.append({
                    "name": child.name,
                    "path": child,
                    "has_metadata": True,
                    **meta,
                })
            except (json.JSONDecodeError, KeyError):
                if step5_path.exists():
                    scenarios.append({
                        "name": child.name,
                        "path": child,
                        "has_metadata": False,
                    })
        elif step5_path.exists():
            scenarios.append({
                "name": child.name,
                "path": child,
                "has_metadata": False,
            })
    return scenarios
