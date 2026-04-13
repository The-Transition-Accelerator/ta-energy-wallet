<!-- AUTO-GENERATED from .meta.yaml files. Do not edit directly. -->

# Input Parameters

## Annual Heating Loads

`heating_loads.csv`

Total annual space heating energy demand by climate zone, dwelling type, and envelope performance tier. Values represent thermal energy output required (delivered heat), not metered input energy.

**Source:** DSPM Canada Reference Library — Calibrated to CEUD data with climate zone adjustments based on heating degree days.

**Keys:** `climate_zone`, `dwelling_type`, `envelope_tier`

| Column | Description | Unit | Type |
|--------|-------------|------|------|
| `climate_zone` | Climate zone identifier | — | categorical: CZ_5, CZ_6, CZ_7A |
| `dwelling_type` | Dwelling type category | — | categorical: sfd, row, apt, mob |
| `envelope_tier` | Building envelope performance tier | — | categorical: poor, average, good |
| `heating_load_annual` | Total annual space heating load delivered to the home | GJ/year | numeric (5–140) |

> Loads are not year-varying; the same values apply across all projection years.

---

## Annual Cooling Loads

`cooling_loads.csv`

Total annual space cooling energy demand by climate zone, dwelling type, and envelope performance tier. Values represent thermal energy that must be removed from the home, not metered input energy.

**Source:** DSPM Canada Reference Library — Calibrated to CEUD data with climate zone adjustments based on cooling degree days.

**Keys:** `climate_zone`, `dwelling_type`, `envelope_tier`

| Column | Description | Unit | Type |
|--------|-------------|------|------|
| `climate_zone` | Climate zone identifier | — | categorical: CZ_5, CZ_6, CZ_7A |
| `dwelling_type` | Dwelling type category | — | categorical: sfd, row, apt, mob |
| `envelope_tier` | Building envelope performance tier | — | categorical: poor, average, good |
| `cooling_load_annual` | Total annual space cooling load for the home | GJ/year | numeric (5–26) |

> Loads are not year-varying; the same values apply across all projection years.

---

## Heating & Cooling System Efficiency

`heating_system_efficiency.csv`

Heating and cooling system efficiencies by HVAC system type and climate zone. Includes fuel proportion vectors (share of heating load met by each fuel) and seasonal efficiency values for each fuel. Heat pump seasonal COPs vary by climate zone to reflect cold-weather performance derating.

**Source:** DSPM Canada Reference Library — COP curves collapsed to annual-average efficiency per climate zone.

**Keys:** `climate_zone`, `hvac_system`

| Column | Description | Unit | Type |
|--------|-------------|------|------|
| `climate_zone` | Climate zone identifier | — | categorical: CZ_5, CZ_6, CZ_7A |
| `hvac_system` | HVAC system configuration name | — | categorical: 23 system types |
| `heating_system_proportion_gas` | Share of heating load met by natural gas | decimal | numeric (0–1) |
| `heating_system_proportion_electric` | Share of heating load met by electricity | decimal | numeric (0–1) |
| `heating_system_proportion_oil` | Share of heating load met by fuel oil | decimal | numeric (0–1) |
| `heating_system_proportion_propane` | Share of heating load met by propane | decimal | numeric (0–1) |
| `heating_system_proportion_wood` | Share of heating load met by wood | decimal | numeric (0–1) |
| `heating_system_efficiency_gas` | Seasonal efficiency for gas heating (AFUE or equivalent) | dimensionless | numeric (0–5) |
| `heating_system_efficiency_electric` | Seasonal efficiency for electric heating (COP or resistance=1.0) | dimensionless | numeric (0–5) |
| `heating_system_efficiency_oil` | Seasonal efficiency for oil heating (AFUE or equivalent) | dimensionless | numeric (0–5) |
| `heating_system_efficiency_propane` | Seasonal efficiency for propane heating (AFUE or equivalent) | dimensionless | numeric (0–5) |
| `heating_system_efficiency_wood` | Seasonal efficiency for wood heating | dimensionless | numeric (0–5) |
| `cooling_system_efficiency` | Seasonal cooling efficiency (SEER-equivalent COP) | dimensionless | numeric (0–10) |

> Heat pump efficiencies represent whole-system annual-average COP, not compressor-only sCOP. This means backup system efficiency (e.g., electric resistance) is factored in, resulting in lower values than compressor-only ratings.

---

## HVAC Equipment Costs

