from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional, Set, Tuple

import polars as pl

from .io import load_all_input_parameter_tables
from .join import attach_input_parameters
from .spec import InputParameterTableSpec
from .validate import validate_cross_table_parameter_registry


def load_model_input_tables(
    inputs_dir: Path,
    expanded_columns: Set[str],
) -> Tuple[Dict[str, pl.DataFrame], Dict[str, InputParameterTableSpec]]:
    """Load and validate all input parameter tables once.

    The result can be passed to :func:`build_model_input_table` via
    ``tables_and_specs`` to reuse the loaded tables across partitions
    (the spec inference depends only on the expanded table's *columns*,
    which are identical for every partition).
    """
    tables_list, specs_list = load_all_input_parameter_tables(
        inputs_dir,
        expanded_columns=expanded_columns,
    )

    # Relaxed cross-table validation (strict=False) to accommodate
    # multi-lookup tables whose raw value cols differ from final output names.
    validate_cross_table_parameter_registry(specs_list, strict=False)

    tables = {spec.path.stem: table for table, spec in zip(tables_list, specs_list)}
    specs = {spec.path.stem: spec for spec in specs_list}
    return tables, specs


def build_model_input_table(
    expanded_archetypes: pl.DataFrame,
    *,
    inputs_root: Path,
    input_parameters_subdir: str = "input_parameters",
    tables_and_specs: Optional[
        Tuple[Dict[str, pl.DataFrame], Dict[str, InputParameterTableSpec]]
    ] = None,
) -> pl.DataFrame:
    """Orchestrate Step 3 input parameter loading and matching.

    Phase 3B: passes ``expanded_columns`` (the column names from
    *expanded_archetypes*) through the loading pipeline so that the
    multi-lookup system can detect slot expansions and alt variants.

    Cross-table parameter validation is run in relaxed mode (non-strict)
    because multi-lookup tables produce output columns with different names
    than their raw value columns.  The primary coverage check is performed
    on the final output table by ``validate_final_model_input_table``.

    When ``tables_and_specs`` is provided (from
    :func:`load_model_input_tables`), the load phase is skipped — used by
    partitioned execution to load parameter tables once.
    """
    if tables_and_specs is None:
        tables_and_specs = load_model_input_tables(
            inputs_root / input_parameters_subdir,
            set(expanded_archetypes.columns),
        )
    tables, specs = tables_and_specs

    return attach_input_parameters(
        expanded_archetypes,
        tables,
        specs,
        validate=True,
    )
