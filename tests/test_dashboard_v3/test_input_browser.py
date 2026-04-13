"""Tests for the input browser module."""

from pathlib import Path
from dashboard_v3.data.input_browser import load_meta_yaml, build_file_tree, file_info_panel


def test_load_meta_yaml_existing():
    """Should load .meta.yaml for a known CSV."""
    from dashboard_v3.data.loader import INPUTS_ROOT
    path = INPUTS_ROOT / "ontario" / "archetypes" / "climate_zone.csv"
    meta = load_meta_yaml(path)
    assert meta is not None
    assert "title" in meta


def test_load_meta_yaml_nonexistent(tmp_path):
    """Should return None for a CSV without .meta.yaml."""
    csv_path = tmp_path / "fake.csv"
    csv_path.write_text("a,b\n1,2\n")
    assert load_meta_yaml(csv_path) is None


def test_build_file_tree():
    """Should return 3 categories for the ontario input set."""
    tree = build_file_tree("ontario")
    assert len(tree) == 3
    cats = {t["category"] for t in tree}
    assert cats == {"archetypes", "alternative_configurations", "input_parameters"}
    for entry in tree:
        assert len(entry["files"]) > 0
        for f in entry["files"]:
            assert "filename" in f
            assert "row_count" in f


def test_file_info_panel_with_meta():
    """Should extract metadata fields."""
    entry = {
        "filename": "test.csv",
        "row_count": 5,
        "col_count": 3,
        "meta": {
            "title": "Test Title",
            "question": "Test question?",
            "topic": "test",
            "description": "A test file.",
            "source": {"name": "TestSource", "detail": "Detail"},
            "keys": ["a"],
            "columns": {"a": {"type": "categorical"}},
        },
    }
    info = file_info_panel(entry)
    assert info["title"] == "Test Title"
    assert info["source_name"] == "TestSource"
    assert info["row_count"] == 5


def test_file_info_panel_without_meta():
    """Should use filename as fallback title."""
    entry = {"filename": "my_data.csv", "row_count": 10, "col_count": 2, "meta": None}
    info = file_info_panel(entry)
    assert info["title"] == "my_data"
    assert info["source_name"] == ""
