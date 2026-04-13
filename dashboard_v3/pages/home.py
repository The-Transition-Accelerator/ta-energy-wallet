"""Home page — landing page with hero, problem statement, and pipeline overview."""

import dash
from dash import dcc, html

dash.register_page(__name__, path="/", name="Home", order=0)

# ---------------------------------------------------------------------------
# Pipeline step data
# ---------------------------------------------------------------------------

PIPELINE_CARDS = [
    {
        "steps": "Steps 1\u20133",
        "title": "Define Model Inputs",
        "desc": (
            "Define archetype granularity, alternative technology configurations "
            "to compare against, and input parameters (energy costs, technology "
            "performance, etc.)."
        ),
    },
    {
        "steps": "Step 4",
        "title": "Calculate Energy Costs",
        "desc": (
            "Compute annualized costs comparing baseline vs alternative "
            "configurations for vehicles, heating/cooling, hot water, and "
            "other household energy uses."
        ),
    },
    {
        "steps": "Step 5",
        "title": "Analyze Energy Bills",
        "desc": (
            "Re-aggregate costs by where households actually pay: electricity "
            "bill, natural gas bill, gas station, EV chargers, and more."
        ),
    },
]


# ---------------------------------------------------------------------------
# Component helpers
# ---------------------------------------------------------------------------


def _pipeline_card(card: dict) -> html.Div:
    return html.Div(
        [
            html.Div(
                card["steps"],
                className="pipeline-step-badge mb-sm",
            ),
            html.H3(
                card["title"],
                style={"fontSize": "16px", "fontWeight": "600", "marginBottom": "6px"},
            ),
            html.P(card["desc"], className="text-sm"),
        ],
        className="card flex-1",
    )


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

layout = html.Div(
    [
        # ------------------------------------------------------------------
        # 1. Hero
        # ------------------------------------------------------------------
        html.Div(
            [
                html.H1(
                    "Energy Wallet Model Explorer",
                    style={"fontSize": "36px", "marginBottom": "12px"},
                ),
                html.P(
                    "Explore inputs and outputs of a flexible Python-based model for "
                    "analyzing household energy affordability in the context of the "
                    "electro-tech revolution.",
                    style={
                        "fontSize": "16px",
                        "maxWidth": "720px",
                        "lineHeight": "1.7",
                    },
                    className="text-muted",
                ),
                html.P(
                    "Built by The Transition Accelerator\u2019s Insights & Analytics team.",
                    className="text-muted text-sm mt-md",
                ),
                html.Div(
                    [
                        dcc.Link(
                            "Explore Results \u2192",
                            href="/results",
                            className="btn-primary",
                            style={
                                "display": "inline-block",
                                "padding": "10px 20px",
                                "background": "#4C78A8",
                                "color": "#fff",
                                "borderRadius": "6px",
                                "textDecoration": "none",
                                "fontWeight": "600",
                                "fontSize": "14px",
                            },
                        ),
                        dcc.Link(
                            "Browse Inputs \u2192",
                            href="/inputs",
                            style={
                                "display": "inline-block",
                                "padding": "10px 20px",
                                "background": "transparent",
                                "color": "#4C78A8",
                                "border": "1px solid #4C78A8",
                                "borderRadius": "6px",
                                "textDecoration": "none",
                                "fontWeight": "600",
                                "fontSize": "14px",
                            },
                        ),
                    ],
                    className="flex-row gap-md mt-md",
                ),
            ],
            className="hero-section mb-lg",
        ),
        # ------------------------------------------------------------------
        # 2. Problem Statement
        # ------------------------------------------------------------------
        html.Div(
            [
                html.H2(
                    "Energy Affordability in the Age of Electrification",
                    style={"fontSize": "20px", "marginBottom": "12px"},
                ),
                html.P(
                    "Growing electricity demand, massive grid investments, and the "
                    "emergence of capable new technologies like electric vehicles and "
                    "cold-climate heat pumps are making energy affordability far more "
                    "complicated than tracking rate trajectories. Understanding "
                    "household energy costs now requires considering energy rates, "
                    "technology costs, and technology capabilities together.",
                    className="text-sm",
                    style={"lineHeight": "1.7", "marginBottom": "10px", "maxWidth": "800px"},
                ),
                html.P(
                    "The Energy Wallet model quantifies these trade-offs for thousands of "
                    "household archetypes, producing population-weighted cost comparisons "
                    "that show who saves, who pays more, and why.",
                    className="text-sm",
                    style={"lineHeight": "1.7", "maxWidth": "800px"},
                ),
            ],
            className="mb-lg",
        ),
        # ------------------------------------------------------------------
        # 3. Pipeline Overview
        # ------------------------------------------------------------------
        html.Div(
            [
                html.H2(
                    "Model Pipeline",
                    style={"fontSize": "20px", "marginBottom": "12px"},
                ),
                html.Div(
                    [_pipeline_card(c) for c in PIPELINE_CARDS],
                    className="flex-row gap-md",
                ),
            ],
            className="mb-lg",
        ),
    ]
)