`hvac_costs.csv`

Installed equipment costs, expected useful life, and annual maintenance costs for HVAC systems by dwelling type. Costs are averaged across climate zones and conditioning loads (envelope tiers) from the source data. For combined systems (heat pump + backup furnace), costs are derived using component addition: HP_unit_cost + backup_furnace_cost, validated against known bundled prices.

**Source:** TA Energy Wallet Analysis — Ontario Utility — OSM (Ontario Savings Model) equipment cost outputs, 2025 no-rebate values. EULs from Table 15 (furnace operating efficiency and EUL) and Table 16 (heat pump sCOP and EUL).

**Keys:** `dwelling_type`, `hvac_system`

| Column | Description | Unit | Type |
|--------|-------------|------|------|
| `dwelling_type` | Dwelling type category | — | categorical: sfd, row, apt, mob |
| `hvac_system` | HVAC system configuration name | — | categorical: 23 system types |
| `hvac_equipment_cost` | Installed equipment cost (no rebate) | $ | numeric (2800–36100) |
| `hvac_assumed_life` | Expected useful life | years | numeric (15–30) |
| `hvac_maintenance_cost_annual` | Annual maintenance cost | $/year | numeric (0–550) |

> Condensing and non-condensing gas furnace costs are identical in this version; the source data does not distinguish them. Flag for future update.

> Costs vary by dwelling type (sfd generally higher due to larger system sizing).

> HP with oil/propane/wood backup costs are derived via component addition, validated by exactly reproducing known HP w gas backup costs.

> Electric baseboard (wo AC) has 30-year EUL per Table 15. GSHP has 25-year EUL per Table 16; all other systems use 15 years.

---

## Annual DHW Loads

`dhw_loads.csv`

Annual domestic hot water energy requirements by dwelling type, reflecting differences in average occupancy and dwelling size.

**Source:** CEUD — Residential Sector — Ontario — Tables 35, 37, and 39.

**Keys:** `dwelling_type`

| Column | Description | Unit | Type |
|--------|-------------|------|------|
| `dwelling_type` | Dwelling type category | — | categorical: sfd, row, apt, mob |
| `dhw_load_annual` | Total annual domestic hot water energy demand | GJ/year | numeric (13–18) |

> Loads are not year-varying; the same values apply across all projection years.

---

## DHW Equipment Costs

`dhw_costs.csv`

Equipment purchase costs, expected useful life, and annual maintenance costs by DHW system type. All systems assume a standard residential storage tank.

**Source:** TA Energy Wallet Analysis — Ontario Utility — Baseline and upgrade DHW equipment cost tables from the Ontario Savings Model.

**Keys:** `dhw_system`

| Column | Description | Unit | Type |
|--------|-------------|------|------|
| `dhw_system` | Domestic hot water system type | — | categorical: HPWH, electric resistance, gas, oil, propane, wood |
| `dhw_equipment_cost` | Installed equipment cost | $ | numeric (1250–4500) |
| `dhw_assumed_life` | Expected useful life | years | numeric (15–15) |
| `dhw_maintenance_cost_annual` | Annual maintenance cost | $/year | numeric (125–200) |

> All systems have 15-year EUL per TA Energy Wallet Analysis — Ontario Utility.

> HPWH has lower maintenance ($125) than storage tank systems ($150-$200) despite higher equipment cost.

---

## DHW System Efficiency

`dhw_system_efficiency.csv`

DHW system fuel proportions and efficiencies by system type. Defines which fuel each system uses and its operating efficiency. Each system has a single primary fuel with proportion = 1.0 and all others = 0.0.

**Source:** TA Energy Wallet Analysis — Ontario Utility — DHW system fuel proportions and efficiencies.

**Keys:** `dhw_system`

| Column | Description | Unit | Type |
|--------|-------------|------|------|
| `dhw_system` | Domestic hot water system type | — | categorical: HPWH, electric resistance, gas, oil, propane, wood |
| `dhw_system_proportion_gas` | Share of DHW load met by natural gas | decimal | numeric (0–1) |
| `dhw_system_proportion_electric` | Share of DHW load met by electricity | decimal | numeric (0–1) |
| `dhw_system_proportion_oil` | Share of DHW load met by fuel oil | decimal | numeric (0–1) |
| `dhw_system_proportion_propane` | Share of DHW load met by propane | decimal | numeric (0–1) |
| `dhw_system_proportion_wood` | Share of DHW load met by wood | decimal | numeric (0–1) |
| `dhw_system_efficiency_gas` | Gas DHW system efficiency | dimensionless | numeric (0–5) |
| `dhw_system_efficiency_electric` | Electric DHW system efficiency (COP or resistance=1.0) | dimensionless | numeric (0–5) |
| `dhw_system_efficiency_oil` | Oil DHW system efficiency | dimensionless | numeric (0–5) |
| `dhw_system_efficiency_propane` | Propane DHW system efficiency | dimensionless | numeric (0–5) |
| `dhw_system_efficiency_wood` | Wood DHW system efficiency | dimensionless | numeric (0–5) |

