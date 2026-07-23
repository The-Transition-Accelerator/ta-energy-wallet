from __future__ import annotations

import argparse
from pathlib import Path
import sys

import polars as pl

from energy_wallet.archetypes import (
    ArchetypeJoinError,
    ArchetypeTableError,
    load_all_archetype_tables,
    merge_archetypes,
)
from energy_wallet.alternative_configurations import (
    AlternativeConfigJoinError,
    AlternativeConfigTableError,
    build_expanded_archetype_table,
)
from energy_wallet.input_parameters import (
    InputParameterJoinError,
    InputParameterTableError,
    build_model_input_table,
    load_model_input_tables,
)
from energy_wallet.partitioning import (
    DEFAULT_PARTITION_ROWS,
    StepOutputWriter,
    compute_partition_count,
    estimate_csv_output_gb,
    resolve_output_format,
)
from energy_wallet.calculations import (
    CalculationError,
    compute_energy_wallet,
)
from energy_wallet.energy_type_analysis import (
    EnergyTypeAnalysisError,
    compute_utility_bill_perspective,
)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="energy-wallet",
        description=(
            "Run the Energy Wallet model pipeline. "
            "Steps 1-5: archetype loading, alternative configuration expansion, "
            "input parameter attachment, energy wallet calculations, and "
            "utility bill perspective analysis."
        ),
    )

    parser.add_argument(
        "--inputs-root",
        type=Path,
        default=None,
        help=(
            "Root inputs directory (overrides --input-set). "
            "If provided, this path is used directly as the inputs root."
        ),
    )
    parser.add_argument(
        "--input-set",
        default=None,
        help=(
            "Named input set subdirectory under inputs/. "
            "E.g., --input-set test_input_set_1 resolves to inputs/test_input_set_1/. "
            "Required unless --inputs-root is provided."
        ),
    )
    parser.add_argument(
        "--archetypes-subdir",
        default="archetypes",
        help="Subdirectory under inputs root containing archetype CSV files",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("outputs") / "step1_archetypes_merged.csv",
        help="Output CSV path for Step 1 merged archetype distribution",
    )
    parser.add_argument(
        "--step2-output",
        type=Path,
        default=Path("outputs") / "step2_archetypes_expanded.csv",
        help="Output CSV path for Step 2 expanded archetype distribution",
    )
    parser.add_argument(
        "--step3-output",
        type=Path,
        default=Path("outputs") / "step3_model_inputs.csv",
        help="Output CSV path for Step 3 model input table",
    )
    parser.add_argument(
        "--share-col",
        default="population_share",
        help="Share column name in archetype tables",
    )
    parser.add_argument(
        "--weight-col",
        default="population_weight",
        help="Output weight column name for merged archetypes",
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=1e-3,
        help="Validation tolerance for share sums (default: 0.001)",
    )
    parser.add_argument(
        "--keep-provenance-shares",
        action="store_true",
        help="Keep per-table share provenance columns in Step 1 output (dropped by default)",
    )
    parser.add_argument(
        "--alternatives-subdir",
        default="alternative_configurations",
        help="Subdirectory under inputs root containing alternative configuration CSV files",
    )
    parser.add_argument(
        "--adoption-share-col",
        default="adoption_share",
        help="Adoption share column name in alternative configuration tables",
    )
    parser.add_argument(
        "--skip-step2",
        action="store_true",
        help="Run Step 1 only and skip Step 2 expansion",
    )
    parser.add_argument(
        "--skip-step3",
        action="store_true",
        help="Run through Step 2 only and skip Step 3 input parameter attachment",
    )
    parser.add_argument(
        "--input-parameters-subdir",
        default="input_parameters",
        help="Subdirectory under inputs root containing input parameter CSV files",
    )
    parser.add_argument(
        "--step4-output",
        type=Path,
        default=Path("outputs") / "step4_energy_wallet.csv",
        help="Output CSV path for Step 4 energy wallet calculations",
    )
    parser.add_argument(
        "--step5-output",
        type=Path,
        default=Path("outputs") / "step5_utility_bills.csv",
        help="Output CSV path for Step 5 utility bill perspective",
    )
    parser.add_argument(
        "--skip-step4",
        action="store_true",
        help="Skip Step 4 energy wallet calculations",
    )
    parser.add_argument(
        "--skip-step5",
        action="store_true",
        help="Skip Step 5 utility bill perspective analysis",
    )
    parser.add_argument(
        "--output-format",
        choices=["auto", "csv", "parquet"],
        default="auto",
        help=(
            "Output file format (default: auto). auto = csv for single-partition "
            "runs, parquet part-files for partitioned runs. Parquet is faster "
            "and much smaller."
        ),
    )
    parser.add_argument(
        "--partition-rows",
        type=int,
        default=DEFAULT_PARTITION_ROWS,
        help=(
            "Maximum expanded-archetype rows processed per partition in Steps 3-5 "
            f"(default: {DEFAULT_PARTITION_ROWS}). Bounds peak memory; results are "
            "identical regardless of partitioning."
        ),
    )

    return parser.parse_args(argv)


