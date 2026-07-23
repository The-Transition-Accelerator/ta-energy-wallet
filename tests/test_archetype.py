from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd
import polars as pl
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from energy_wallet.archetypes import (  # noqa: E402
    ArchetypeJoinError,
    ArchetypeTableError,
    load_all_archetype_tables,
    load_archetype_table,
    merge_archetypes,
)


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(path, index=False)


def _load_as_maps(archetypes_dir: Path):
    tables, specs = load_all_archetype_tables(archetypes_dir)
    table_map = {s.path.stem: t for t, s in zip(tables, specs)}
    spec_map = {s.path.stem: s for s in specs}
    return table_map, spec_map


def test_load_archetype_table_infers_spec_and_filters_zero_shares(tmp_path: Path) -> None:
    csv_path = tmp_path / "vehicle_type.csv"
    _write_csv(
        csv_path,
        [
            {"vehicle_type": "gasoline", "population_share": 0.85},
            {"vehicle_type": "electric", "population_share": 0.15},
            {"vehicle_type": "unused", "population_share": 0.0},
        ],
    )

    df, spec = load_archetype_table(csv_path)

    assert spec.new_var_col == "vehicle_type"
    assert spec.conditioning_cols == []
    assert spec.year_col is None
    assert len(df) == 2
    assert "unused" not in df["vehicle_type"].to_list()


def test_load_archetype_table_rejects_invalid_column_order(tmp_path: Path) -> None:
    csv_path = tmp_path / "dwelling_type.csv"
    _write_csv(
        csv_path,
        [
            {"population_share": 0.65, "dwelling_type": "single_family"},
            {"population_share": 0.35, "dwelling_type": "apartment"},
        ],
    )

    with pytest.raises(ArchetypeTableError, match="last column must be 'population_share'"):
        load_archetype_table(csv_path)


def test_load_archetype_table_validates_conditioned_partition_sums(tmp_path: Path) -> None:
    csv_path = tmp_path / "heating_system.csv"
    _write_csv(
        csv_path,
        [
            {"dwelling_type": "single_family", "heating_system": "furnace", "population_share": 0.50},
            {"dwelling_type": "single_family", "heating_system": "heat_pump", "population_share": 0.40},
            {"dwelling_type": "apartment", "heating_system": "furnace", "population_share": 0.40},
            {"dwelling_type": "apartment", "heating_system": "heat_pump", "population_share": 0.60},
        ],
    )

    with pytest.raises(ArchetypeTableError, match="shares must sum to 1.0"):
        load_archetype_table(csv_path)


def test_merge_archetypes_matches_step1_worked_example(tmp_path: Path) -> None:
    archetypes_dir = tmp_path / "archetypes"

    _write_csv(
        archetypes_dir / "dwelling_type.csv",
        [
            {"dwelling_type": "single_family", "population_share": 0.65},
            {"dwelling_type": "apartment", "population_share": 0.35},
        ],
    )
    _write_csv(
        archetypes_dir / "heating_system.csv",
        [
            {"dwelling_type": "single_family", "heating_system": "furnace", "population_share": 0.60},
            {"dwelling_type": "single_family", "heating_system": "heat_pump", "population_share": 0.30},
            {"dwelling_type": "single_family", "heating_system": "boiler", "population_share": 0.10},
            {"dwelling_type": "apartment", "heating_system": "furnace", "population_share": 0.40},
            {"dwelling_type": "apartment", "heating_system": "heat_pump", "population_share": 0.55},
            {"dwelling_type": "apartment", "heating_system": "boiler", "population_share": 0.05},
        ],
    )
    _write_csv(
        archetypes_dir / "vehicle_type.csv",
        [
            {"vehicle_type": "gasoline", "population_share": 0.85},
            {"vehicle_type": "electric", "population_share": 0.15},
        ],
    )

    tables, specs = _load_as_maps(archetypes_dir)
    merged = merge_archetypes(tables, specs, keep_provenance_shares=False)

    assert len(merged) == 12
    assert set(["dwelling_type", "heating_system", "vehicle_type", "population_weight"]).issubset(
        merged.columns
    )
    assert merged["population_weight"].sum() == pytest.approx(1.0, abs=1e-6)

    sf_furnace_gas = merged.filter(
        (pl.col("dwelling_type") == "single_family")
        & (pl.col("heating_system") == "furnace")
        & (pl.col("vehicle_type") == "gasoline")
    )
    assert len(sf_furnace_gas) == 1
    assert float(sf_furnace_gas["population_weight"][0]) == pytest.approx(0.3315, abs=1e-6)


