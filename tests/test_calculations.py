"""Tests for Step 4: Energy Wallet Calculations."""
from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from energy_wallet.calculations.annualize import annualized_capital  # noqa: E402
from energy_wallet.calculations.vehicle import compute_vehicle_slot_costs  # noqa: E402
from energy_wallet.calculations.hvac import compute_hvac_costs  # noqa: E402
from energy_wallet.calculations.dhw import compute_dhw_costs  # noqa: E402
from energy_wallet.calculations.other import compute_other_costs  # noqa: E402
from energy_wallet.calculations.pipeline import compute_energy_wallet  # noqa: E402
from energy_wallet.calculations.errors import CalculationError  # noqa: E402


# ---------------------------------------------------------------------------
# Annualize
# ---------------------------------------------------------------------------

def test_annualize_basic() -> None:
    """PMT formula: cost * rate / (1 - (1+rate)^{-life})."""
    cost = pd.Series([10000.0])
    rate = pd.Series([0.03])
    life = pd.Series([10.0])

    result = annualized_capital(cost, rate, life)
    # Manual: 10000 * 0.03 / (1 - 1.03^{-10}) = 10000 * 0.03 / 0.14635 ≈ 1172.31
    expected = 10000.0 * 0.03 / (1 - (1.03) ** (-10))
    np.testing.assert_allclose(result.values, [expected], rtol=1e-6)


def test_annualize_zero_cost() -> None:
    """Zero cost returns zero payment."""
    result = annualized_capital(
        pd.Series([0.0]), pd.Series([0.03]), pd.Series([10.0])
    )
    assert result.iloc[0] == 0.0


def test_annualize_zero_life() -> None:
    """Life <= 0 returns zero payment."""
    result = annualized_capital(
        pd.Series([10000.0]), pd.Series([0.03]), pd.Series([0.0])
    )
    assert result.iloc[0] == 0.0


def test_annualize_zero_rate() -> None:
    """Rate = 0 returns zero (guarded)."""
    result = annualized_capital(
        pd.Series([10000.0]), pd.Series([0.0]), pd.Series([10.0])
    )
    assert result.iloc[0] == pytest.approx(1000.0)


# ---------------------------------------------------------------------------
# Vehicle slot costs
# ---------------------------------------------------------------------------

def _make_vehicle_df(
    slot: int = 1,
    suffix: str = "base",
    vehicle_type: str = "ICE",
) -> pd.DataFrame:
    """Build a single-row DataFrame with all columns needed for vehicle slot calcs."""
    s = str(slot)
    sfx = suffix
    if vehicle_type == "ICE":
        return pd.DataFrame([{
            f"vehicle_{s}_purchase_cost_{sfx}": 30000.0,
            f"vehicle_{s}_assumed_life_{sfx}": 12.0,
            f"vehicle_{s}_maintenance_cost_per_km_{sfx}": 0.05,
            f"vehicle_{s}_efficiency_gas_{sfx}": 0.0025,  # GJ/km
            f"vehicle_{s}_efficiency_electric_{sfx}": 0.0,
            f"ev_{s}_efficiency_factor_{sfx}": 1.0,
            f"ev_{s}_pct_charged_home_{sfx}": 0.0,
            f"ev_{s}_pct_charged_level2_{sfx}": 0.0,
            f"ev_{s}_pct_charged_fast_{sfx}": 0.0,
            f"vkt_{s}_annual_{sfx}": 15000.0,
            "discount_rate": 0.03,
            "cost_gasoline": 35.0,
            "cost_electricity_home": 50.0,
            "cost_electricity_level2": 55.0,
            "cost_electricity_fast": 60.0,
        }])
    elif vehicle_type == "EV":
        return pd.DataFrame([{
            f"vehicle_{s}_purchase_cost_{sfx}": 40000.0,
            f"vehicle_{s}_assumed_life_{sfx}": 15.0,
            f"vehicle_{s}_maintenance_cost_per_km_{sfx}": 0.02,
            f"vehicle_{s}_efficiency_gas_{sfx}": 0.0,
            f"vehicle_{s}_efficiency_electric_{sfx}": 0.18,  # kWh/km
            f"ev_{s}_efficiency_factor_{sfx}": 0.90,
            f"ev_{s}_pct_charged_home_{sfx}": 0.70,
            f"ev_{s}_pct_charged_level2_{sfx}": 0.20,
            f"ev_{s}_pct_charged_fast_{sfx}": 0.10,
            f"vkt_{s}_annual_{sfx}": 14000.0,
            "discount_rate": 0.03,
            "cost_gasoline": 35.0,
            "cost_electricity_home": 50.0,
            "cost_electricity_level2": 55.0,
            "cost_electricity_fast": 60.0,
        }])
    else:  # "none"
        return pd.DataFrame([{
            f"vehicle_{s}_purchase_cost_{sfx}": 0.0,
            f"vehicle_{s}_assumed_life_{sfx}": 1.0,
            f"vehicle_{s}_maintenance_cost_per_km_{sfx}": 0.0,
            f"vehicle_{s}_efficiency_gas_{sfx}": 0.0,
            f"vehicle_{s}_efficiency_electric_{sfx}": 0.0,
            f"ev_{s}_efficiency_factor_{sfx}": 1.0,
            f"ev_{s}_pct_charged_home_{sfx}": 0.0,
            f"ev_{s}_pct_charged_level2_{sfx}": 0.0,
            f"ev_{s}_pct_charged_fast_{sfx}": 0.0,
            f"vkt_{s}_annual_{sfx}": 0.0,
            "discount_rate": 0.03,
            "cost_gasoline": 35.0,
            "cost_electricity_home": 50.0,
            "cost_electricity_level2": 55.0,
            "cost_electricity_fast": 60.0,
        }])


