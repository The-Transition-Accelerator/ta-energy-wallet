"""Unit tests for DSPM converter core transforms."""

from __future__ import annotations

import pytest
import pandas as pd
import numpy as np

from energy_wallet.dspm_converter.unit_conversion import (
    kwh_to_gj,
    gj_to_kwh,
    KWH_TO_GJ,
)
from energy_wallet.dspm_converter.aggregation import (
    weighted_average,
    aggregate_envelope_bins,
    compute_population_shares,
)
from energy_wallet.dspm_converter.mapping import (
    map_fuel_name,
    map_climate_zones,
    EW_FUELS,
)
from energy_wallet.dspm_converter.efficiency import (
    compute_heating_efficiency,
    compute_cooling_efficiency,
    estimate_heating_temp_weights,
    HEATING_TEMPS,
    COOLING_TEMPS,
)
from energy_wallet.dspm_converter.fuel_proportions import (
    compute_fuel_proportions,
)
from energy_wallet.dspm_converter.errors import (
    DSPMValidationError,
    DSPMDataError,
)


# ===== Unit Conversion =====

class TestUnitConversion:
    def test_kwh_to_gj_basic(self):
        assert kwh_to_gj(1000) == pytest.approx(3.6)

    def test_gj_to_kwh_basic(self):
        assert gj_to_kwh(3.6) == pytest.approx(1000, rel=1e-3)

    def test_roundtrip(self):
        original = 500.0
        assert gj_to_kwh(kwh_to_gj(original)) == pytest.approx(original, rel=1e-6)

    def test_zero(self):
        assert kwh_to_gj(0) == 0.0
        assert gj_to_kwh(0) == 0.0

    def test_negative(self):
        assert kwh_to_gj(-100) == pytest.approx(-0.36)


# ===== Weighted Average =====

class TestWeightedAverage:
    def test_basic(self):
        assert weighted_average([10, 20, 30], [1, 1, 1]) == pytest.approx(20.0)

    def test_unequal_weights(self):
        assert weighted_average([10, 20], [3, 1]) == pytest.approx(12.5)

    def test_zero_weights(self):
        """Zero-guard: should return 0.0, not raise."""
        assert weighted_average([10, 20, 30], [0, 0, 0]) == 0.0

    def test_single_value(self):
        assert weighted_average([42], [1]) == pytest.approx(42.0)

    def test_empty(self):
        assert weighted_average([], []) == 0.0


# ===== Envelope Bin Aggregation =====

class TestEnvelopeAggregation:
    def _make_building_stock(self):
        return pd.DataFrame({
            "climate_zone": ["CZ_5"] * 6,
            "building_type": ["sfd"] * 6,
            "building_envelope_bin": [-5, -4, -3, -2, -1, 1],
            "building_genome_qty": [100, 100, 100, 200, 200, 300],
            "load_heating_annual_kwh": [
                15000, 14000, 13000, 10000, 9000, 7000
            ],
        })

    def test_basic_aggregation(self):
        bs = self._make_building_stock()
        groups = {"poor": [-5, -4, -3], "average": [-2, -1], "good": [1]}
        result = aggregate_envelope_bins(
            bs, groups,
            group_by=["climate_zone", "building_type"],
            load_cols=["load_heating_annual_kwh"],
        )
        assert len(result) == 3
        assert set(result["envelope_tier"]) == {"poor", "average", "good"}

        # Poor group: (15000*100 + 14000*100 + 13000*100) / 300 = 14000
        poor = result[result["envelope_tier"] == "poor"]
        assert poor.iloc[0]["load_heating_annual_kwh"] == pytest.approx(14000)

        # Average group: (10000*200 + 9000*200) / 400 = 9500
        avg = result[result["envelope_tier"] == "average"]
        assert avg.iloc[0]["load_heating_annual_kwh"] == pytest.approx(9500)

    def test_unmapped_bins_dropped(self):
        bs = self._make_building_stock()
        groups = {"poor": [-5, -4]}
        result = aggregate_envelope_bins(
            bs, groups,
            group_by=["climate_zone", "building_type"],
            load_cols=["load_heating_annual_kwh"],
        )
        assert len(result) == 1
        assert result.iloc[0]["envelope_tier"] == "poor"


# ===== Population Shares =====