---

## Vehicle Purchase & Maintenance Costs

`vehicle_costs.csv`

Vehicle purchase costs by type (car, SUV, truck), powertrain (ICE, EV), and year. Representative vehicles were selected from the most popular models sold in Canada in 2024, choosing the most affordable option within each class. Costs are based on MSRP plus Ontario-specific fees and levies (~$2,900 on average) and 13% HST. ICE costs are held constant across years. BEV future costs (2030, 2035) are estimated relative to ICE costs using federal ZEV regulatory analysis projections. By 2035, electric cars are projected to be 4% cheaper than ICE cars, while BEV trucks are expected to be 1.5% more expensive. Vehicle assumed life is 12 years.

**Source:** TA Energy Wallet Analysis — Ontario Utility — Vehicle MSRP from manufacturer websites for 2025 model year. Ontario-specific fees (AC excise tax, dealer administration fee, tire levy, PPSA, delivery and destination charges) sourced from local dealerships. BEV cost projections from Canada Gazette, Part II, Vol. 157, No. 26, December 20, 2023, Government of Canada (page 4023).

**Keys:** `year`, `vehicle_type`, `vehicle_category`

| Column | Description | Unit | Type |
|--------|-------------|------|------|
| `year` | Projection year | — | categorical: 2025, 2030, 2035 |
| `vehicle_type` | Vehicle type | — | categorical: none, car, SUV, truck |
| `vehicle_category` | Powertrain category | — | categorical: none, ICE, EV |
| `vehicle_purchase_cost` | Total purchase cost including fees and taxes | $ | numeric (0–72000) |
| `vehicle_assumed_life` | Expected vehicle lifespan | years | numeric (1–12) |
| `vehicle_maintenance_cost_per_km` | Per-kilometre maintenance cost | $/km | numeric (0–0.09) |

> No real change in ICE vehicle prices is assumed between 2025 and 2035.

> Ontario-specific fees include AC excise tax, dealer administration fee, tire levy, PPSA (Personal Property Security Registration), and delivery and destination charges.

> The 'none' vehicle type uses zero cost and assumed_life=1 to avoid division-by-zero in PMT annualization.

---

## Vehicle Energy Efficiency

`vehicle_efficiency.csv`

Vehicle energy efficiency by type, powertrain, climate zone, and year. ICE efficiency is expressed as gasoline consumption (GJ/km); BEV efficiency is expressed as electricity consumption (kWh/km). BEV efficiency includes climate-zone-specific derating factors for cold-weather battery performance. Future efficiency improvements (2030, 2035) are based on EPRI's "Improved" scenario, which incorporates technological advancements such as improved aerodynamics, powertrain enhancements, and increased battery energy density for BEVs. The substantial ICE efficiency gains (approaching 50% by 2035) are primarily attributed to the widespread adoption of hybrid powertrains, assumed to become the industry standard.

**Source:** TA Energy Wallet Analysis — Ontario Utility — Base-year (2025) efficiencies from NRCan Fuel Consumption Guide. Future-year improvements from Electric Power Research Institute (EPRI) "Improved" scenario. EV cold-weather derating factors by climate zone from TA Energy Wallet Analysis — Ontario Utility.

**Keys:** `year`, `vehicle_type`, `vehicle_category`, `climate_zone`

| Column | Description | Unit | Type |
|--------|-------------|------|------|
| `year` | Projection year | — | categorical: 2025, 2030, 2035 |
| `vehicle_type` | Vehicle type | — | categorical: none, car, SUV, truck |
| `vehicle_category` | Powertrain category | — | categorical: ICE, EV, none |
| `climate_zone` | Climate zone identifier | — | categorical: CZ_5, CZ_6, CZ_7A |
| `vehicle_efficiency_gas` | Gasoline consumption rate | GJ/km | numeric (0–0.005) |
| `vehicle_efficiency_electric` | Electricity consumption rate | kWh/km | numeric (0–0.3) |
| `ev_efficiency_factor` | Climate-zone-specific EV efficiency derating factor | dimensionless | numeric (0.86–1.0) |