def test_vehicle_ice_costs() -> None:
    df = _make_vehicle_df(slot=1, suffix="base", vehicle_type="ICE")
    result = compute_vehicle_slot_costs(df, slot=1, suffix="base")

    # Capital > 0
    assert result["vehicle_1_base_annual_capital"].iloc[0] > 0

    # Maintenance = 0.05 * 15000 = 750
    np.testing.assert_allclose(result["vehicle_1_base_annual_maintenance"].iloc[0], 750.0)

    # Gas energy = 0.0025 * 15000 = 37.5 GJ
    np.testing.assert_allclose(result["vehicle_1_base_gas_energy_gj"].iloc[0], 37.5)

    # Gas cost = 37.5 * 35 = 1312.5
    np.testing.assert_allclose(result["vehicle_1_base_gas_cost"].iloc[0], 1312.5)

    # EV energy = 0 (ICE)
    assert result["vehicle_1_base_ev_energy_gj"].iloc[0] == 0.0
    assert result["vehicle_1_base_ev_cost"].iloc[0] == 0.0


def test_vehicle_ev_costs() -> None:
    df = _make_vehicle_df(slot=1, suffix="alt", vehicle_type="EV")
    result = compute_vehicle_slot_costs(df, slot=1, suffix="alt")

    # Gas = 0 (EV)
    assert result["vehicle_1_alt_gas_energy_gj"].iloc[0] == 0.0
    assert result["vehicle_1_alt_gas_cost"].iloc[0] == 0.0

    # EV energy > 0
    ev_energy_gj = result["vehicle_1_alt_ev_energy_gj"].iloc[0]
    assert ev_energy_gj > 0

    # Manual: 0.18 kWh/km * 14000 km = 2520 kWh; / 0.90 = 2800 kWh; * 0.0036 = 10.08 GJ
    expected_gj = 0.18 * 14000 / 0.90 * 0.0036
    np.testing.assert_allclose(ev_energy_gj, expected_gj, rtol=1e-6)

    # EV cost = energy * weighted price
    weighted_price = 0.70 * 50 + 0.20 * 55 + 0.10 * 60
    expected_ev_cost = expected_gj * weighted_price
    np.testing.assert_allclose(result["vehicle_1_alt_ev_cost"].iloc[0], expected_ev_cost, rtol=1e-6)

    # Home/public split
    ev_cost_home = result["vehicle_1_alt_ev_cost_home"].iloc[0]
    ev_cost_public = result["vehicle_1_alt_ev_cost_public"].iloc[0]
    np.testing.assert_allclose(
        ev_cost_home + ev_cost_public,
        result["vehicle_1_alt_ev_cost"].iloc[0],
        rtol=1e-6,
    )


def test_vehicle_none_costs() -> None:
    df = _make_vehicle_df(slot=2, suffix="base", vehicle_type="none")
    result = compute_vehicle_slot_costs(df, slot=2, suffix="base")

    # All costs should be zero
    assert result["vehicle_2_base_annual_capital"].iloc[0] == 0.0
    assert result["vehicle_2_base_annual_maintenance"].iloc[0] == 0.0
    assert result["vehicle_2_base_gas_cost"].iloc[0] == 0.0
    assert result["vehicle_2_base_ev_cost"].iloc[0] == 0.0
    assert result["vehicle_2_base_total_cost"].iloc[0] == 0.0


