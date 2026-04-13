"""Filter sidebar component for the Results page."""

from __future__ import annotations

from dash import dcc, html

from dashboard_v3.data.summary import available_dimensions


def build_filter_sidebar(df, exclude_dims: set[str] | None = None) -> html.Div:
    """Build the filter sidebar layout with dropdowns for each dimension.

    Returns a Div with dcc.Dropdown components. The actual filtering
    is handled by callbacks in the Results page.
    """
    exclude_dims = exclude_dims or set()
    dims = available_dimensions(df)
    filter_groups = []

    for col, label in dims.items():
        if col in exclude_dims:
            continue
        unique_vals = sorted(df[col].dropna().unique(), key=str)
        if len(unique_vals) <= 1:
            continue
        filter_groups.append(
            html.Div(
                [
                    html.Label(label, className="text-sm text-muted"),
                    dcc.Dropdown(
                        id={"type": "result-filter", "col": col},
                        options=[{"label": str(v), "value": v} for v in unique_vals],
                        value=unique_vals,
                        multi=True,
                        clearable=False,
                        style={"fontSize": "13px"},
                    ),
                ],
                className="filter-group",
            )
        )

    return html.Div(
        [
            html.H3("Filters"),
            *filter_groups,
        ],
        className="filter-sidebar",
    )
