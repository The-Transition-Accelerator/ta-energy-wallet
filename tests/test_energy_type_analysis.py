"""Tests for Step 5: Utility Bill Perspective (energy-type analysis)."""
from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pandas as pd
import polars as pl
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from energy_wallet.calculations.pipeline import compute_energy_wallet  # noqa: E402
from energy_wallet.energy_type_analysis.pipeline import compute_utility_bill_perspective  # noqa: E402


def _make_full_model_input() -> pl.DataFrame:
    """Build a minimal but complete model input DataFrame."""
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

        # Vehicle 2 (none)
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

    return pl.DataFrame([data])


def test_utility_bill_reconciliation() -> None:
    """Sum of 7 energy bill categories should equal utility_bill_total.

    Additionally, utility_bill_total + capital + maintenance (from Step 4
    intermediate columns) should equal energy_wallet total.
    """
    df = _make_full_model_input()
    step4 = compute_energy_wallet(df)
    step5 = compute_utility_bill_perspective(step4)

    for sfx in ("base", "alt"):
        # 7 energy categories should sum to utility_bill_total
        bill_sum = (
            step5[f"utility_bill_electricity_{sfx}"][0]
            + step5[f"utility_bill_natural_gas_{sfx}"][0]
            + step5[f"utility_bill_oil_{sfx}"][0]
            + step5[f"utility_bill_propane_{sfx}"][0]
            + step5[f"utility_bill_wood_{sfx}"][0]
            + step5[f"utility_bill_gasoline_{sfx}"][0]
            + step5[f"utility_bill_public_ev_charging_{sfx}"][0]
        )
        np.testing.assert_allclose(
            bill_sum, step5[f"utility_bill_total_{sfx}"][0], rtol=1e-5
        )

        # bill_total + capital + maintenance should equal energy_wallet
        # (capital/maintenance are in Step 4 intermediates, not Step 5 output)
        capital = 0.0
        for slot in (1, 2):
            col = f"vehicle_{slot}_{sfx}_annual_capital"
            if col in step5.columns:
                capital += step5[col][0]
        for prefix in (f"hvac_{sfx}_annual_capital", f"dhw_{sfx}_annual_capital",
                        f"other_{sfx}_panel_annual_capital"):
            if prefix in step5.columns:
                capital += step5[prefix][0]

        maintenance = 0.0
        for slot in (1, 2):
            col = f"vehicle_{slot}_{sfx}_annual_maintenance"
            if col in step5.columns:
                maintenance += step5[col][0]
        for prefix in (f"hvac_{sfx}_annual_maintenance", f"dhw_{sfx}_annual_maintenance"):
            if prefix in step5.columns:
                maintenance += step5[prefix][0]

        wallet = step5[f"energy_wallet_{sfx}"][0]
        np.testing.assert_allclose(bill_sum + capital + maintenance, wallet, rtol=1e-5)


def test_utility_bill_categories_exist() -> None:
    """All expected utility bill columns should be present."""
    df = _make_full_model_input()
    step4 = compute_energy_wallet(df)
    step5 = compute_utility_bill_perspective(step4)

    for sfx in ("base", "alt"):
        for cat in (
            "electricity", "natural_gas", "oil", "propane", "wood",
            "gasoline", "public_ev_charging", "total",
        ):
            assert f"utility_bill_{cat}_{sfx}" in step5.columns
        # Capital and maintenance should NOT be in Step 5 output
        assert f"capital_total_{sfx}" not in step5.columns
        assert f"maintenance_total_{sfx}" not in step5.columns


def test_utility_bill_ice_base_has_gasoline_no_ev() -> None:
    """Base config with ICE vehicle: gasoline > 0, public EV = 0."""
    df = _make_full_model_input()
    step4 = compute_energy_wallet(df)
    step5 = compute_utility_bill_perspective(step4)

    assert step5["utility_bill_gasoline_base"][0] > 0
    assert step5["utility_bill_public_ev_charging_base"][0] == 0.0


def test_utility_bill_ev_alt_has_ev_no_gasoline() -> None:
    """Alt config with EV vehicle: gasoline = 0, public EV > 0."""
    df = _make_full_model_input()
    step4 = compute_energy_wallet(df)
    step5 = compute_utility_bill_perspective(step4)

    assert step5["utility_bill_gasoline_alt"][0] == 0.0
    assert step5["utility_bill_public_ev_charging_alt"][0] > 0


def test_utility_bill_diff_columns() -> None:
    """Diff columns should be alt - base."""
    df = _make_full_model_input()
    step4 = compute_energy_wallet(df)
    step5 = compute_utility_bill_perspective(step4)

    for cat in ("electricity", "natural_gas", "gasoline", "total"):
        diff = step5[f"utility_bill_{cat}_diff"][0]
        expected = (
            step5[f"utility_bill_{cat}_alt"][0]
            - step5[f"utility_bill_{cat}_base"][0]
        )
        np.testing.assert_allclose(diff, expected)
    # Capital and maintenance diff columns should NOT exist
    assert "capital_total_diff" not in step5.columns
    assert "maintenance_total_diff" not in step5.columns