> ICE efficiency does not vary by climate zone.

> EV derating factors: CZ_5=0.94, CZ_6=0.90, CZ_7A=0.86.

---

## Annual Vehicle Kilometres Travelled

`vehicle_km_traveled.csv`

Annual vehicle kilometres travelled (VKT) by vehicle type. Based on Ontario 2019 data to avoid COVID-era distortions. The same VKT applies to both baseline and alternative configurations.

**Source:** CEUD — Transportation — Ontario — Table 21 (cars) and Table 34 (trucks/SUVs).

**Keys:** `vehicle_type`

| Column | Description | Unit | Type |
|--------|-------------|------|------|
| `vehicle_type` | Vehicle type | — | categorical: none, car, truck, SUV |
| `vkt_annual` | Annual kilometres travelled | km/year | numeric (0–18000) |

> VKT is not year-varying or climate-zone-varying in this version.

---

## EV Charging Location Splits

`vehicle_charging.csv`

Defines the share of EV charging by location (home, public Level 2, DCFC), differentiated by dwelling type, vehicle type/category, and home charging access. Households without home charging rely entirely on public infrastructure.

**Source:** TA Energy Wallet Analysis — Ontario Utility — Table 7. Based on PlugShare Research & CAA, The Voice of the Canadian Electric Vehicle Driver (November 2024).

**Keys:** `dwelling_type`, `vehicle_type`, `vehicle_category`, `has_home_charging`

| Column | Description | Unit | Type |
|--------|-------------|------|------|
| `dwelling_type` | Dwelling type category | — | categorical: sfd, row, apt, mob |
| `vehicle_type` | Vehicle type | — | categorical: none, car, SUV, truck |
| `vehicle_category` | Powertrain category | — | categorical: EV, ICE, none |
| `has_home_charging` | Whether the household has home EV charging access | — | categorical: yes, no |
| `ev_pct_charged_home` | Share of total charging done at home | decimal | numeric (0–1) |
| `ev_pct_charged_level2` | Share of total charging done at public Level 2 stations | decimal | numeric (0–1) |
| `ev_pct_charged_fast` | Share of total charging done at DCFC fast chargers | decimal | numeric (0–1) |

> These figures are based on limited data, as the current evidence on charging behaviour is sparse and varies widely across studies and jurisdictions.

---

## Residential Energy Rates

`costs_home_energy.csv`

Average residential energy rates for Ontario in 2025 C$/GJ. Electricity, natural gas, oil, and gasoline rates are from CER Canada's Energy Future 2026 and represent average rates that include fixed charges, so fixed charge columns are set to zero to avoid double-counting.

**Source:** Canada Energy Regulator — Canada's Energy Future 2026 — End-Use Prices, Current Measures scenario, Residential sector, Ontario. Propane from NRCan; wood from Ontario-based firewood retail (TA Energy Wallet Analysis — Ontario Utility).

**Keys:** `year`

| Column | Description | Unit | Type |
|--------|-------------|------|------|
| `year` | Projection year | — | categorical: 2025, 2030, 2035 |
| `cost_electricity_home` | Average residential electricity rate (includes fixed charges) | $/GJ | numeric |
| `electricity_fixed_charge_monthly` | Monthly fixed electricity distribution charge (set to 0) | $/month | numeric |
| `cost_natural_gas_home` | Average natural gas rate (includes fixed charges) | $/GJ | numeric |
| `natural_gas_fixed_charge_monthly` | Monthly fixed natural gas distribution charge (set to 0) | $/month | numeric |
| `cost_oil_home` | Average heating oil rate | $/GJ | numeric |
| `cost_propane_home` | Propane variable rate | $/GJ | numeric |
| `cost_wood_home` | Wood fuel variable rate | $/GJ | numeric |

> All rates are in $/GJ. The model multiplies GJ loads by these rates directly.

> Electricity, natural gas, and oil rates are average rates inclusive of fixed charges. Fixed charge columns are set to 0 to avoid double-counting.

> Propane and wood rates are unchanged from the TA Energy Wallet Analysis — Ontario Utility (no CER source available).

