from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from energy_wallet.archetypes import load_all_archetype_tables, merge_archetypes  # noqa: E402
from energy_wallet.alternative_configurations import build_expanded_archetype_table  # noqa: E402
from energy_wallet.input_parameters import build_model_input_table  # noqa: E402
from energy_wallet.input_parameters.errors import InputParameterJoinError  # noqa: E402
from energy_wallet.input_parameters.io import infer_spec_from_columns  # noqa: E402
from energy_wallet.input_parameters.join import attach_input_parameters  # noqa: E402
from energy_wallet.input_parameters.spec import InputParameterTableSpec  # noqa: E402


def _baseline_and_expanded_from_repo_inputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    inputs_root = Path("inputs/test_input_set_1")
    tables_list, specs_list = load_all_archetype_tables(inputs_root / "archetypes")
    tables = {spec.path.stem: table for table, spec in zip(tables_list, specs_list)}
    specs = {spec.path.stem: spec for spec in specs_list}
    baseline = merge_archetypes(tables, specs, keep_provenance_shares=False)

    expanded = build_expanded_archetype_table(
        baseline,
        inputs_root=inputs_root,
    )
    return baseline, expanded


def test_infer_spec_treats_scenario_and_year_as_join_dimensions() -> None:
    spec = infer_spec_from_columns(
        Path("example.csv"),
        [
            "climate_zone",
            "fuel_price_scenario",
            "year",
            "cost_electricity_home",
            "discount_rate",
        ],
        known_join_columns={"climate_zone"},
    )

    assert spec.join_cols == ["climate_zone", "fuel_price_scenario", "year"]
    assert spec.input_value_cols == ["cost_electricity_home", "discount_rate"]
    assert spec.year_col == "year"


def test_attach_input_parameters_raises_when_match_coverage_is_missing() -> None:
    expanded = pd.DataFrame(
        [
            {"vehicle_type": "ICE", "population_weight": 1.0},
        ]
    )
    table = pd.DataFrame(
        [
            {"vehicle_type": "EV", "vehicle_purchase_cost_base": 35000.0},
        ]
    )

    spec = InputParameterTableSpec(
        path=Path("vehicle_costs.csv"),
        join_cols=["vehicle_type"],
        input_value_cols=["vehicle_purchase_cost_base"],
        year_col=None,
    )

    with pytest.raises(InputParameterJoinError, match="missing input data coverage"):
        attach_input_parameters(
            expanded,
            tables={"vehicle_costs": table},
            specs={"vehicle_costs": spec},
            validate=False,
        )


def test_build_model_input_table_end_to_end_with_repo_inputs() -> None:
    _, expanded = _baseline_and_expanded_from_repo_inputs()

    model_inputs = build_model_input_table(
        expanded,
        inputs_root=Path("inputs/test_input_set_1"),
    )

    assert len(model_inputs) == len(expanded)

    required_subset = [
        "cost_electricity_home",
        "discount_rate",
        "vehicle_1_purchase_cost_base",
        "vehicle_1_purchase_cost_alt",
        "vehicle_2_purchase_cost_base",
        "vehicle_2_purchase_cost_alt",
        "hvac_equipment_cost_base",
        "hvac_equipment_cost_alt",
        "dhw_equipment_cost_base",
        "dhw_equipment_cost_alt",
        "panel_upgrade_cost_base",
        "panel_upgrade_cost_alt",
    ]
    for col in required_subset:
        assert col in model_inputs.columns
        assert not model_inputs[col].isna().any()

    by_scenario_year = model_inputs.groupby(["scn_adoption", "year"], observed=True)[
        "population_weight"
    ].sum()
    assert (by_scenario_year - 1.0).abs().max() <= 1e-9
