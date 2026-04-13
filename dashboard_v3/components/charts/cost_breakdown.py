"""Cost Breakdown chart — stacked bar by category, Baseline vs Alternative."""

from __future__ import annotations

import plotly.graph_objects as go

from dashboard_v3.data.constants import WEIGHT_COL, plotly_template
from dashboard_v3.data.summary import weighted_mean

# Category pairs: (base_col, alt_col, label, color)
CATEGORIES = [
    ("vehicles_base_total_cost", "vehicles_alt_total_cost", "Vehicles", "#D62728"),
    ("hvac_base_total_cost", "hvac_alt_total_cost", "HVAC", "#4C78A8"),
    ("dhw_base_total_cost", "dhw_alt_total_cost", "DHW", "#2CA02C"),
    ("other_base_total_cost", "other_alt_total_cost", "Other", "#7F7F7F"),
]


def cost_breakdown_chart(df, dark: bool = False) -> go.Figure:
    """Create a stacked bar chart: cost by category for Baseline vs Alternative."""
    base_labels = []
    alt_labels = []
    base_vals: dict[str, list[float]] = {}
    alt_vals: dict[str, list[float]] = {}

    for base_col, alt_col, label, color in CATEGORIES:
        if base_col not in df.columns or alt_col not in df.columns:
            continue
        base_vals[label] = [weighted_mean(df[base_col], df[WEIGHT_COL])]
        alt_vals[label] = [weighted_mean(df[alt_col], df[WEIGHT_COL])]

    fig = go.Figure()

    for base_col, alt_col, label, color in CATEGORIES:
        if label not in base_vals:
            continue
        # Baseline bar
        fig.add_trace(go.Bar(
            name=label,
            x=["Baseline"],
            y=base_vals[label],
            marker_color=color,
            legendgroup=label,
            hovertemplate=f"{label}: " + "$%{y:,.0f}<extra></extra>",
        ))

    for base_col, alt_col, label, color in CATEGORIES:
        if label not in alt_vals:
            continue
        # Alternative bar
        fig.add_trace(go.Bar(
            name=label,
            x=["Alternative"],
            y=alt_vals[label],
            marker_color=color,
            legendgroup=label,
            showlegend=False,
            hovertemplate=f"{label}: " + "$%{y:,.0f}<extra></extra>",
        ))

    fig.update_layout(
        barmode="stack",
        yaxis_title="$/year",
        yaxis_tickformat="$,.0f",
        template=plotly_template(dark),
        height=420,
        margin=dict(t=40, b=40, l=60, r=20),
        showlegend=True,
        legend=dict(
            orientation="h", x=0.5, xanchor="center", y=1.02, yanchor="bottom",
            font=dict(size=11),
        ),
    )

    return fig
