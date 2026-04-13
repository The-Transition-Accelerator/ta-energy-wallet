"""Inputs page — read-only file browser with .meta.yaml metadata display."""

from __future__ import annotations

import dash
import dash_ag_grid as dag
import pandas as pd
from dash import Input, Output, State, callback, dcc, html, no_update

from dashboard_v3.data.loader import CATEGORY_LABELS, INPUTS_ROOT, discover_csv_files, discover_input_sets, load_csv
from dashboard_v3.data.input_browser import load_meta_yaml, file_info_panel

dash.register_page(__name__, path="/inputs", name="Explore Inputs", order=1)

# ---------------------------------------------------------------------------
# Category-to-tab mapping
# ---------------------------------------------------------------------------

TAB_CATEGORIES = [
    ("archetypes", "Archetypes"),
    ("alternative_configurations", "Alt Configurations"),
    ("input_parameters", "Input Parameters"),
]

# ---------------------------------------------------------------------------
# AG Grid column type detection
# ---------------------------------------------------------------------------


def _build_column_defs(df: pd.DataFrame, col_tooltips: dict[str, str] | None = None) -> list[dict]:
    """Build AG Grid column definitions with type-appropriate formatting (read-only)."""
    if col_tooltips is None:
        col_tooltips = {}

    col_defs = []
    for col in df.columns:
        col_def: dict = {
            "field": col,
            "headerName": col,
            "headerTooltip": col_tooltips.get(col, ""),
            "sortable": True,
            "filter": True,
            "resizable": True,
            "editable": False,
        }
        col_lower = col.lower()

        if col_lower == "population_share":
            col_def["type"] = "numericColumn"
            col_def["valueFormatter"] = {"function": "d3.format('.1%')(params.value)"}
        elif "share" in col_lower:
            col_def["type"] = "numericColumn"
            col_def["valueFormatter"] = {"function": "d3.format('.4f')(params.value)"}
        elif any(k in col_lower for k in ("cost", "price", "charge")):
            col_def["type"] = "numericColumn"
            col_def["valueFormatter"] = {"function": "d3.format(',.2f')(params.value)"}
        elif any(k in col_lower for k in ("life", "year")):
            col_def["type"] = "numericColumn"
            col_def["valueFormatter"] = {"function": "d3.format('.0f')(params.value)"}
        elif any(k in col_lower for k in ("efficiency", "proportion", "factor")):
            col_def["type"] = "numericColumn"
            col_def["valueFormatter"] = {"function": "d3.format('.4f')(params.value)"}
        elif any(k in col_lower for k in ("load", "annual", "vkt", "km")):
            col_def["type"] = "numericColumn"
            col_def["valueFormatter"] = {"function": "d3.format(',.2f')(params.value)"}

        col_defs.append(col_def)
    return col_defs


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------


def layout(**kwargs) -> html.Div:
    input_sets = discover_input_sets()
    default_set = "ontario" if "ontario" in input_sets else (input_sets[0] if input_sets else "")

    return html.Div(
        [
            html.H2("Explore Inputs", className="mb-sm"),
            html.P(
                "Browse input files across archetypes, alternative configurations, and parameters.",
                className="text-sm text-muted",
                style={"marginBottom": "16px"},
            ),
            # Input set selector
            html.Div(
                [
                    html.Label("Input Set", className="text-sm text-muted"),
                    dcc.Dropdown(
                        id="v3-input-set-selector",
                        options=[{"label": s, "value": s} for s in input_sets],
                        value=default_set,
                        clearable=False,
                        style={"width": "260px"},
                    ),
                ],
                className="mb-sm",
            ),
            # Category tabs
            dcc.Tabs(
                id="v3-file-category-tabs",
                value="archetypes",
                children=[
                    dcc.Tab(label=label, value=cat_id, className="tab", selected_className="tab--selected")
                    for cat_id, label in TAB_CATEGORIES
                ],
                className="custom-tabs",
            ),
            # File list (RadioItems)
            html.Div(id="v3-file-list-container", className="mb-sm"),
            # File info header (populated when a file is selected)
            html.Div(id="v3-file-info-header"),
            # Toolbar
            html.Div(
                [
                    html.Button(
                        "Export CSV",
                        id="v3-export-csv-btn",
                        className="btn",
                        n_clicks=0,
                    ),
                    dcc.Download(id="v3-csv-download"),
                ],
                className="toolbar",
            ),
            # AG Grid
            html.Div(id="v3-grid-container"),
            # Hidden stores
            dcc.Store(id="v3-current-file-path"),
        ]
    )


# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------


