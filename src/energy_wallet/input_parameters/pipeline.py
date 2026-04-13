from __future__ import annotations

from pathlib import Path

import pandas as pd

from .io import load_all_input_parameter_tables
from .join import attach_input_parameters
from .validate import validate_cross_table_parameter_registry


def build_model_input_table(
    expanded_archetypes: pd.DataFrame,
    *,
    inputs_root: Path,
    input_parameters_subdir: str = "input_parameters",
) -> pd.DataFrame:
    """Orchestrate Step 3 input parameter loading and matching.

    Phase 3B: passes ``expanded_columns`` (the column names from
    *expanded_archetypes*) through the loading pipeline so that the
    multi-lookup system can detect slot expansions and alt variants.

    Cross-table parameter validation is run in relaxed mode (non-strict)
    because multi-lookup tables produce output columns with different names
    than their raw value columns.  The primary coverage check is performed
    on the final output table by ``validate_final_model_input_table``.
    """
    inputs_dir = inputs_root / input_parameters_subdir

    expanded_columns = set(expanded_archetypes.columns)

    tables_list, specs_list = load_all_input_parameter_tables(
        inputs_dir,
        expanded_columns=expanded_columns,
    )

    # Relaxed cross-table validation (strict=False) to accommodate
    # multi-lookup tables whose raw value cols differ from final output names.
    validate_cross_table_parameter_registry(specs_list, strict=False)

    tables = {spec.path.stem: table for table, spec in zip(tables_list, specs_list)}
    specs = {spec.path.stem: spec for spec in specs_list}

    return attach_input_parameters(
        expanded_archetypes,
        tables,
        specs,
        validate=True,
    )
