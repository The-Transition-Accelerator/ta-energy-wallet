# Energy Wallet Model - Test Data Set

This directory contains a complete test data set for validating the Energy Wallet Model implementation. The test data is designed to be realistic but simple enough to manually verify calculations.

## Directory Structure

```
inputs/
├── archetypes/                      # Step 1: one CSV per archetype variable
├── alternative_configurations/      # Step 2: one CSV per alt config variable
├── input_parameters/                # Step 3: cost, efficiency, and load tables
└── README.md                        # This file
```

## Test Data Overview

### Step 1: Baseline Archetype Tables

These tables define the current distribution of household archetypes using a **two-level vehicle taxonomy**: vehicle type (car, truck, none) and vehicle category (ICE, EV, none) are defined in separate tables for each vehicle slot.

**Files:**
1. `dwelling_type.csv` - 2 types (single_family, apartment), no conditioning, no year
2. `heating_system.csv` - 3 types (furnace, heat_pump, boiler), conditioned on dwelling_type
3. `climate_zone.csv` - 3 types (cold, moderate, warm), no conditioning, no year
4. `vehicle_1_type.csv` - 3 types (car, truck, none), no conditioning, no year
5. `vehicle_1_category.csv` - 3 categories (ICE, EV, none), conditioned on vehicle_1_type
6. `vehicle_2_type.csv` - 3 types (car, truck, none), no conditioning, no year
7. `vehicle_2_category.csv` - 3 categories (ICE, EV, none), conditioned on vehicle_2_type

**Expected Output:**
- 2 dwelling types x 3 heating systems x 3 climate zones x 3 vehicle_1_types x (2-3 vehicle_1_categories) x 3 vehicle_2_types x (2-3 vehicle_2_categories) = 1,350 unique baseline archetypes
- All weights should sum to 1.0

**Key Test Cases:**
- Independent variables (dwelling_type, climate_zone, vehicle_1_type, vehicle_2_type) create full Cartesian products
- Conditioned variables (heating_system on dwelling_type; vehicle_1_category on vehicle_1_type; vehicle_2_category on vehicle_2_type) create targeted combinations
- Two-level vehicle taxonomy: type (car/truck/none) x category (ICE/EV/none), with `none` type always mapping to `none` category
- Vehicle slot 1 is the primary (higher-VKT) vehicle; slot 2 may be `none` for single-vehicle households

### Step 2: Alternative Configuration Tables

These tables define how households transition to alternative configurations.

**Files:**
1. `alt_vehicle_1_category.csv` - Vehicle 1 category transitions (ICE→EV), conditioned on vehicle_1_type and vehicle_1_category, **includes scenario dimension** (conservative) and **year dimension** (2030, 2040, 2050)
   - ICE cars/trucks: EV adoption grows from 20% (2030) to 100% (2050)
   - EVs always remain EVs (identity rows, adoption_share = 1.0)
   - `none` remains `none` (identity rows)

2. `alt_vehicle_2_category.csv` - Vehicle 2 category transitions, same structure as vehicle 1
   - ICE cars/trucks: EV adoption grows from 0% (2030) to 100% (2050), lagging vehicle 1
   - EVs always remain EVs; `none` remains `none`

3. `alt_heating.csv` - Heating system transitions, conditioned on heating_system only (no scenario or year dimensions)
   - All furnaces and boilers transition to heat pumps (100% adoption)
   - Heat pumps remain heat pumps

**Expected Output:**
- Each baseline archetype expands across years and scenarios
- Weight conservation: sum of expanded weights equals original baseline weight for each archetype

**Key Test Cases:**
- Scenario and year dimensions in vehicle alt tables create parallel time-varying analyses
- Alt heating has no scenario or year dimension (constant adoption across all scenarios/years)
- Identity rows (EV→EV, none→none, heat_pump→heat_pump) ensure complete coverage for all baseline categories
- Vehicle type is preserved across the transition (only the category changes: ICE→EV)

### Step 3: Input Parameter Tables

These tables provide all parameters needed to calculate energy wallet costs.

**Files:**

