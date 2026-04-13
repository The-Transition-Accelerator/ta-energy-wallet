from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Optional, Tuple

import pandas as pd

from .errors import InputParameterTableError
from .lookup import _detect_alt_variant, _detect_slot_variants, _rename_value_col_for_slot
from .required import REQUIRED_INPUT_PARAMETERS
from .spec import InputParameterTableSpec
from .validate import validate_input_parameter_table


def discover_input_parameter_files(
    inputs_dir: Path,
    *,
    suffix: str = ".csv",
    include: Optional[Iterable[str]] = None,
    exclude: Optional[Iterable[str]] = None,
) -> List[Path]:
    """Discover input parameter CSV tables."""
    if not inputs_dir.exists():
        raise InputParameterTableError(f"Inputs directory not found: {inputs_dir}")

    include_set = set()
    if include:
        for x in include:
            include_set.add(x)
            include_set.add(Path(x).stem)

    exclude_set = set()
    if exclude:
        for x in exclude:
            exclude_set.add(x)
            exclude_set.add(Path(x).stem)

    files: List[Path] = []
    for p in inputs_dir.iterdir():
        if not (p.is_file() and p.suffix == suffix):
            continue
        if include_set and (p.name not in include_set) and (p.stem not in include_set):
            continue
        if (p.name in exclude_set) or (p.stem in exclude_set):
            continue
        files.append(p)

    files = sorted(files)
    if not files:
        raise InputParameterTableError(
            f"No input parameter CSV files found in {inputs_dir} (suffix='{suffix}')"
        )

    return files


def infer_spec_from_columns(
    path: Path,
    cols: List[str],
    *,
    known_join_columns: Optional[set[str]] = None,
    expanded_columns: Optional[set[str]] = None,
) -> InputParameterTableSpec:
    """Infer join columns vs input value columns.

    When *expanded_columns* is provided (Phase 3B), each column is classified
    as:
      - **direct join col**: exists verbatim in *expanded_columns*
      - **tech-type join col**: detected via slot expansion
        (``_detect_slot_variants``) or simple alt variant
        (``_detect_alt_variant``) in the lookup module
      - **dimension col**: ``"year"`` or contains ``"scenario"``
      - **value col**: everything else

    When *expanded_columns* is ``None``, the function falls back to the
    original *known_join_columns* behaviour for backward compatibility.
    """
    required_set = set(REQUIRED_INPUT_PARAMETERS)

    if expanded_columns is not None:
        return _infer_spec_with_expanded(path, cols, expanded_columns, required_set)

    # Legacy fallback: use known_join_columns
    known_join_columns = known_join_columns or set()

    def _is_dimension_col(col: str) -> bool:
        if col in known_join_columns:
            return True
        if col == "year":
            return True
        if "scenario" in col.lower():
            return True
        return False

    join_cols = [c for c in cols if _is_dimension_col(c)]
    input_value_cols = [c for c in cols if c not in join_cols]

    if not input_value_cols:
        raise InputParameterTableError(
            f"{path.name}: no input value columns detected. Provide at least one parameter column."
        )

    # Sanity: at least one value column should be known to Step 3.
    if not any(c in required_set for c in input_value_cols):
        raise InputParameterTableError(
            f"{path.name}: none of the inferred value columns are recognized required parameters."
        )

    year_col = "year" if "year" in join_cols else None

    return InputParameterTableSpec(
        path=path,
        join_cols=join_cols,
        input_value_cols=input_value_cols,
        year_col=year_col,
    )


