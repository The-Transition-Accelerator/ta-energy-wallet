"""Smoke tests — verify all dashboard_v3 modules import cleanly."""


def test_app_imports():
    import dashboard_v3.app  # noqa: F401


def test_all_pages_import():
    # Pages call dash.register_page() at module level, which requires a Dash
    # app to be instantiated first.  Import the app module to satisfy that
    # requirement before importing each page.
    import dashboard_v3.app  # noqa: F401 — ensures Dash app exists
    import dashboard_v3.pages.home  # noqa: F401
    import dashboard_v3.pages.inputs  # noqa: F401
    import dashboard_v3.pages.results  # noqa: F401


def test_data_modules():
    from dashboard_v3.data.constants import WEIGHT_COL, DIMENSION_COLUMNS
    from dashboard_v3.data.summary import weighted_mean, renormalize_weights
    from dashboard_v3.data.loader import discover_input_sets, discover_scenarios
    from dashboard_v3.data.input_browser import build_file_tree, load_meta_yaml
    assert WEIGHT_COL == "population_weight"


def test_chart_modules():
    from dashboard_v3.components.charts.overview import overview_chart
    from dashboard_v3.components.charts.cost_breakdown import cost_breakdown_chart
    from dashboard_v3.components.charts.waterfall import waterfall_chart
    from dashboard_v3.components.charts.distribution import distribution_chart
    from dashboard_v3.components.charts.time_series import time_series_chart
    from dashboard_v3.components.charts.comparator import compute_comparison


def test_component_modules():
    from dashboard_v3.components.metric_cards import metric_card, metric_row
    from dashboard_v3.components.filter_sidebar import build_filter_sidebar
