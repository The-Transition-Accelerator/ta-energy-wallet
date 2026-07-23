from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Optional, Tuple

import polars as pl

from energy_wallet.dtypes import optimize_dtypes

from .errors import AlternativeConfigTableError
from .spec import AlternativeConfigTableSpec
from .validate import validate_table


def discover_alternative_configuration_files(
    inputs_dir: Path,
    *,
    suffix: str = ".csv",
    include: Optional[Iterable[str]] = None,
    exclude: Optional[Iterable[str]] = None,
) -> List[Path]:
    if not inputs_dir.exists():
        raise AlternativeConfigTableError(f"Inputs directory not found: {inputs_dir}")

    include_set = set()
    if include:
        for x in include:
            include_set.add(x)
            if x.endswith(suffix):
                include_set.add(Path(x).stem)
            else:
                include_set.add(f"{x}{suffix}")

    exclude_set = set()
    if exclude:
        for x in exclude:
            exclude_set.add(x)
            if x.endswith(suffix):
                exclude_set.add(Path(x).stem)
            else:
                exclude_set.add(f"{x}{suffix}")

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
        raise AlternativeConfigTableError(
            f"No alternative configuration CSV files found in {inputs_dir} (suffix='{suffix}')"
        )

    return files


def infer_spec_from_columns(
    path: Path,
    cols: List[str],
    *,
    share_col: str = "adoption_share",
    scenario_cols: Optional[List[str]] = None,
) -> AlternativeConfigTableSpec:
    if len(cols) < 3:
        raise AlternativeConfigTableError(
            f"{path.name}: expected at least [conditioning][new_alt_var][{share_col}]"
        )

    if cols[-1] != share_col:
        raise AlternativeConfigTableError(
            f"{path.name}: last column must be '{share_col}' but found '{cols[-1]}'"
        )

    year_col = None
    variable_region_end = -1
    if len(cols) >= 4 and cols[-2] == "year":
        year_col = "year"
        variable_region_end = -2

    variable_region = cols[:variable_region_end]
    if not variable_region:
        raise AlternativeConfigTableError(
            f"{path.name}: missing conditioning/new alternative variable columns"
        )

    if scenario_cols is None:
        scenario_cols = [c for c in variable_region if c.startswith("scn_")]

    for c in scenario_cols:
        if c not in variable_region:
            raise AlternativeConfigTableError(
                f"{path.name}: declared scenario column '{c}' not found before year/share"
            )

    if scenario_cols:
        scenario_indices = [variable_region.index(c) for c in scenario_cols]
        first_scenario_idx = min(scenario_indices)
        new_alt_idx = first_scenario_idx - 1

        if new_alt_idx < 1:
            raise AlternativeConfigTableError(
                f"{path.name}: expected [conditioning][new_alt_var][scenario...] ordering"
            )

        new_alt_var_col = variable_region[new_alt_idx]
        conditioning_cols = variable_region[:new_alt_idx]
        scenario_tail = variable_region[new_alt_idx + 1:]
        if set(scenario_tail) != set(scenario_cols) or len(scenario_tail) != len(scenario_cols):
            raise AlternativeConfigTableError(
                f"{path.name}: scenario columns must come after new alt variable "
                "and before year/share"
            )
    else:
        if len(variable_region) < 2:
            raise AlternativeConfigTableError(
                f"{path.name}: requires at least one conditioning column and one alt variable column"
            )
        new_alt_var_col = variable_region[-1]
        conditioning_cols = variable_region[:-1]

    return AlternativeConfigTableSpec(
        path=path,
        conditioning_cols=conditioning_cols,
        new_alt_var_col=new_alt_var_col,
        scenario_cols=list(scenario_cols),
        year_col=year_col,
        share_col=share_col,
    )


def load_alternative_configuration_table(
    path: Path,
    *,
    share_col: str = "adoption_share",
    tolerance: float = 1e-3,
    scenario_cols: Optional[List[str]] = None,
) -> Tuple[pl.DataFrame, AlternativeConfigTableSpec]:
    df = optimize_dtypes(pl.read_csv(path))
    spec = infer_spec_from_columns(path, df.columns, share_col=share_col, scenario_cols=scenario_cols)

    max_value = df[spec.share_col].max()
    if max_value is not None and max_value > 1:
        df = df.with_columns((pl.col(spec.share_col) / 100.0).alias(spec.share_col))

    df = df.filter(pl.col(spec.share_col) != 0)

    validate_table(df, spec, tolerance=tolerance)
    return df, spec


def load_all_alternative_configuration_tables(
    inputs_dir: Path,
    *,
    share_col: str = "adoption_share",
    tolerance: float = 1e-3,
    logger=None,
    include: Optional[Iterable[str]] = None,
    exclude: Optional[Iterable[str]] = None,
    scenario_cols_by_file: Optional[dict[str, List[str]]] = None,
) -> Tuple[List[pl.DataFrame], List[AlternativeConfigTableSpec]]:
    files = discover_alternative_configuration_files(
        inputs_dir,
        include=include,
        exclude=exclude,
    )

    tables: List[pl.DataFrame] = []
    specs: List[AlternativeConfigTableSpec] = []

    scenario_cols_by_file = scenario_cols_by_file or {}

    for p in files:
        if logger:
            logger.info(f"Loading alternative configuration table: {p.name}")
        else:
            print(f"Loading alternative configuration table: {p.name}")

        scenario_cols = scenario_cols_by_file.get(p.stem)
        df, spec = load_alternative_configuration_table(
            p,
            share_col=share_col,
            tolerance=tolerance,
            scenario_cols=scenario_cols,
        )
        tables.append(df)
        specs.append(spec)

    return tables, specs
