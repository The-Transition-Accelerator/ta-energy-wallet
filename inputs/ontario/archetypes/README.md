<!-- AUTO-GENERATED from .meta.yaml files. Do not edit directly. -->

# Archetypes

## Climate Zone Distribution

`climate_zone.csv`

Defines climate zone population weights for Ontario. Weights represent the share of Ontario households in each climate zone, derived from Statistics Canada census tract population data mapped to Canadian climate zones.

**Source:** DSPM Canada Reference Library — CEUD 2021 building stock data; census tract population mapping.

**Keys:** None (single-row table)

| Column | Description | Unit | Type |
|--------|-------------|------|------|
| `climate_zone` | Climate zone identifier per National Energy Code of Canada | — | categorical: CZ_5, CZ_6, CZ_7A |
| `population_share` | Share of Ontario households in this climate zone | proportion | numeric (0–1) |

---

## Dwelling Type Distribution

`dwelling_type.csv`

Defines dwelling type population weights by climate zone. Four categories cover the Ontario housing stock: single-family detached, row/townhouse, apartment, and mobile home.

**Source:** DSPM Canada Reference Library — CEUD 2021 building stock data.

**Keys:** `climate_zone`

| Column | Description | Unit | Type |
|--------|-------------|------|------|
| `climate_zone` | Climate zone identifier | — | categorical: CZ_5, CZ_6, CZ_7A |
| `dwelling_type` | Dwelling type category | — | categorical: sfd, row, apt, mob |
| `population_share` | Share of households of this dwelling type within the climate zone | proportion | numeric (0–1) |

---

## Building Envelope Performance Tiers

`envelope_tier.csv`

Segments households into three building envelope performance tiers (poor, average, good) by climate zone and dwelling type. Derived from DSPM's 10-bin envelope distribution collapsed into 3 tiers. Weights are calibrated so that weighted averages align with CEUD source data.

**Source:** DSPM Canada Reference Library — Envelope bin aggregation: bins [-5,-4,-3] → poor, [-2,-1,1] → average, [2,3,4,5] → good.

**Keys:** `climate_zone`, `dwelling_type`

| Column | Description | Unit | Type |
|--------|-------------|------|------|
| `climate_zone` | Climate zone identifier | — | categorical: CZ_5, CZ_6, CZ_7A |
| `dwelling_type` | Dwelling type category | — | categorical: sfd, row, apt, mob |
| `envelope_tier` | Building envelope performance tier | — | categorical: poor, average, good |
| `population_share` | Share of households in this envelope tier within the climate zone and dwelling type | proportion | numeric (0–1) |

---

## Income Quintile Distribution

`income_quintile.csv`

Defines income quintile population weights. All five quintiles are represented at equal 20% shares, by definition.

**Source:** By definition — Quintiles divide the population into five equal groups of 20% each.

**Keys:** None (single-row table)

| Column | Description | Unit | Type |
|--------|-------------|------|------|
| `income_quintile` | Income quintile tier (1st = lowest, 5th = highest) | — | categorical: 1st, 2nd, 3rd, 4th, 5th |
| `population_share` | Share of households in this income tier | proportion | numeric (0–1) |

---

## HVAC System Distribution

`hvac_system.csv`

Defines the distribution of baseline HVAC system types by climate zone and dwelling type. System names encode fuel type, efficiency tier, and whether air conditioning is included (e.g., "condensing gas w AC", "ashp w electric backup").

**Source:** DSPM Canada Reference Library — Equipment share data from CEUD 2021, mapped to Energy Wallet HVAC categories.

**Keys:** `climate_zone`, `dwelling_type`

| Column | Description | Unit | Type |
|--------|-------------|------|------|
| `climate_zone` | Climate zone identifier | — | categorical: CZ_5, CZ_6, CZ_7A |
| `dwelling_type` | Dwelling type category | — | categorical: sfd, row, apt, mob |
| `hvac_system` | HVAC system configuration name | — | categorical: 23 system types |
| `population_share` | Share of households with this HVAC system within the climate zone and dwelling type | proportion | numeric (0–1) |

---

## DHW System Distribution

`dhw_system.csv`

Defines the distribution of domestic hot water equipment types. Shares are uniform across climate zones and dwelling types. Covers electric resistance, natural gas, oil, propane, wood, and heat pump water heaters.

**Source:** DSPM Canada Reference Library — Equipment share data from CEUD 2021.

**Keys:** None (single-row table)

| Column | Description | Unit | Type |
|--------|-------------|------|------|
| `dhw_system` | Domestic hot water system type | — | categorical: HPWH, electric resistance, gas, oil, propane, wood |
| `population_share` | Share of households with this DHW system | proportion | numeric (0–1) |

