# Energy Wallet Input Files - Data Dictionary

Generated from: **Canada Reference** library, province **ON**
Generated on: 2026-04-04

This document traces each output column back to its DSPM source file and column for auditability.

## Archetype Files

### climate_zone.csv
*Proportion of households by climate zone*

| Column | Source File | Source Column(s) | Notes |
|--------|-----------|-----------------|-------|
| climate_zone | building_stock_library.csv | climate_zone | Mapped to EW naming (e.g., CZ_5) |
| population_share | building_stock_library.csv | building_genome_qty | Proportion of total provincial building stock |

### dwelling_type.csv
*Dwelling type shares within each climate zone*

| Column | Source File | Source Column(s) | Notes |
|--------|-----------|-----------------|-------|
| climate_zone | building_stock_library.csv | climate_zone |  |
| dwelling_type | building_stock_library.csv | building_type | Renamed: building_type -> dwelling_type |
| population_share | building_stock_library.csv | building_genome_qty | Sums to 1.0 within each climate_zone |

### hvac_system.csv
*HVAC system shares by climate zone and dwelling type*

| Column | Source File | Source Column(s) | Notes |
|--------|-----------|-----------------|-------|
| climate_zone | equipment_shares_base_year.csv | climate_zone |  |
| dwelling_type | equipment_shares_base_year.csv | building_type | Renamed: building_type -> dwelling_type |
| hvac_system | hvac_specs.csv | equipment_config_id | Mapped to EW name via auto-derived name map |
| population_share | equipment_shares_base_year.csv | equipment_stock_share_pct | Normalized to sum to 1.0 within each (climate_zone, dwelling_type) |

### dhw_system.csv
*DHW system shares by climate zone and dwelling type*

| Column | Source File | Source Column(s) | Notes |
|--------|-----------|-----------------|-------|
| climate_zone | equipment_shares_base_year.csv | climate_zone |  |
| dwelling_type | equipment_shares_base_year.csv | building_type | Renamed: building_type -> dwelling_type |
| dhw_system | dhw_specs.csv | equipment_config_id | Mapped to EW name via auto-derived name map |
| population_share | equipment_shares_base_year.csv | equipment_stock_share_pct | Normalized to sum to 1.0 within each (climate_zone, dwelling_type) |

### envelope_tier.csv
*Envelope quality tier shares by CZ and dwelling type*

| Column | Source File | Source Column(s) | Notes |
|--------|-----------|-----------------|-------|
| climate_zone | building_stock_library.csv | climate_zone |  |
| dwelling_type | building_stock_library.csv | building_type | Renamed: building_type -> dwelling_type |
| envelope_tier | building_stock_library.csv | building_envelope_bin | Aggregated: bins grouped into poor/average/good tiers |
| population_share | building_stock_library.csv | building_genome_qty | Sums to 1.0 within each (climate_zone, dwelling_type) |

## Input Parameter Files

### heating_loads.csv
*Annual heating load by CZ, dwelling type, and envelope tier*

| Column | Source File | Source Column(s) | Notes |
|--------|-----------|-----------------|-------|
| climate_zone | building_stock_library.csv | climate_zone |  |
| dwelling_type | building_stock_library.csv | building_type |  |
| envelope_tier | building_stock_library.csv | building_envelope_bin | Aggregated into tiers |
| heating_load_annual | building_stock_library.csv | load_heating_annual_kwh | Population-weighted average, converted kWh -> GJ |

### cooling_loads.csv
*Annual cooling load by CZ, dwelling type, and envelope tier*

| Column | Source File | Source Column(s) | Notes |
|--------|-----------|-----------------|-------|
| climate_zone | building_stock_library.csv | climate_zone |  |
| dwelling_type | building_stock_library.csv | building_type |  |
| envelope_tier | building_stock_library.csv | building_envelope_bin | Aggregated into tiers |
| cooling_load_annual | building_stock_library.csv | load_cooling_annual_kwh | Population-weighted average, converted kWh -> GJ |

### heating_system_efficiency.csv
*HVAC heating/cooling efficiency and fuel proportions by climate zone*

