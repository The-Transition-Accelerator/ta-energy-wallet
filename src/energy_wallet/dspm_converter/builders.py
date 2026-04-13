"""Build all output CSV files for the EW input set from DSPM data.

Replaces the old archetypes_builder.py and params_builder.py with a single
module producing 13 files: 5 archetypes + 8 input parameters.

When multi_province=True, every output table includes a 'province' column.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .aggregation import compute_population_shares
from .mapping import EW_FUELS, map_fuel_name
from .unit_conversion import kwh_to_gj

logger = logging.getLogger(__name__)


def _prov_cols(multi_province: bool) -> List[str]:
    """Return ['province'] when multi-province mode, else []."""
    return ["province"] if multi_province else []


# ---------------------------------------------------------------------------
# Archetype builders
# ---------------------------------------------------------------------------


def build_climate_zone_csv(
    building_stock: pd.DataFrame,
    multi_province: bool = False,
) -> pd.DataFrame:
    """climate_zone.csv: proportion of households by climate zone."""
    shares = compute_population_shares(
        building_stock,
        group_cols=["climate_zone"],
        within_cols=_prov_cols(multi_province),
        weight_col="building_genome_qty",
    )
    cols = _prov_cols(multi_province) + ["climate_zone", "population_share"]
    return shares[cols]


def build_dwelling_type_csv(
    building_stock: pd.DataFrame,
    multi_province: bool = False,
) -> pd.DataFrame:
    """dwelling_type.csv: proportion by dwelling type within each CZ."""
    df = building_stock.copy()
    df["dwelling_type"] = df["building_type"]
    shares = compute_population_shares(
        df,
        group_cols=["dwelling_type"],
        within_cols=_prov_cols(multi_province) + ["climate_zone"],
        weight_col="building_genome_qty",
    )
    cols = _prov_cols(multi_province) + ["climate_zone", "dwelling_type", "population_share"]
    return shares[cols]


def build_hvac_system_csv(
    equipment_shares: pd.DataFrame,
    hvac_name_map: Dict[str, str],
    multi_province: bool = False,
) -> pd.DataFrame:
    """hvac_system.csv: HVAC system shares by CZ + dwelling type.

    Each (climate_zone, dwelling_type) combo sums to 100%.
    """
    hvac_ids = set(hvac_name_map.keys())
    df = equipment_shares[
        equipment_shares["equipment_config_id"].isin(hvac_ids)
    ].copy()
    df["hvac_system"] = df["equipment_config_id"].map(hvac_name_map)
    if "building_type" in df.columns:
        df["dwelling_type"] = df["building_type"]

    share_col = "equipment_stock_share_pct"
    prov = _prov_cols(multi_province)
    group_cols = prov + ["climate_zone", "dwelling_type", "hvac_system"]
    grouped = df.groupby(group_cols, sort=True)[share_col].sum().reset_index()

    # Normalize within each (province?, climate_zone, dwelling_type)
    norm_within = prov + ["climate_zone", "dwelling_type"]
    totals = grouped.groupby(norm_within)[share_col].transform("sum")
    grouped["population_share"] = grouped[share_col] / totals

    out_cols = prov + ["climate_zone", "dwelling_type", "hvac_system", "population_share"]
    return grouped[out_cols]


def build_dhw_system_csv(
    equipment_shares: pd.DataFrame,
    dhw_name_map: Dict[str, str],
    multi_province: bool = False,
) -> pd.DataFrame:
    """dhw_system.csv: DHW system shares by CZ + dwelling type.

    Each (climate_zone, dwelling_type) combo sums to 100%.
    """
    dhw_ids = set(dhw_name_map.keys())
    df = equipment_shares[
        equipment_shares["equipment_config_id"].isin(dhw_ids)
    ].copy()
    df["dhw_system"] = df["equipment_config_id"].map(dhw_name_map)
    if "building_type" in df.columns:
        df["dwelling_type"] = df["building_type"]

    share_col = "equipment_stock_share_pct"
    prov = _prov_cols(multi_province)
    group_cols = prov + ["climate_zone", "dwelling_type", "dhw_system"]
    grouped = df.groupby(group_cols, sort=True)[share_col].sum().reset_index()

    norm_within = prov + ["climate_zone", "dwelling_type"]
    totals = grouped.groupby(norm_within)[share_col].transform("sum")
    grouped["population_share"] = grouped[share_col] / totals

    out_cols = prov + ["climate_zone", "dwelling_type", "dhw_system", "population_share"]
    return grouped[out_cols]


def build_envelope_tier_csv(
    envelope_agg: pd.DataFrame,
    multi_province: bool = False,
) -> pd.DataFrame:
    """envelope_tier.csv: envelope tier shares by CZ + dwelling type."""
    df = envelope_agg.copy()
    if "building_type" in df.columns:
        df["dwelling_type"] = df["building_type"]

    prov = _prov_cols(multi_province)
    shares = compute_population_shares(
        df,
        group_cols=["envelope_tier"],
        within_cols=prov + ["climate_zone", "dwelling_type"],
        weight_col="building_genome_qty",
    )
    cols = prov + ["climate_zone", "dwelling_type", "envelope_tier", "population_share"]
    return shares[cols]


# ---------------------------------------------------------------------------
# Input parameter builders
# ---------------------------------------------------------------------------


def build_heating_loads_csv(
    envelope_agg: pd.DataFrame,
    multi_province: bool = False,
) -> pd.DataFrame:
    """heating_loads.csv: pop-weighted heating load by CZ + DT + tier (GJ)."""
    df = envelope_agg.copy()
    if "building_type" in df.columns:
        df["dwelling_type"] = df["building_type"]

    prov = _prov_cols(multi_province)
    key_cols = prov + ["climate_zone", "dwelling_type", "envelope_tier"]
    result = df[key_cols].copy()
    result["heating_load_annual"] = df["load_heating_annual_kwh"].apply(kwh_to_gj)
    return result.sort_values(key_cols).reset_index(drop=True)


def build_cooling_loads_csv(
    envelope_agg: pd.DataFrame,
    multi_province: bool = False,
) -> pd.DataFrame:
    """cooling_loads.csv: pop-weighted cooling load by CZ + DT + tier (GJ)."""
    df = envelope_agg.copy()
    if "building_type" in df.columns:
        df["dwelling_type"] = df["building_type"]

    prov = _prov_cols(multi_province)
    key_cols = prov + ["climate_zone", "dwelling_type", "envelope_tier"]
    result = df[key_cols].copy()
    result["cooling_load_annual"] = df["load_cooling_annual_kwh"].apply(kwh_to_gj)
    return result.sort_values(key_cols).reset_index(drop=True)


def build_heating_system_efficiency_csv(
    efficiencies: pd.DataFrame,
    fuel_proportions: pd.DataFrame,
    hvac_name_map: Dict[str, str],
    hvac_specs: pd.DataFrame,
    fuel_name_map: Dict[str, str],
    multi_province: bool = False,
) -> pd.DataFrame:
    """heating_system_efficiency.csv: CZ-specific efficiencies and fuel proportions.

    Keyed by (climate_zone, hvac_system). Contains proportion and efficiency
    per fuel + cooling efficiency.
    """
    prov = _prov_cols(multi_province)
    merge_keys = prov + ["climate_zone", "equipment_config_id"]
    merged = efficiencies.merge(fuel_proportions, on=merge_keys)
    merged["hvac_system"] = merged["equipment_config_id"].map(hvac_name_map)
    # Drop unmapped configs
    merged = merged.dropna(subset=["hvac_system"])

    # Assign per-fuel efficiency based on primary/secondary COP
    for _, spec_row in hvac_specs.iterrows():
        config_id = spec_row["equipment_config_id"]
        if config_id not in hvac_name_map:
            continue
        mask = merged["equipment_config_id"] == config_id
        if not mask.any():
            continue

        primary_fuel = map_fuel_name(
            spec_row["equipment_primary_energy_source"], fuel_name_map
        )
        has_secondary = pd.notna(spec_row.get("equipment_secondary_energy_source"))
        secondary_fuel = None
        if has_secondary:
            secondary_fuel = map_fuel_name(
                spec_row["equipment_secondary_energy_source"], fuel_name_map
            )

        for idx in merged.index[mask]:
            row_data = merged.loc[idx]
            primary_eff = row_data["primary_heating_efficiency"]
            secondary_eff = row_data["secondary_heating_efficiency"]

            for fuel in EW_FUELS:
                proportion = row_data[f"proportion_{fuel}"]
                if proportion <= 0:
                    merged.loc[idx, f"efficiency_{fuel}"] = 0.0
                elif fuel == primary_fuel and fuel == secondary_fuel:
                    merged.loc[idx, f"efficiency_{fuel}"] = row_data["heating_efficiency"]
                elif fuel == primary_fuel:
                    merged.loc[idx, f"efficiency_{fuel}"] = primary_eff
                elif fuel == secondary_fuel:
                    merged.loc[idx, f"efficiency_{fuel}"] = secondary_eff
                else:
                    merged.loc[idx, f"efficiency_{fuel}"] = 0.0

    # If multiple config IDs map to same EW name within a CZ, average
    agg_cols = {}
    for fuel in EW_FUELS:
        agg_cols[f"proportion_{fuel}"] = "mean"
        agg_cols[f"efficiency_{fuel}"] = "mean"
    agg_cols["cooling_efficiency"] = "mean"

    group_keys = prov + ["climate_zone", "hvac_system"]
    grouped = (
        merged.groupby(group_keys, sort=True)
        .agg(agg_cols)
        .reset_index()
    )

    # Rename to EW column names
    result = grouped[group_keys].copy()
    for fuel in EW_FUELS:
        result[f"heating_system_proportion_{fuel}"] = grouped[f"proportion_{fuel}"]
    for fuel in EW_FUELS:
        result[f"heating_system_efficiency_{fuel}"] = grouped[f"efficiency_{fuel}"]
    result["cooling_system_efficiency"] = grouped["cooling_efficiency"].replace(0, 1.0)

    return result


def build_hvac_costs_csv(
    equipment_cat: pd.DataFrame,
    hvac_name_map: Dict[str, str],
    building_types: List[str],
    multi_province: bool = False,
    provinces: Optional[List[str]] = None,
) -> pd.DataFrame:
    """hvac_costs.csv: equipment cost, life, and maintenance by DT + system."""
    hvac_ids = set(hvac_name_map.keys())
    df = equipment_cat[equipment_cat["equipment_config_id"].isin(hvac_ids)].copy()
    df["hvac_system"] = df["equipment_config_id"].map(hvac_name_map)

    cost_cols = {"cost_equipment": "mean", "equipment_eul": "mean"}
    grouped = df.groupby("hvac_system", sort=True).agg(cost_cols).reset_index()

    prov_list = provinces or []
    rows = []
    for _, hvac_row in grouped.iterrows():
        for dt in building_types:
            base = {
                "dwelling_type": dt,
                "hvac_system": hvac_row["hvac_system"],
                "hvac_equipment_cost": hvac_row["cost_equipment"],
                "hvac_assumed_life": hvac_row["equipment_eul"],
                "hvac_maintenance_cost_annual": 120,  # PLACEHOLDER
            }
            if multi_province:
                for prov in prov_list:
                    rows.append({"province": prov, **base})
            else:
                rows.append(base)

    return pd.DataFrame(rows)


def build_other_energy_uses_csv(
    building_stock: pd.DataFrame,
    equipment_shares: pd.DataFrame,
    multi_province: bool = False,
) -> pd.DataFrame:
    """other_energy_uses.csv: non-HVAC/DHW loads by CZ + dwelling type.

    Sums lighting + cooking + dryer + appliances, split by electric/gas
    using equipment stock shares.
    """
    bs = building_stock.copy()
    if "building_type" in bs.columns:
        bs["dwelling_type"] = bs["building_type"]

    prov = _prov_cols(multi_province)

    def _get_share(config_id: str, climate_zone: str, building_type: str,
                   province: Optional[str] = None) -> float:
        mask = equipment_shares["equipment_config_id"] == config_id
        bt_col = "building_type" if "building_type" in equipment_shares.columns else None
        cz_col = "climate_zone" if "climate_zone" in equipment_shares.columns else None
        prov_col = "province" if "province" in equipment_shares.columns else None

        if prov_col and province and bt_col and cz_col:
            specific = mask & (equipment_shares[prov_col] == province) & (
                equipment_shares[cz_col] == climate_zone
            ) & (equipment_shares[bt_col] == building_type)
            if specific.any():
                return float(equipment_shares.loc[specific, "equipment_stock_share_pct"].iloc[0])

        if bt_col and cz_col:
            specific = mask & (equipment_shares[bt_col] == building_type) & (
                equipment_shares[cz_col] == climate_zone
            )
            if specific.any():
                return float(equipment_shares.loc[specific, "equipment_stock_share_pct"].iloc[0])
            bt_mask = mask & (equipment_shares[bt_col] == building_type)
            if bt_mask.any():
                return float(equipment_shares.loc[bt_mask, "equipment_stock_share_pct"].iloc[0])
        if bt_col:
            bt_mask = mask & (equipment_shares[bt_col] == building_type)
            if bt_mask.any():
                return float(equipment_shares.loc[bt_mask, "equipment_stock_share_pct"].iloc[0])
            all_mask = mask & (equipment_shares[bt_col] == "all")
            if all_mask.any():
                return float(equipment_shares.loc[all_mask, "equipment_stock_share_pct"].iloc[0])
        if mask.any():
            return float(equipment_shares.loc[mask, "equipment_stock_share_pct"].iloc[0])
        return 0.0

    load_cols = [
        "load_lighting_annual_kwh",
        "load_cooking_annual_kwh",
        "load_dryer_annual_kwh",
        "load_appliances_annual_kwh",
    ]

    def _weighted_mean_loads(g: pd.DataFrame) -> pd.Series:
        total_weight = g["building_genome_qty"].sum()
        if total_weight == 0:
            return pd.Series({col: 0.0 for col in load_cols})
        return pd.Series({
            col: (g[col] * g["building_genome_qty"]).sum() / total_weight
            for col in load_cols
        })

    group_keys = prov + ["climate_zone", "dwelling_type"]
    agg = (
        bs.groupby(group_keys)
        .apply(_weighted_mean_loads, include_groups=False)
        .reset_index()
    )

    rows = []
    for _, r in agg.iterrows():
        cz = r["climate_zone"]
        dt = r["dwelling_type"]
        province_val = r.get("province") if multi_province else None

        lighting_kwh = r["load_lighting_annual_kwh"]
        cooking_kwh = r["load_cooking_annual_kwh"]
        dryer_kwh = r["load_dryer_annual_kwh"]
        appliances_kwh = r["load_appliances_annual_kwh"]

        cooking_elec = _get_share("config_range_res_001", cz, dt, province_val)
        cooking_gas = _get_share("config_range_res_002", cz, dt, province_val)
        dryer_elec = _get_share("config_dryer_res_001", cz, dt, province_val)
        dryer_gas = _get_share("config_dryer_res_002", cz, dt, province_val)

        cooking_total = cooking_elec + cooking_gas
        if cooking_total > 0:
            cooking_elec /= cooking_total
            cooking_gas /= cooking_total

        dryer_total = dryer_elec + dryer_gas
        if dryer_total > 0:
            dryer_elec /= dryer_total
            dryer_gas /= dryer_total

        other_elec_kwh = (
            lighting_kwh
            + cooking_kwh * cooking_elec
            + dryer_kwh * dryer_elec
            + appliances_kwh
        )
        other_gas_kwh = (
            cooking_kwh * cooking_gas
            + dryer_kwh * dryer_gas
        )

        row = {
            "climate_zone": cz,
            "dwelling_type": dt,
            "other_electricity_annual": kwh_to_gj(other_elec_kwh),
            "other_natural_gas_annual": kwh_to_gj(other_gas_kwh),
        }
        if multi_province:
            row = {"province": province_val, **row}
        rows.append(row)

    return pd.DataFrame(rows)


def build_dhw_system_efficiency_csv(
    dhw_specs: pd.DataFrame,
    dhw_name_map: Dict[str, str],
    fuel_name_map: Dict[str, str],
    multi_province: bool = False,
    provinces: Optional[List[str]] = None,
) -> pd.DataFrame:
    """dhw_system_efficiency.csv: DHW efficiency and fuel proportions per system.

    No climate zone dimension. Single-fuel per DHW type.
    """
    base_rows: List[Dict] = []
    for _, spec_row in dhw_specs.iterrows():
        config_id = spec_row["equipment_config_id"]
        if config_id not in dhw_name_map:
            continue

        ew_name = dhw_name_map[config_id]
        fuel_dspm = spec_row["equipment_energy_source"]
        fuel_ew = map_fuel_name(fuel_dspm, fuel_name_map)
        cop = float(spec_row["cop"])

        row: Dict = {"dhw_system": ew_name}
        for f in EW_FUELS:
            row[f"dhw_system_proportion_{f}"] = 1.0 if f == fuel_ew else 0.0
        for f in EW_FUELS:
            row[f"dhw_system_efficiency_{f}"] = cop if f == fuel_ew else 0.0
        base_rows.append(row)

    if not multi_province or not provinces:
        return pd.DataFrame(base_rows)

    # Cross-product with provinces
    rows = []
    for prov in provinces:
        for r in base_rows:
            rows.append({"province": prov, **r})
    return pd.DataFrame(rows)


def build_dhw_loads_csv(
    building_stock: pd.DataFrame,
    multi_province: bool = False,
) -> pd.DataFrame:
    """dhw_loads.csv: pop-weighted DHW load by dwelling type (GJ)."""
    bs = building_stock.copy()
    if "building_type" in bs.columns:
        bs["dwelling_type"] = bs["building_type"]

    prov = _prov_cols(multi_province)
    group_keys = prov + ["dwelling_type"]

    def _weighted_mean_dhw(g: pd.DataFrame) -> float:
        total_weight = g["building_genome_qty"].sum()
        if total_weight == 0:
            return 0.0
        return (g["load_dhw_annual_kwh"] * g["building_genome_qty"]).sum() / total_weight

    avg_dhw = (
        bs.groupby(group_keys)
        .apply(_weighted_mean_dhw, include_groups=False)
        .reset_index(name="avg_dhw_kwh")
    )

    result = avg_dhw[group_keys].copy()
    result["dhw_load_annual"] = avg_dhw["avg_dhw_kwh"].apply(kwh_to_gj)
    return result


def build_dhw_costs_csv(
    equipment_cat: pd.DataFrame,
    dhw_name_map: Dict[str, str],
    multi_province: bool = False,
    provinces: Optional[List[str]] = None,
) -> pd.DataFrame:
    """dhw_costs.csv: DHW equipment cost, life, and maintenance per system."""
    dhw_ids = set(dhw_name_map.keys())
    df = equipment_cat[equipment_cat["equipment_config_id"].isin(dhw_ids)].copy()

    if len(df) > 0:
        df["dhw_system"] = df["equipment_config_id"].map(dhw_name_map)
        cost_cols = {"cost_equipment": "mean", "equipment_eul": "mean"}
        grouped = df.groupby("dhw_system", sort=True).agg(cost_cols).reset_index()
        base_rows = [
            {
                "dhw_system": r["dhw_system"],
                "dhw_equipment_cost": r["cost_equipment"],
                "dhw_assumed_life": r["equipment_eul"],
                "dhw_maintenance_cost_annual": 150,  # PLACEHOLDER
            }
            for _, r in grouped.iterrows()
        ]
    else:
        # Fallback: all DHW systems with placeholder costs
        base_rows = [
            {
                "dhw_system": ew_name,
                "dhw_equipment_cost": 1950,  # PLACEHOLDER
                "dhw_assumed_life": 15,  # PLACEHOLDER
                "dhw_maintenance_cost_annual": 150,  # PLACEHOLDER
            }
            for ew_name in sorted(set(dhw_name_map.values()))
        ]

    if not multi_province or not provinces:
        return pd.DataFrame(base_rows)

    rows = []
    for prov in provinces:
        for r in base_rows:
            rows.append({"province": prov, **r})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def build_all(
    building_stock: pd.DataFrame,
    equipment_shares: pd.DataFrame,
    envelope_agg: pd.DataFrame,
    hvac_specs: pd.DataFrame,
    dhw_specs: pd.DataFrame,
    equipment_cat: pd.DataFrame,
    efficiencies: pd.DataFrame,
    fuel_props: pd.DataFrame,
    hvac_name_map: Dict[str, str],
    dhw_name_map: Dict[str, str],
    fuel_name_map: Dict[str, str],
    building_types: List[str],
    multi_province: bool = False,
) -> Tuple[Dict[str, pd.DataFrame], Dict[str, pd.DataFrame]]:
    """Build all output files.

    Returns (archetypes, input_parameters) as dicts of {filename_stem: DataFrame}.
    """
    provinces = (
        sorted(building_stock["province"].unique()) if multi_province else None
    )

    archetypes = {
        "climate_zone": build_climate_zone_csv(building_stock, multi_province),
        "dwelling_type": build_dwelling_type_csv(building_stock, multi_province),
        "hvac_system": build_hvac_system_csv(
            equipment_shares, hvac_name_map, multi_province,
        ),
        "dhw_system": build_dhw_system_csv(
            equipment_shares, dhw_name_map, multi_province,
        ),
        "envelope_tier": build_envelope_tier_csv(envelope_agg, multi_province),
    }

    params = {
        "heating_loads": build_heating_loads_csv(envelope_agg, multi_province),
        "cooling_loads": build_cooling_loads_csv(envelope_agg, multi_province),
        "heating_system_efficiency": build_heating_system_efficiency_csv(
            efficiencies, fuel_props, hvac_name_map, hvac_specs, fuel_name_map,
            multi_province,
        ),
        "hvac_costs": build_hvac_costs_csv(
            equipment_cat, hvac_name_map, building_types, multi_province, provinces,
        ),
        "other_energy_uses": build_other_energy_uses_csv(
            building_stock, equipment_shares, multi_province,
        ),
        "dhw_system_efficiency": build_dhw_system_efficiency_csv(
            dhw_specs, dhw_name_map, fuel_name_map, multi_province, provinces,
        ),
        "dhw_loads": build_dhw_loads_csv(building_stock, multi_province),
        "dhw_costs": build_dhw_costs_csv(
            equipment_cat, dhw_name_map, multi_province, provinces,
        ),
    }

    for name, df in archetypes.items():
        logger.info("Archetype %s: %d rows", name, len(df))
    for name, df in params.items():
        logger.info("Param %s: %d rows x %d cols", name, len(df), len(df.columns))

    return archetypes, params
