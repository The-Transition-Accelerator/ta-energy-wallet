"""Pipeline orchestrator: chains all converter steps.

Reads DSPM data, computes CZ-specific efficiencies, builds output, writes atomically.
"""

from __future__ import annotations

import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

from .aggregation import aggregate_envelope_bins
from .builders import build_all
from .documentation import generate_documentation
from .efficiency import compute_all_efficiencies_by_cz
from .errors import DSPMValidationError
from .fuel_proportions import compute_all_fuel_proportions_by_cz
from .mapping import map_climate_zones
from .reader import (
    load_building_envelope_bins,
    load_building_stock,
    load_design_temperatures,
    load_dhw_specs,
    load_equipment_categorization,
    load_equipment_shares,
    load_hvac_specs,
)

logger = logging.getLogger(__name__)

# Load columns needed for envelope aggregation
ENVELOPE_LOAD_COLS = [
    "load_heating_annual_kwh",
    "load_cooling_annual_kwh",
    "load_dhw_annual_kwh",
    "load_lighting_annual_kwh",
    "load_cooking_annual_kwh",
    "load_dryer_annual_kwh",
    "load_appliances_annual_kwh",
]

# Default envelope bin grouping
DEFAULT_ENVELOPE_GROUPS = {
    "poor": [-5, -4, -3],
    "average": [-2, -1, 1],
    "good": [2, 3, 4, 5],
}

# Default building types
DEFAULT_BUILDING_TYPES = ["sfd", "row", "apt", "mob"]


def _derive_climate_zone_map(building_stock: pd.DataFrame) -> Dict[str, str]:
    """Auto-derive climate zone mapping from building stock data."""
    raw_czs = building_stock["climate_zone"].astype(str).unique()
    return {cz: f"CZ_{cz.upper()}" for cz in sorted(raw_czs)}


def _derive_name_map(specs: pd.DataFrame) -> Dict[str, str]:
    """Auto-derive equipment name map from specs (config_id -> config_name)."""
    return dict(zip(specs["equipment_config_id"], specs["equipment_config_name"]))


def _derive_fuel_name_map() -> Dict[str, str]:
    """Default DSPM -> EW fuel name mapping."""
    return {
        "electricity": "electric",
        "gas": "gas",
        "oil": "oil",
        "propane": "propane",
        "wood": "wood",
    }


def _compute_cz_design_temps(
    building_stock: pd.DataFrame,
    design_temps: pd.DataFrame,
) -> Dict[str, Tuple[float, float]]:
    """Compute population-weighted design temperatures per climate zone.

    Joins building_stock (has weather_station, climate_zone, building_genome_qty)
    with design_temperatures (has weather_station, design_temp_heat, design_temp_cool).

    Returns {climate_zone: (design_temp_heat, design_temp_cool)}.
    """
    merged = building_stock.merge(design_temps, on="weather_station", how="left")

    # Drop rows where design temp is missing (shouldn't happen with clean data)
    merged = merged.dropna(subset=["design_temp_heat", "design_temp_cool"])

    result = {}
    for cz, group in merged.groupby("climate_zone"):
        total_pop = group["building_genome_qty"].sum()
        if total_pop == 0:
            # Fallback: simple average
            dt_heat = group["design_temp_heat"].mean()
            dt_cool = group["design_temp_cool"].mean()
        else:
            dt_heat = (
                (group["design_temp_heat"] * group["building_genome_qty"]).sum()
                / total_pop
            )
            dt_cool = (
                (group["design_temp_cool"] * group["building_genome_qty"]).sum()
                / total_pop
            )
        result[cz] = (float(dt_heat), float(dt_cool))
        logger.info(
            "CZ %s: design_temp_heat=%.1f, design_temp_cool=%.1f",
            cz, dt_heat, dt_cool,
        )

    return result


