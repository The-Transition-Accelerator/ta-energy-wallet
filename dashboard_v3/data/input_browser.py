"""Input file browser — discovers CSVs, reads .meta.yaml, builds file tree data."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from dashboard_v3.data.loader import (
    INPUTS_ROOT,
    EXPECTED_SUBDIRS,
    CATEGORY_LABELS,
    discover_csv_files,
    load_csv,
)


def load_meta_yaml(csv_path: Path) -> dict[str, Any] | None:
    """Load the .meta.yaml companion for a CSV, if it exists."""
    meta_path = csv_path.with_suffix(".meta.yaml")
    if not meta_path.exists():
        return None
    with open(meta_path) as f:
        return yaml.safe_load(f)


def build_file_tree(input_set: str) -> list[dict]:
    """Build a hierarchical file tree for the input set.

    Returns a list of category dicts, each with 'category', 'label', and 'files'.
    """
    tree = []
    for cat in sorted(EXPECTED_SUBDIRS):
        files = discover_csv_files(input_set, cat)
        file_entries = []
        for f in files:
            file_path = INPUTS_ROOT / input_set / cat / f
            meta = load_meta_yaml(file_path)
            try:
                df = load_csv(file_path)
                row_count, col_count = len(df), len(df.columns)
            except Exception:
                row_count, col_count = 0, 0
            file_entries.append({
                "filename": f,
                "path": file_path,
                "category": cat,
                "meta": meta,
                "row_count": row_count,
                "col_count": col_count,
            })
        tree.append({
            "category": cat,
            "label": CATEGORY_LABELS.get(cat, cat),
            "files": file_entries,
        })
    return tree


def file_info_panel(file_entry: dict) -> dict:
    """Extract display-ready info from a file entry."""
    meta = file_entry.get("meta") or {}
    return {
        "title": meta.get("title", file_entry["filename"].replace(".csv", "")),
        "question": meta.get("question", ""),
        "topic": meta.get("topic", ""),
        "description": meta.get("description", ""),
        "source_name": meta.get("source", {}).get("name", ""),
        "source_detail": meta.get("source", {}).get("detail", ""),
        "row_count": file_entry["row_count"],
        "col_count": file_entry["col_count"],
        "keys": meta.get("keys", []),
        "columns": meta.get("columns", {}),
    }
