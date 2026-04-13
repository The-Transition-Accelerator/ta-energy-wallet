<!-- AUTO-GENERATED from datapackage.yaml and .meta.yaml files. Do not edit directly. -->

# Ontario Household Energy Affordability

A proof-of-concept Energy Wallet data library representing Ontario households. Model inputs are based on a combination of the Transition Accelerator's Demand-Side Pathways Model (DSPM) Canada Reference Data Library, which is primarily based on NRCan's Comprehensive Energy Use Database (CEUD) for base year 2021, and other Ontario-specific data sources from a previously conducted energy wallet analysis for a utility in Ontario. The data library covers 3 climate zones, 4 dwelling types, 5 income quintiles, 23 HVAC system configurations, and 3 projection years (2025-2035). It evaluates a full electrification scenario: all baseline heating systems transition to cold-climate ASHP with electric backup, DHW to 80% electric resistance / 20% HPWH, and all ICE vehicles to EV.

| | |
|---|---|
| **Geography** | Ontario, Canada |
| **Climate Zones** | CZ_5, CZ_6, CZ_7A |
| **Projection Years** | 2025, 2030, 2035 |
| **Currency** | 2025 CAD |
| **Version** | 0.1.0 |

## Sources

- **DSPM Canada Reference Library** — Calibrated building stock model for Ontario (heating/cooling loads, HVAC system shares, building envelopes)
- **TA Energy Wallet Analysis — Ontario Utility** — Equipment costs, efficiencies, vehicle parameters, and charging splits from a previously conducted energy wallet analysis
- **Canada Energy Regulator — Canada's Energy Future 2026** — Residential and transportation energy prices (electricity, natural gas, oil, gasoline)
- **CEUD** — Comprehensive Energy Use Database — DHW loads, vehicle kilometres travelled, appliance energy
- **Statistics Canada** — Vehicle type distributions (SHS PUMF 2019) and EV registration shares (Table 23-10-0308-01)

---

## Demographics & Housing Stock

| Question | File | Source |
|----------|------|--------|
| What climate zones are covered? | [`archetypes/climate_zone.csv`](archetypes/climate_zone.csv) | DSPM Canada Reference Library |
| What types of homes are modeled? | [`archetypes/dwelling_type.csv`](archetypes/dwelling_type.csv) | DSPM Canada Reference Library |
| How energy-efficient are the building envelopes? | [`archetypes/envelope_tier.csv`](archetypes/envelope_tier.csv) | DSPM Canada Reference Library |
| How are households distributed by income? | [`archetypes/income_quintile.csv`](archetypes/income_quintile.csv) | By definition |

## Space Heating & Cooling

| Question | File | Source |
|----------|------|--------|
| Who heats with what system? | [`archetypes/hvac_system.csv`](archetypes/hvac_system.csv) | DSPM Canada Reference Library |
| What if households switch to heat pumps? | [`alternative_configurations/alt_hvac_system.csv`](alternative_configurations/alt_hvac_system.csv) | User-defined scenario |
| How much heating energy is needed? | [`input_parameters/heating_loads.csv`](input_parameters/heating_loads.csv) | DSPM Canada Reference Library |
| How much cooling energy is needed? | [`input_parameters/cooling_loads.csv`](input_parameters/cooling_loads.csv) | DSPM Canada Reference Library |
| How efficient is each heating/cooling system? | [`input_parameters/heating_system_efficiency.csv`](input_parameters/heating_system_efficiency.csv) | DSPM Canada Reference Library |
| What does HVAC equipment cost? | [`input_parameters/hvac_costs.csv`](input_parameters/hvac_costs.csv) | TA Energy Wallet Analysis — Ontario Utility |

## Hot Water

| Question | File | Source |
|----------|------|--------|
| Who has what hot water system? | [`archetypes/dhw_system.csv`](archetypes/dhw_system.csv) | DSPM Canada Reference Library |
| What if households switch to electric water heating? | [`alternative_configurations/alt_dhw_system.csv`](alternative_configurations/alt_dhw_system.csv) | User-defined scenario |
| How much hot water energy is needed? | [`input_parameters/dhw_loads.csv`](input_parameters/dhw_loads.csv) | CEUD — Residential Sector — Ontario |
| What does hot water equipment cost? | [`input_parameters/dhw_costs.csv`](input_parameters/dhw_costs.csv) | TA Energy Wallet Analysis — Ontario Utility |
| How efficient is each hot water system? | [`input_parameters/dhw_system_efficiency.csv`](input_parameters/dhw_system_efficiency.csv) | TA Energy Wallet Analysis — Ontario Utility |

