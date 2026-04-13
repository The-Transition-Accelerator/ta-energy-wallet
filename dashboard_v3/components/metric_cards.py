"""Metric card components for top-line statistics."""

from __future__ import annotations

from dash import html


def metric_card(label: str, value: str, css_class: str = "") -> html.Div:
    """Build a single metric card."""
    return html.Div(
        [
            html.Div(label, className="metric-label"),
            html.Div(value, className=f"metric-value {css_class}"),
        ],
        className="metric-card",
    )


def metric_row(metrics: list[dict]) -> html.Div:
    """Build a row of metric cards.

    Each dict: {"label": str, "value": str, "class": optional str}
    """
    cards = [
        metric_card(m["label"], m["value"], m.get("class", ""))
        for m in metrics
    ]
    return html.Div(
        cards,
        style={
            "display": "grid",
            "gridTemplateColumns": f"repeat({len(cards)}, 1fr)",
            "gap": "12px",
        },
        className="mb-md",
    )
