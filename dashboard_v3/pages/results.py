"""Results page — charts, metrics, and filters."""

from __future__ import annotations

import numpy as np
import pandas as pd

import dash
from dash import Input, Output, State, callback, dcc, html, no_update, ALL, MATCH
import plotly.graph_objects as go

from dashboard_v3.data.loader import OUTPUTS_ROOT, discover_scenarios, load_step5
from dashboard_v3.data.constants import COLORS, WEIGHT_COL, plotly_template
from dashboard_v3.data.summary import (
    apply_filters,
    available_dimensions,
    renormalize_weights,
    weighted_mean,
)
from dashboard_v3.components.metric_cards import metric_card, metric_row
from dashboard_v3.components.charts.overview import overview_chart

dash.register_page(__name__, path="/results", name="Explore Results", order=2)

# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

TAB_STYLE = {"padding": "8px 16px", "fontSize": "13px"}
TAB_SELECTED_STYLE = {**TAB_STYLE, "fontWeight": "600"}


def layout(**kwargs) -> html.Div:
    scenarios = discover_scenarios()
    default = scenarios[0]["name"] if scenarios else None

    return html.Div(
        [
            html.H2("Explore Results", className="mb-md"),
            # Top bar: data source + year
            html.Div(
                [
                    html.Div([
                        html.Label("Data Source", className="text-sm text-muted"),
                        dcc.Dropdown(
                            id="result-scenario-selector",
                            options=[{"label": s["name"], "value": s["name"]} for s in scenarios],
                            value=default,
                            clearable=False,
                            style={"width": "300px"},
                        ),
                    ]),
                    html.Div([
                        html.Label("Year", className="text-sm text-muted"),
                        dcc.Dropdown(
                            id="result-year-selector",
                            options=[],
                            value=None,
                            clearable=False,
                            style={"width": "140px"},
                        ),
                    ]),
                ],
                className="flex-row gap-md mb-md",
                style={"alignItems": "flex-end"},
            ),
            # Filters strip (horizontal, above charts)
            html.Div(id="result-filter-strip", className="mb-md"),
            # Tabs + content
            dcc.Tabs(
                id="result-tabs",
                value="overview",
                children=[
                    dcc.Tab(label="Overview", value="overview", style=TAB_STYLE, selected_style=TAB_SELECTED_STYLE),
                    dcc.Tab(label="Cost Breakdown", value="cost_breakdown", style=TAB_STYLE, selected_style=TAB_SELECTED_STYLE),
                    dcc.Tab(label="Waterfall", value="waterfall", style=TAB_STYLE, selected_style=TAB_SELECTED_STYLE),
                    dcc.Tab(label="Distribution", value="distribution", style=TAB_STYLE, selected_style=TAB_SELECTED_STYLE),
                ],
            ),
            html.Div(id="result-tab-content", className="mt-md"),
            # Hidden store
            dcc.Store(id="filter-state-store", storage_type="session"),
        ]
    )


# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------


@callback(
    Output("result-filter-strip", "children"),
    Output("filter-state-store", "data"),
    Output("result-year-selector", "options"),
    Output("result-year-selector", "value"),
    Input("result-scenario-selector", "value"),
)
def load_scenario_and_build_filters(scenario_name: str | None):
    """Load scenario data and build horizontal filter strip + year selector."""
    if not scenario_name:
        return html.Div(), {}, [], None

    step5_path = OUTPUTS_ROOT / scenario_name / "step5_utility_bills.csv"
    if not step5_path.exists():
        return (
            html.Div("No step5 output found.", className="empty-state"),
            {}, [], None,
        )

    df = load_step5(step5_path)
    dims = available_dimensions(df)

    # Year options
    if "year" in df.columns:
        years = sorted(df["year"].dropna().unique())
        year_options = [{"label": str(int(y)), "value": y} for y in years]
        year_default = years[0]
    else:
        year_options = [{"label": "All", "value": "all"}]
        year_default = "all"

    # Build horizontal filter groups
    filter_items = []
    initial_filters = {}
    for col, label in dims.items():
        unique_vals = sorted(df[col].dropna().unique(), key=str)
        if len(unique_vals) <= 1:
            continue
        initial_filters[col] = unique_vals
        filter_items.append(
            html.Div(
                [
                    html.Label(label, className="text-sm text-muted"),
                    dcc.Dropdown(
                        id={"type": "result-filter", "col": col},
                        options=[{"label": str(v), "value": v} for v in unique_vals],
                        value=unique_vals,
                        multi=True,
                        clearable=False,
                        style={"fontSize": "12px", "minWidth": "150px"},
                    ),
                ],
                style={"flex": "1", "minWidth": "150px", "maxWidth": "250px"},
            )
        )

    if not filter_items:
        return html.Div(), initial_filters, year_options, year_default

    strip = html.Div(
        [
            html.Details(
                [
                    html.Summary(
                        "Filters",
                        style={"fontSize": "13px", "fontWeight": "600", "cursor": "pointer", "marginBottom": "8px"},
                    ),
                    html.Div(
                        filter_items,
                        style={
                            "display": "flex",
                            "flexWrap": "wrap",
                            "gap": "12px",
                            "padding": "8px 0",
                        },
                    ),
                ],
                open=False,
            ),
        ],
        className="card",
        style={"padding": "12px 16px"},
    )

    return strip, initial_filters, year_options, year_default