def _validate_join_keys(
    archetypes: Dict[str, pd.DataFrame],
    params: Dict[str, pd.DataFrame],
) -> None:
    """Verify every archetype value has matching rows in parameter tables."""
    gaps = []

    # hvac_system coverage
    if "hvac_system" in archetypes and "heating_system_efficiency" in params:
        arch_hvac = set(archetypes["hvac_system"]["hvac_system"])
        param_hvac = set(params["heating_system_efficiency"]["hvac_system"])
        missing = arch_hvac - param_hvac
        if missing:
            gaps.append(
                f"hvac_system in archetypes but not in "
                f"heating_system_efficiency: {sorted(missing)}"
            )

    if "hvac_system" in archetypes and "hvac_costs" in params:
        arch_hvac = set(archetypes["hvac_system"]["hvac_system"])
        param_hvac = set(params["hvac_costs"]["hvac_system"])
        missing = arch_hvac - param_hvac
        if missing:
            gaps.append(
                f"hvac_system in archetypes but not in "
                f"hvac_costs: {sorted(missing)}"
            )

    # dwelling_type coverage
    if "dwelling_type" in archetypes and "other_energy_uses" in params:
        arch_dt = set(archetypes["dwelling_type"]["dwelling_type"])
        param_dt = set(params["other_energy_uses"]["dwelling_type"])
        missing = arch_dt - param_dt
        if missing:
            gaps.append(
                f"dwelling_type in archetypes but not in "
                f"other_energy_uses: {sorted(missing)}"
            )

    # dhw_system coverage
    if "dhw_system" in archetypes and "dhw_system_efficiency" in params:
        arch_dhw = set(archetypes["dhw_system"]["dhw_system"])
        param_dhw = set(params["dhw_system_efficiency"]["dhw_system"])
        missing = arch_dhw - param_dhw
        if missing:
            gaps.append(
                f"dhw_system in archetypes but not in "
                f"dhw_system_efficiency: {sorted(missing)}"
            )

    # envelope_tier + climate_zone + dwelling_type for heating_loads
    if "envelope_tier" in archetypes and "heating_loads" in params:
        key_cols = ["climate_zone", "dwelling_type", "envelope_tier"]
        arch_keys = set(
            archetypes["envelope_tier"][key_cols].itertuples(index=False, name=None)
        )
        param_keys = set(
            params["heating_loads"][key_cols].itertuples(index=False, name=None)
        )
        missing = arch_keys - param_keys
        if missing:
            gaps.append(
                f"{len(missing)} (climate_zone, dwelling_type, envelope_tier) "
                f"combos in archetypes but not in heating_loads"
            )

    if gaps:
        raise DSPMValidationError(
            "Join-key coverage gaps found:\n" + "\n".join(f"  - {g}" for g in gaps)
        )

    logger.info("Join-key validation passed.")


def _write_output_atomic(
    output_dir: Path,
    archetypes: Dict[str, pd.DataFrame],
    params: Dict[str, pd.DataFrame],
    documentation: str,
) -> None:
    """Write all CSVs atomically via temp dir + rename."""
    parent = output_dir.parent
    parent.mkdir(parents=True, exist_ok=True)

    tmp_dir = Path(tempfile.mkdtemp(dir=parent, prefix=f".{output_dir.name}_tmp_"))
    try:
        # Archetypes
        arch_dir = tmp_dir / "archetypes"
        arch_dir.mkdir()
        for name, df in archetypes.items():
            df.to_csv(arch_dir / f"{name}.csv", index=False)

        # Input parameters
        params_dir = tmp_dir / "input_parameters"
        params_dir.mkdir()
        for name, df in params.items():
            df.to_csv(params_dir / f"{name}.csv", index=False)

        # Documentation
        (tmp_dir / "documentation.md").write_text(documentation)

        # Atomic swap
        if output_dir.exists():
            shutil.rmtree(output_dir)
        os.rename(tmp_dir, output_dir)

        logger.info("Output written to %s", output_dir)

    except Exception:
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)
        raise