> All dollar values are in 2025 constant Canadian dollars.

---

## Vehicle Energy Rates

`costs_vehicle_energy.csv`

Gasoline and public EV charging costs in $/GJ. Gasoline rates are from CER Canada's Energy Future 2026 (average rates, 2025 C$). Home EV charging uses the residential electricity rate from costs_home_energy.csv. Public charging premiums of $0.12/kWh (33.33 $/GJ for Level 2) and $0.46/kWh (127.78 $/GJ for DCFC) are added to the residential electricity rate.

**Source:** Canada Energy Regulator — Canada's Energy Future 2026 — End-Use Prices, Current Measures scenario, Transportation sector, Ontario. EV charging premiums from PlugShare Research & CAA, The Voice of the Canadian Electric Vehicle Driver (November 2024).

**Keys:** `year`

| Column | Description | Unit | Type |
|--------|-------------|------|------|
| `year` | Projection year | — | categorical: 2025, 2030, 2035 |
| `cost_gasoline` | Average gasoline price | $/GJ | numeric |
| `cost_electricity_level2` | Public Level 2 EV charging rate (residential electricity + $0.12/kWh premium) | $/GJ | numeric |
| `cost_electricity_fast` | DCFC fast charging rate (residential electricity + $0.46/kWh premium) | $/GJ | numeric |

> All rates are in $/GJ. The model multiplies GJ energy by these rates directly.

> Gasoline is an average rate in 2025 constant Canadian dollars.

> EV charging rates = residential electricity rate (from costs_home_energy.csv) + public charging premium.

---

## Discount Rate

`discount_rate.csv`

Discount rate used for annualizing capital costs via the PMT formula. Applied to all equipment categories (HVAC, DHW, vehicles, panel upgrades).

**Source:** Assumption — Standard 3% real discount rate for household energy analysis.

**Keys:** None (single-row table)

| Column | Description | Unit | Type |
|--------|-------------|------|------|
| `discount_rate` | Annual real discount rate | decimal | numeric (0–0.10) |

---

## Other Residential Energy Uses

`other_energy_uses.csv`

Annual electricity and natural gas consumption for appliances, lighting, and other non-HVAC/DHW end-uses, by dwelling type. Values are held constant across the study period and are identical for baseline and upgrade configurations.

**Source:** DSPM Canada Reference Library — Based on CEUD appliance and lighting energy intensity data.

**Keys:** `dwelling_type`

| Column | Description | Unit | Type |
|--------|-------------|------|------|
| `dwelling_type` | Dwelling type category | — | categorical: sfd, row, apt, mob |
| `other_electricity_annual` | Annual electricity consumption for non-HVAC/DHW end-uses | GJ/year | numeric (10–15) |
| `other_natural_gas_annual` | Annual natural gas consumption for non-HVAC/DHW end-uses (cooking, etc.) | GJ/year | numeric (0–1) |

> Values are not year-varying; the same values apply across all projection years.

> These values are the same for baseline and alternative configurations — no electrification impact.

> Natural gas consumption (~0.22 GJ/year) represents cooking gas only.

---

## Electrical Panel Upgrade Triggers & Costs

`panel_upgrade_triggers_and_costs.csv`

Defines logic for when an electrical panel upgrade is triggered in the alternative configuration. A $5,000 panel upgrade cost is applied when a household adopts both an electrified HVAC system (any heat pump type) and an EV. Assumed panel life is 25 years.

**Source:** User assumption — Panel upgrade trigger logic and cost estimate.

**Keys:** `alt_hvac_system`, `alt_vehicle_1_category`

| Column | Description | Unit | Type |
|--------|-------------|------|------|
| `alt_hvac_system` | Alternative HVAC system in the upgrade scenario | — | categorical: ashp w gas backup, ashp w oil backup, ashp w propane backup, ccashp w electric backup, ccashp w gas backup |
| `alt_vehicle_1_category` | Alternative primary vehicle powertrain | — | categorical: none, ICE, EV |
| `panel_upgrade_cost` | Cost of electrical panel upgrade | $ | numeric (0–5000) |
| `panel_assumed_life` | Expected panel lifespan for annualization | years | numeric (25–25) |

> The logic determining when a panel upgrade is triggered (HP + EV) should be reviewed in future iterations to better reflect real-world conditions.

> Panel upgrade cost of $5,000 is a rough estimate; actual costs vary by dwelling type and existing panel capacity.

---
