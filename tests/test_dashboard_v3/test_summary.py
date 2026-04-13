"""Tests for dashboard_v3.data.summary — weighted statistics and filters."""

import numpy as np
import pandas as pd
import pytest

from dashboard_v3.data.summary import (
    apply_filters,
    available_dimensions,
    detect_mandatory_groupby,
    renormalize_weights,
    weighted_mean,
    weighted_median,
    weighted_mean_by_group,
    weighted_percentile,
)


# ---------------------------------------------------------------------------
# weighted_mean
# ---------------------------------------------------------------------------


def test_weighted_mean_basic():
    vals = pd.Series([100.0, 200.0])
    wts = pd.Series([0.5, 0.5])
    assert weighted_mean(vals, wts) == pytest.approx(150.0)


def test_weighted_mean_unequal_weights():
    vals = pd.Series([100.0, 200.0])
    wts = pd.Series([0.75, 0.25])
    assert weighted_mean(vals, wts) == pytest.approx(125.0)


def test_weighted_mean_with_nan():
    vals = pd.Series([100.0, float("nan"), 300.0])
    wts = pd.Series([0.5, 0.3, 0.2])
    # NaN row excluded; result = (100*0.5 + 300*0.2) / (0.5+0.2)
    expected = (100 * 0.5 + 300 * 0.2) / 0.7
    assert weighted_mean(vals, wts) == pytest.approx(expected)


def test_weighted_mean_empty():
    vals = pd.Series([], dtype=float)
    wts = pd.Series([], dtype=float)
    assert np.isnan(weighted_mean(vals, wts))


def test_weighted_mean_zero_weights():
    vals = pd.Series([100.0, 200.0])
    wts = pd.Series([0.0, 0.0])
    assert np.isnan(weighted_mean(vals, wts))


# ---------------------------------------------------------------------------
# weighted_median / weighted_percentile
# ---------------------------------------------------------------------------


def test_weighted_median_basic():
    vals = pd.Series([1.0, 2.0, 3.0])
    wts = pd.Series([1.0, 1.0, 1.0])
    result = weighted_median(vals, wts)
    assert result == pytest.approx(2.0, abs=0.5)


def test_weighted_percentile_extremes():
    vals = pd.Series([10.0, 20.0, 30.0])
    wts = pd.Series([1.0, 1.0, 1.0])
    assert weighted_percentile(vals, wts, 0.0) == pytest.approx(10.0, abs=1.0)


def test_weighted_percentile_empty():
    assert np.isnan(weighted_percentile(pd.Series([], dtype=float), pd.Series([], dtype=float), 0.5))


# ---------------------------------------------------------------------------
# renormalize_weights
# ---------------------------------------------------------------------------


def test_renormalize_weights_simple():
    df = pd.DataFrame({
        "population_weight": [0.3, 0.7],
        "value": [100.0, 200.0],
    })
    result = renormalize_weights(df)
    assert result["population_weight"].sum() == pytest.approx(1.0)


def test_renormalize_weights_by_year():
    df = pd.DataFrame({
        "year": [2025, 2025, 2030, 2030],
        "population_weight": [0.2, 0.2, 0.1, 0.1],
        "value": [1, 2, 3, 4],
    })
    result = renormalize_weights(df)
    for year in [2025, 2030]:
        subset = result[result["year"] == year]
        assert subset["population_weight"].sum() == pytest.approx(1.0)


def test_renormalize_weights_zero_total():
    df = pd.DataFrame({
        "population_weight": [0.0, 0.0],
        "value": [100.0, 200.0],
    })
    result = renormalize_weights(df)
    assert (result["population_weight"] == 0.0).all()


# ---------------------------------------------------------------------------
# detect_mandatory_groupby
# ---------------------------------------------------------------------------


def test_detect_mandatory_groupby():
    df = pd.DataFrame({"year": [2025], "scn_adoption": ["high"], "value": [1]})
    cols = detect_mandatory_groupby(df)
    assert "year" in cols
    assert "scn_adoption" in cols


def test_detect_mandatory_groupby_no_year():
    df = pd.DataFrame({"value": [1]})
    assert detect_mandatory_groupby(df) == []


# ---------------------------------------------------------------------------
# available_dimensions
# ---------------------------------------------------------------------------


def test_available_dimensions():
    df = pd.DataFrame({"year": [2025], "climate_zone": ["CZ_5"], "other_col": [1]})
    dims = available_dimensions(df)
    assert "year" in dims
    assert "climate_zone" in dims
    assert "other_col" not in dims


# ---------------------------------------------------------------------------
# apply_filters
# ---------------------------------------------------------------------------


def test_apply_filters():
    df = pd.DataFrame({
        "climate_zone": ["CZ_5", "CZ_6", "CZ_5", "CZ_7"],
        "value": [10, 20, 30, 40],
    })
    result = apply_filters(df, {"climate_zone": ["CZ_5"]})
    assert len(result) == 2
    assert (result["value"] == [10, 30]).all()


def test_apply_filters_empty():
    df = pd.DataFrame({"climate_zone": ["CZ_5", "CZ_6"], "value": [10, 20]})
    result = apply_filters(df, {"climate_zone": ["CZ_99"]})
    assert len(result) == 0


def test_apply_filters_nonexistent_column():
    df = pd.DataFrame({"value": [10, 20]})
    result = apply_filters(df, {"missing_col": ["x"]})
    assert len(result) == 2  # No filtering applied


# ---------------------------------------------------------------------------
# weighted_mean_by_group
# ---------------------------------------------------------------------------


def test_weighted_mean_by_group():
    df = pd.DataFrame({
        "year": [2025, 2025, 2030, 2030],
        "population_weight": [0.5, 0.5, 0.5, 0.5],
        "value": [100.0, 200.0, 300.0, 400.0],
    })
    result = weighted_mean_by_group(df, "value", ["year"])
    assert len(result) == 2
    row_2025 = result[result["year"] == 2025].iloc[0]
    assert row_2025["value"] == pytest.approx(150.0)