def test_merge_archetypes_enforces_conditioning_constraints(tmp_path: Path) -> None:
    archetypes_dir = tmp_path / "archetypes"

    _write_csv(
        archetypes_dir / "dwelling_type.csv",
        [
            {"dwelling_type": "single_family", "population_share": 0.5},
            {"dwelling_type": "apartment", "population_share": 0.5},
        ],
    )
    _write_csv(
        archetypes_dir / "heating_system.csv",
        [
            {"dwelling_type": "single_family", "heating_system": "furnace", "population_share": 1.0},
            {"dwelling_type": "apartment", "heating_system": "heat_pump", "population_share": 1.0},
        ],
    )

    tables, specs = _load_as_maps(archetypes_dir)
    merged = merge_archetypes(tables, specs, keep_provenance_shares=False)

    impossible = merged.filter(
        ((pl.col("dwelling_type") == "single_family") & (pl.col("heating_system") == "heat_pump"))
        | ((pl.col("dwelling_type") == "apartment") & (pl.col("heating_system") == "furnace"))
    )
    assert len(impossible) == 0
    assert merged["population_weight"].sum() == pytest.approx(1.0, abs=1e-6)


def test_merge_archetypes_with_year_expands_time_invariant_tables(tmp_path: Path) -> None:
    archetypes_dir = tmp_path / "archetypes"

    _write_csv(
        archetypes_dir / "dwelling_type.csv",
        [
            {"dwelling_type": "single_family", "population_share": 0.7},
            {"dwelling_type": "apartment", "population_share": 0.3},
        ],
    )

    _write_csv(
        archetypes_dir / "heating_system.csv",
        [
            {"dwelling_type": "single_family", "heating_system": "furnace", "population_share": 1.0},
            {"dwelling_type": "apartment", "heating_system": "boiler", "population_share": 1.0},
        ],
    )

    _write_csv(
        archetypes_dir / "vehicle_type.csv",
        [
            {"vehicle_type": "gasoline", "year": 2025, "population_share": 0.9},
            {"vehicle_type": "electric", "year": 2025, "population_share": 0.1},
            {"vehicle_type": "gasoline", "year": 2030, "population_share": 0.7},
            {"vehicle_type": "electric", "year": 2030, "population_share": 0.3},
        ],
    )

    tables, specs = _load_as_maps(archetypes_dir)
    merged = merge_archetypes(tables, specs, keep_provenance_shares=False)

    assert "year" in merged.columns
    assert set(merged["year"].to_list()) == {2025, 2030}

    by_year = merged.group_by("year").agg(pl.col("population_weight").sum())
    for row in by_year.iter_rows(named=True):
        assert row["population_weight"] == pytest.approx(1.0, abs=1e-6)


def test_merge_archetypes_raises_on_unresolvable_conditioning_dependency(tmp_path: Path) -> None:
    archetypes_dir = tmp_path / "archetypes"

    _write_csv(
        archetypes_dir / "dwelling_type.csv",
        [
            {"dwelling_type": "single_family", "population_share": 1.0},
        ],
    )

    _write_csv(
        archetypes_dir / "heating_system.csv",
        [
            {
                "missing_dimension": "x",
                "heating_system": "furnace",
                "population_share": 1.0,
            },
        ],
    )

    tables, specs = _load_as_maps(archetypes_dir)
    with pytest.raises(ArchetypeJoinError, match="conditioning columns not available yet"):
        merge_archetypes(tables, specs)
