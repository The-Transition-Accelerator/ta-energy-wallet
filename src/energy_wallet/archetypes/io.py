from __future__ import annotations
from pathlib import Path
from typing import List, Tuple, Optional, Iterable
import pandas as pd

from .errors import ArchetypeTableError
from .spec import ArchetypeTableSpec
from .validate import validate_table


def discover_archetype_files(
    inputs_dir: Path,
    *,
    suffix: str = ".csv",
    include: Optional[Iterable[str]] = None,
    exclude: Optional[Iterable[str]] = None,
) -> List[Path]:
    """
    Discover archetype table files.

    New architecture: files are named by the archetype variable they define,
    so we do NOT require a 'w_' prefix.

    Parameters
    ----------
    inputs_dir : Path
        Directory containing archetype CSV files.
    suffix : str
        File extension to match (default '.csv').
    include : Iterable[str] | None
        Optional list of filename stems or filenames to include.
        Examples: ['dwelling_type', 'vehicle_type'] or ['dwelling_type.csv']
    exclude : Iterable[str] | None
        Optional list of filename stems or filenames to exclude.

    Returns
    -------
    List[Path]
    """
    if not inputs_dir.exists():
        raise ArchetypeTableError(f"Inputs directory not found: {inputs_dir}")

    # Normalize include/exclude to sets of both "stem" and "name"
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

    files = []
    for p in inputs_dir.iterdir():
        if not (p.is_file() and p.suffix == suffix):
            continue

        if include_set:
            if (p.name not in include_set) and (p.stem not in include_set):
                continue

        if exclude_set:
            if (p.name in exclude_set) or (p.stem in exclude_set):
                continue

        files.append(p)

    files = sorted(files)

    if not files:
        raise ArchetypeTableError(f"No archetype CSV files found in {inputs_dir} (suffix='{suffix}')")

    return files


def infer_spec_from_columns(
    path: Path,
    cols: List[str],
    share_col: str = "population_share",
) -> ArchetypeTableSpec:
    if len(cols) < 2:
        raise ArchetypeTableError(f"{path.name}: must have at least [new_var][{share_col}]")

    if cols[-1] != share_col:
        raise ArchetypeTableError(
            f"{path.name}: last column must be '{share_col}' but found '{cols[-1]}'. "
            f"Required order: [conditioning...][new_variable][year?][{share_col}]"
        )

    year_col = None
    if len(cols) >= 3 and cols[-2] == "year":
        year_col = "year"
        new_var_col = cols[-3]
        conditioning_cols = cols[:-3]
        if len(cols) < 3:
            raise ArchetypeTableError(f"{path.name}: invalid column layout (needs new_var before year/share).")
    else:
        new_var_col = cols[-2]
        conditioning_cols = cols[:-2]

    return ArchetypeTableSpec(
        path=path,
        conditioning_cols=list(conditioning_cols),
        new_var_col=new_var_col,
        year_col=year_col,
        share_col=share_col,
    )


def load_archetype_table(
    path: Path,
    share_col: str = "population_share",
    tolerance: float = 1e-3,
) -> Tuple[pd.DataFrame, ArchetypeTableSpec]:
    df = pd.read_csv(path)

    cols = list(df.columns)
    spec = infer_spec_from_columns(path, cols, share_col=share_col)

    # Filter zero-share rows early (optimization requirement)
    df = df[df[spec.share_col] != 0].copy()

    validate_table(df, spec, tolerance=tolerance)
    return df, spec


def load_all_archetype_tables(
    inputs_dir: Path,
    share_col: str = "population_share",
    tolerance: float = 1e-3,
    logger=None,
    *,
    include: Optional[Iterable[str]] = None,
    exclude: Optional[Iterable[str]] = None,
) -> Tuple[List[pd.DataFrame], List[ArchetypeTableSpec]]:
    files = discover_archetype_files(inputs_dir, include=include, exclude=exclude)

    tables: List[pd.DataFrame] = []
    specs: List[ArchetypeTableSpec] = []

    for p in files:
        if logger:
            logger.info(f"Loading archetype table: {p.name}")
        else:
            print(f"Loading archetype table: {p.name}")

        df, spec = load_archetype_table(p, share_col=share_col, tolerance=tolerance)
        tables.append(df)
        specs.append(spec)

    return tables, specs
