"""Distribution chart — winners/losers histogram of per-household cost differences."""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go
from dash import dcc, html

from dashboard_v3.data.constants import COLORS, WEIGHT_COL, plotly_template
from dashboard_v3.data.summary import weighted_mean


def distribution_chart(df, dark: bool = False, n_bins: int = 30) -> go.Figure:
    """Create a population-weighted histogram of Alt - Baseline cost differences.

    Uses absolute differences ($/yr). Green bars = savings, red bars = cost increase.
    Requires energy_wallet_base, energy_wallet_alt, and population_weight columns.
    """
    base_col = "energy_wallet_base"
    alt_col = "energy_wallet_alt"

    if base_col not in df.columns or alt_col not in df.columns:
        fig = go.Figure()
        fig.add_annotation(text="Missing energy_wallet columns", showarrow=False)
        return fig

    diff = (df[alt_col] - df[base_col]).values
    weights = df[WEIGHT_COL].values if WEIGHT_COL in df.columns else np.ones(len(df))

    # Normalize weights
    w_total = weights.sum()
    if w_total > 0:
        weights = weights / w_total

    valid = ~np.isnan(diff) & ~np.isnan(weights)
    diff = diff[valid]
    weights = weights[valid]

    if len(diff) == 0:
        fig = go.Figure()
        fig.add_annotation(text="No valid data for distribution", showarrow=False)
        return fig

    v_min, v_max = np.nanmin(diff), np.nanmax(diff)
    buf = (v_max - v_min) * 0.02 if v_max != v_min else 1.0
    bin_edges = np.linspace(v_min - buf, v_max + buf, n_bins + 1)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

    bin_indices = np.clip(np.digitize(diff, bin_edges) - 1, 0, n_bins - 1)

    bin_weights = np.zeros(n_bins)
    for i in range(len(diff)):
        bin_weights[bin_indices[i]] += weights[i]

    bar_colors = [
        COLORS["savings"] if c < 0 else COLORS["cost_increase"]
        for c in bin_centers
    ]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=bin_centers,
            y=bin_weights,
            width=(bin_edges[1] - bin_edges[0]) * 0.9,
            marker_color=bar_colors,
            hovertemplate="Diff: $%{x:,.0f}/yr<br>Pop Share: %{y:.4f}<extra></extra>",
        )
    )
    fig.add_vline(
        x=0,
        line_dash="dash",
        line_color="gray" if dark else "black",
        line_width=2,
        annotation_text="Break-even",
        annotation_position="top",
    )

    # Impact summary metrics
    pct_save = weights[diff < 0].sum() * 100 if np.any(diff < 0) else 0.0
    pct_cost = weights[diff > 0].sum() * 100 if np.any(diff > 0) else 0.0

    fig.update_layout(
        title=f"{pct_save:.0f}% save, {pct_cost:.0f}% pay more",
        title_font_size=13,
        xaxis_title="Cost Difference ($/year)",
        xaxis_tickformat="$,.0f",
        yaxis_title="Population Share",
        template=plotly_template(dark),
        height=400,
        showlegend=False,
        margin=dict(t=40, b=40, l=60),
    )

    return fig