# ---------------------------------------------------------------------------
# HVAC costs
# ---------------------------------------------------------------------------

def _make_hvac_df(suffix: str = "base") -> pd.DataFrame:
    sfx = suffix
    data = {
        f"hvac_equipment_cost_{sfx}": 8000.0,
        f"hvac_assumed_life_{sfx}": 15.0,
        f"hvac_maintenance_cost_annual_{sfx}": 200.0,
        f"heating_load_annual_{sfx}": 80.0,  # GJ
        f"cooling_load_annual_{sfx}": 10.0,  # GJ
        f"cooling_system_efficiency_{sfx}": 3.5,
        "discount_rate": 0.03,
        "cost_electricity_home": 50.0,
        "cost_natural_gas_home": 20.0,
        "cost_oil_home": 45.0,
        "cost_propane_home": 40.0,
        "cost_wood_home": 15.0,
    }
    # Furnace: 100% gas
    for fuel in ("gas", "electric", "oil", "propane", "wood"):
        data[f"heating_system_proportion_{fuel}_{sfx}"] = 1.0 if fuel == "gas" else 0.0
        data[f"heating_system_efficiency_{fuel}_{sfx}"] = 0.92 if fuel == "gas" else 1.0

    return pd.DataFrame([data])


def test_hvac_furnace_costs() -> None:
    df = _make_hvac_df("base")
    result = compute_hvac_costs(df, suffix="base")

    assert result["hvac_base_annual_capital"].iloc[0] > 0
    assert result["hvac_base_annual_maintenance"].iloc[0] == 200.0

    # Heating: 80 GJ * 1.0 / 0.92 * 20 = 1739.13
    expected_heating = 80.0 / 0.92 * 20.0
    np.testing.assert_allclose(
        result["hvac_base_heating_cost"].iloc[0], expected_heating, rtol=1e-4
    )

    # Cooling: 10 / 3.5 * 50 = 142.86
    expected_cooling = 10.0 / 3.5 * 50.0
    np.testing.assert_allclose(
        result["hvac_base_cooling_cost"].iloc[0], expected_cooling, rtol=1e-4
    )


# ---------------------------------------------------------------------------
# DHW costs
# ---------------------------------------------------------------------------

def _make_dhw_df(suffix: str = "base") -> pd.DataFrame:
    sfx = suffix
    data = {
        f"dhw_equipment_cost_{sfx}": 1500.0,
        f"dhw_assumed_life_{sfx}": 12.0,
        f"dhw_maintenance_cost_annual_{sfx}": 50.0,
        f"dhw_load_annual_{sfx}": 18.0,  # GJ
        "discount_rate": 0.03,
        "cost_electricity_home": 50.0,
        "cost_natural_gas_home": 20.0,
        "cost_oil_home": 45.0,
        "cost_propane_home": 40.0,
        "cost_wood_home": 15.0,
    }
    # 60% gas, 40% electric
    for fuel in ("gas", "electric", "oil", "propane", "wood"):
        if fuel == "gas":
            data[f"dhw_system_proportion_{fuel}_{sfx}"] = 0.6
            data[f"dhw_system_efficiency_{fuel}_{sfx}"] = 0.62
        elif fuel == "electric":
            data[f"dhw_system_proportion_{fuel}_{sfx}"] = 0.4
            data[f"dhw_system_efficiency_{fuel}_{sfx}"] = 0.95
        else:
            data[f"dhw_system_proportion_{fuel}_{sfx}"] = 0.0
            data[f"dhw_system_efficiency_{fuel}_{sfx}"] = 1.0

    return pd.DataFrame([data])


def test_dhw_costs() -> None:
    df = _make_dhw_df("base")
    result = compute_dhw_costs(df, suffix="base")

    assert result["dhw_base_annual_capital"].iloc[0] > 0
    assert result["dhw_base_annual_maintenance"].iloc[0] == 50.0

    # Gas: 18 * 0.6 / 0.62 * 20 = 348.39
    expected_gas_cost = 18.0 * 0.6 / 0.62 * 20.0
    np.testing.assert_allclose(
        result["dhw_base_gas_cost"].iloc[0], expected_gas_cost, rtol=1e-4
    )

    # Electric: 18 * 0.4 / 0.95 * 50 = 378.95
    expected_elec_cost = 18.0 * 0.4 / 0.95 * 50.0
    np.testing.assert_allclose(
        result["dhw_base_electric_cost"].iloc[0], expected_elec_cost, rtol=1e-4
    )


