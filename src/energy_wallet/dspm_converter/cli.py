"""Interactive CLI for the DSPM-to-Energy-Wallet converter."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import List, Optional, Tuple

from .errors import DSPMConverterError
from .pipeline import run_pipeline
from .reader import get_available_provinces

# Default location for DSPM data libraries (relative to project root)
DEFAULT_LIBRARIES_DIR = "dspm_data_libraries"

# Sentinel for "all provinces" selection
ALL_PROVINCES = "ALL"


def _find_libraries(libraries_dir: Path) -> List[Tuple[Path, str, str]]:
    """Scan for DSPM data libraries.

    Returns list of (path, display_name, description) for each library found.
    """
    if not libraries_dir.exists():
        return []

    libraries = []
    for entry in sorted(libraries_dir.iterdir()):
        if not entry.is_dir():
            continue
        # A library must have at least building_stock_library.csv
        if not (entry / "building_stock_library.csv").exists():
            continue

        # Try to read display info from library_config.json
        config_file = entry / "library_config.json"
        display_name = entry.name
        description = ""
        if config_file.exists():
            try:
                config = json.loads(config_file.read_text())
                display_name = config.get("display_name", entry.name)
                description = config.get("description", "")
            except (json.JSONDecodeError, KeyError):
                pass

        libraries.append((entry, display_name, description))

    return libraries


def _prompt_choice(prompt: str, options: List[str]) -> int:
    """Prompt the user to select from a numbered list. Returns 0-based index."""
    for i, option in enumerate(options, 1):
        print(f"  [{i}] {option}")
    print()

    while True:
        try:
            raw = input(f"{prompt} [1-{len(options)}]: ").strip()
            idx = int(raw) - 1
            if 0 <= idx < len(options):
                return idx
            print(f"  Please enter a number between 1 and {len(options)}.")
        except ValueError:
            print(f"  Please enter a number between 1 and {len(options)}.")
        except (EOFError, KeyboardInterrupt):
            print("\nAborted.")
            sys.exit(1)


def _prompt_confirm(prompt: str, default: bool = True) -> bool:
    """Prompt for yes/no confirmation."""
    suffix = "[Y/n]" if default else "[y/N]"
    try:
        raw = input(f"{prompt} {suffix}: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\nAborted.")
        sys.exit(1)

    if not raw:
        return default
    return raw in ("y", "yes")


def _interactive_flow(libraries_dir: Path) -> Tuple[Path, Optional[str], str]:
    """Run the interactive library + province selection flow.

    Returns (library_path, province_or_None, library_name).
    province is None when user selects "All provinces".
    """
    print()
    print("Energy Wallet - DSPM Data Converter")
    print("=" * 36)
    print()

    # Find libraries
    libraries = _find_libraries(libraries_dir)
    if not libraries:
        print(f"No DSPM data libraries found in {libraries_dir}/")
        print("Each library should be a subdirectory containing building_stock_library.csv")
        sys.exit(1)

    # Select library
    if len(libraries) == 1:
        lib_path, lib_name, lib_desc = libraries[0]
        print(f"Found library: {lib_name}")
        if lib_desc:
            print(f"  {lib_desc}")
        print()
    else:
        print("Available data libraries:")
        options = []
        for _, name, desc in libraries:
            label = name
            if desc:
                label += f" - {desc}"
            options.append(label)
        lib_idx = _prompt_choice("Select a library", options)
        lib_path, lib_name, lib_desc = libraries[lib_idx]
        print()

    # Get provinces (with "All provinces" option)
    provinces = get_available_provinces(lib_path)
    province_options = [ALL_PROVINCES + " (all provinces)"] + provinces
    print("Available provinces:")
    prov_idx = _prompt_choice("Select a province", province_options)
    if prov_idx == 0:
        province = None  # All provinces
    else:
        province = provinces[prov_idx - 1]
    print()

    return lib_path, province, lib_name


def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="dspm-converter",
        description="Convert DSPM data library into Energy Wallet input files.",
    )
    parser.add_argument(
        "--library",
        type=str,
        default=None,
        help="Library directory name within dspm_data_libraries/ (skip interactive selection)",
    )
    parser.add_argument(
        "--province",
        type=str,
        default=None,
        help=(
            "Province code, e.g., ON (skip interactive selection). "
            "Use ALL for all provinces."
        ),
    )
    parser.add_argument(
        "--libraries-dir",
        type=Path,
        default=None,
        help=f"Path to libraries directory (default: {DEFAULT_LIBRARIES_DIR}/)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what files would be created without writing anything",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose (DEBUG) logging",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    """CLI main function. Returns exit code."""
    args = _parse_args(argv)

    # Configure logging
    level = logging.DEBUG if args.verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(levelname)s %(name)s: %(message)s",
    )

    # Determine libraries directory
    libraries_dir = args.libraries_dir or Path(DEFAULT_LIBRARIES_DIR)

    # Determine library and province (interactive or from args)
    if args.library and args.province:
        # Non-interactive mode
        lib_path = libraries_dir / args.library
        if not lib_path.exists():
            available = [d.name for d in libraries_dir.iterdir() if d.is_dir()]
            print(
                f"Library '{args.library}' not found in {libraries_dir}/. "
                f"Available: {sorted(available)}",
                file=sys.stderr,
            )
            return 1
        province: Optional[str] = None if args.province == ALL_PROVINCES else args.province
        lib_name = args.library

        # Try to get display name
        config_file = lib_path / "library_config.json"
        if config_file.exists():
            try:
                config = json.loads(config_file.read_text())
                lib_name = config.get("display_name", args.library)
            except (json.JSONDecodeError, KeyError):
                pass
    elif args.library:
        # Library specified, need province interactively
        lib_path = libraries_dir / args.library
        if not lib_path.exists():
            print(f"Library '{args.library}' not found.", file=sys.stderr)
            return 1
        lib_name = args.library
        provinces = get_available_provinces(lib_path)
        province_options = [ALL_PROVINCES + " (all provinces)"] + provinces
        print("\nAvailable provinces:")
        prov_idx = _prompt_choice("Select a province", province_options)
        if prov_idx == 0:
            province = None
        else:
            province = provinces[prov_idx - 1]
    else:
        # Full interactive mode
        lib_path, province, lib_name = _interactive_flow(libraries_dir)

    # Show summary
    province_label = "all provinces" if province is None else province
    print(f"Converting for {province_label} using {lib_name}...")
    print(f"  Library: {lib_path}")
    output_dir = lib_path / "energy_wallet_inputs"
    print(f"  Output:  {output_dir}")
    print()

    if not args.dry_run:
        if not _prompt_confirm("Proceed?"):
            print("Aborted.")
            return 0

    print()

    # Run pipeline
    try:
        result = run_pipeline(
            library_path=lib_path,
            province=province,
            library_name=lib_name,
            dry_run=args.dry_run,
        )
    except DSPMConverterError as exc:
        print(f"\nConversion failed: {exc}", file=sys.stderr)
        return 2

    if result:
        print(f"\nComplete! Output: {result}")
        print(
            f"  {len(list((result / 'archetypes').glob('*.csv')))} archetype files, "
            f"{len(list((result / 'input_parameters').glob('*.csv')))} input parameter files, "
            f"1 documentation file"
        )

    return 0