## Vehicles

| Question | File | Source |
|----------|------|--------|
| What type of vehicle do households drive? | [`archetypes/vehicle_1_type.csv`](archetypes/vehicle_1_type.csv) | Statistics Canada |
| What share of vehicles are electric vs. ICE? | [`archetypes/vehicle_1_category.csv`](archetypes/vehicle_1_category.csv) | Statistics Canada |
| Do households have a second vehicle? | [`archetypes/vehicle_2_type.csv`](archetypes/vehicle_2_type.csv) | N/A |
| What powertrain does the second vehicle have? | [`archetypes/vehicle_2_category.csv`](archetypes/vehicle_2_category.csv) | N/A |
| Which households can charge an EV at home? | [`archetypes/has_home_charging.csv`](archetypes/has_home_charging.csv) | Pollution Probe & Electric Mobility Canada; Dunsky Energy + Climate Advisors |
| What if all ICE vehicles switch to EVs? | [`alternative_configurations/alt_vehicle_1_category.csv`](alternative_configurations/alt_vehicle_1_category.csv) | User-defined scenario |
| What do vehicles cost to buy and maintain? | [`input_parameters/vehicle_costs.csv`](input_parameters/vehicle_costs.csv) | TA Energy Wallet Analysis — Ontario Utility |
| How fuel-efficient are vehicles? | [`input_parameters/vehicle_efficiency.csv`](input_parameters/vehicle_efficiency.csv) | TA Energy Wallet Analysis — Ontario Utility |
| How far do people drive? | [`input_parameters/vehicle_km_traveled.csv`](input_parameters/vehicle_km_traveled.csv) | CEUD — Transportation — Ontario |
| Where do EV owners charge? | [`input_parameters/vehicle_charging.csv`](input_parameters/vehicle_charging.csv) | TA Energy Wallet Analysis — Ontario Utility |

## Energy Prices & Financial

| Question | File | Source |
|----------|------|--------|
| What are the home energy prices? | [`input_parameters/costs_home_energy.csv`](input_parameters/costs_home_energy.csv) | Canada Energy Regulator — Canada's Energy Future 2026 |
| What do gasoline and EV charging cost? | [`input_parameters/costs_vehicle_energy.csv`](input_parameters/costs_vehicle_energy.csv) | Canada Energy Regulator — Canada's Energy Future 2026 |
| What discount rate is used for capital cost annualization? | [`input_parameters/discount_rate.csv`](input_parameters/discount_rate.csv) | Assumption |

## Other Residential Energy

| Question | File | Source |
|----------|------|--------|
| How much energy is used for appliances, lighting, etc.? | [`input_parameters/other_energy_uses.csv`](input_parameters/other_energy_uses.csv) | DSPM Canada Reference Library |

## Electrical Panel

| Question | File | Source |
|----------|------|--------|
| When is a panel upgrade needed and what does it cost? | [`input_parameters/panel_upgrade_triggers_and_costs.csv`](input_parameters/panel_upgrade_triggers_and_costs.csv) | User assumption |

---

## Reference Tables

| Question | File | Source |
|----------|------|--------|
| How are HVAC systems classified for output grouping? | [`reference/hvac_system_groups.csv`](reference/hvac_system_groups.csv) | Analyst-defined |

---

## Known Limitations

- **`archetypes/vehicle_2_type.csv`** — Second vehicle set to 100% none. The energy wallet definition currently only includes the first primary vehicle.
- **`archetypes/has_home_charging.csv`** — Data quality for home charging access rates is limited. Opportunities for improving this input with better data should be evaluated in future updates.
- **`input_parameters/hvac_costs.csv`** — Condensing and non-condensing gas furnace costs are identical; the source data does not distinguish them.
- **`input_parameters/vehicle_charging.csv`** — Charging behaviour figures are based on limited data that varies widely across studies and jurisdictions.
- **`input_parameters/panel_upgrade_triggers_and_costs.csv`** — Panel upgrade trigger logic (HP + EV) should be reviewed in future iterations.
