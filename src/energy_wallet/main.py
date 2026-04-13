from __future__ import annotations

import argparse
from pathlib import Path
import sys

import pandas as pd

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


def run_step1(
    *,
    inputs_root: Path,
    archetypes_subdir: str,
    output_path: Path,
    share_col: str,
    weight_col: str,
    tolerance: float,
    keep_provenance_shares: bool,
) -> Path:
    archetypes_dir = inputs_root / archetypes_subdir

    tables_list, specs_list = load_all_archetype_tables(
        archetypes_dir,
        share_col=share_col,
        tolerance=tolerance,
    )

    tables = {spec.path.stem: table for table, spec in zip(tables_list, specs_list)}
    specs = {spec.path.stem: spec for spec in specs_list}

    merged = merge_archetypes(
        tables,
        specs,
        weight_col_out=weight_col,
        keep_provenance_shares=keep_provenance_shares,
        tolerance=tolerance,
        validate=True,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(output_path, index=False)
    return output_path


def run_step2(
    *,
    baseline_archetypes_path: Path,
    inputs_root: Path,
    alternatives_subdir: str,
    output_path: Path,
    adoption_share_col: str,
    weight_col: str,
    tolerance: float,
) -> Path:
    baseline = pd.read_csv(baseline_archetypes_path)

    expanded = build_expanded_archetype_table(
        baseline,
        inputs_root=inputs_root,
        alternatives_subdir=alternatives_subdir,
        share_col=adoption_share_col,
        baseline_weight_col=weight_col,
        expanded_weight_col=weight_col,
        tolerance=tolerance,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    expanded.to_csv(output_path, index=False)
    return output_path


def run_step3(
    *,
    expanded_archetypes_path: Path,
    inputs_root: Path,
    input_parameters_subdir: str,
    output_path: Path,
) -> Path:
    expanded = pd.read_csv(expanded_archetypes_path)

    model_inputs = build_model_input_table(
        expanded,
        inputs_root=inputs_root,
        input_parameters_subdir=input_parameters_subdir,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    model_inputs.to_csv(output_path, index=False)
    return output_path


def run_step4(
    *,
    model_inputs_path: Path,
    output_path: Path,
) -> Path:
    model_inputs = pd.read_csv(model_inputs_path)

    step4_output = compute_energy_wallet(model_inputs)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    step4_output.to_csv(output_path, index=False)
    return output_path


def run_step5(
    *,
    step4_output_path: Path,
    output_path: Path,
) -> Path:
    step4_output = pd.read_csv(step4_output_path)

    step5_output = compute_utility_bill_perspective(step4_output)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    step5_output.to_csv(output_path, index=False)
    return output_path


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    args = _resolve_paths(args)

    try:
        step1_output = run_step1(
            inputs_root=args.inputs_root,
            archetypes_subdir=args.archetypes_subdir,
            output_path=args.output,
            share_col=args.share_col,
            weight_col=args.weight_col,
            tolerance=args.tolerance,
            keep_provenance_shares=args.keep_provenance_shares,
        )
    except (ArchetypeTableError, ArchetypeJoinError) as exc:
        print(f"Step 1 failed: {exc}", file=sys.stderr)
        return 2

    print(f"Step 1 complete. Merged archetype table written to: {step1_output}")

    if args.skip_step2:
        print("Step 2 skipped (--skip-step2).")
        print("Step 3 cannot run without Step 2 output.")
        return 0

    try:
        step2_output = run_step2(
            baseline_archetypes_path=step1_output,
            inputs_root=args.inputs_root,
            alternatives_subdir=args.alternatives_subdir,
            output_path=args.step2_output,
            adoption_share_col=args.adoption_share_col,
            weight_col=args.weight_col,
            tolerance=args.tolerance,
        )
    except (AlternativeConfigTableError, AlternativeConfigJoinError) as exc:
        print(f"Step 2 failed: {exc}", file=sys.stderr)
        return 3

    print(f"Step 2 complete. Expanded archetype table written to: {step2_output}")

    if args.skip_step3:
        print("Step 3 skipped (--skip-step3).")
        return 0

    try:
        step3_output = run_step3(
            expanded_archetypes_path=step2_output,
            inputs_root=args.inputs_root,
            input_parameters_subdir=args.input_parameters_subdir,
            output_path=args.step3_output,
        )
    except (InputParameterTableError, InputParameterJoinError) as exc:
        print(f"Step 3 failed: {exc}", file=sys.stderr)
        return 4

    print(f"Step 3 complete. Final model input table written to: {step3_output}")

    if args.skip_step4:
        print("Step 4 skipped (--skip-step4).")
        print("Step 5 cannot run without Step 4 output.")
        return 0

    try:
        step4_output = run_step4(
            model_inputs_path=step3_output,
            output_path=args.step4_output,
        )
    except CalculationError as exc:
        print(f"Step 4 failed: {exc}", file=sys.stderr)
        return 5

    print(f"Step 4 complete. Energy wallet calculations written to: {step4_output}")

    if args.skip_step5:
        print("Step 5 skipped (--skip-step5).")
        return 0

    try:
        step5_output = run_step5(
            step4_output_path=step4_output,
            output_path=args.step5_output,
        )
    except EnergyTypeAnalysisError as exc:
        print(f"Step 5 failed: {exc}", file=sys.stderr)
        return 6

    print(f"Step 5 complete. Utility bill perspective written to: {step5_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