def _infer_spec_with_expanded(
    path: Path,
    cols: List[str],
    expanded_columns: set[str],
    required_set: set[str],
) -> InputParameterTableSpec:
    """Classify columns using expanded archetype column names (Phase 3B)."""
    direct_join_cols: List[str] = []
    tech_type_join_cols: List[str] = []
    dimension_cols: List[str] = []
    value_cols: List[str] = []

    for col in cols:
        if col == "year":
            dimension_cols.append(col)
        elif "scenario" in col.lower():
            dimension_cols.append(col)
        elif col in expanded_columns:
            direct_join_cols.append(col)
        else:
            # Try slot expansion detection
            expansion = _detect_slot_variants(col, expanded_columns)
            if expansion is not None:
                tech_type_join_cols.append(col)
                continue
            # Try simple alt variant detection
            alt_col = _detect_alt_variant(col, expanded_columns)
            if alt_col is not None:
                tech_type_join_cols.append(col)
                continue
            # Not a join column -- treat as value column
            value_cols.append(col)

    if not value_cols:
        raise InputParameterTableError(
            f"{path.name}: no input value columns detected. Provide at least one parameter column."
        )

    # Relaxed required-parameter check for tech-type tables.
    # Raw value cols won't have _base/_alt suffixes for multi-lookup tables,
    # so check whether the raw name OR the name with _base suffix OR the
    # slot-expanded name with _base suffix appears in the required set.
    #
    # For slot expansion: "vehicle_purchase_cost" with a detected slot
    # expansion on "vehicle_type" -> "vehicle_1_purchase_cost_base".
    has_recognized = False
    for c in value_cols:
        if c in required_set:
            has_recognized = True
            break
        if f"{c}_base" in required_set:
            has_recognized = True
            break
        # Try slot-expanded naming: insert _1 after first word, then add _base
        if tech_type_join_cols:
            # For each tech-type join col, try generating the slot-expanded name
            for tc in tech_type_join_cols:
                expansion = _detect_slot_variants(tc, expanded_columns)
                if expansion is not None and expansion.slot_variants:
                    try:
                        renamed = _rename_value_col_for_slot(
                            c, tc, expansion.slot_variants[0]
                        )
                        if f"{renamed}_base" in required_set:
                            has_recognized = True
                            break
                    except ValueError:
                        pass
            if has_recognized:
                break
    if not has_recognized:
        raise InputParameterTableError(
            f"{path.name}: none of the inferred value columns are recognized required parameters. "
            f"Value cols: {value_cols}"
        )

    join_cols = direct_join_cols + tech_type_join_cols + dimension_cols
    year_col = "year" if "year" in dimension_cols else None
    is_multi_lookup = bool(tech_type_join_cols)

    return InputParameterTableSpec(
        path=path,
        join_cols=join_cols,
        input_value_cols=value_cols,
        year_col=year_col,
        direct_join_cols=direct_join_cols,
        tech_type_join_cols=tech_type_join_cols,
        is_multi_lookup=is_multi_lookup,
    )


def load_input_parameter_table(
    path: Path,
    *,
    known_join_columns: Optional[set[str]] = None,
    expanded_columns: Optional[set[str]] = None,
) -> Tuple[pd.DataFrame, InputParameterTableSpec]:
    """Load a single input parameter table and run table-level validation."""
    df = pd.read_csv(path)
    spec = infer_spec_from_columns(
        path,
        list(df.columns),
        known_join_columns=known_join_columns,
        expanded_columns=expanded_columns,
    )
    validate_input_parameter_table(df, spec)
    return df, spec


def load_all_input_parameter_tables(
    inputs_dir: Path,
    *,
    known_join_columns: Optional[set[str]] = None,
    expanded_columns: Optional[set[str]] = None,
    logger=None,
    include: Optional[Iterable[str]] = None,
    exclude: Optional[Iterable[str]] = None,
) -> Tuple[List[pd.DataFrame], List[InputParameterTableSpec]]:
    """Load and validate all input parameter tables."""
    files = discover_input_parameter_files(inputs_dir, include=include, exclude=exclude)

    tables: List[pd.DataFrame] = []
    specs: List[InputParameterTableSpec] = []

    for p in files:
        if logger:
            logger.info(f"Loading input parameter table: {p.name}")
        else:
            print(f"Loading input parameter table: {p.name}")

        df, spec = load_input_parameter_table(
            p,
            known_join_columns=known_join_columns,
            expanded_columns=expanded_columns,
        )
        tables.append(df)
        specs.append(spec)

    return tables, specs
