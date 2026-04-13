"""Registry for required Step 3 input parameter names.

This module centralizes the required parameter definitions from Model Architecture.md
(section 3.3). After Phase 3B multi-lookup expansion, vehicle parameters carry slot
numbers (N=1,2) and all technology-type parameters carry _base/_alt suffixes.

Validation code can import this list to enforce coverage and uniqueness.
"""

from __future__ import annotations


def _per_slot_vehicle_params() -> tuple[str, ...]:
    """Vehicle parameters expanded per slot (N=1,2) and suffix (base,alt)."""
    templates = (
        "vehicle_{N}_purchase_cost_{s}",
        "vehicle_{N}_assumed_life_{s}",
        "vehicle_{N}_maintenance_cost_per_km_{s}",
        "vehicle_{N}_efficiency_gas_{s}",
        "vehicle_{N}_efficiency_electric_{s}",
        "ev_{N}_efficiency_factor_{s}",
        "ev_{N}_pct_charged_home_{s}",
        "ev_{N}_pct_charged_level2_{s}",
        "ev_{N}_pct_charged_fast_{s}",
    )
    params: list[str] = []
    for n in (1, 2):
        for s in ("base", "alt"):
            for t in templates:
                params.append(t.replace("{N}", str(n)).replace("{s}", s))
    return tuple(params)


def _per_slot_vkt_params() -> tuple[str, ...]:
    """VKT context parameters (directly in CSV with slot + suffix)."""
    params: list[str] = []
    for n in (1, 2):
        for s in ("base", "alt"):
            params.append(f"vkt_{n}_annual_{s}")
    return tuple(params)


def _hvac_params() -> tuple[str, ...]:
    """HVAC parameters with _base/_alt suffix (from multi-lookup on heating_system)."""
    templates = (
        "hvac_equipment_cost_{s}",
        "hvac_assumed_life_{s}",
        "hvac_maintenance_cost_annual_{s}",
        "heating_system_proportion_gas_{s}",
        "heating_system_proportion_electric_{s}",
        "heating_system_proportion_oil_{s}",
        "heating_system_proportion_propane_{s}",
        "heating_system_proportion_wood_{s}",
        "heating_system_efficiency_gas_{s}",
        "heating_system_efficiency_electric_{s}",
        "heating_system_efficiency_oil_{s}",
        "heating_system_efficiency_propane_{s}",
        "heating_system_efficiency_wood_{s}",
        "cooling_system_efficiency_{s}",
    )
    params: list[str] = []
    for s in ("base", "alt"):
        for t in templates:
            params.append(t.replace("{s}", s))
    return tuple(params)


def _heating_cooling_load_params() -> tuple[str, ...]:
    """Heating/cooling load context parameters (directly in CSV)."""
    return (
        "heating_load_annual_base",
        "heating_load_annual_alt",
        "cooling_load_annual_base",
        "cooling_load_annual_alt",
    )


def _dhw_params() -> tuple[str, ...]:
    """DHW parameters with _base/_alt suffix (context params)."""
    templates = (
        "dhw_equipment_cost_{s}",
        "dhw_assumed_life_{s}",
        "dhw_maintenance_cost_annual_{s}",
        "dhw_load_annual_{s}",
        "dhw_system_proportion_gas_{s}",
        "dhw_system_proportion_electric_{s}",
        "dhw_system_proportion_oil_{s}",
        "dhw_system_proportion_propane_{s}",
        "dhw_system_proportion_wood_{s}",
        "dhw_system_efficiency_gas_{s}",
        "dhw_system_efficiency_electric_{s}",
        "dhw_system_efficiency_oil_{s}",
        "dhw_system_efficiency_propane_{s}",
        "dhw_system_efficiency_wood_{s}",
    )
    params: list[str] = []
    for s in ("base", "alt"):
        for t in templates:
            params.append(t.replace("{s}", s))
    return tuple(params)


def _other_params() -> tuple[str, ...]:
    """Other energy use context parameters (directly in CSV)."""
    return (
        "other_electricity_annual_base",
        "other_electricity_annual_alt",
        "other_natural_gas_annual_base",
        "other_natural_gas_annual_alt",
    )


def _panel_params() -> tuple[str, ...]:
    """Panel upgrade context parameters (directly in CSV)."""
    return (
        "panel_upgrade_cost_base",
        "panel_upgrade_cost_alt",
        "panel_assumed_life_base",
        "panel_assumed_life_alt",
    )


# Shared parameters (no _base/_alt suffix)
_SHARED_PARAMETERS: tuple[str, ...] = (
    "cost_electricity_home",
    "cost_natural_gas_home",
    "cost_oil_home",
    "cost_propane_home",
    "cost_wood_home",
    "cost_gasoline",
    "cost_electricity_level2",
    "cost_electricity_fast",
    "discount_rate",
    "electricity_fixed_charge_monthly",
    "natural_gas_fixed_charge_monthly",
)


REQUIRED_INPUT_PARAMETERS: tuple[str, ...] = (
    _SHARED_PARAMETERS
    + _per_slot_vehicle_params()
    + _per_slot_vkt_params()
    + _hvac_params()
    + _heating_cooling_load_params()
    + _dhw_params()
    + _other_params()
    + _panel_params()
)
