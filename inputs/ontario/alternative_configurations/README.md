<!-- AUTO-GENERATED from .meta.yaml files. Do not edit directly. -->

# Alternative Configurations

## HVAC Full Electrification Scenario

`alt_hvac_system.csv`

Full electrification scenario: all baseline fossil fuel and electric resistance HVAC systems are replaced with cold-climate air-source heat pumps with electric backup (ccashp w electric backup) at 100% adoption. Systems that are already electrified (existing ASHP, CCASHP, GSHP) have no upgrade path and remain at their baseline configuration.

**Source:** User-defined scenario — Full electrification scenario definition.

**Keys:** `hvac_system`

| Column | Description | Unit | Type |
|--------|-------------|------|------|
| `hvac_system` | Baseline HVAC system being replaced | — | categorical: 12 baseline system types |
| `alt_hvac_system` | Alternative HVAC system (ccASHP with electric backup) | — | categorical: ccashp w electric backup |
| `adoption_share` | Share of households adopting the upgrade | proportion | numeric (0–1) |

---

## DHW Electrification Scenario

`alt_dhw_system.csv`

Full electrification scenario: all baseline DHW systems are replaced with electric alternatives — 80% electric resistance and 20% heat pump water heater (HPWH). Propane and wood DHW systems have no upgrade path and remain at their baseline configuration.

**Source:** User-defined scenario — Full electrification scenario definition. 80/20 split between electric resistance and HPWH.

**Keys:** `dhw_system`

| Column | Description | Unit | Type |
|--------|-------------|------|------|
| `dhw_system` | Baseline DHW system being replaced | — | categorical: electric resistance, gas, oil |
| `alt_dhw_system` | Alternative DHW system | — | categorical: electric resistance, HPWH |
| `adoption_share` | Share of households adopting this specific upgrade path | proportion | numeric (0–1) |

---

## Vehicle Full Electrification Scenario

`alt_vehicle_1_category.csv`

Full electrification scenario: all ICE vehicles are replaced with battery electric vehicles at 100% adoption. Applies uniformly to all vehicle types (car, SUV, truck). Households with no vehicle remain unchanged.

**Source:** User-defined scenario — Full electrification scenario definition.

**Keys:** `vehicle_1_type`, `vehicle_1_category`

| Column | Description | Unit | Type |
|--------|-------------|------|------|
| `vehicle_1_type` | Primary vehicle type | — | categorical: car, SUV, truck, none |
| `vehicle_1_category` | Baseline powertrain category | — | categorical: ICE, none |
| `alt_vehicle_1_category` | Alternative powertrain category | — | categorical: EV, none |
| `adoption_share` | Share of households adopting this powertrain | proportion | numeric (0–1) |

---