@callback(
    Output("v3-file-list-container", "children"),
    Input("v3-file-category-tabs", "value"),
    State("v3-input-set-selector", "value"),
)
def update_file_list_for_tab(category: str, input_set: str | None):
    """Render RadioItems for the selected tab's category."""
    if not input_set or not category:
        return html.Div("Select an input set.", className="text-muted text-sm")

    files = discover_csv_files(input_set, category)
    if not files:
        return html.Div(
            "No files in this category.",
            className="text-muted text-sm",
            style={"padding": "16px", "textAlign": "center"},
        )

    options = [
        {"label": f.replace(".csv", "").replace("_", " ").title(), "value": f"{category}/{f}"}
        for f in files
    ]
    return dcc.RadioItems(
        id="v3-file-radio-items",
        options=options,
        value=options[0]["value"],
        className="file-list",
        labelStyle={"display": "block"},
    )


@callback(
    Output("v3-file-info-header", "children"),
    Output("v3-grid-container", "children"),
    Output("v3-current-file-path", "data"),
    Input("v3-file-radio-items", "value"),
    State("v3-input-set-selector", "value"),
    State("dark-mode-store", "data"),
)
def load_file(file_value: str | None, input_set: str | None, dark: bool):
    """Load selected CSV, display .meta.yaml metadata header and AG Grid."""
    if not file_value or not input_set:
        return (
            None,
            html.Div("Select a file to view.", className="empty-state"),
            None,
        )

    cat, filename = file_value.split("/", 1)
    file_path = INPUTS_ROOT / input_set / cat / filename
    if not file_path.exists():
        return (
            None,
            html.Div(f"File not found: {file_path}", className="empty-state"),
            None,
        )

    df = load_csv(file_path)
    table_type = CATEGORY_LABELS.get(cat, cat)

    # Load .meta.yaml if present
    meta = load_meta_yaml(file_path)
    col_tooltips: dict[str, str] = {}

    if meta:
        # Build a synthetic file_entry dict for file_info_panel
        entry = {
            "filename": filename,
            "path": file_path,
            "category": cat,
            "meta": meta,
            "row_count": len(df),
            "col_count": len(df.columns),
        }
        info = file_info_panel(entry)

        # Column tooltips from .meta.yaml columns section
        for col_name, col_meta in (info.get("columns") or {}).items():
            if isinstance(col_meta, dict):
                tip = col_meta.get("description", "")
            else:
                tip = str(col_meta)
            if tip:
                col_tooltips[col_name] = tip

        # Build rich header
        header_children = [html.H3(info["title"], style={"marginBottom": "8px"})]
        if info.get("question"):
            header_children.append(
                html.P(info["question"], style={"fontStyle": "italic", "marginBottom": "8px"}, className="text-sm text-muted")
            )
        if info.get("description"):
            header_children.append(html.P(info["description"], className="text-sm", style={"marginBottom": "8px"}))
        source_parts = []
        if info.get("source_name"):
            source_parts.append(info["source_name"])
        if info.get("source_detail"):
            source_parts.append(info["source_detail"])
        if source_parts:
            header_children.append(
                html.P("Source: " + " — ".join(source_parts), className="text-sm text-muted", style={"marginBottom": "6px"})
            )
        header_children.append(
            html.P(
                f"{table_type}  |  {len(df)} rows \u00d7 {len(df.columns)} columns",
                className="text-sm text-muted",
            )
        )
    else:
        # Minimal header (no .meta.yaml)
        header_children = [
            html.Div(
                [
                    html.Span(filename, style={"fontWeight": "700", "fontSize": "15px"}),
                    html.Span(f"  {table_type}", className="text-muted text-sm"),
                ],
            ),
            html.P(
                f"{len(df)} rows \u00d7 {len(df.columns)} columns",
                className="text-sm text-muted",
            ),
        ]

    header = html.Div(header_children, className="mb-sm")

    # AG Grid (read-only)
    theme = "ag-theme-alpine-dark" if dark else "ag-theme-alpine"
    use_auto_height = len(df) < 100
    grid = dag.AgGrid(
        id="v3-input-grid",
        rowData=df.to_dict("records"),
        columnDefs=_build_column_defs(df, col_tooltips),
        className=theme,
        defaultColDef={
            "flex": 1,
            "minWidth": 100,
            "editable": False,
        },
        dashGridOptions={
            "animateRows": False,
            "pagination": False,
            "domLayout": "autoHeight" if use_auto_height else "normal",
        },
        style={"height": "500px"} if not use_auto_height else {},
    )

    return header, grid, str(file_path)


@callback(
    Output("v3-csv-download", "data"),
    Input("v3-export-csv-btn", "n_clicks"),
    State("v3-input-grid", "rowData"),
    State("v3-file-radio-items", "value"),
    prevent_initial_call=True,
)
def export_csv(n_clicks: int, row_data: list[dict] | None, file_value: str | None):
    """Download the currently displayed grid data as CSV."""
    if not n_clicks or not row_data or not file_value:
        return no_update
    _, filename = file_value.split("/", 1)
    df = pd.DataFrame(row_data)
    return dcc.send_data_frame(df.to_csv, filename, index=False)
