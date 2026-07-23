from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd
import polars as pl
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from energy_wallet.alternative_configurations import (  # noqa: E402
    AlternativeConfigJoinError,
    AlternativeConfigTableError,
    load_all_alternative_configuration_tables,
    load_alternative_configuration_table,
    merge_alternative_configurations,
)


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(path, index=False)


def _load_as_maps(inputs_dir: Path, scenario_cols_by_file: dict[str, list[str]] | None = None):
    tables, specs = load_all_alternative_configuration_tables(
        inputs_dir,
        scenario_cols_by_file=scenario_cols_by_file,
    )
    table_map = {s.path.stem: t for t, s in zip(tables, specs)}
    spec_map = {s.path.stem: s for s in specs}
    return table_map, spec_map


def test_load_alt_table_infers_scenario_year_and_filters_zero(tmp_path: Path) -> None:
    csv_path = tmp_path / "alt_vehicle.csv"
    _write_csv(
        csv_path,
        [
            {
                "vehicle_type": "ICE",
                "alt_vehicle_type": "EV",
                "scn_adoption": "conservative",
                "year": 2025,
                "adoption_share": 30,
            },
            {
                "vehicle_type": "ICE",
                "alt_vehicle_type": "ICE",
                "scn_adoption": "conservative",
                "year": 2025,
                "adoption_share": 70,
            },
            {
                "vehicle_type": "EV",
                "alt_vehicle_type": "EV",
                "scn_adoption": "conservative",
                "year": 2025,
                "adoption_share": 0,
            },
        ],
    )

    df, spec = load_alternative_configuration_table(csv_path)

    assert spec.new_alt_var_col == "alt_vehicle_type"
    assert spec.conditioning_cols == ["vehicle_type"]
    assert spec.scenario_cols == ["scn_adoption"]
    assert spec.year_col == "year"
    assert len(df) == 2
    assert df["adoption_share"].sum() == pytest.approx(1.0, abs=1e-6)


def test_load_alt_table_requires_alt_column_name_prefix(tmp_path: Path) -> None:
    csv_path = tmp_path / "alt_heating.csv"
    _write_csv(
        csv_path,
        [
            {
                "heating_system": "furnace",
                "new_heating_system": "heat_pump",
                "adoption_share": 1.0,
            }
        ],
    )

    with pytest.raises(AlternativeConfigTableError, match="must start with 'alt_'"):
        load_alternative_configuration_table(csv_path)


def test_merge_alt_configs_matches_worked_example_weights() -> None:
    baseline = pl.DataFrame(
        [
            {"dwelling_type": "single_family", "heating_system": "furnace", "vehicle_type": "ICE", "population_weight": 0.40},
            {"dwelling_type": "single_family", "heating_system": "heat_pump", "vehicle_type": "ICE", "population_weight": 0.20},
            {"dwelling_type": "apartment", "heating_system": "boiler", "vehicle_type": "ICE", "population_weight": 0.15},
        ]
    )

    alt_vehicle = pl.DataFrame(
        [
            {"vehicle_type": "ICE", "alt_vehicle_type": "EV", "adoption_share": 0.30},
            {"vehicle_type": "ICE", "alt_vehicle_type": "ICE", "adoption_share": 0.70},
        ]
    )

    alt_heating = pl.DataFrame(
        [
            {"heating_system": "furnace", "alt_vehicle_type": "EV", "alt_heating_system": "heat_pump", "adoption_share": 0.80},
            {"heating_system": "furnace", "alt_vehicle_type": "EV", "alt_heating_system": "furnace", "adoption_share": 0.20},
            {"heating_system": "furnace", "alt_vehicle_type": "ICE", "alt_heating_system": "heat_pump", "adoption_share": 0.20},
            {"heating_system": "furnace", "alt_vehicle_type": "ICE", "alt_heating_system": "furnace", "adoption_share": 0.80},
            {"heating_system": "heat_pump", "alt_vehicle_type": "EV", "alt_heating_system": "heat_pump", "adoption_share": 1.0},
            {"heating_system": "heat_pump", "alt_vehicle_type": "ICE", "alt_heating_system": "heat_pump", "adoption_share": 1.0},
            {"heating_system": "boiler", "alt_vehicle_type": "EV", "alt_heating_system": "boiler", "adoption_share": 1.0},
            {"heating_system": "boiler", "alt_vehicle_type": "ICE", "alt_heating_system": "boiler", "adoption_share": 1.0},
        ]
    )

    from energy_wallet.alternative_configurations.spec import AlternativeConfigTableSpec

    tables = {"alt_vehicle": alt_vehicle, "alt_heating": alt_heating}
    specs = {
        "alt_vehicle": AlternativeConfigTableSpec(
            path=Path("alt_vehicle.csv"),
            conditioning_cols=["vehicle_type"],
            new_alt_var_col="alt_vehicle_type",
            scenario_cols=[],
            year_col=None,
            share_col="adoption_share",
        ),
        "alt_heating": AlternativeConfigTableSpec(
            path=Path("alt_heating.csv"),
            conditioning_cols=["heating_system", "alt_vehicle_type"],
            new_alt_var_col="alt_heating_system",
            scenario_cols=[],
            year_col=None,
            share_col="adoption_share",
        ),
    }

    expanded = merge_alternative_configurations(
        baseline,
        tables,
        specs,
        keep_provenance_shares=False,
    )

    assert len(expanded) == 8
    assert expanded["population_weight"].sum() == pytest.approx(0.75, abs=1e-6)

    row = expanded.filter(
        (pl.col("dwelling_type") == "single_family")
        & (pl.col("heating_system") == "furnace")
        & (pl.col("vehicle_type") == "ICE")
        & (pl.col("alt_vehicle_type") == "EV")
        & (pl.col("alt_heating_system") == "heat_pump")
    )
    assert len(row) == 1
    assert float(row["population_weight"][0]) == pytest.approx(0.096, abs=1e-6)