# ---------------------------------------------------------------------------
# Other costs
# ---------------------------------------------------------------------------

def _make_other_df(suffix: str = "base", uses_gas: bool = True) -> pd.DataFrame:
    sfx = suffix
    data = {
        f"other_electricity_annual_{sfx}": 5.0,  # GJ
        f"other_natural_gas_annual_{sfx}": 3.0 if uses_gas else 0.0,  # GJ
        "cost_electricity_home": 50.0,
        "cost_natural_gas_home": 20.0,
        "electricity_fixed_charge_monthly": 15.0,
        "natural_gas_fixed_charge_monthly": 12.0,
        f"panel_upgrade_cost_{sfx}": 2000.0,
        f"panel_assumed_life_{sfx}": 30.0,
        "discount_rate": 0.03,
    }
    # Gas usage flags
    data[f"heating_system_proportion_gas_{sfx}"] = 1.0 if uses_gas else 0.0
    data[f"dhw_system_proportion_gas_{sfx}"] = 0.0

    return pd.DataFrame([data])


def test_other_costs_with_gas() -> None:
    df = _make_other_df("base", uses_gas=True)
    result = compute_other_costs(df, suffix="base")

    # Other elec: 5 * 50 = 250
    np.testing.assert_allclose(result["other_base_electricity_cost"].iloc[0], 250.0)

    # Other NG: 3 * 20 = 60
    np.testing.assert_allclose(result["other_base_natural_gas_cost"].iloc[0], 60.0)

    # Elec fixed: 15 * 12 = 180
    np.testing.assert_allclose(result["other_base_electricity_fixed_charge"].iloc[0], 180.0)

    # NG fixed: 12 * 12 = 144 (uses gas = True)
    np.testing.assert_allclose(result["other_base_natural_gas_fixed_charge"].iloc[0], 144.0)


def test_other_costs_ng_fixed_excluded_when_no_gas() -> None:
    df = _make_other_df("alt", uses_gas=False)
    result = compute_other_costs(df, suffix="alt")

    # NG fixed charge should be 0 when no gas is used
    np.testing.assert_allclose(result["other_alt_natural_gas_fixed_charge"].iloc[0], 0.0)


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------

