"""Shared registries, color palettes, and constants for the dashboard.

Ported from dashboard/charts.py — no Streamlit dependency.
"""

from __future__ import annotations

from collections import OrderedDict

# ---------------------------------------------------------------------------
# Weight column
# ---------------------------------------------------------------------------

WEIGHT_COL = "population_weight"

# ---------------------------------------------------------------------------
# Dimension registry — categorical columns available for slicing/filtering
# ---------------------------------------------------------------------------

DIMENSION_COLUMNS: OrderedDict[str, str] = OrderedDict(
    [
        ("year", "Year"),
        ("scn_adoption", "Adoption Scenario"),
        ("climate_zone", "Climate Zone"),
        ("dwelling_type", "Dwelling Type"),
        ("hvac_system", "Baseline HVAC System"),
        ("alt_hvac_system", "Alt HVAC System"),
        ("dhw_type", "Baseline DHW Type"),
        ("alt_dhw_type", "Alt DHW Type"),
        ("vehicle_1_type", "Vehicle Type"),
        ("vehicle_1_category", "Baseline Drivetrain"),
        ("alt_vehicle_1_category", "Alt Drivetrain"),
        ("has_home_charging", "Home Charging Access"),
    ]
)

# ---------------------------------------------------------------------------
# Metric registry — numeric columns available for visualization
# ---------------------------------------------------------------------------

METRIC_GROUPS: OrderedDict[str, OrderedDict[str, str]] = OrderedDict(
    [
        (
            "Energy Wallet Totals",
            OrderedDict(
                [
                    ("energy_wallet_base", "Total Cost (Baseline)"),
                    ("energy_wallet_alt", "Total Cost (Alternative)"),
                    ("energy_wallet_diff_absolute", "Cost Difference ($)"),
                    ("energy_wallet_diff_percent", "Cost Difference (%)"),
                ]
            ),
        ),
        (
            "Domain Subtotals",
            OrderedDict(
                [
                    ("energy_wallet_vehicle_base", "Vehicles (Baseline)"),
                    ("energy_wallet_vehicle_alt", "Vehicles (Alternative)"),
                    ("energy_wallet_home_base", "Home (Baseline)"),
                    ("energy_wallet_home_alt", "Home (Alternative)"),
                    ("energy_wallet_vehicle_diff_absolute", "Vehicle Cost Diff ($)"),
                    ("energy_wallet_home_diff_absolute", "Home Cost Diff ($)"),
                ]
            ),
        ),
        (
            "Category Subtotals",
            OrderedDict(
                [
                    ("vehicles_base_total_cost", "Vehicles (Baseline)"),
                    ("vehicles_alt_total_cost", "Vehicles (Alternative)"),
                    ("hvac_base_total_cost", "HVAC (Baseline)"),
                    ("hvac_alt_total_cost", "HVAC (Alternative)"),
                    ("dhw_base_total_cost", "DHW (Baseline)"),
                    ("dhw_alt_total_cost", "DHW (Alternative)"),
                    ("other_base_total_cost", "Other (Baseline)"),
                    ("other_alt_total_cost", "Other (Alternative)"),
                ]
            ),
        ),
        (
            "Utility Bills",
            OrderedDict(
                [
                    ("utility_bill_electricity_base", "Electricity (Baseline)"),
                    ("utility_bill_electricity_alt", "Electricity (Alt)"),
                    ("utility_bill_electricity_diff", "Electricity Diff ($)"),
                    ("utility_bill_natural_gas_base", "Natural Gas (Baseline)"),
                    ("utility_bill_natural_gas_alt", "Natural Gas (Alt)"),
                    ("utility_bill_natural_gas_diff", "Natural Gas Diff ($)"),
                    ("utility_bill_gasoline_base", "Gasoline (Baseline)"),
                    ("utility_bill_gasoline_alt", "Gasoline (Alt)"),
                    ("utility_bill_gasoline_diff", "Gasoline Diff ($)"),
                    ("utility_bill_oil_base", "Oil (Baseline)"),
                    ("utility_bill_oil_alt", "Oil (Alt)"),
                    ("utility_bill_propane_base", "Propane (Baseline)"),
                    ("utility_bill_propane_alt", "Propane (Alt)"),
                    ("utility_bill_wood_base", "Wood (Baseline)"),
                    ("utility_bill_wood_alt", "Wood (Alt)"),
                    (
                        "utility_bill_public_ev_charging_base",
                        "Public EV Charging (Baseline)",
                    ),
                    (
                        "utility_bill_public_ev_charging_alt",
                        "Public EV Charging (Alt)",
                    ),
                ]
            ),
        ),
    ]
)

# ---------------------------------------------------------------------------
# Color palettes
# ---------------------------------------------------------------------------

COLORS = {
    "baseline": "#4C78A8",
    "alternative": "#E45756",
    "savings": "#2CA02C",
    "cost_increase": "#D62728",
    "neutral": "#7F7F7F",
}

UTILITY_BILL_COLORS = OrderedDict(
    [
        ("electricity", "#F5C542"),
        ("natural_gas", "#4C78A8"),
        ("oil", "#8B6914"),
        ("propane", "#9467BD"),
        ("wood", "#2CA02C"),
        ("gasoline", "#D62728"),
        ("public_ev_charging", "#17BECF"),
    ]
)

UTILITY_BILL_LABELS = OrderedDict(
    [
        ("electricity", "Electricity"),
        ("natural_gas", "Natural Gas"),
        ("oil", "Oil"),
        ("propane", "Propane"),
        ("wood", "Wood"),
        ("gasoline", "Gasoline"),
        ("public_ev_charging", "Public EV Charging"),
    ]
)

# ---------------------------------------------------------------------------
# Plotly theme helper
# ---------------------------------------------------------------------------


def plotly_template(dark: bool = False) -> str:
    """Return the appropriate Plotly template name for current theme."""
    return "plotly_dark" if dark else "plotly"
