"""Time Series chart — energy wallet evolution across years."""

from __future__ import annotations

import plotly.graph_objects as go

from dashboard_v3.data.constants import COLORS, WEIGHT_COL, plotly_template
from dashboard_v3.data.summary import weighted_mean_by_group


def time_series_chart(df, dark: bool = False) -> go.Figure:
    """Create a line/bar chart showing energy wallet cost over years.

    Shows population-weighted mean Baseline and Alternative totals per year.
    Falls back to a single-point display if only one year is present.
    """
    if "year" not in df.columns:
        fig = go.Figure()
        fig.add_annotation(text="No year column in data", showarrow=False)
        return fig

    base_col = "energy_wallet_base"
    alt_col = "energy_wallet_alt"

    if base_col not in df.columns or alt_col not in df.columns:
        fig = go.Figure()
        fig.add_annotation(text="Missing energy_wallet columns", showarrow=False)
        return fig

    # Aggregate by year
    base_by_year = weighted_mean_by_group(df, base_col, ["year"])
    alt_by_year = weighted_mean_by_group(df, alt_col, ["year"])

    years_base = base_by_year["year"].tolist()
    years_alt = alt_by_year["year"].tolist()

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        name="Baseline",
        x=years_base,
        y=base_by_year[base_col].tolist(),
        mode="lines+markers",
        line=dict(color=COLORS["baseline"], width=2),
        marker=dict(size=8),
        hovertemplate="Baseline: $%{y:,.0f}/yr<extra></extra>",
    ))

    fig.add_trace(go.Scatter(
        name="Alternative",
        x=years_alt,
        y=alt_by_year[alt_col].tolist(),
        mode="lines+markers",
        line=dict(color=COLORS["alternative"], width=2),
        marker=dict(size=8),
        hovertemplate="Alternative: $%{y:,.0f}/yr<extra></extra>",
    ))

    fig.update_layout(
        title="Energy Wallet Over Time",
        xaxis_title="Year",
        yaxis_title="$/year",
        yaxis_tickformat="$,.0f",
        template=plotly_template(dark),
        height=400,
        margin=dict(t=40, b=40),
        legend=dict(orientation="h", y=1.1),
    )

    return fig
