"""Waterfall chart — component-level cost difference decomposition."""

from __future__ import annotations

import plotly.graph_objects as go

from dashboard_v3.data.constants import COLORS, WEIGHT_COL, plotly_template
from dashboard_v3.data.summary import weighted_mean


def _wm(df, col: str) -> float:
    """Weighted mean, returns 0.0 if column missing."""
    if col not in df.columns or df.empty:
        return 0.0
    return weighted_mean(df[col], df[WEIGHT_COL])


# (label, col_template using {s} for suffix, special handler key)
DETAILED_COMPONENTS = [
    ("Vehicle Capital", None, "vehicle_capital"),
    ("Vehicle Fuel", None, "vehicle_fuel"),
    ("Vehicle Maint.", None, "vehicle_maint"),
    ("HVAC Capital", "hvac_{s}_annual_capital", None),
    ("HVAC Fuel", None, "hvac_fuel"),
    ("HVAC Maint.", "hvac_{s}_annual_maintenance", None),
    ("DHW Capital", "dhw_{s}_annual_capital", None),
    ("DHW Fuel", "dhw_{s}_fuel_cost", None),
    ("DHW Maint.", "dhw_{s}_annual_maintenance", None),
    ("Other Elec.", "other_{s}_electricity_cost", None),
    ("Other NG", "other_{s}_natural_gas_cost", None),
    ("Fixed Charges", None, "fixed_charges"),
    ("Panel Upgrade", "other_{s}_panel_annual_capital", None),
]


def _component_value(df, suffix: str, col_template: str | None, special: str | None) -> float:
    """Compute the weighted-mean value of one waterfall component."""
    if special == "vehicle_capital":
        return sum(_wm(df, f"vehicle_{slot}_{suffix}_annual_capital") for slot in (1, 2))
    elif special == "vehicle_fuel":
        return sum(_wm(df, f"vehicle_{slot}_{suffix}_fuel_cost") for slot in (1, 2))
    elif special == "vehicle_maint":
        return sum(_wm(df, f"vehicle_{slot}_{suffix}_annual_maintenance") for slot in (1, 2))
    elif special == "hvac_fuel":
        return _wm(df, f"hvac_{suffix}_heating_cost") + _wm(df, f"hvac_{suffix}_cooling_cost")
    elif special == "fixed_charges":
        return (
            _wm(df, f"other_{suffix}_electricity_fixed_charge")
            + _wm(df, f"other_{suffix}_natural_gas_fixed_charge")
        )
    else:
        return _wm(df, col_template.format(s=suffix))


def waterfall_chart(df, dark: bool = False) -> go.Figure:
    """Create a waterfall chart showing component-level Alt - Baseline differences."""
    labels = []
    values = []

    for label, col_template, special in DETAILED_COMPONENTS:
        base_val = _component_value(df, "base", col_template, special)
        alt_val = _component_value(df, "alt", col_template, special)
        diff = alt_val - base_val
        labels.append(label)
        values.append(diff)

    net = sum(values)
    measures = ["relative"] * len(values) + ["total"]
    values.append(net)
    labels.append("Net Difference")

    fig = go.Figure(
        go.Waterfall(
            orientation="v",
            measure=measures,
            x=labels,
            y=values,
            text=[f"${v:+,.0f}" for v in values],
            textposition="outside",
            connector=dict(line=dict(color="rgba(63, 63, 63, 0.3)")),
            increasing=dict(marker=dict(color=COLORS["cost_increase"])),
            decreasing=dict(marker=dict(color=COLORS["savings"])),
            totals=dict(marker=dict(color=COLORS["baseline"])),
        )
    )

    fig.update_layout(
        yaxis_title="Cost Difference ($/year)",
        yaxis_tickformat="$,.0f",
        template=plotly_template(dark),
        height=450,
        showlegend=False,
        margin=dict(t=30, b=80, l=60),
    )

    return fig