_DEFAULT_INPUTS_ROOT = Path("inputs")
_DEFAULT_OUTPUTS_ROOT = Path("outputs")


def _resolve_paths(args: argparse.Namespace) -> argparse.Namespace:
    """Resolve ``--input-set`` / ``--inputs-root`` into effective paths.

    Precedence:
    1. ``--inputs-root`` (explicit path) always wins.
    2. ``--input-set`` resolves to ``inputs/<set_name>/``.
    3. If neither is given, print available sets and exit with an error.
    """
    inputs_root_explicit = args.inputs_root is not None

    if inputs_root_explicit:
        # --inputs-root provided directly; ignore --input-set if also given.
        if args.input_set is not None:
            print(
                f"Warning: --inputs-root was explicitly set to {args.inputs_root}. "
                f"--input-set '{args.input_set}' is ignored.",
                file=sys.stderr,
            )
    elif args.input_set is not None:
        # Validate the set name is a simple directory name.
        if (
            "/" in args.input_set
            or "\\" in args.input_set
            or args.input_set in (".", "..")
        ):
            print(
                f"Error: --input-set must be a simple directory name, "
                f"got: '{args.input_set}'",
                file=sys.stderr,
            )
            sys.exit(1)
        args.inputs_root = _DEFAULT_INPUTS_ROOT / args.input_set
    else:
        # Neither flag provided — list available sets and exit.
        available = _list_available_input_sets(_DEFAULT_INPUTS_ROOT)
        if available:
            sets_str = ", ".join(available)
            print(
                f"Error: --input-set is required. "
                f"Available input sets: {sets_str}",
                file=sys.stderr,
            )
        else:
            print(
                f"Error: --input-set is required and no input sets were found "
                f"under {_DEFAULT_INPUTS_ROOT}/.",
                file=sys.stderr,
            )
        sys.exit(1)

    # Validate the resolved inputs root exists.
    if not args.inputs_root.exists():
        print(
            f"Error: inputs directory not found: {args.inputs_root}",
            file=sys.stderr,
        )
        sys.exit(1)

    # Adjust default output paths when --input-set is active.
    if args.input_set is not None and not inputs_root_explicit:
        output_root = _DEFAULT_OUTPUTS_ROOT / args.input_set
        _default_outputs = {
            "output": "step1_archetypes_merged.csv",
            "step2_output": "step2_archetypes_expanded.csv",
            "step3_output": "step3_model_inputs.csv",
            "step4_output": "step4_energy_wallet.csv",
            "step5_output": "step5_utility_bills.csv",
        }
        for attr, filename in _default_outputs.items():
            if getattr(args, attr) == _DEFAULT_OUTPUTS_ROOT / filename:
                setattr(args, attr, output_root / filename)

    return args


def _list_available_input_sets(inputs_root: Path) -> list[str]:
    """Return sorted names of subdirectories under *inputs_root* that look
    like input sets (i.e. contain at least one of the expected subdirs)."""
    expected_subdirs = {"archetypes", "alternative_configurations", "input_parameters"}
    sets: list[str] = []
    if not inputs_root.is_dir():
        return sets
    for child in sorted(inputs_root.iterdir()):
        if not child.is_dir():
            continue
        child_contents = {p.name for p in child.iterdir() if p.is_dir()}
        if child_contents & expected_subdirs:
            sets.append(child.name)
    return sets