class TestPopulationShares:
    def test_basic(self):
        df = pd.DataFrame({
            "dwelling_type": ["sfd", "apt"],
            "building_genome_qty": [300, 200],
        })
        result = compute_population_shares(
            df, group_cols=["dwelling_type"], within_cols=[],
        )
        sfd_share = result[result["dwelling_type"] == "sfd"]["population_share"].iloc[0]
        assert sfd_share == pytest.approx(0.6)

    def test_within_groups(self):
        df = pd.DataFrame({
            "climate_zone": ["CZ_5", "CZ_5", "CZ_6", "CZ_6"],
            "dwelling_type": ["sfd", "apt", "sfd", "apt"],
            "building_genome_qty": [300, 200, 100, 100],
        })
        result = compute_population_shares(
            df,
            group_cols=["dwelling_type"],
            within_cols=["climate_zone"],
        )
        # In CZ_6, sfd and apt should each be 0.5
        cz6_sfd = result[
            (result["climate_zone"] == "CZ_6") &
            (result["dwelling_type"] == "sfd")
        ]["population_share"].iloc[0]
        assert cz6_sfd == pytest.approx(0.5)


# ===== Fuel Name Mapping =====

class TestFuelMapping:
    def test_known_fuels(self):
        fuel_map = {"natural_gas": "gas", "electricity": "electric"}
        assert map_fuel_name("natural_gas", fuel_map) == "gas"
        assert map_fuel_name("electricity", fuel_map) == "electric"

    def test_unknown_fuel(self):
        fuel_map = {"natural_gas": "gas"}
        with pytest.raises(DSPMValidationError):
            map_fuel_name("hydrogen", fuel_map)


# ===== Climate Zone Mapping =====

class TestClimateZoneMapping:
    def test_basic(self):
        df = pd.DataFrame({"climate_zone": [5, 6]})
        cz_map = {"5": "CZ_5", "6": "CZ_6"}
        result = map_climate_zones(df, cz_map)
        assert result["climate_zone"].tolist() == ["CZ_5", "CZ_6"]

    def test_unmapped_raises(self):
        df = pd.DataFrame({"climate_zone": [5, 99]})
        cz_map = {"5": "CZ_5"}
        with pytest.raises(DSPMValidationError):
            map_climate_zones(df, cz_map)


# ===== Temperature Weights =====

class TestTemperatureWeights:
    def test_weights_zero_below_design_temp(self):
        """Temps below design temp should have zero weight."""
        weights = estimate_heating_temp_weights(-20.0)
        # All temps below -20 should be 0
        for temp, w in zip(HEATING_TEMPS, weights):
            if temp < -20.0:
                assert w == 0.0, f"Expected 0 at temp={temp}, got {w}"

    def test_weights_zero_above_balance(self):
        """Temps above 18C should have zero weight."""
        weights = estimate_heating_temp_weights(-40.0)
        for temp, w in zip(HEATING_TEMPS, weights):
            if temp > 18.0:
                assert w == 0.0, f"Expected 0 at temp={temp}, got {w}"

    def test_weights_increase_for_colder_temps(self):
        """Weight should increase as temp decreases (more degree-days)."""
        weights = estimate_heating_temp_weights(-40.0)
        # Compare weight at 0C vs 15C: 0C should have higher weight
        idx_0 = HEATING_TEMPS.index(0)
        idx_15 = HEATING_TEMPS.index(15)
        assert weights[idx_0] > weights[idx_15]

    def test_cold_cz_includes_more_temps(self):
        """A cold CZ (design=-40) should have non-zero weights at more temps
        than a mild CZ (design=-10)."""
        cold = estimate_heating_temp_weights(-40.0)
        mild = estimate_heating_temp_weights(-10.0)
        cold_nonzero = sum(1 for w in cold if w > 0)
        mild_nonzero = sum(1 for w in mild if w > 0)
        assert cold_nonzero > mild_nonzero


# ===== Heating Efficiency =====