| Column | Source File | Source Column(s) | Notes |
|--------|-----------|-----------------|-------|
| climate_zone | building_stock_library.csv + design_temperatures.csv | climate_zone, design_temp_heat | COP curve weighted by degree-day temperature profile per CZ |
| hvac_system | hvac_specs.csv | equipment_config_id | Mapped to EW name |
| heating_system_proportion_{fuel} | hvac_specs.csv | equipment_primary_energy_source, equipment_secondary_energy_source, heating_cap_*_primary, heating_cap_*_secondary | Degree-day-weighted capacity split across 5 EW fuels; dual-fuel systems vary by CZ due to temperature-dependent switchover |
| heating_system_efficiency_{fuel} | hvac_specs.csv | heating_cop_*_primary, heating_cop_*_secondary | Degree-day-weighted COP per fuel; assigned to primary or secondary system |
| cooling_system_efficiency | hvac_specs.csv | cooling_cop_*_primary, cooling_cap_*_primary | Capacity-weighted average cooling COP; 1.0 if no cooling |

### hvac_costs.csv
*HVAC equipment costs by dwelling type and system*

| Column | Source File | Source Column(s) | Notes |
|--------|-----------|-----------------|-------|
| dwelling_type | n/a | n/a | Cross-product of all dwelling types |
| hvac_system | equipment_categorization.csv | equipment_config_id | Mapped to EW name |
| hvac_equipment_cost | equipment_categorization.csv | cost_equipment |  |
| hvac_assumed_life | equipment_categorization.csv | equipment_eul |  |
| hvac_maintenance_cost_annual | n/a | n/a | PLACEHOLDER: $120/year |

### other_energy_uses.csv
*Non-HVAC/DHW energy loads by climate zone and dwelling type*

| Column | Source File | Source Column(s) | Notes |
|--------|-----------|-----------------|-------|
| climate_zone | building_stock_library.csv | climate_zone |  |
| dwelling_type | building_stock_library.csv | building_type |  |
| other_electricity_annual | building_stock_library.csv | load_lighting_annual_kwh, load_cooking_annual_kwh, load_dryer_annual_kwh, load_appliances_annual_kwh | Pop-weighted sum of electric portion; cooking/dryer split by equipment_shares_base_year.csv shares; converted kWh -> GJ |
| other_natural_gas_annual | building_stock_library.csv | load_cooking_annual_kwh, load_dryer_annual_kwh | Pop-weighted sum of gas portion; split by equipment_shares_base_year.csv shares; converted kWh -> GJ |

### dhw_system_efficiency.csv
*DHW efficiency and fuel proportions per system*

| Column | Source File | Source Column(s) | Notes |
|--------|-----------|-----------------|-------|
| dhw_system | dhw_specs.csv | equipment_config_id | Mapped to EW name |
| dhw_system_proportion_{fuel} | dhw_specs.csv | equipment_energy_source | Single-fuel: 1.0 for the system's fuel, 0.0 for others |
| dhw_system_efficiency_{fuel} | dhw_specs.csv | cop | COP assigned to the system's fuel; 0.0 for others |

### dhw_loads.csv
*Annual DHW load by dwelling type*

| Column | Source File | Source Column(s) | Notes |
|--------|-----------|-----------------|-------|
| dwelling_type | building_stock_library.csv | building_type |  |
| dhw_load_annual | building_stock_library.csv | load_dhw_annual_kwh | Population-weighted average, converted kWh -> GJ |

### dhw_costs.csv
*DHW equipment costs per system*

| Column | Source File | Source Column(s) | Notes |
|--------|-----------|-----------------|-------|
| dhw_system | equipment_categorization.csv | equipment_config_id | Mapped to EW name |
| dhw_equipment_cost | equipment_categorization.csv | cost_equipment | Falls back to PLACEHOLDER $1950 if not in equipment_categorization |
| dhw_assumed_life | equipment_categorization.csv | equipment_eul | Falls back to PLACEHOLDER 15 years if not in equipment_categorization |
| dhw_maintenance_cost_annual | n/a | n/a | PLACEHOLDER: $150/year |

## Placeholder Values

The following values are placeholders and should be reviewed:

| File | Column | Value | Notes |
|------|--------|-------|-------|
| hvac_costs.csv | hvac_maintenance_cost_annual | $120/yr | Needs data source |
| dhw_costs.csv | dhw_maintenance_cost_annual | $150/yr | Needs data source |
| dhw_costs.csv | dhw_equipment_cost | $1950 | Fallback if not in equipment_categorization |
| dhw_costs.csv | dhw_assumed_life | 15 yr | Fallback if not in equipment_categorization |