def _make_full_model_input() -> pd.DataFrame:
    """Build a minimal but complete model input DataFrame for pipeline test."""
    data = {
        "discount_rate": 0.03,
        "cost_gasoline": 35.0,
        "cost_electricity_home": 50.0,
        "cost_electricity_level2": 55.0,
        "cost_electricity_fast": 60.0,
        "cost_natural_gas_home": 20.0,
        "cost_oil_home": 45.0,
        "cost_propane_home": 40.0,
        "cost_wood_home": 15.0,
        "electricity_fixed_charge_monthly": 15.0,
        "natural_gas_fixed_charge_monthly": 12.0,
    }

    for sfx in ("base", "alt"):
        # Vehicle 1 (ICE base, EV alt)
        if sfx == "base":
            data.update({
                f"vehicle_1_purchase_cost_{sfx}": 30000.0,
                f"vehicle_1_assumed_life_{sfx}": 12.0,
                f"vehicle_1_maintenance_cost_per_km_{sfx}": 0.05,
                f"vehicle_1_efficiency_gas_{sfx}": 0.0025,
                f"vehicle_1_efficiency_electric_{sfx}": 0.0,
                f"ev_1_efficiency_factor_{sfx}": 1.0,
                f"ev_1_pct_charged_home_{sfx}": 0.0,
                f"ev_1_pct_charged_level2_{sfx}": 0.0,
                f"ev_1_pct_charged_fast_{sfx}": 0.0,
                f"vkt_1_annual_{sfx}": 15000.0,
            })
        else:
            data.update({
                f"vehicle_1_purchase_cost_{sfx}": 40000.0,
                f"vehicle_1_assumed_life_{sfx}": 15.0,
                f"vehicle_1_maintenance_cost_per_km_{sfx}": 0.02,
                f"vehicle_1_efficiency_gas_{sfx}": 0.0,
                f"vehicle_1_efficiency_electric_{sfx}": 0.18,
                f"ev_1_efficiency_factor_{sfx}": 0.90,
                f"ev_1_pct_charged_home_{sfx}": 0.70,
                f"ev_1_pct_charged_level2_{sfx}": 0.20,
                f"ev_1_pct_charged_fast_{sfx}": 0.10,
                f"vkt_1_annual_{sfx}": 14000.0,
            })

        # Vehicle 2 (none for both)
        data.update({
            f"vehicle_2_purchase_cost_{sfx}": 0.0,
            f"vehicle_2_assumed_life_{sfx}": 1.0,
            f"vehicle_2_maintenance_cost_per_km_{sfx}": 0.0,
            f"vehicle_2_efficiency_gas_{sfx}": 0.0,
            f"vehicle_2_efficiency_electric_{sfx}": 0.0,
            f"ev_2_efficiency_factor_{sfx}": 1.0,
            f"ev_2_pct_charged_home_{sfx}": 0.0,
            f"ev_2_pct_charged_level2_{sfx}": 0.0,
            f"ev_2_pct_charged_fast_{sfx}": 0.0,
            f"vkt_2_annual_{sfx}": 0.0,
        })

        # HVAC (furnace: 100% gas)
        data.update({
            f"hvac_equipment_cost_{sfx}": 8000.0,
            f"hvac_assumed_life_{sfx}": 15.0,
            f"hvac_maintenance_cost_annual_{sfx}": 200.0,
            f"heating_load_annual_{sfx}": 80.0,
            f"cooling_load_annual_{sfx}": 10.0,
            f"cooling_system_efficiency_{sfx}": 3.5,
        })
        for fuel in ("gas", "electric", "oil", "propane", "wood"):
            data[f"heating_system_proportion_{fuel}_{sfx}"] = 1.0 if fuel == "gas" else 0.0
            data[f"heating_system_efficiency_{fuel}_{sfx}"] = 0.92 if fuel == "gas" else 1.0

        # DHW (60% gas, 40% electric)
        data.update({
            f"dhw_equipment_cost_{sfx}": 1500.0,
            f"dhw_assumed_life_{sfx}": 12.0,
            f"dhw_maintenance_cost_annual_{sfx}": 50.0,
            f"dhw_load_annual_{sfx}": 18.0,
        })
        for fuel in ("gas", "electric", "oil", "propane", "wood"):
            if fuel == "gas":
                data[f"dhw_system_proportion_{fuel}_{sfx}"] = 0.6
                data[f"dhw_system_efficiency_{fuel}_{sfx}"] = 0.62
            elif fuel == "electric":
                data[f"dhw_system_proportion_{fuel}_{sfx}"] = 0.4
                data[f"dhw_system_efficiency_{fuel}_{sfx}"] = 0.95
            else:
                data[f"dhw_system_proportion_{fuel}_{sfx}"] = 0.0
                data[f"dhw_system_efficiency_{fuel}_{sfx}"] = 1.0

        # Other
        data.update({
            f"other_electricity_annual_{sfx}": 5.0,
            f"other_natural_gas_annual_{sfx}": 3.0,
            f"panel_upgrade_cost_{sfx}": 2000.0 if sfx == "alt" else 0.0,
            f"panel_assumed_life_{sfx}": 30.0,
        })

    return pd.DataFrame([data])


def test_compute_energy_wallet_full_pipeline() -> None:
    """End-to-end pipeline: verify totals and comparison metrics."""
    df = _make_full_model_input()
    result = compute_energy_wallet(df)

    # Check summary columns exist
    assert "energy_wallet_base" in result.columns
    assert "energy_wallet_alt" in result.columns
    assert "energy_wallet_diff_absolute" in result.columns
    assert "energy_wallet_diff_percent" in result.columns

    # Totals should be positive
    assert result["energy_wallet_base"].iloc[0] > 0
    assert result["energy_wallet_alt"].iloc[0] > 0

    # Verify total = sum of components
    for sfx in ("base", "alt"):
        total = result[f"energy_wallet_{sfx}"].iloc[0]
        components = (
            result[f"vehicles_{sfx}_total_cost"].iloc[0]
            + result[f"hvac_{sfx}_total_cost"].iloc[0]
            + result[f"dhw_{sfx}_total_cost"].iloc[0]
            + result[f"other_{sfx}_total_cost"].iloc[0]
        )
        np.testing.assert_allclose(total, components, rtol=1e-9)

    # Verify diff = alt - base
    diff = result["energy_wallet_alt"].iloc[0] - result["energy_wallet_base"].iloc[0]
    np.testing.assert_allclose(result["energy_wallet_diff_absolute"].iloc[0], diff)


def test_compute_energy_wallet_missing_column_raises() -> None:
    """Pipeline raises CalculationError for missing columns."""
    df = pd.DataFrame([{"discount_rate": 0.03}])
    with pytest.raises(CalculationError):
        compute_energy_wallet(df)
