"""Energy Wallet Dashboard v3 — read-only showcase explorer."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the project root is on sys.path so dashboard_v3.* imports work
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import dash
from dash import Dash, dcc, html, Input, Output, callback

app = Dash(
    __name__,
    use_pages=True,
    pages_folder="pages",
    suppress_callback_exceptions=True,
    title="Energy Wallet",
)

# ---------------------------------------------------------------------------
# Dark mode state — persisted in browser localStorage
# ---------------------------------------------------------------------------

dark_store = dcc.Store(id="dark-mode-store", storage_type="local", data=False)

# ---------------------------------------------------------------------------
# Navigation bar
# ---------------------------------------------------------------------------

NAV_ITEMS = [
    ("Home", "/"),
    ("Explore Inputs", "/inputs"),
    ("Explore Results", "/results"),
]


def nav_bar() -> html.Div:
    links = [
        dcc.Link(label, href=href, className="nav-link")
        for label, href in NAV_ITEMS
    ]
    return html.Div(
        [
            html.Div(
                [
                    html.Span("⚡", className="nav-logo"),
                    html.Span("Energy Wallet", className="nav-title"),
                ],
                className="nav-brand",
            ),
            html.Div(links, className="nav-links"),
            html.Button(
                "🌙",
                id="dark-mode-toggle",
                className="dark-mode-btn",
                n_clicks=0,
            ),
        ],
        className="nav-bar",
    )


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

app.layout = html.Div(
    [
        dark_store,
        html.Div(
            "This dashboard is a read-only explorer. To run the model, clone the repository and run locally.",
            className="beta-banner",
        ),
        nav_bar(),
        html.Div(dash.page_container, className="page-content"),
    ],
    id="app-container",
)

# ---------------------------------------------------------------------------
# Dark mode callbacks
# ---------------------------------------------------------------------------

app.clientside_callback(
    """
    function(n_clicks, current) {
        if (n_clicks === 0 && current !== undefined) return current;
        return !current;
    }
    """,
    Output("dark-mode-store", "data"),
    Input("dark-mode-toggle", "n_clicks"),
    dash.State("dark-mode-store", "data"),
)

app.clientside_callback(
    """
    function(dark) {
        const container = document.getElementById('app-container');
        if (dark) {
            container.classList.add('dark');
            document.body.classList.add('dark');
        } else {
            container.classList.remove('dark');
            document.body.classList.remove('dark');
        }
        return dark ? '☀️' : '🌙';
    }
    """,
    Output("dark-mode-toggle", "children"),
    Input("dark-mode-store", "data"),
)


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=False, port=8051)