> Shares are not differentiated by climate zone or dwelling type.

---

## Primary Vehicle Type Distribution

`vehicle_1_type.csv`

Defines the distribution of primary vehicle ownership by type (car, SUV, truck, or none), differentiated by income quintile. Shares are normalized within each quintile from the source data (which reports shares of total households).

**Source:** Statistics Canada — Survey of Household Spending: Public Use Microdata File, 2019. Table 6 from TA Energy Wallet Analysis — Ontario Utility.

**Keys:** `income_quintile`

| Column | Description | Unit | Type |
|--------|-------------|------|------|
| `income_quintile` | Income quintile tier | — | categorical: 1st, 2nd, 3rd, 4th, 5th |
| `vehicle_1_type` | Primary vehicle type | — | categorical: car, SUV, truck, none |
| `population_share` | Share of households with this vehicle type within the income quintile | proportion | numeric (0–1) |

> Shares are not differentiated by dwelling type.

> Source data reports shares of total households; normalized to within-quintile proportions.

---

## Primary Vehicle Powertrain Split

`vehicle_1_category.csv`

Defines the baseline powertrain split between internal combustion engine (ICE) and battery electric vehicle (EV) for each primary vehicle type, based on 2024 Ontario vehicle registration data.

**Source:** Statistics Canada — Table 23-10-0308-01 — Vehicle registrations, by type of vehicle and fuel type. Ontario, 2024. Light-duty vehicles (<=4,536 kg).

**Keys:** `vehicle_1_type`

| Column | Description | Unit | Type |
|--------|-------------|------|------|
| `vehicle_1_type` | Primary vehicle type | — | categorical: car, SUV, truck, none |
| `vehicle_1_category` | Powertrain category | — | categorical: ICE, EV, none |
| `population_share` | Share of vehicles with this powertrain within the vehicle type | proportion | numeric (0–1) |

> ICE includes gasoline, diesel, non-plug-in hybrid, and other fuel types. Non-plug-in hybrids are explicitly incorporated into ICE vehicle efficiency improvement assumptions.

> EV includes battery electric vehicles (BEV) and plug-in hybrid electric vehicles (PHEV).

> Limitation: PHEVs are grouped with BEVs under 'EV'. Future updates may consider adding more granularity to the vehicle categories, such as a separate PHEV category.

---

## Second Vehicle Type Distribution

`vehicle_2_type.csv`

Second vehicle slot. Currently set to 'none' for 100% of households. This data product does not evaluate second vehicles.

**Source:** N/A — Intentionally set to none for all households.

**Keys:** None (single-row table)

| Column | Description | Unit | Type |
|--------|-------------|------|------|
| `vehicle_2_type` | Second vehicle type | — | categorical: none |
| `population_share` | Share of households (always 1.0) | proportion | numeric (1–1) |

> The energy wallet definition currently only includes the first primary vehicle. Second vehicle modeling may be expanded in the future.

---

## Second Vehicle Powertrain Split

`vehicle_2_category.csv`

Powertrain category for the second vehicle slot. Set to 'none' for 100% of households, consistent with vehicle_2_type.

**Source:** N/A — Intentionally set to none for all households.

**Keys:** `vehicle_2_type`

| Column | Description | Unit | Type |
|--------|-------------|------|------|
| `vehicle_2_type` | Second vehicle type | — | categorical: none |
| `vehicle_2_category` | Powertrain category for second vehicle | — | categorical: none |
| `population_share` | Share of households (always 1.0) | proportion | numeric (1–1) |

> The energy wallet definition currently only includes the first primary vehicle. Second vehicle modeling may be expanded in the future.

---

## Home EV Charging Access

`has_home_charging.csv`

Defines the share of households with access to home EV charging by dwelling type. Single-family detached homes have higher access; apartments and multi-family have limited access.

**Source:** Pollution Probe & Electric Mobility Canada; Dunsky Energy + Climate Advisors — Pollution Probe & Electric Mobility Canada (2025), 2024 Canadian Electric Vehicle Owner Charging Experience Survey. Dunsky Energy + Climate Advisors (2022), Updated Projections of Canada's Public Charging Infrastructure Needs, prepared for Natural Resources Canada.

**Keys:** `dwelling_type`

| Column | Description | Unit | Type |
|--------|-------------|------|------|
| `dwelling_type` | Dwelling type category | — | categorical: sfd, row, apt, mob |
| `has_home_charging` | Whether the household has home EV charging access | — | categorical: yes, no |
| `population_share` | Share of households with/without home charging within the dwelling type | proportion | numeric (0–1) |

> Data quality for home charging access rates is limited. Opportunities for improving this input with better data should be evaluated in future updates.

---