1. **vehicle_costs.csv** (Technology-type) - Vehicle purchase costs, lifespans, maintenance costs
   - Keyed by `vehicle_type` and `vehicle_category` (two-level taxonomy)
   - 5 rows: car/ICE, car/EV, truck/ICE, truck/EV, none/none
   - Multi-lookup produces per-slot `_base`/`_alt` columns

2. **vehicle_efficiency.csv** (Technology-type) - Vehicle fuel consumption and charging patterns
   - Keyed by `vehicle_type`, `vehicle_category`, and `climate_zone`
   - 15 rows (5 vehicle type/category combinations x 3 climate zones)
   - EV efficiency derating in cold climates (85% efficiency factor vs 95-100% in moderate/warm)
   - EV charging location splits (home, Level 2, fast charger) sum to 1.0

3. **hvac_costs.csv** (Technology-type) - HVAC equipment costs, lifespans, maintenance
   - Keyed by `dwelling_type` and `heating_system`
   - 6 rows (2 dwelling types x 3 heating systems)

4. **heating_system_efficiency.csv** (Technology-type) - Heating system efficiencies and fuel splits
   - Keyed by `heating_system`
   - 3 rows (furnace, heat_pump, boiler)
   - Fuel proportions (gas, electric, oil, propane, wood) sum to 1.0

5. **heating_cooling_loads.csv** (Context) - Annual heating and cooling energy requirements
   - Keyed by `climate_zone`, `dwelling_type`, and `year`
   - Explicit `_base`/`_alt` value columns

6. **dhw_system.csv** (Context) - Domestic hot water system parameters
   - No join columns (applies to all households)
   - Single row with explicit `_base`/`_alt` suffixed columns

7. **other_energy_uses.csv** (Context) - Plug loads and other energy consumption
   - Keyed by `dwelling_type`
   - Explicit `_base`/`_alt` value columns

8. **panel_upgrade_costs.csv** (Context) - Electrical panel upgrade costs
   - Keyed by `alt_heating_system`, `alt_vehicle_1_type`, `alt_vehicle_2_type`
   - Explicit `_base`/`_alt` value columns

9. **shared_parameters.csv** (Context) - Fuel prices, discount rate, fixed charges, VKT
   - Keyed by `year` (2025, 2030, 2040, 2050)
   - Includes shared inputs (no suffix): fuel prices, discount rate, fixed charges
   - Includes explicit `_base`/`_alt` inputs: VKT per slot, panel assumed life

**Key Test Cases:**
- Technology-type tables use generic columns (`vehicle_type`, `vehicle_category`) that trigger multi-lookup
- Context tables use explicit `_base`/`_alt` suffixes and are joined once as passthrough
- Vehicle parameters use the two-level taxonomy (type + category) for differentiated costs
- `none` vehicle type has all-zero values (`assumed_life` = 1 to avoid division by zero)
- EV charging percentages sum to 1.0 for each vehicle type/category/climate combination
- Heating fuel proportions sum to 1.0 for each heating system

## Validation Checks

When running the model, verify these outputs:

### Step 1 Output:
```
All weights sum to 1.0 (no year dimension in test data)
Example row: single_family, furnace, cold, car, ICE, car, ICE
  weight = 0.65 × 0.60 × 0.50 × 0.60 × 0.95 × 0.55 × 0.95 = 0.0615...
```

### Step 2 Output:
```
Each baseline archetype expands across years (2030, 2040, 2050) and scenarios (conservative)
Weight conservation: sum across all alternatives = original baseline weight for each archetype
```

### Step 3 Output:
```
Every row should have all required input parameters
No missing values
Validation checks pass:
- ev_{N}_pct_charged_home_{s} + ev_{N}_pct_charged_level2_{s} + ev_{N}_pct_charged_fast_{s} = 1.0
- heating_system_proportion_* sum to 1.0
- All inputs present from section 3.3 of Model Architecture
```

## Data Quality Notes

- All monetary values are in 2025 inflation-adjusted dollars
- All energy values are in GJ
- All energy costs are in $/GJ
- All efficiencies are dimensionless ratios (COP for heat pumps)
- All proportions are decimals between 0 and 1
- All weights sum to 1.0 within their respective groupings