def _expand_equipment_shares_cz(
    equipment_shares: pd.DataFrame,
    climate_zone_map: Dict[str, str],
    building_stock: pd.DataFrame,
    multi_province: bool,
) -> pd.DataFrame:
    """Map climate zone names in equipment_shares, expanding 'all' rows."""
    if "climate_zone" not in equipment_shares.columns:
        return equipment_shares

    all_mask = equipment_shares["climate_zone"].astype(str) == "all"

    if not all_mask.any():
        return map_climate_zones(equipment_shares, climate_zone_map)

    all_rows = equipment_shares[all_mask].copy()
    specific_rows = equipment_shares[~all_mask].copy()
    expanded = []

    if multi_province:
        # Per-province expansion: only expand to CZs that exist in each province
        prov_czs = (
            building_stock.groupby("province")["climate_zone"]
            .apply(lambda x: sorted(x.unique()))
            .to_dict()
        )
        for prov, czs in prov_czs.items():
            prov_all = all_rows[all_rows["province"] == prov] if "province" in all_rows.columns else all_rows
            for cz in czs:
                copy = prov_all.copy()
                copy["climate_zone"] = cz
                if "province" not in copy.columns:
                    copy["province"] = prov
                expanded.append(copy)
    else:
        mapped_czs = list(climate_zone_map.values())
        for cz in mapped_czs:
            copy = all_rows.copy()
            copy["climate_zone"] = cz
            expanded.append(copy)

    if not specific_rows.empty:
        specific_rows = map_climate_zones(specific_rows, climate_zone_map)
        expanded.append(specific_rows)

    return pd.concat(expanded, ignore_index=True)