def test_merge_alt_configs_conserves_weight_by_scenario_and_year(tmp_path: Path) -> None:
    baseline = pl.DataFrame(
        [
            {"heating_system": "furnace", "vehicle_type": "ICE", "population_weight": 1.0},
        ]
    )

    alt_dir = tmp_path / "alternative_configurations"
    _write_csv(
        alt_dir / "alt_vehicle.csv",
        [
            {"vehicle_type": "ICE", "alt_vehicle_type": "EV", "scn_adoption": "conservative", "year": 2025, "adoption_share": 0.3},
            {"vehicle_type": "ICE", "alt_vehicle_type": "ICE", "scn_adoption": "conservative", "year": 2025, "adoption_share": 0.7},
            {"vehicle_type": "ICE", "alt_vehicle_type": "EV", "scn_adoption": "aggressive", "year": 2025, "adoption_share": 0.8},
            {"vehicle_type": "ICE", "alt_vehicle_type": "ICE", "scn_adoption": "aggressive", "year": 2025, "adoption_share": 0.2},
            {"vehicle_type": "ICE", "alt_vehicle_type": "EV", "scn_adoption": "conservative", "year": 2030, "adoption_share": 0.5},
            {"vehicle_type": "ICE", "alt_vehicle_type": "ICE", "scn_adoption": "conservative", "year": 2030, "adoption_share": 0.5},
            {"vehicle_type": "ICE", "alt_vehicle_type": "EV", "scn_adoption": "aggressive", "year": 2030, "adoption_share": 0.9},
            {"vehicle_type": "ICE", "alt_vehicle_type": "ICE", "scn_adoption": "aggressive", "year": 2030, "adoption_share": 0.1},
        ],
    )
    _write_csv(
        alt_dir / "alt_heating.csv",
        [
            {"heating_system": "furnace", "alt_vehicle_type": "EV", "alt_heating_system": "heat_pump", "adoption_share": 1.0},
            {"heating_system": "furnace", "alt_vehicle_type": "ICE", "alt_heating_system": "furnace", "adoption_share": 1.0},
        ],
    )

    tables, specs = _load_as_maps(alt_dir)
    expanded = merge_alternative_configurations(
        baseline,
        tables,
        specs,
        keep_provenance_shares=False,
    )

    by_scenario_year = expanded.group_by(["scn_adoption", "year"]).agg(pl.col("population_weight").sum())
    for scenario, year in [("conservative", 2025), ("aggressive", 2025), ("conservative", 2030), ("aggressive", 2030)]:
        weight = by_scenario_year.filter(
            (pl.col("scn_adoption") == scenario) & (pl.col("year") == year)
        )["population_weight"][0]
        assert weight == pytest.approx(1.0, abs=1e-6)


def test_merge_alt_configs_fails_when_conditioning_not_available() -> None:
    baseline = pl.DataFrame([
        {"vehicle_type": "ICE", "population_weight": 1.0},
    ])

    from energy_wallet.alternative_configurations.spec import AlternativeConfigTableSpec

    tables = {
        "alt_heating": pl.DataFrame(
            [
                {
                    "heating_system": "furnace",
                    "alt_heating_system": "heat_pump",
                    "adoption_share": 1.0,
                }
            ]
        )
    }
    specs = {
        "alt_heating": AlternativeConfigTableSpec(
            path=Path("alt_heating.csv"),
            conditioning_cols=["heating_system"],
            new_alt_var_col="alt_heating_system",
            scenario_cols=[],
            year_col=None,
            share_col="adoption_share",
        )
    }

    with pytest.raises(AlternativeConfigJoinError, match="conditioning/join columns not available"):
        merge_alternative_configurations(baseline, tables, specs)
