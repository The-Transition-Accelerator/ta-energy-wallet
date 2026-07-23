from __future__ import annotations

from pathlib import Path
from typing import Optional

import polars as pl

from .io import load_all_alternative_configuration_tables
from .join import merge_alternative_configurations


def build_expanded_archetype_table(
    baseline_archetypes: pl.DataFrame,
    *,
    inputs_root: Path,
    alternatives_subdir: str = "alternative_configurations",
    share_col: str = "adoption_share",
    baseline_weight_col: str = "population_weight",
    expanded_weight_col: str = "population_weight",
    tolerance: float = 1e-3,
    scenario_cols_by_file: Optional[dict[str, list[str]]] = None,
) -> pl.DataFrame:
    inputs_dir = inputs_root / alternatives_subdir

    tables_list, specs_list = load_all_alternative_configuration_tables(
        inputs_dir,
        share_col=share_col,
        tolerance=tolerance,
        scenario_cols_by_file=scenario_cols_by_file,
    )

    tables = {spec.path.stem: table for table, spec in zip(tables_list, specs_list)}
    specs = {spec.path.stem: spec for spec in specs_list}

    return merge_alternative_configurations(
        baseline_archetypes,
        tables,
        specs,
        baseline_weight_col=baseline_weight_col,
        expanded_weight_col=expanded_weight_col,
        tolerance=tolerance,
        keep_provenance_shares=False,
        validate=True,
    )