def run_pipeline(
    library_path: Path,
    province: Optional[str] = None,
    library_name: str = "",
    *,
    building_types: Optional[List[str]] = None,
    envelope_bin_groups: Optional[Dict[str, List[int]]] = None,
    dry_run: bool = False,
) -> Optional[Path]:
    """Run the full DSPM -> EW conversion pipeline.

    Parameters
    ----------
    library_path : Path
        Path to the DSPM data library directory.
    province : str or None
        Province code (e.g., "ON"). None means all provinces.
    library_name : str
        Display name for the library (for documentation).
    building_types : list, optional
        Building types to include (default: sfd, row, apt, mob).
    envelope_bin_groups : dict, optional
        Envelope bin grouping (default: poor/average/good).
    dry_run : bool
        If True, compute everything but don't write files.

    Returns
    -------
    Path to output directory, or None if dry_run.
    """
    if building_types is None:
        building_types = DEFAULT_BUILDING_TYPES
    if envelope_bin_groups is None:
        envelope_bin_groups = DEFAULT_ENVELOPE_GROUPS

    multi_province = province is None

    # Step 1: Read DSPM data
    print("  Step 1/7: Reading DSPM data...", end=" ", flush=True)
    building_stock = load_building_stock(library_path, province, building_types)
    hvac_specs = load_hvac_specs(library_path)
    dhw_specs = load_dhw_specs(library_path)
    equipment_cat = load_equipment_categorization(library_path)
    equipment_shares = load_equipment_shares(library_path, province, building_types)
    design_temps = load_design_temperatures(library_path)
    print("done")

    # When multi-province, rename province_territory -> province
    if multi_province:
        if "province_territory" in building_stock.columns:
            building_stock = building_stock.rename(
                columns={"province_territory": "province"}
            )
        if "province_territory" in equipment_shares.columns:
            equipment_shares = equipment_shares.rename(
                columns={"province_territory": "province"}
            )

    # Derive mappings from data
    climate_zone_map = _derive_climate_zone_map(building_stock)
    hvac_name_map = _derive_name_map(hvac_specs)
    dhw_name_map = _derive_name_map(dhw_specs)
    fuel_name_map = _derive_fuel_name_map()

    # Apply climate zone mapping
    building_stock = map_climate_zones(building_stock, climate_zone_map)

    # Map CZ in equipment_shares; handle 'all' by expanding to each CZ
    equipment_shares = _expand_equipment_shares_cz(
        equipment_shares, climate_zone_map, building_stock, multi_province,
    )

    # Step 2: Compute CZ climate profiles
    print("  Step 2/7: Computing climate zone profiles...", end=" ", flush=True)
    if multi_province:
        # Per-province CZ design temps (same CZ number may differ across provinces)
        cz_design_temps_by_prov: Dict[str, Dict[str, Tuple[float, float]]] = {}
        for prov in sorted(building_stock["province"].unique()):
            prov_bs = building_stock[building_stock["province"] == prov]
            cz_design_temps_by_prov[prov] = _compute_cz_design_temps(
                prov_bs, design_temps,
            )
    else:
        cz_design_temps = _compute_cz_design_temps(building_stock, design_temps)
    print("done")

    # Step 3: Aggregate envelope bins + compute efficiencies
    print("  Step 3/7: Computing efficiencies by climate zone...", end=" ", flush=True)
    envelope_group_by = (
        (["province"] if multi_province else [])
        + ["climate_zone", "building_type"]
    )
    envelope_agg = aggregate_envelope_bins(
        building_stock,
        envelope_bin_groups,
        group_by=envelope_group_by,
        load_cols=[c for c in ENVELOPE_LOAD_COLS if c in building_stock.columns],
    )

    if multi_province:
        eff_dfs = []
        fp_dfs = []
        for prov, prov_temps in cz_design_temps_by_prov.items():
            eff = compute_all_efficiencies_by_cz(hvac_specs, prov_temps)
            eff["province"] = prov
            eff_dfs.append(eff)
            fp = compute_all_fuel_proportions_by_cz(
                hvac_specs, prov_temps, fuel_name_map,
            )
            fp["province"] = prov
            fp_dfs.append(fp)
        efficiencies = pd.concat(eff_dfs, ignore_index=True)
        fuel_props = pd.concat(fp_dfs, ignore_index=True)
    else:
        efficiencies = compute_all_efficiencies_by_cz(hvac_specs, cz_design_temps)
        fuel_props = compute_all_fuel_proportions_by_cz(
            hvac_specs, cz_design_temps, fuel_name_map
        )
    print("done")

    # Step 4: Build archetype files
    print("  Step 4/7: Building archetype files...", end=" ", flush=True)
    archetypes, params = build_all(
        building_stock=building_stock,
        equipment_shares=equipment_shares,
        envelope_agg=envelope_agg,
        hvac_specs=hvac_specs,
        dhw_specs=dhw_specs,
        equipment_cat=equipment_cat,
        efficiencies=efficiencies,
        fuel_props=fuel_props,
        hvac_name_map=hvac_name_map,
        dhw_name_map=dhw_name_map,
        fuel_name_map=fuel_name_map,
        building_types=building_types,
        multi_province=multi_province,
    )
    print("done")

    # Step 5: (combined with step 4 above)
    print("  Step 5/7: Building input parameter files... done")

    # Step 6: Validate
    print("  Step 6/7: Validating output...", end=" ", flush=True)
    _validate_join_keys(archetypes, params)
    print("done")

    # Step 7: Write output
    output_dir = library_path / "energy_wallet_inputs"
    province_label = "all provinces" if multi_province else province
    doc_text = generate_documentation(
        library_name or library_path.name, province_label,
    )

    if dry_run:
        print("  Step 7/7: DRY RUN - no files written")
        print(f"\n  Would write to: {output_dir}")
        print(f"\n  Archetype files ({len(archetypes)}):")
        for name, df in sorted(archetypes.items()):
            print(f"    {name}.csv: {len(df)} rows x {len(df.columns)} cols")
        print(f"\n  Input parameter files ({len(params)}):")
        for name, df in sorted(params.items()):
            print(f"    {name}.csv: {len(df)} rows x {len(df.columns)} cols")
        return None

    print("  Step 7/7: Writing files...", end=" ", flush=True)
    _write_output_atomic(output_dir, archetypes, params, doc_text)
    print("done")

    return output_dir