@callback(
    Output("result-tab-content", "children"),
    Input("result-tabs", "value"),
    Input("result-year-selector", "value"),
    Input({"type": "result-filter", "col": ALL}, "value"),
    State("result-scenario-selector", "value"),
    State("dark-mode-store", "data"),
)
def update_tab(tab: str, selected_year, filter_values: list, scenario_name: str | None, dark: bool):
    """Update tab content based on selected tab, year, and filter state."""
    if not scenario_name:
        return html.Div("Select a scenario.", className="empty-state")

    step5_path = OUTPUTS_ROOT / scenario_name / "step5_utility_bills.csv"
    if not step5_path.exists():
        return html.Div("No results found.", className="empty-state")

    df = load_step5(step5_path)

    # Filter by selected year
    if selected_year and selected_year != "all" and "year" in df.columns:
        df = df[df["year"] == selected_year]

    # Apply filters from pattern-matching callbacks
    triggered = dash.callback_context.inputs_list
    if triggered and len(triggered) > 2:
        filter_inputs = triggered[2]  # The ALL pattern inputs
        filters = {}
        for f_input in filter_inputs:
            col = f_input["id"]["col"]
            vals = f_input.get("value", [])
            if vals:
                filters[col] = vals
        df = apply_filters(df, filters)

    # Renormalize weights after filtering
    if WEIGHT_COL in df.columns:
        df = renormalize_weights(df)

    if len(df) == 0:
        return html.Div(
            [
                html.H3("No data matches current filters"),
                html.P("Try adjusting the filter selections."),
            ],
            className="empty-state",
        )

    if tab == "overview":
        return _render_overview(df, dark)
    elif tab == "cost_breakdown":
        return _render_cost_breakdown(df, dark)
    elif tab == "waterfall":
        return _render_waterfall(df, dark)
    elif tab == "distribution":
        return _render_distribution(df, dark)
    return html.Div("Unknown tab.", className="empty-state")


# ---------------------------------------------------------------------------
# Tab renderers
# ---------------------------------------------------------------------------


def _fmt_dollar(v: float) -> str:
    if v != v:  # NaN check
        return "N/A"
    return f"${v:,.0f}"


def _fmt_pct(v: float) -> str:
    if v != v:
        return "N/A"
    return f"{v:+.1f}%"


def _render_overview(df, dark: bool) -> html.Div:
    wm_base = weighted_mean(df["energy_wallet_base"], df[WEIGHT_COL])
    wm_alt = weighted_mean(df["energy_wallet_alt"], df[WEIGHT_COL])
    diff = wm_alt - wm_base
    pct = (diff / wm_base * 100) if wm_base != 0 else 0

    savings_label = "Savings" if diff < 0 else "Additional Cost"
    metrics = metric_row([
        {"label": "Baseline (Avg)", "value": _fmt_dollar(wm_base)},
        {"label": "Alternative (Avg)", "value": _fmt_dollar(wm_alt)},
        {"label": savings_label, "value": _fmt_dollar(abs(diff)), "class": "positive" if diff < 0 else "negative"},
        {"label": "Change", "value": _fmt_pct(pct), "class": "positive" if pct < 0 else "negative"},
    ])

    chart = dcc.Graph(
        figure=overview_chart(df, dark),
        config={"displayModeBar": False},
    )

    return html.Div([metrics, chart])


def _render_cost_breakdown(df, dark: bool) -> html.Div:
    from dashboard_v3.components.charts.cost_breakdown import cost_breakdown_chart
    return html.Div([
        dcc.Graph(figure=cost_breakdown_chart(df, dark), config={"displayModeBar": False}),
    ])


def _render_waterfall(df, dark: bool) -> html.Div:
    from dashboard_v3.components.charts.waterfall import waterfall_chart
    return html.Div([
        dcc.Graph(figure=waterfall_chart(df, dark), config={"displayModeBar": False}),
    ])


def _render_distribution(df, dark: bool) -> html.Div:
    from dashboard_v3.components.charts.distribution import distribution_chart
    return html.Div([
        dcc.Graph(figure=distribution_chart(df, dark), config={"displayModeBar": False}),
    ])
