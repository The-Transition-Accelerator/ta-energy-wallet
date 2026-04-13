"""Comparator chart components — A/B cohort comparison with waterfall + distribution."""

from __future__ import annotations

import numpy as np
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

SUMMARY_COMPONENTS = [
    ("Vehicles", "vehicles_{s}_total_cost", None),
    ("HVAC", "hvac_{s}_total_cost", None),
    ("DHW", "dhw_{s}_total_cost", None),
    ("Other", "other_{s}_total_cost", None),
]


def _component_value(df, suffix: str, col_template: str | None, special: str | None) -> float:
    """Compute the weighted-mean value of one component for a given wallet suffix."""
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


def compute_comparison(
    a_subset, b_subset, a_suffix: str, b_suffix: str, detailed: bool = True,
) -> list[dict]:
    """Compute component-level comparison between two cohorts.

    Returns list of dicts with keys: Component, A, B, diff_abs, diff_pct.
    """
    components = DETAILED_COMPONENTS if detailed else SUMMARY_COMPONENTS
    records = []
    for label, col_template, special in components:
        a_val = _component_value(a_subset, a_suffix, col_template, special)
        b_val = _component_value(b_subset, b_suffix, col_template, special)
        diff_abs = b_val - a_val
        diff_pct = (diff_abs / a_val * 100) if a_val != 0 else float("nan")
        records.append({
            "Component": label,
            "A": a_val,
            "B": b_val,
            "diff_abs": diff_abs,
            "diff_pct": diff_pct,
        })
    return records


def comparator_waterfall(records: list[dict], dark: bool = False) -> go.Figure:
    """Create a waterfall chart from comparison records."""
    labels = [r["Component"] for r in records]
    values = [r["diff_abs"] for r in records]

    net = sum(values)
    measures = ["relative"] * len(values) + ["total"]
    values_plot = values + [net]
    labels_plot = labels + ["Net Difference"]

    fig = go.Figure(
        go.Waterfall(
            orientation="v",
            measure=measures,
            x=labels_plot,
            y=values_plot,
            text=[f"${v:+,.0f}" for v in values_plot],
            textposition="outside",
            connector=dict(line=dict(color="rgba(63, 63, 63, 0.3)")),
            increasing=dict(marker=dict(color=COLORS["cost_increase"])),
            decreasing=dict(marker=dict(color=COLORS["savings"])),
            totals=dict(marker=dict(color=COLORS["baseline"])),
        )
    )

    fig.update_layout(
        title="Component Difference Waterfall (B - A)",
        yaxis_title="Cost Difference ($/year)",
        yaxis_tickformat="$,.0f",
        template=plotly_template(dark),
        height=500,
        showlegend=False,
        margin=dict(t=40, b=80),
    )

    return fig


def comparator_distribution(
    a_subset, b_subset, a_suffix: str, b_suffix: str,
    dark: bool = False, n_bins: int = 30,
) -> go.Figure:
    """Create a population-weighted histogram of per-household differences.

    Requires __baseline_row_id for household matching.
    """
    a_col = f"energy_wallet_{a_suffix}"
    b_col = f"energy_wallet_{b_suffix}"

    if "__baseline_row_id" not in a_subset.columns:
        fig = go.Figure()
        fig.add_annotation(
            text="__baseline_row_id column required for distribution",
            showarrow=False,
        )
        return fig

    # Match households
    a_merge = a_subset[["__baseline_row_id", a_col, WEIGHT_COL]].rename(
        columns={a_col: "_a_value"}
    )
    b_merge = b_subset[["__baseline_row_id", b_col]].rename(
        columns={b_col: "_b_value"}
    )
    matched = a_merge.merge(b_merge, on="__baseline_row_id", how="inner")

    if matched.empty:
        fig = go.Figure()
        fig.add_annotation(text="No matched households found", showarrow=False)
        return fig

    # Renormalize weights
    w_total = matched[WEIGHT_COL].sum()
    if w_total > 0:
        matched[WEIGHT_COL] = matched[WEIGHT_COL] / w_total

    diff = (matched["_b_value"] - matched["_a_value"]).values
    weights = matched[WEIGHT_COL].values

    v_min, v_max = np.nanmin(diff), np.nanmax(diff)
    buf = (v_max - v_min) * 0.02 if v_max != v_min else 1.0
    bin_edges = np.linspace(v_min - buf, v_max + buf, n_bins + 1)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

    bin_indices = np.clip(np.digitize(diff, bin_edges) - 1, 0, n_bins - 1)
    bin_weights = np.zeros(n_bins)
    for i in range(len(diff)):
        if not np.isnan(diff[i]):
            bin_weights[bin_indices[i]] += weights[i]

    bar_colors = [
        COLORS["savings"] if c < 0 else COLORS["cost_increase"]
        for c in bin_centers
    ]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=bin_centers,
        y=bin_weights,
        width=(bin_edges[1] - bin_edges[0]) * 0.9,
        marker_color=bar_colors,
        hovertemplate="Diff: $%{x:,.0f}/yr<br>Pop Share: %{y:.4f}<extra></extra>",
    ))
    fig.add_vline(
        x=0,
        line_dash="dash",
        line_color="gray" if dark else "black",
        line_width=2,
        annotation_text="Break-even",
        annotation_position="top",
    )

    pct_save = weights[diff < 0].sum() * 100 if np.any(diff < 0) else 0.0
    pct_cost = weights[diff > 0].sum() * 100 if np.any(diff > 0) else 0.0

    fig.update_layout(
        title=f"Distribution ({pct_save:.0f}% save, {pct_cost:.0f}% pay more)",
        xaxis_title="Cost Difference ($/year)",
        xaxis_tickformat="$,.0f",
        yaxis_title="Population Share",
        template=plotly_template(dark),
        height=450,
        showlegend=False,
        margin=dict(t=40, b=40),
    )

    return fig
