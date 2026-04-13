"""Overview chart — Baseline vs Alternative grouped bar by category."""

from __future__ import annotations

import plotly.graph_objects as go

from dashboard_v3.data.constants import COLORS, WEIGHT_COL, plotly_template
from dashboard_v3.data.summary import weighted_mean

# Category column pairs: (base_col, alt_col, label)
CATEGORIES = [
    ("vehicles_base_total_cost", "vehicles_alt_total_cost", "Vehicles"),
    ("hvac_base_total_cost", "hvac_alt_total_cost", "HVAC"),
    ("dhw_base_total_cost", "dhw_alt_total_cost", "DHW"),
    ("other_base_total_cost", "other_alt_total_cost", "Other"),
]


def overview_chart(df, dark: bool = False) -> go.Figure:
    """Create a grouped bar chart: Baseline vs Alternative by cost category."""
    labels = []
    base_vals = []
    alt_vals = []

    for base_col, alt_col, label in CATEGORIES:
        if base_col not in df.columns or alt_col not in df.columns:
            continue
        labels.append(label)
        base_vals.append(weighted_mean(df[base_col], df[WEIGHT_COL]))
        alt_vals.append(weighted_mean(df[alt_col], df[WEIGHT_COL]))

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Baseline",
        x=labels,
        y=base_vals,
        marker_color=COLORS["baseline"],
    ))
    fig.add_trace(go.Bar(
        name="Alternative",
        x=labels,
        y=alt_vals,
        marker_color=COLORS["alternative"],
    ))

    fig.update_layout(
        barmode="group",
        yaxis_title="$/year",
        yaxis_tickformat="$,.0f",
        template=plotly_template(dark),
        height=380,
        margin=dict(t=40, b=40, l=60, r=20),
        showlegend=True,
        legend=dict(
            orientation="h", x=0.5, xanchor="center", y=1.02, yanchor="bottom",
            font=dict(size=11),
        ),
    )

    return fig