class TestHeatingEfficiency:
    def _make_single_fuel_row(self, cop_value=0.95):
        """Create a row for a single-fuel gas furnace."""
        row = {
            "equipment_config_id": "test_001",
            "load_share_primary": "1",
            "equipment_primary_energy_source": "natural_gas",
        }
        for temp in HEATING_TEMPS:
            if temp < 0:
                t_str = f"neg_{abs(temp)}"
            else:
                t_str = str(temp)
            t_str = t_str.replace(".0", "").replace(".", ".")
            row[f"heating_cop_{t_str}_primary"] = cop_value
            row[f"heating_cap_{t_str}_primary"] = 10.0
        return pd.Series(row)

    def test_single_fuel_constant_cop(self):
        """Constant COP should return that COP value."""
        row = self._make_single_fuel_row(cop_value=0.95)
        eff = compute_heating_efficiency(row)
        assert eff == pytest.approx(0.95, rel=1e-3)

    def test_single_fuel_with_temp_weights(self):
        """With temp weights, constant COP still returns same value."""
        row = self._make_single_fuel_row(cop_value=0.95)
        weights = estimate_heating_temp_weights(-30.0)
        eff = compute_heating_efficiency(row, temp_weights=weights)
        assert eff == pytest.approx(0.95, rel=1e-3)

    def test_single_fuel_zero_capacity(self):
        """All zero capacity should return 0 (zero-guard)."""
        row = self._make_single_fuel_row()
        for temp in HEATING_TEMPS:
            if temp < 0:
                t_str = f"neg_{abs(temp)}"
            else:
                t_str = str(temp)
            t_str = t_str.replace(".0", "").replace(".", ".")
            row[f"heating_cap_{t_str}_primary"] = 0.0
        eff = compute_heating_efficiency(row)
        assert eff == 0.0


# ===== Cooling Efficiency =====

class TestCoolingEfficiency:
    def test_no_cooling(self):
        row = pd.Series({"has_cooling": 0})
        assert compute_cooling_efficiency(row) == 0.0

    def test_with_cooling(self):
        row = {"has_cooling": 1}
        for temp in COOLING_TEMPS:
            if temp < 0:
                t_str = f"neg_{abs(temp)}"
            else:
                t_str = str(temp)
            t_str = t_str.replace(".0", "").replace(".", ".")
            row[f"cooling_cop_{t_str}_primary"] = 3.5
            row[f"cooling_cap_{t_str}_primary"] = 10.0
        eff = compute_cooling_efficiency(pd.Series(row))
        assert eff == pytest.approx(3.5, rel=1e-3)


# ===== Fuel Proportions =====

class TestFuelProportions:
    def test_single_fuel(self):
        fuel_map = {"natural_gas": "gas", "electricity": "electric"}
        row = pd.Series({
            "equipment_primary_energy_source": "natural_gas",
            "equipment_secondary_energy_source": None,
            "load_share_primary": "1",
        })
        props = compute_fuel_proportions(row, fuel_map)
        assert props["gas"] == 1.0
        assert props["electric"] == 0.0
        assert sum(props.values()) == pytest.approx(1.0)

    def test_fixed_split(self):
        fuel_map = {"natural_gas": "gas", "electricity": "electric"}
        row = pd.Series({
            "equipment_primary_energy_source": "natural_gas",
            "equipment_secondary_energy_source": "electricity",
            "load_share_primary": "0.7",
        })
        props = compute_fuel_proportions(row, fuel_map)
        assert props["gas"] == pytest.approx(0.7)
        assert props["electric"] == pytest.approx(0.3)
        assert sum(props.values()) == pytest.approx(1.0)

    def test_proportions_sum_to_one(self):
        fuel_map = {"natural_gas": "gas", "electricity": "electric"}
        row = pd.Series({
            "equipment_primary_energy_source": "natural_gas",
            "equipment_secondary_energy_source": None,
            "load_share_primary": "1",
        })
        props = compute_fuel_proportions(row, fuel_map)
        assert sum(props.values()) == pytest.approx(1.0)
        assert set(props.keys()) == set(EW_FUELS)

    def test_single_fuel_with_temp_weights(self):
        """Temp weights shouldn't affect single-fuel proportions."""
        fuel_map = {"natural_gas": "gas", "electricity": "electric"}
        row = pd.Series({
            "equipment_primary_energy_source": "natural_gas",
            "equipment_secondary_energy_source": None,
            "load_share_primary": "1",
        })
        weights = estimate_heating_temp_weights(-30.0)
        props = compute_fuel_proportions(row, fuel_map, temp_weights=weights)
        assert props["gas"] == 1.0
        assert sum(props.values()) == pytest.approx(1.0)
