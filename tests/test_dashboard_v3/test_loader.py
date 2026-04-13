"""Tests for dashboard_v3.data.loader — CSV loading, caching, discovery."""

import json
from pathlib import Path

import pandas as pd
import pytest

from dashboard_v3.data.loader import (
    INPUTS_ROOT,
    OUTPUTS_ROOT,
    count_input_files,
    discover_csv_files,
    discover_input_sets,
    discover_scenarios,
    load_csv,
    load_step5,
    load_step5_cached,
)


# ---------------------------------------------------------------------------
# discover_input_sets
# ---------------------------------------------------------------------------


def test_discover_input_sets():
    """Real input sets should be discoverable."""
    sets = discover_input_sets()
    assert isinstance(sets, list)
    # We know test_input_set_1 exists
    assert len(sets) > 0


def test_discover_csv_files():
    """Should find CSV files in a known category."""
    sets = discover_input_sets()
    first_set = sets[0] if sets else "test_input_set_1"
    files = discover_csv_files(first_set, "archetypes")
    assert isinstance(files, list)
    assert len(files) > 0
    assert all(f.endswith(".csv") for f in files)


def test_discover_csv_files_nonexistent():
    files = discover_csv_files("nonexistent_set_xyz", "archetypes")
    assert files == []


def test_count_input_files():
    sets = discover_input_sets()
    first_set = sets[0] if sets else "test_input_set_1"
    counts = count_input_files(first_set)
    assert isinstance(counts, dict)
    assert "archetypes" in counts
    assert counts["archetypes"] > 0


# ---------------------------------------------------------------------------
# CSV I/O
# ---------------------------------------------------------------------------


def test_load_csv():
    """Load a known CSV file."""
    sets = discover_input_sets()
    first_set = sets[0] if sets else "test_input_set_1"
    csv_files = discover_csv_files(first_set, "archetypes")
    if csv_files:
        path = INPUTS_ROOT / first_set / "archetypes" / csv_files[0]
        df = load_csv(path)
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0


# ---------------------------------------------------------------------------
# Output loading
# ---------------------------------------------------------------------------


def test_load_step5_caching(tmp_path):
    """Verify the cache key includes mtime."""
    csv_path = tmp_path / "test.csv"
    df = pd.DataFrame({"x": [1, 2, 3]})
    df.to_csv(csv_path, index=False)

    result1 = load_step5(csv_path)
    assert len(result1) == 3

    # Write different data
    df2 = pd.DataFrame({"x": [10, 20]})
    df2.to_csv(csv_path, index=False)

    result2 = load_step5(csv_path)
    assert len(result2) == 2  # Should reload due to mtime change

    # Clear cache to avoid test pollution
    load_step5_cached.cache_clear()


# ---------------------------------------------------------------------------
# Scenario discovery
# ---------------------------------------------------------------------------


def test_discover_scenarios():
    """Should return a list of scenario dicts."""
    scenarios = discover_scenarios()
    assert isinstance(scenarios, list)
    for s in scenarios:
        assert "name" in s
        assert "path" in s


def test_discover_scenarios_with_metadata(tmp_path, monkeypatch):
    """Scenario with scenario.json should be discovered with metadata."""
    import dashboard_v3.data.loader as loader

    # Temporarily override OUTPUTS_ROOT
    monkeypatch.setattr(loader, "OUTPUTS_ROOT", tmp_path)

    # Create a scenario with metadata
    scn_dir = tmp_path / "test_scenario"
    scn_dir.mkdir()
    (scn_dir / "step5_utility_bills.csv").write_text("a,b\n1,2\n")
    meta = {"input_set": "test", "created": "2025-01-01", "steps_completed": 5, "row_count": 1, "input_set_hash": "abc"}
    (scn_dir / "scenario.json").write_text(json.dumps(meta))

    scenarios = discover_scenarios()
    assert len(scenarios) == 1
    assert scenarios[0]["name"] == "test_scenario"
    assert scenarios[0]["has_metadata"] is True
    assert scenarios[0]["input_set"] == "test"
