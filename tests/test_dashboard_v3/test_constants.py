from dashboard_v3.data.constants import (
    WEIGHT_COL, DIMENSION_COLUMNS, METRIC_GROUPS, COLORS,
    UTILITY_BILL_COLORS, UTILITY_BILL_LABELS, plotly_template,
)

def test_weight_col():
    assert WEIGHT_COL == "population_weight"

def test_dimension_columns_count():
    assert len(DIMENSION_COLUMNS) == 12

def test_metric_groups_has_four_groups():
    assert len(METRIC_GROUPS) == 4

def test_plotly_template():
    assert plotly_template(False) == "plotly"
    assert plotly_template(True) == "plotly_dark"

def test_colors_has_required_keys():
    for key in ("baseline", "alternative", "savings", "cost_increase"):
        assert key in COLORS