def _write_output(df: pl.DataFrame, path: Path, fmt: str = "csv") -> Path:
    """Write a DataFrame to disk in the requested format."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "parquet":
        out = path.with_suffix(".parquet")
        df.write_parquet(out)
        return out
    df.write_csv(path)
    return path


def run_step1(
    *,
    inputs_root: Path,
    archetypes_subdir: str,
    share_col: str,
    weight_col: str,
    tolerance: float,
    keep_provenance_shares: bool,
) -> pl.DataFrame:
    archetypes_dir = inputs_root / archetypes_subdir

    tables_list, specs_list = load_all_archetype_tables(
        archetypes_dir,
        share_col=share_col,
        tolerance=tolerance,
    )

    tables = {spec.path.stem: table for table, spec in zip(tables_list, specs_list)}
    specs = {spec.path.stem: spec for spec in specs_list}

    return merge_archetypes(
        tables,
        specs,
        weight_col_out=weight_col,
        keep_provenance_shares=keep_provenance_shares,
        tolerance=tolerance,
        validate=True,
    )


def run_step2(
    *,
    baseline: pl.DataFrame,
    inputs_root: Path,
    alternatives_subdir: str,
    adoption_share_col: str,
    weight_col: str,
    tolerance: float,
) -> pl.DataFrame:
    return build_expanded_archetype_table(
        baseline,
        inputs_root=inputs_root,
        alternatives_subdir=alternatives_subdir,
        share_col=adoption_share_col,
        baseline_weight_col=weight_col,
        expanded_weight_col=weight_col,
        tolerance=tolerance,
    )


def run_step3(
    *,
    expanded: pl.DataFrame,
    inputs_root: Path,
    input_parameters_subdir: str,
    tables_and_specs=None,
) -> pl.DataFrame:
    return build_model_input_table(
        expanded,
        inputs_root=inputs_root,
        input_parameters_subdir=input_parameters_subdir,
        tables_and_specs=tables_and_specs,
    )


def run_step4(*, model_inputs: pl.DataFrame) -> pl.DataFrame:
    return compute_energy_wallet(model_inputs)


def run_step5(*, step4_output: pl.DataFrame) -> pl.DataFrame:
    return compute_utility_bill_perspective(step4_output)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    args = _resolve_paths(args)

    if args.partition_rows < 1:
        print(
            f"Error: --partition-rows must be >= 1, got {args.partition_rows}",
            file=sys.stderr,
        )
        return 1

    try:
        step1_df = run_step1(
            inputs_root=args.inputs_root,
            archetypes_subdir=args.archetypes_subdir,
            share_col=args.share_col,
            weight_col=args.weight_col,
            tolerance=args.tolerance,
            keep_provenance_shares=args.keep_provenance_shares,
        )
    except (ArchetypeTableError, ArchetypeJoinError) as exc:
        print(f"Step 1 failed: {exc}", file=sys.stderr)
        return 2

    if args.skip_step2:
        out = _write_output(step1_df, args.output, resolve_output_format(args.output_format, 1))
        print(f"Step 1 complete. Merged archetype table written to: {out}")
        print("Step 2 skipped (--skip-step2).")
        print("Step 3 cannot run without Step 2 output.")
        return 0

    try:
        step2_df = run_step2(
            baseline=step1_df,
            inputs_root=args.inputs_root,
            alternatives_subdir=args.alternatives_subdir,
            adoption_share_col=args.adoption_share_col,
            weight_col=args.weight_col,
            tolerance=args.tolerance,
        )
    except (AlternativeConfigTableError, AlternativeConfigJoinError) as exc:
        # Still write Step 1's output so the failure can be inspected.
        out = _write_output(step1_df, args.output, resolve_output_format(args.output_format, 1))
        print(f"Step 1 complete. Merged archetype table written to: {out}")
        print(f"Step 2 failed: {exc}", file=sys.stderr)
        return 3

    # Output format resolves once the partition count is known, so Step 1's
    # write is deferred until here (Step 2 failure path above still writes it).
    n_parts = compute_partition_count(len(step2_df), args.partition_rows)
    fmt = resolve_output_format(args.output_format, n_parts)

    out = _write_output(step1_df, args.output, fmt)
    print(f"Step 1 complete. Merged archetype table written to: {out}")
    del step1_df
    out = _write_output(step2_df, args.step2_output, fmt)
    print(f"Step 2 complete. Expanded archetype table written to: {out}")

    if args.skip_step3:
        print("Step 3 skipped (--skip-step3).")
        return 0

    if n_parts > 1:
        print(
            f"Expanded table: {len(step2_df):,} rows. Running Steps 3-5 in "
            f"{n_parts} partitions (<={args.partition_rows:,} rows each) to bound memory."
        )
        if args.output_format == "auto":
            print(
                "Output format: parquet (auto-selected for partitioned runs; "
                "pass --output-format csv to override)."
            )
        elif fmt == "csv":
            projected_gb = estimate_csv_output_gb(step2_df)
            if projected_gb > 10:
                print(
                    f"Note: at this scale CSV outputs will total roughly "
                    f"{projected_gb:.0f} GB. Consider --output-format parquet."
                )

    try:
        tables_and_specs = load_model_input_tables(
            args.inputs_root / args.input_parameters_subdir,
            set(step2_df.columns),
        )
    except (InputParameterTableError, InputParameterJoinError) as exc:
        print(f"Step 3 failed: {exc}", file=sys.stderr)
        return 4

    writers = {"step3": StepOutputWriter(args.step3_output, fmt, n_parts)}
    if not args.skip_step4:
        writers["step4"] = StepOutputWriter(args.step4_output, fmt, n_parts)
        if not args.skip_step5:
            writers["step5"] = StepOutputWriter(args.step5_output, fmt, n_parts)

    def _abort(message: str, exit_code: int) -> int:
        for w in writers.values():
            w.abort()
        print(message, file=sys.stderr)
        return exit_code

    for k in range(n_parts):
        part = step2_df.slice(k * args.partition_rows, args.partition_rows)
        ctx = f" [partition {k + 1}/{n_parts}]" if n_parts > 1 else ""

        try:
            step3_part = run_step3(
                expanded=part,
                inputs_root=args.inputs_root,
                input_parameters_subdir=args.input_parameters_subdir,
                tables_and_specs=tables_and_specs,
            )
        except (InputParameterTableError, InputParameterJoinError) as exc:
            return _abort(f"Step 3 failed{ctx}: {exc}", 4)
        writers["step3"].write_partition(step3_part, k)

        if not args.skip_step4:
            try:
                step4_part = run_step4(model_inputs=step3_part)
            except CalculationError as exc:
                return _abort(f"Step 4 failed{ctx}: {exc}", 5)
            del step3_part
            writers["step4"].write_partition(step4_part, k)

            if not args.skip_step5:
                try:
                    step5_part = run_step5(step4_output=step4_part)
                except EnergyTypeAnalysisError as exc:
                    return _abort(f"Step 5 failed{ctx}: {exc}", 6)
                del step4_part
                writers["step5"].write_partition(step5_part, k)
                del step5_part
            else:
                del step4_part
        else:
            del step3_part

        if n_parts > 1:
            print(f"[partition {k + 1}/{n_parts}] complete")

    out = writers["step3"].finalize()
    print(f"Step 3 complete. Final model input table written to: {out}")

    if args.skip_step4:
        print("Step 4 skipped (--skip-step4).")
        print("Step 5 cannot run without Step 4 output.")
        return 0

    out = writers["step4"].finalize()
    print(f"Step 4 complete. Energy wallet calculations written to: {out}")

    if args.skip_step5:
        print("Step 5 skipped (--skip-step5).")
        return 0

    out = writers["step5"].finalize()
    print(f"Step 5 complete. Utility bill perspective written to: {out}")
    if fmt == "parquet" and n_parts > 1:
        print(f'Read results lazily with: pl.scan_parquet("{out}/*.parquet")')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
