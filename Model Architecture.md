## Objective
The Energy Wallet Model is a scenario analysis tool for exploring how technology transitions and behavioral shifts impact household energy costs and affordability. The model compares baseline household configurations to alternative future scenarios, evaluating impacts both at the individual household archetype level and across the full population.

**What is an Energy Wallet?**

The energy wallet encompasses the total costs households face for their direct energy needs:
- **Direct energy costs**: Electricity, natural gas, gasoline, and other fuels
- **Operating and maintenance costs**: Ongoing costs for energy-consuming equipment
- **Capital costs**: Upfront investment in equipment needed to use that energy (e.g., vehicles, heating systems, appliances)

The energy wallet framework captures all these components because households can procure their energy needs through different technology choices with varying cost profiles across these categories—examining only one component misses the complete economic picture.

**What the Model Does:**

The model evaluates energy wallet changes from:
- **Technology transitions**: Equipment substitutions (e.g., gas furnace → heat pump, gasoline vehicle → electric vehicle)
- **Behavioral/contextual changes**: Shifts in usage patterns or access (e.g., reduced vehicle miles traveled due to improved transit)
- **Combined scenarios**: Multiple simultaneous changes (e.g., comprehensive household electrification)

By operating at the household archetype level, the model enables:
- **Distributional analysis**: Identification of which household types face cost increases vs. decreases under different scenarios
- **Population-level impacts**: Weighted aggregation to estimate economy-wide effects
- **Equity assessments**: Comparison of impacts across household segments (e.g., by income, geography, dwelling type)
- **Policy scenario testing**: Evaluation of how different technology adoption patterns affect household affordability

## Model Architecture
### Unit of Analysis: Household Archetypes
The model operates on **household archetypes**, where each archetype represents a unique combination of household characteristics that materially impact energy costs. These defining characteristics are called **archetype variables**.

**Examples of archetype variables:**
- Geographic location (state, climate zone)
- Dwelling characteristics (single-family, apartment, square footage)
- Equipment/technology stock (heating system type, vehicle type)
- Household demographics (income bracket, size)

### Step 1: Construct Baseline Distribution of Household Archetypes

**Goal:** Build a population-weighted table of household archetypes reflecting a baseline distribution of households.
 
#### 1.1 Data Structure: Archetype Tables

The baseline distribution is built from multiple **archetype tables** (stored as separate CSV files), each introducing **one** new way to differentiate households.

Each archetype table MUST contain the following columns:

1. **New archetype variable** (1 column, required)
    - The categorical variable being introduced by this table
    - Example: `heating_system` with values {furnace, heat_pump, boiler}

2. **Population share** (1 column, required)
    - The proportion of households in this category
    - Must be named `population_share`
    - Must be expressed as a decimal (0-1) or percentage

In addition to these two columns, 

3. **Conditioning variables** (0+ columns, optional)
    - Existing archetype variables (defined in other tables) that correlate with or constrain the new variable
    - Example: `dwelling_type` might condition the distribution of `heating_system`
    - These represent either:
        - Empirical correlations observed in data
        - Logical constraints (e.g., certain equipment incompatible with certain dwelling types)

4. **Year variable** (0 or 1 column, optional)
    - Special variable `year` that allows population distributions to change over time
    - Example: `year` with values `[2025, 2030, 2040, 2050]`
    - Creates time series dimension in the analysis
    - When present, population shares must be provided for each year value
    - If not present, distribution is assumed constant across all analysis years

**Key structural requirements:**
- For each unique combination of conditioning variables and year (if present), population shares must sum to 1.0 (100%)
- Column order must be: [Conditioning variables] → [New archetype variable] → [Year (if present)] → [Population share]

**Design Philosophy: File-Based Flexibility**

The model is designed to be **fully configurable through the file system**. Users can:
- **Add new archetype variables**: Create a new CSV file following the archetype table structure
- **Remove archetype variables**: Delete the corresponding CSV file
- **Modify distributions**: Edit existing CSV files to change population shares or add/remove categories

**Downstream Impact of Archetype Variable Selection**

Every archetype variable defined in Step 1 must appear as a join key in at least one Step 3 input parameter table. The purpose of an archetype variable is to differentiate energy wallet costs — if an archetype variable does not differentiate any input parameter, the resulting table will contain duplicate rows with identical cost profiles, wasting memory without adding analytical value. As a design principle, only add archetype variables that actually differentiate energy wallet costs.

The model automatically discovers and processes all archetype table files in the designated directory without requiring code changes. This file-based approach enables:
- Quick experimentation with different segmentation schemes
- Easy version control of different analysis configurations
- Future development of a web-based interface where users can create/modify/remove archetype variables through a browser, with changes persisted to the file system

#### 1.2 Table Joining Logic

The model combines archetype tables sequentially through a **cross-join with conditioning constraints**:

1. **Cross-join operation**: Each table is joined to create all possible combinations of archetype variables
    - If variables are independent (no conditioning), this creates a full Cartesian product (all possible combinations)
    - Example: 3 dwelling types × 4 heating systems = 12 combinations
2. **Conditioning constraints**: When conditioning variables are specified, only valid combinations are retained
    - Example: If `heating_system` is conditioned on `dwelling_type`, the join respects that relationship
3. **Weight calculation**: Population shares are multiplied across all tables to produce a final weight for each household archetype
    - This assumes **conditional independence**: variables not explicitly correlated are treated as independent
4. **Final output**: A single combined table with:
    - All archetype variables (one column per variable)
    - A final population weight (product of all individual shares)
    - Each row represents one unique household archetype
    - By default, individual archetype table population shares are dropped after the final weight is calculated, since they are no longer needed. This behavior can be overridden via the `--keep-provenance-shares` CLI flag.

**Mathematical note:** Final weights must sum to 1.0 across all archetypes for each unique combination of year (if present) and scenario (if present), representing 100% of the population within that year-scenario group.

#### 1.3 Optimization Considerations

- **Row filtering**: Automatically remove rows with population share = 0 in individual tables before joining (these represent impossible/nonexistent combinations)
- **Join ordering**: Consider joining tables from smallest to largest to minimize intermediate table sizes and reduce memory usage
- **Memory management**: Given potentially large archetype counts, monitor memory usage during joins

#### 1.4 Validation Rules

**Individual archetype tables:**

- Column order must be: [Conditioning variables] → [New archetype variable] → [Year (if present)] → [Population share]
- For each unique combination of conditioning variables, year (if present), and scenario (if present), population shares must sum to 1.0 (±0.001 tolerance)
- All population shares must be ≥ 0 and ≤ 1

**Combined archetype table:**

- Final population weights must sum to 1.0 (±0.001 tolerance) for each year (if year variable is present)
- No duplicate archetype combinations (including year and scenario if present)
- All weights > 0 (zero-weight archetypes should have been filtered; negative weights indicate an input error and must be rejected)

#### 1.5 Important Construction Constraints

This approach imposes specific requirements on how archetype tables are built:

- **One new variable per table**: Each table introduces exactly one new archetype variable
- **Shares partition only on the new variable**: Population shares partition households only along the new variable (within each group of conditioning variables and year if present)
- **Explicit correlations only**: Any relationship between variables must be explicitly defined through conditioning variables; otherwise variables are assumed independent
- **Year handling**: If `year` variable is included, it creates a time series dimension allowing population distributions to evolve over time

#### 1.6 Worked Example

Let's walk through joining the archetype tables used in the test data set. The model uses a **two-level vehicle taxonomy**: `vehicle_type` (car, truck, none) and `vehicle_category` (ICE, EV, none), with separate tables for each vehicle slot.

**Table 1: dwelling_type.csv** (no conditioning variables)

|dwelling_type|population_share|
|---|---|
|single_family|0.65|
|apartment|0.35|

**Table 2: heating_system.csv** (conditioned on dwelling_type)

|dwelling_type|heating_system|population_share|
|---|---|---|
|single_family|furnace|0.60|
|single_family|heat_pump|0.30|
|single_family|boiler|0.10|
|apartment|furnace|0.40|
|apartment|heat_pump|0.55|
|apartment|boiler|0.05|

Note: Within each `dwelling_type`, shares sum to 1.0.

**Table 3: climate_zone.csv** (no conditioning variables)

|climate_zone|population_share|
|---|---|
|cold|0.50|
|moderate|0.30|
|warm|0.20|

**Table 4: vehicle_1_type.csv** (no conditioning variables)

|vehicle_1_type|population_share|
|---|---|
|car|0.60|
|truck|0.30|
|none|0.10|

**Table 5: vehicle_1_category.csv** (conditioned on vehicle_1_type)

|vehicle_1_type|vehicle_1_category|population_share|
|---|---|---|
|car|ICE|0.95|
|car|EV|0.05|
|truck|ICE|0.99|
|truck|EV|0.01|
|none|none|1.00|

Note: Within each `vehicle_1_type`, shares sum to 1.0. The `none` type always maps to `none` category.

**Table 6: vehicle_2_type.csv** (no conditioning variables)

|vehicle_2_type|population_share|
|---|---|
|car|0.55|
|truck|0.15|
|none|0.30|

**Table 7: vehicle_2_category.csv** (conditioned on vehicle_2_type)

|vehicle_2_type|vehicle_2_category|population_share|
|---|---|---|
|car|ICE|0.95|
|car|EV|0.05|
|truck|ICE|0.99|
|truck|EV|0.01|
|none|none|1.00|

Note: Same category distribution as vehicle slot 1, but conditioned on `vehicle_2_type`.

**Step-by-step joining:**

_Step 1: Join Table 1 and Table 2_ Since `heating_system` is conditioned on `dwelling_type`, we match on that variable and multiply weights:

|dwelling_type|heating_system|weight|
|---|---|---|
|single_family|furnace|0.65 × 0.60 = 0.39|
|single_family|heat_pump|0.65 × 0.30 = 0.195|
|single_family|boiler|0.65 × 0.10 = 0.065|
|apartment|furnace|0.35 × 0.40 = 0.14|
|apartment|heat_pump|0.35 × 0.55 = 0.1925|
|apartment|boiler|0.35 × 0.05 = 0.0175|

Validation: 0.39 + 0.195 + 0.065 + 0.14 + 0.1925 + 0.0175 = 1.0 ✓

_Step 2: Join with Table 3_ Since `climate_zone` has no conditioning variables, we create all combinations (Cartesian product), expanding to 18 rows (6 × 3 climate zones).

_Step 3: Join with Table 4_ Since `vehicle_1_type` has no conditioning variables, we create all combinations (Cartesian product), expanding to 54 rows (18 × 3 vehicle types).

_Step 4: Join with Table 5_ Since `vehicle_1_category` is conditioned on `vehicle_1_type`, we match on that variable and multiply weights. Rows where `vehicle_1_type = none` get `vehicle_1_category = none` with share 1.0 (no expansion). Rows with `car` or `truck` expand into ICE/EV splits.

_Step 5: Join with Table 6_ Since `vehicle_2_type` has no conditioning variables, we create all combinations, expanding by 3 vehicle types.

_Step 6: Join with Table 7_ Since `vehicle_2_category` is conditioned on `vehicle_2_type`, we match and multiply. Same pattern as Step 4.

**Final result:** Each combination of (dwelling_type × heating_system × climate_zone × vehicle_1_type × vehicle_1_category × vehicle_2_type × vehicle_2_category) produces one row, with weights summing to 1.0.

This example demonstrates:

- How the **two-level vehicle taxonomy** separates vehicle type (car/truck/none) from fuel category (ICE/EV/none) for cleaner multi-lookup joins in Step 3
- How conditioning creates targeted correlations (heating system depends on dwelling type; vehicle category depends on vehicle type)
- How independent variables create full combinations (climate_zone, vehicle_1_type, vehicle_2_type cross with everything)
- How weights multiply through the joins and maintain the 100% population constraint
- How multi-vehicle households are represented through two vehicle "slots" (slot 2 may be `none`)



### Step 2: Construct Alternative Configurations

**Goal:** Define alternative technology and behavioral configurations that households could adopt, creating an expanded table that pairs each baseline archetype with one or more feasible alternative scenarios for comparison.

#### 2.1 Conceptual Framework

The model compares **baseline configurations** (current household characteristics) against **alternative configurations** (potential future states after technological or behavioral changes). Alternative configurations can involve:

- **Technology substitution**: Equipment changes (e.g., gas furnace → heat pump, gasoline vehicle → electric vehicle)
- **Behavioral/contextual changes**: Shifts in usage patterns or access (e.g., high VMT → low VMT due to improved transit/bike infrastructure)
- **Combined changes**: Multiple simultaneous transitions (e.g., "full electrification" = furnace → heat pump AND gasoline → EV)

Each alternative configuration is evaluated at the archetype level, enabling:
- Comparison of energy wallet costs before and after transitions
- Identification of which specific household types benefit or face higher costs
- Population-weighted aggregate impacts across all households or specific segments

#### 2.2 Data Structure: Alternative Configuration Tables

Alternative configurations are defined through **alternative configuration tables** (alt config tables, stored as separate CSV files). Similar to Step 1's archetype tables, these tables use conditioning variables and introduce new alternative archetype variables.

Each alt config table contains the following types of columns:

1. **Conditioning archetype variables** (1+ columns, required)
   - Existing baseline archetype variables that determine which alternatives apply
   - Can include both baseline variables (e.g., `dwelling_type`, `heating_system`) and previously defined alternative variables (e.g., `alt_heating_system`)
   - Example: `vehicle_type` conditions the available vehicle alternatives
   - These define the baseline state from which alternatives are evaluated

2. **New alternative archetype variable** (1 column, required)
   - The alternative value for an archetype variable being changed
   - Uses the naming convention: `alt_{variable_name}`
   - Example: `alt_vehicle_type` with values `[EV]` specifies vehicle transitions to electric
   - Example: `alt_heating_system` with values `[heat_pump, electric_resistance]` specifies heating alternatives

3. **Scenario variables** (0+ columns, optional)
   - Special variables that create parallel versions of the analysis with different adoption patterns
   - Must use the naming convention `scn_{scenario_name}` (e.g., `scn_adoption` with values `[conservative, moderate, aggressive]`)
   - This prefix enables the system to auto-detect scenario columns and distinguish them from archetype and alternative variables
   - Creates separate scenario runs that can be compared
   - Scenario variables expand the analysis table multiplicatively

4. **Year variable** (0 or 1 column, optional)
   - Special variable `year` that allows adoption shares to change over time
   - Example: `year` with values `[2025, 2030, 2040, 2050]`
   - Creates time series dimension showing how adoption evolves
   - When present, adoption shares must be provided for each year value
   - If not present, adoption shares are assumed constant across all analysis years

5. **Adoption share** (1 column, required)
   - The proportion of households in this conditioning group that adopt this alternative
   - Must be expressed as a decimal (0-1) or percentage

**Key structural requirements:**
- For each unique combination of conditioning archetype variables, scenario variables, and year (if present), adoption shares must sum to 1.0 (100%)
- Column order must be: [Conditioning archetype variables] → [New alternative archetype variable] → [Scenario variables (if present)] → [Year (if present)] → [Adoption share]
- Setting adoption share = 0 explicitly excludes that combination (documents ineligibility)

**Naming convention:**
- Alternative archetype variables must use the format: `alt_{original_variable_name}`
- Example: `vehicle_1_category` becomes `alt_vehicle_1_category`, `heating_system` becomes `alt_heating_system`

#### 2.3 Alternative Configuration Table Construction Logic

Alternative configuration tables follow similar logic to Step 1's archetype tables:

**Construction approach:**
- Each table introduces **one new alternative archetype variable**
- The table may have **one or more conditioning archetype variables** (baseline or previously defined alternative variables)
- The table may optionally include **scenario variables** to create parallel alternative scenarios
- The table may optionally include a **year variable** to allow adoption shares to evolve over time
- Adoption shares partition households only along the new alternative variable (within each group of conditioning variables, scenario, and year if present)

**Multiple tables can be chained together** to define complex alternative scenarios:
- Table 1 might define `alt_vehicle_1_category` conditioned on baseline `vehicle_1_type` and `vehicle_1_category`
- Table 2 might define `alt_heating_system` conditioned on baseline `heating_system`
- This allows building up alternative configurations incrementally

**Example: Simple single-variable alternative**

*Table: alt_vehicle_1_category.csv*

| vehicle_1_type | vehicle_1_category | alt_vehicle_1_category | adoption_share |
| -------------- | ------------------ | ---------------------- | -------------- |
| car            | ICE                | EV                     | 1.0            |
| car            | EV                 | EV                     | 1.0            |
| truck          | ICE                | EV                     | 1.0            |
| truck          | EV                 | EV                     | 1.0            |
| none           | none               | none                   | 1.0            |

This table says:
- ICE car and truck households transition to EV (100% adoption of this alternative)
- EV households remain EV; `none` remains `none`
- Result: All vehicles end up as EVs in the alternative scenario

**Example: Multiple alternative options**

*Table: alt_heating.csv*

| heating_system | alt_heating_system  | adoption_share |
| -------------- | ------------------- | -------------- |
| furnace        | heat_pump           | 0.60           |
| furnace        | electric_resistance | 0.40           |
| heat_pump      | heat_pump           | 1.0            |
| boiler         | heat_pump           | 0.0            |
| boiler         | electric_resistance | 1.0            |

This table says:
- Furnace households: 60% adopt heat pumps, 40% adopt electric resistance
- Heat pump households: remain heat pumps
- Boiler households: explicitly excluded (ineligible for heat pump transition)

#### 2.4 Joining Alternative Configuration Tables

Alternative configuration tables are joined sequentially, similar to Step 1's baseline archetype construction:

1. **Start with baseline archetypes** (output from Step 1)

2. **Join first alt config table**
   - Match on conditioning archetype variables
   - Create new rows for each alternative option
   - Split baseline weights according to adoption shares
   - Add `alt_{variable}` column(s) from this table

3. **Join subsequent alt config tables**
   - Match on conditioning archetype variables (which may now include previously defined `alt_{variable}` columns)
   - Expand existing rows based on new alternative options
   - Split weights according to adoption shares

4. **Weight calculation**
   - Weights are multiplied across all alternative tables
   - Similar to Step 1: `final_weight = baseline_weight × adoption_share_1 × adoption_share_2 × ...`

5. **Final output structure**
   Each row contains:
   - All baseline archetype variables
   - All alternative archetype variables (`alt_{variable}` columns)
   - Final weight (portion of population in this baseline archetype × alternative configuration combination)

#### 2.5 Optimization Considerations

- **Row filtering**: Remove rows with adoption_share = 0 before joining
- **Join ordering**: Consider joining tables from smallest to largest to minimize intermediate table sizes
- **Memory management**: Expanded table can be significantly larger than baseline (monitor memory usage)
- **Logging**: Track number of alternatives per archetype and total expanded rows

#### 2.6 Validation Rules

**Individual alt config tables:**
- Column order must be: [Conditioning archetype variables] → [New alternative archetype variable] → [Scenario variables (if present)] → [Year (if present)] → [Adoption share]
- All adoption shares must be ≥ 0 and ≤ 1
- For each unique combination of conditioning archetype variables, scenario variables, and year (if present), adoption shares must sum to 1.0 (±0.001 tolerance)
- Alternative variable names must follow `alt_{variable}` naming convention
- All conditioning archetype variables must exist in either baseline archetypes or previously processed alt config tables

**Expanded archetype table (after all alt config tables joined):**
- For each original baseline archetype (and year/scenario combination if present), sum of weights across all alternative configurations must equal original baseline weight (±0.001 tolerance)
- No duplicate combinations of (baseline archetype × all alternative variables × scenario × year)
- All weights > 0

#### 2.7 Important Construction Constraints

This approach requires alt config tables to be constructed with:

- **One new alternative variable per table**: Each table introduces exactly one new `alt_{variable}` column
- **Shares partition only on the new alternative variable**: Adoption shares partition households only along the new alternative variable (within each group of conditioning variables, scenario, and year if present)
- **Explicit correlations only**: Any relationship between alternative variables must be explicitly defined through conditioning variables
- **Complete coverage**: For each unique combination of conditioning variables, scenario, and year (if present), adoption shares must sum to 1.0
- **Documented exclusions**: Set adoption_share = 0 to explicitly document ineligible combinations
- **Scenario handling**: Scenario variables create parallel alternative scenarios that can be compared
- **Year handling**: Year variable allows adoption shares to evolve over time, enabling dynamic transition modeling

#### 2.8 Worked Example

**Baseline archetypes (from Step 1, simplified):**

| dwelling_type | heating_system | vehicle_1_type | vehicle_1_category | baseline_weight |
| ------------- | -------------- | -------------- | ------------------ | --------------- |
| single_family | furnace        | car            | ICE                | 0.40            |
| single_family | heat_pump      | car            | ICE                | 0.20            |
| apartment     | boiler         | truck          | ICE                | 0.15            |

**Alt Config Table 1: alt_vehicle_1_category.csv** (with scenario and year dimensions)

| vehicle_1_type | vehicle_1_category | alt_vehicle_1_category | scn_adoption | year | adoption_share |
| -------------- | ------------------ | ---------------------- | ----------------- | ---- | -------------- |
| car            | ICE                | EV                     | conservative      | 2030 | 0.20           |
| car            | ICE                | ICE                    | conservative      | 2030 | 0.80           |
| car            | EV                 | EV                     | conservative      | 2030 | 1.00           |
| truck          | ICE                | EV                     | conservative      | 2030 | 0.20           |
| truck          | ICE                | ICE                    | conservative      | 2030 | 0.80           |
| truck          | EV                 | EV                     | conservative      | 2030 | 1.00           |
| none           | none               | none                   | conservative      | 2030 | 1.00           |

Note: 20% of ICE households adopt EVs in 2030, 80% remain ICE. EV and none households stay as-is. Adoption shares sum to 1.0 within each (vehicle_1_type, vehicle_1_category, scn_adoption, year) group.

**After joining Table 1 (showing year=2030, conservative scenario only):**

| dwelling_type | heating_system | vehicle_1_type | vehicle_1_category | alt_vehicle_1_category | weight |
| ------------- | -------------- | -------------- | ------------------ | ---------------------- | ------ |
| single_family | furnace        | car            | ICE                | EV                     | 0.08   |
| single_family | furnace        | car            | ICE                | ICE                    | 0.32   |
| single_family | heat_pump      | car            | ICE                | EV                     | 0.04   |
| single_family | heat_pump      | car            | ICE                | ICE                    | 0.16   |
| apartment     | boiler         | truck          | ICE                | EV                     | 0.03   |
| apartment     | boiler         | truck          | ICE                | ICE                    | 0.12   |

Weight calculations:
- Row 1: 0.40 × 0.20 = 0.08
- Row 2: 0.40 × 0.80 = 0.32
- Row 3: 0.20 × 0.20 = 0.04
- Row 4: 0.20 × 0.80 = 0.16
- Row 5: 0.15 × 0.20 = 0.03
- Row 6: 0.15 × 0.80 = 0.12

**Alt Config Table 2: alt_heating.csv** (no scenario or year dimensions)

| heating_system | alt_heating_system | adoption_share |
| -------------- | ------------------ | -------------- |
| furnace        | heat_pump          | 1.00           |
| heat_pump      | heat_pump          | 1.00           |
| boiler         | heat_pump          | 1.00           |

Note: In the test data, all heating systems transition to heat pumps at 100% adoption. Zero-share rows (e.g., furnace→furnace with share 0) are filtered out before joining.

**After joining Table 2 (final expanded table):**

| dwelling_type | heating_system | vehicle_1_type | vehicle_1_category | alt_vehicle_1_category | alt_heating_system | final_weight |
| ------------- | -------------- | -------------- | ------------------ | ---------------------- | ------------------ | ------------ |
| single_family | furnace        | car            | ICE                | EV                     | heat_pump          | 0.08         |
| single_family | furnace        | car            | ICE                | ICE                    | heat_pump          | 0.32         |
| single_family | heat_pump      | car            | ICE                | EV                     | heat_pump          | 0.04         |
| single_family | heat_pump      | car            | ICE                | ICE                    | heat_pump          | 0.16         |
| apartment     | boiler         | truck          | ICE                | EV                     | heat_pump          | 0.03         |
| apartment     | boiler         | truck          | ICE                | ICE                    | heat_pump          | 0.12         |

Weight calculations (adoption_share = 1.0 for all rows, so weights are unchanged):
- All weights × 1.0 = same as after Table 1

Validation: Sum of final_weights = 0.08 + 0.32 + 0.04 + 0.16 + 0.03 + 0.12 = 0.75 ✓

This equals sum of original baseline weights: 0.40 + 0.20 + 0.15 = 0.75 ✓

This example demonstrates:
- How the **two-level vehicle taxonomy** works in alternatives: `alt_vehicle_1_category` changes the fuel category (ICE→EV) while preserving the vehicle type (car/truck)
- How alternative variables are introduced one at a time
- How weights are split proportionally based on adoption shares
- How scenario and year dimensions create parallel analyses with evolving adoption rates
- How identity rows (EV→EV, none→none) ensure complete coverage
- How weights maintain consistency with baseline totals

### Step 3: Load and Validate Input Parameters

**Goal:** Load all required input parameters needed to calculate energy wallet costs for both baseline and alternative configurations, ensuring complete coverage across all archetypes.

#### 3.1 Conceptual Framework

Energy wallet calculations require detailed input parameters for equipment costs, energy consumption, fuel prices, and system efficiencies. These inputs must be defined for:
- **Baseline configurations**: Current household technology and behavior
- **Alternative configurations**: Future technology and behavioral scenarios
- **Shared parameters**: Values that do not vary based on technology choice or household behavior, and therefore apply identically to both baseline and alternative configurations (e.g., fuel prices, discount rates, utility fixed charges)

Inputs are organized by the major components of household energy consumption:
1. **Vehicle**: Purchase cost, life span, maintenance, fuel consumption, and charging behavior
2. **HVAC System**: Equipment cost, life span, maintenance, heating/cooling loads, and system efficiencies
3. **Domestic Hot Water (DHW) System**: Equipment cost, life span, maintenance, hot water loads, and system efficiencies
4. **Other Energy Uses**: Remaining household electricity and natural gas consumption (sans the equipment that consumes this energy), plus miscellaneous costs (e.g., electrical panel upgrades)

Input parameters may vary by:
- **Household archetype** (e.g., heating loads differ by climate zone)
- **Analysis scenario** (e.g., testing sensitivity to different fuel prices - scenarios may already exist in the expanded archetype table from Step 2)
- **Year** (e.g., tracking how costs and efficiencies change over time)

#### 3.2 Data Structure: Input Parameter Tables

Input parameters are defined through **input parameter tables** (stored as separate CSV files). These tables provide the flexibility to define inputs at different levels of granularity based on data availability and analysis needs.

There are two categories of input parameter tables:

##### Technology-Type Tables (Unified)

Technology-type tables define parameters that are properties of a technology choice (e.g., the cost of a vehicle depends on its type, not on whether it is the baseline or alternative). These tables:

- Are keyed by a **generic type column** (e.g., `vehicle_type`, `heating_system`) that does not exist verbatim in the expanded archetype table but maps to one or more slot/variant columns
- Have value columns with **no** `_base`/`_alt` suffix
- Are joined multiple times by Step 3's multi-lookup system, which automatically produces `_base` and `_alt` output columns

Example: `vehicle_costs.csv` is keyed by `vehicle_type` and `vehicle_category` and contains `vehicle_purchase_cost`. Step 3 detects the slot pattern and looks it up four times:
1. (`vehicle_type`, `vehicle_category`) → (`vehicle_1_type`, `vehicle_1_category`) → produces `vehicle_1_purchase_cost_base`
2. (`vehicle_type`, `vehicle_category`) → (`alt_vehicle_1_type`, `alt_vehicle_1_category`) → produces `vehicle_1_purchase_cost_alt`
3. (`vehicle_type`, `vehicle_category`) → (`vehicle_2_type`, `vehicle_2_category`) → produces `vehicle_2_purchase_cost_base`
4. (`vehicle_type`, `vehicle_category`) → (`alt_vehicle_2_type`, `alt_vehicle_2_category`) → produces `vehicle_2_purchase_cost_alt`

**Note on multi-vehicle complexity:** The multi-vehicle slot approach adds complexity to the multi-lookup system but provides essential flexibility for modeling multi-vehicle households. The complexity is largely encapsulated within Step 3's lookup engine. For studies that don't require a second vehicle, all vehicle 2 archetypes can be set to `none` (see §4.1).

##### Context Tables (Explicit _base/_alt)

Context tables define parameters that vary by scenario context rather than technology type, or parameters where the base and alt values are intentionally different (e.g., VKT, heating loads). These tables:

- Have value columns with explicit `_base` and/or `_alt` suffixes
- Are joined once to the expanded archetype table (passthrough behavior)
- May also be keyed by direct archetype/alternative columns that exist verbatim in the expanded table

Example: `shared_parameters.csv` has `vkt_1_annual_base` and `vkt_1_annual_alt` as separate columns because VKT can differ between base and alt to reflect behavioral changes.

**Unsuffixed context parameters:** If a context parameter is the same for both baseline and alternative (e.g., heating loads that do not change between scenarios), the value column may be authored **without** a `_base`/`_alt` suffix (e.g., `heating_load_annual` instead of separate `heating_load_annual_base` and `heating_load_annual_alt` columns). Step 3 will automatically duplicate the unsuffixed column into both `_base` and `_alt` copies in the final model input table, provided the suffixed form appears in the required parameter registry (section 3.3). This is distinct from shared parameters (e.g., `discount_rate`), which are not duplicated because they are referenced without suffixes throughout the pipeline.

##### Common Structure

Each input parameter table contains:

1. **Join columns** (0+ columns, optional)
   - Baseline archetype variables (e.g., `climate_zone`, `dwelling_type`)
   - Alternative archetype variables (e.g., `alt_heating_system`, `alt_vehicle_1_category`)
   - Generic type columns for technology-type tables (e.g., `vehicle_type`, `heating_system`)
   - When present, inputs must be provided for every unique combination of join key values that exists in the expanded archetype table

2. **Scenario variables** (0+ columns, optional)
   - Scenario variables that may have been introduced in Step 2 or can be introduced here
   - Example: `scn_electricity_price` with values `[low, medium, high]`

3. **Year variable** (0 or 1 column, optional)
   - Special variable `year` that allows inputs to change over time
   - If not present in a table, values are assumed constant across all years

4. **Input value columns** (1+ columns, required)
   - The actual input parameter values
   - For technology-type tables: no `_base`/`_alt` suffix (Step 3 adds them)
   - For context tables: explicit `_base` and/or `_alt` suffix, or no suffix if the value is the same for both (Step 3 auto-duplicates into `_base` and `_alt`)
   - Shared inputs have no suffix (e.g., `cost_electricity_home`) and are not duplicated

**Key structural requirements:**
- After Step 3 expansion, all output column names must be unique
- Each required input parameter (in its final `_base`/`_alt` form) must be produced by exactly one table
- When join columns are present, input values must be provided for all combinations that exist in the expanded archetype table
- Tables can contain multiple input value columns for efficiency

#### 3.3 Required Input Parameters

The following input parameters define the **contract between Step 3 and Steps 4/5**. Regardless of how input CSV files are structured or which input set is used, the final model input table produced by Step 3 must contain all of the parameters listed below. Steps 4 and 5 reference these column names directly in their calculations. This registry is defined in `required.py` and is used to validate the final model input table.

All monetary values should be in inflation-adjusted dollars pegged to a baseline year. All energy quantities should be in GJ. All energy costs should be in $/GJ.

The column names listed below are the **final output names** after Step 3 processing. For technology-type tables, the raw CSV column names differ (see section 3.4 for the multi-lookup mechanism). For context tables with unsuffixed value columns, Step 3 auto-duplicates them into `_base` and `_alt` copies (see section 3.2).

**Shared Parameters (Apply to Both Baseline and Alternative):**

Shared parameters are values that do not vary based on technology choice or household behavior — they apply identically to both baseline and alternative configurations. Examples include fuel prices, discount rates, and utility fixed charges. Because they are independent of the technology or behavior being modeled, they carry no `_base` or `_alt` suffix:

- `cost_electricity_home` - Cost per GJ of electricity at home ($/GJ)
- `cost_natural_gas_home` - Cost per GJ of natural gas at home ($/GJ)
- `cost_oil_home` - Cost per GJ of oil at home ($/GJ)
- `cost_propane_home` - Cost per GJ of propane at home ($/GJ)
- `cost_wood_home` - Cost per GJ of wood at home ($/GJ)
- `cost_gasoline` - Cost per GJ of gasoline ($/GJ)
- `cost_electricity_level2` - Cost per GJ of electricity at Level 2 charger ($/GJ)
- `cost_electricity_fast` - Cost per GJ of electricity at fast charger ($/GJ)
- `discount_rate` - Discount rate for annualizing capital costs (decimal)
- `electricity_fixed_charge_monthly` - Monthly fixed charge for electricity service ($/month)
- `natural_gas_fixed_charge_monthly` - Monthly fixed charge for natural gas service ($/month)

**Vehicle Inputs (Per Slot N=1,2; Baseline and Alternative Versions):**

The model supports up to two vehicles per household. Vehicle slot 1 is the primary (higher-VKT) vehicle; slot 2 is the secondary vehicle (may be `none` for single-vehicle households). Parameters below use `{N}` for the slot number and `{s}` for `base` or `alt`.

- `vehicle_{N}_purchase_cost_{s}` - Upfront vehicle cost ($)
- `vehicle_{N}_assumed_life_{s}` - Expected vehicle lifespan (years)
- `vehicle_{N}_maintenance_cost_per_km_{s}` - Maintenance cost per km ($/km)
- `vehicle_{N}_efficiency_gas_{s}` - Gasoline energy per km (GJ/km); 0 for EVs
- `vehicle_{N}_efficiency_electric_{s}` - Electric energy per km (kWh/km); 0 for ICE
- `ev_{N}_efficiency_factor_{s}` - Derating factor for cold climate EV efficiency (decimal, ≤1.0)
- `ev_{N}_pct_charged_home_{s}` - Percent of EV charging at home (decimal, 0-1)
- `ev_{N}_pct_charged_level2_{s}` - Percent of EV charging at Level 2 public charger (decimal, 0-1)
- `ev_{N}_pct_charged_fast_{s}` - Percent of EV charging at fast charger (decimal, 0-1)
- `vkt_{N}_annual_{s}` - Annual vehicle kilometers traveled (km/year) - may differ to reflect behavioral changes

For the `none` vehicle type, all cost and efficiency values are 0 (`assumed_life` = 1 to avoid division by zero in annualization).

**HVAC System Inputs (Baseline and Alternative Versions):**

- `hvac_equipment_cost_{s}` - Equipment purchase + installation cost ($)
- `hvac_assumed_life_{s}` - Expected equipment lifespan (years)
- `hvac_maintenance_cost_annual_{s}` - Annual maintenance cost ($)
- `heating_load_annual_{s}` - Annual heating load required (GJ/year, independent of system efficiency) - may differ to reflect envelope improvements or behavioral changes
- `cooling_load_annual_{s}` - Annual cooling load required (GJ/year, independent of system efficiency) - may differ to reflect envelope improvements or behavioral changes
- `heating_system_proportion_{fuel}_{s}` - Proportion of heating load met by fuel (decimal, 0-1), for each fuel in {gas, electric, oil, propane, wood}. Must sum to 1.0.
- `heating_system_efficiency_{fuel}_{s}` - Heating system efficiency for fuel (decimal), for each fuel in {gas, electric, oil, propane, wood}. Typically 0.8-0.98 for combustion, 2.0-4.0 for heat pumps.
- `cooling_system_efficiency_{s}` - Cooling system efficiency (decimal, typically 2.5-4.5 for AC)

**DHW System Inputs (Baseline and Alternative Versions):**

- `dhw_equipment_cost_{s}` - Equipment purchase + installation cost ($)
- `dhw_assumed_life_{s}` - Expected equipment lifespan (years)
- `dhw_maintenance_cost_annual_{s}` - Annual maintenance cost ($)
- `dhw_load_annual_{s}` - Annual hot water load required (GJ/year, independent of system efficiency) - may differ to reflect behavioral changes
- `dhw_system_proportion_{fuel}_{s}` - Proportion of DHW load met by fuel (decimal, 0-1), for each fuel in {gas, electric, oil, propane, wood}. Must sum to 1.0.
- `dhw_system_efficiency_{fuel}_{s}` - DHW system efficiency for fuel (decimal), for each fuel in {gas, electric, oil, propane, wood}.

**Other Energy Use and Miscellaneous Costs (Baseline and Alternative Versions):**

- `other_electricity_annual_{s}` - Other electricity used annually (GJ/year) - may differ to reflect efficiency improvements or behavioral changes
- `other_natural_gas_annual_{s}` - Other natural gas used annually (GJ/year) - may differ to reflect efficiency improvements or behavioral changes
- `panel_upgrade_cost_{s}` - Cost of electrical panel upgrade if required ($)
- `panel_assumed_life_{s}` - Expected useful life of panel upgrade for annualization (years)
#### 3.4 Input Loading and Multi-Lookup Matching Logic

The model loads input parameters and matches them to the expanded archetype table from Step 2. This step includes a **multi-lookup system** that automatically detects how input table key columns map to the expanded archetype columns and generates the correct join operations.

1. **Load all input parameter tables** from designated directory
   - Each table can contain multiple input value columns
   - Tables are classified as technology-type or context based on their columns

2. **Classify join columns** using expanded archetype column names
   - **Direct match**: Column exists verbatim in the expanded table (e.g., `climate_zone`, `dwelling_type`, `alt_heating_system`)
   - **Slot-expanded tech type**: Column maps to numbered slot variants (e.g., `vehicle_type` → `vehicle_1_type`, `vehicle_2_type`; `vehicle_category` → `vehicle_1_category`, `vehicle_2_category`, `alt_vehicle_1_category`, `alt_vehicle_2_category`). Detected by splitting the column name at `_` boundaries and searching for `{prefix}_{N}_{suffix}` patterns.
   - **Non-slot tech type**: Column exists in expanded table AND has an `alt_` variant (e.g., `heating_system` exists and `alt_heating_system` also exists)

3. **Build lookup plan for each table**
   - **Passthrough tables**: All join columns are direct matches and value columns already have `_base`/`_alt` suffixes → single left-join, no column renaming
   - **Multi-lookup tables**: Tech-type join columns detected → generate one lookup per (slot, base/alt) combination. Each lookup remaps the join key and renames value columns with the appropriate slot number and suffix.

4. **Execute lookups and combine all inputs**
   - For each table, execute its lookup plan (single join or multiple lookups)
   - After all tables: each row has values for all required input parameters
   - Final table structure: [All archetype variables] + [All alternative variables] + [All scenario variables] + [Year] + [Weight] + [All input parameters with _base/_alt suffixes]

5. **Value column naming convention for multi-lookup**
   - Slot-expanded: insert slot number after first word, then append suffix. Example: `vehicle_purchase_cost` → `vehicle_1_purchase_cost_base`
   - Non-slot tech type: append suffix directly. Example: `hvac_equipment_cost` → `hvac_equipment_cost_base`

#### 3.5 Optimization Considerations

- **Memory management**: Input tables can be large if many archetype variables are used; monitor memory during joins
- **Join efficiency**: Join input tables with fewer variables first to reduce intermediate table sizes
- **Logging**: Track which input tables are loaded and how many archetypes they match
- **Year dimension**: Be mindful that including `year` variable can significantly increase table size

#### 3.6 Validation Rules

**Individual input parameter tables:**
- Input value column names must follow standardized naming convention
- All input values must be non-negative (except discount rate which must be positive)
- All `assumed_life` values must be >= 1 (to avoid division by zero in annualization)
- Efficiency values must be > 0 (except for vehicle `none` type where both gas and electric efficiency may be 0)
- Proportion values must be between 0 and 1
- For heating/DHW systems, sum of all fuel proportions must equal 1.0 for each archetype

**Cross-table validation:**
- No duplicate output parameter column names across tables
- For multi-lookup tables, validation is relaxed because raw column names differ from final output names; the primary coverage check is performed on the final output table

**Final joined table:**
- All required input parameters from section 3.3 must be present
- No missing values (every archetype × alternative × scenario × year combination must have all inputs)
- For each vehicle slot N and suffix s, EV charging percentages must sum to 1.0:
  - `ev_{N}_pct_charged_home_{s} + ev_{N}_pct_charged_level2_{s} + ev_{N}_pct_charged_fast_{s} = 1.0`

#### 3.7 Important Construction Constraints

Input parameter tables must be constructed with:

- **Complete coverage**: Every combination of join key values in the expanded table must have input values
- **Unique output names**: After multi-lookup expansion, each output parameter must be produced by exactly one table
- **Consistent units**: All monetary values in inflation-adjusted dollars, all energy in GJ, all energy costs in $/GJ
- **Baseline year consistency**: All monetary values should be adjusted to the same baseline year
- **Logical constraints**: Proportions sum to 1.0, efficiencies are realistic, shared inputs only defined once
- **Year handling**: If `year` is not present in an input table, values apply to all years
- **`none` vehicle handling**: Include `none` as a vehicle type in technology-type tables with all-zero values (`assumed_life` = 1 to avoid division by zero)

#### 3.8 Worked Example

**Expanded archetype table (from Step 2, simplified):**

Columns include: `dwelling_type`, `heating_system`, `climate_zone`, `vehicle_1_type`, `vehicle_1_category`, `vehicle_2_type`, `vehicle_2_category`, `alt_vehicle_1_category`, `alt_vehicle_2_category`, `alt_heating_system`, `scn_adoption`, `year`, `weight`

**Technology-type Input Table: vehicle_costs.csv**

| vehicle_type | vehicle_category | vehicle_purchase_cost | vehicle_assumed_life | vehicle_maintenance_cost_per_km |
| ------------ | ---------------- | --------------------- | -------------------- | ------------------------------- |
| car          | ICE              | 35000                 | 12                   | 0.08                            |
| car          | EV               | 42000                 | 15                   | 0.04                            |
| truck        | ICE              | 45000                 | 12                   | 0.09                            |
| truck        | EV               | 55000                 | 15                   | 0.05                            |
| none         | none             | 0                     | 1                    | 0.00                            |

Note: Keyed by both `vehicle_type` and `vehicle_category` (the two-level vehicle taxonomy). No `_base`/`_alt` suffix. Step 3 multi-lookup detects the slot pattern and joins this table four times, producing columns like `vehicle_1_purchase_cost_base`, `vehicle_1_purchase_cost_alt`, `vehicle_2_purchase_cost_base`, `vehicle_2_purchase_cost_alt`. For each lookup, the join matches both `vehicle_type` → `vehicle_{N}_type` and `vehicle_category` → `vehicle_{N}_category` (or their `alt_` variants).

**Technology-type Input Table: heating_system_efficiency.csv**

| heating_system | heating_system_proportion_gas | heating_system_efficiency_gas | ... | cooling_system_efficiency |
| -------------- | ----------------------------- | ----------------------------- | --- | ------------------------ |
| furnace        | 1.0                           | 0.92                          | ... | 3.5                      |
| heat_pump      | 0.0                           | 1.0                           | ... | 3.5                      |
| boiler         | 0.8                           | 0.85                          | ... | 3.0                      |

Step 3 joins this twice: once on `heating_system` (→ `_base` suffix) and once on `alt_heating_system` (→ `_alt` suffix).

**Context Input Table: shared_parameters.csv**

| year | cost_electricity_home | cost_natural_gas_home | ... | vkt_1_annual_base | vkt_1_annual_alt | vkt_2_annual_base | vkt_2_annual_alt | panel_assumed_life_base | panel_assumed_life_alt |
| ---- | --------------------- | --------------------- | --- | ----------------- | ---------------- | ----------------- | ---------------- | ----------------------- | ---------------------- |
| 2025 | 50.0                  | 20.0                  | ... | 15000             | 14500            | 10000             | 9500             | 30                      | 30                     |
| 2030 | 55.0                  | 22.0                  | ... | 15000             | 14000            | 10000             | 9000             | 30                      | 30                     |

This table already has explicit `_base`/`_alt` suffixes and direct join columns (`year`), so it is joined once as a passthrough.

**After joining all inputs**, each row has all archetype variables, all alternative variables, weight, and the complete set of ~140 input parameter columns needed for Step 4 calculations.

### Step 4: Energy Wallet Calculations

**Goal:** Compute the total annualized energy wallet cost for each household archetype under both baseline and alternative configurations, enabling direct cost comparison.

#### 4.1 Conceptual Framework

The energy wallet represents the total annual cost a household faces for its direct energy needs. It is the sum of four major cost categories:

1. **Vehicle costs** (slots 1 and 2): Capital, maintenance, gasoline, and electricity for each vehicle
2. **HVAC costs**: Capital, maintenance, heating fuel (5 fuel types), and cooling
3. **DHW costs**: Capital, maintenance, and fuel (5 fuel types)
4. **Other costs**: Residual electricity and natural gas consumption, utility fixed charges, and electrical panel upgrades

Each category is computed independently for both `base` and `alt` configurations using the input parameters attached in Step 3. The model then calculates the absolute and percentage difference between the two configurations for each archetype.

**Excluding vehicle 2 from a study:** The model requires vehicle 2 archetype and input parameter tables to exist because Step 4 references vehicle 2 input parameters directly. For studies that do not require a second vehicle, define a single archetype table for vehicle 2 with all households assigned to `vehicle_2_type = none` (`population_share = 1.0`) and a corresponding vehicle 2 category table mapping `none → none`. This produces all-zero vehicle 2 costs and effectively excludes it from the analysis.

#### 4.2 Annualized Capital Cost Formula

Equipment capital costs are annualized using the standard PMT (payment) formula so that upfront investments can be compared on an equal annual basis with recurring costs:

```
annualized_cost = purchase_cost × rate / (1 - (1 + rate)^{-life})
```

Where:
- `purchase_cost` = upfront equipment cost ($)
- `rate` = discount rate (decimal, e.g. 0.03)
- `life` = expected useful life (years)

**Edge cases:**
- If `purchase_cost = 0`: returns 0 (no cost to annualize)
- If `life ≤ 0`: returns 0 (guards against bad data)
- If `rate = 0`: formula is undefined; guarded in implementation

This formula is applied to: vehicle purchase cost, HVAC equipment cost, DHW equipment cost, and panel upgrade cost.

#### 4.3 Vehicle Cost Calculations

Vehicle costs are computed per slot (N=1,2) and per configuration (base, alt). The `none` vehicle type (for single-vehicle households) produces all-zero costs.

**Capital:**
```
vehicle_{N}_annual_capital_{s} = PMT(vehicle_{N}_purchase_cost_{s}, discount_rate, vehicle_{N}_assumed_life_{s})
```

**Maintenance:**
```
vehicle_{N}_annual_maintenance_{s} = vehicle_{N}_maintenance_cost_per_km_{s} × vkt_{N}_annual_{s}
```

**Gasoline cost:**
```
vehicle_{N}_gas_energy_gj_{s} = vehicle_{N}_efficiency_gas_{s} × vkt_{N}_annual_{s}
vehicle_{N}_gas_cost_{s} = vehicle_{N}_gas_energy_gj_{s} × cost_gasoline
```

For ICE vehicles, `efficiency_gas` is in GJ/km (positive), so `gas_energy_gj` gives total annual gasoline consumption. For EVs, `efficiency_gas = 0`, and for ICE vehicles, `efficiency_electric = 0`. These constraints are enforced through input data construction rather than runtime validation — incorrect input values (e.g., non-zero `efficiency_gas` for an EV) will produce erroneous but non-failing results.

**EV electricity cost:**
```
ev_energy_kwh = vehicle_{N}_efficiency_electric_{s} × vkt_{N}_annual_{s}
ev_energy_kwh_derated = ev_energy_kwh / ev_{N}_efficiency_factor_{s}
ev_energy_gj = ev_energy_kwh_derated × 0.0036

vehicle_{N}_ev_cost_{s} = ev_energy_gj × weighted_price
```

Where:
- `efficiency_electric` is in kWh/km (0 for ICE vehicles)
- `ev_efficiency_factor` is a cold-climate derating factor (≤ 1.0; dividing increases consumption)
- `0.0036` converts kWh to GJ
- `weighted_price = pct_home × cost_electricity_home + pct_l2 × cost_electricity_level2 + pct_fast × cost_electricity_fast`

For Step 5's utility bill perspective, EV costs are also split into home vs. public charging:
```
vehicle_{N}_ev_cost_home_{s} = ev_energy_gj × pct_home × cost_electricity_home
vehicle_{N}_ev_cost_public_{s} = ev_energy_gj × (pct_l2 × cost_electricity_level2 + pct_fast × cost_electricity_fast)
```

**Vehicle total:**
```
vehicle_{N}_total_cost_{s} = annual_capital + annual_maintenance + gas_cost + ev_cost
vehicles_total_cost_{s} = vehicle_1_total_cost_{s} + vehicle_2_total_cost_{s}
```

#### 4.4 HVAC Cost Calculations

HVAC costs include equipment capital, maintenance, heating fuel consumption across 5 fuel types, and cooling.

**Capital and maintenance:**
```
hvac_annual_capital_{s} = PMT(hvac_equipment_cost_{s}, discount_rate, hvac_assumed_life_{s})
hvac_annual_maintenance_{s} = hvac_maintenance_cost_annual_{s}  (direct input)
```

**Heating fuel costs** (for each fuel in {gas, electric, oil, propane, wood}):
```
energy_{fuel} = heating_load_annual_{s} × proportion_{fuel}_{s} / efficiency_{fuel}_{s}
cost_{fuel} = energy_{fuel} × price_{fuel}
```

Where:
- `proportion_{fuel}` = fraction of heating load met by this fuel (sums to 1.0 across all fuels)
- `efficiency_{fuel}` = system efficiency for this fuel (e.g., 0.92 for gas furnace, 3.0 for heat pump)
- `price_{fuel}` = cost per GJ of fuel (from shared parameters)

**Division-by-zero handling:** `np.where(proportion > 0, load × proportion / efficiency, 0)` — only calculates where the fuel is actually used.

**Cooling cost** (always electric):
```
cooling_energy = cooling_load_annual_{s} / cooling_system_efficiency_{s}
hvac_cooling_cost_{s} = cooling_energy × cost_electricity_home
```

**HVAC total:**
```
hvac_total_cost_{s} = annual_capital + annual_maintenance + sum(heating_fuel_costs) + cooling_cost
```

#### 4.5 DHW Cost Calculations

DHW costs follow the same pattern as HVAC heating: equipment capital, maintenance, and fuel costs across the same 5 fuel types.

**Capital and maintenance:**
```
dhw_annual_capital_{s} = PMT(dhw_equipment_cost_{s}, discount_rate, dhw_assumed_life_{s})
dhw_annual_maintenance_{s} = dhw_maintenance_cost_annual_{s}  (direct input)
```

**Fuel costs** (for each fuel in {gas, electric, oil, propane, wood}):
```
dhw_energy_{fuel} = dhw_load_annual_{s} × proportion_{fuel}_{s} / efficiency_{fuel}_{s}
dhw_cost_{fuel} = dhw_energy_{fuel} × price_{fuel}
```

**DHW total:**
```
dhw_total_cost_{s} = annual_capital + annual_maintenance + sum(fuel_costs)
```

#### 4.6 Other Costs

Other costs capture residual energy consumption, utility fixed charges, and panel upgrades.

**Other energy usage:**
```
other_electricity_cost_{s} = other_electricity_annual_{s} × cost_electricity_home
other_natural_gas_cost_{s} = other_natural_gas_annual_{s} × cost_natural_gas_home
```

**Fixed charges:**
```
electricity_fixed_charge_{s} = electricity_fixed_charge_monthly × 12
```

The natural gas fixed charge is conditional — it only applies if the household uses any natural gas in this configuration:
```
uses_gas = (heating_proportion_gas_{s} > 0) OR (dhw_proportion_gas_{s} > 0) OR (other_natural_gas_annual_{s} > 0)
natural_gas_fixed_charge_{s} = natural_gas_fixed_charge_monthly × 12 × uses_gas
```

This means a household that fully electrifies (no gas heating, no gas DHW, no other gas use) avoids the natural gas fixed charge in the alternative configuration.

**Panel upgrade (annualized):**
```
panel_annual_capital_{s} = PMT(panel_upgrade_cost_{s}, discount_rate, panel_assumed_life_{s})
```

**Other total:**
```
other_total_cost_{s} = other_electricity_cost + other_natural_gas_cost + electricity_fixed_charge + natural_gas_fixed_charge + panel_annual_capital
```

#### 4.7 Energy Wallet Totals and Comparison

**Grand total for each configuration:**
```
energy_wallet_{s} = vehicles_total_cost_{s} + hvac_total_cost_{s} + dhw_total_cost_{s} + other_total_cost_{s}
```

**Sub-totals by domain:**
```
energy_wallet_vehicle_{s} = vehicles_total_cost_{s}
energy_wallet_home_{s} = hvac_total_cost_{s} + dhw_total_cost_{s} + other_total_cost_{s}
```

**Comparison metrics:**
```
energy_wallet_diff_absolute = energy_wallet_alt - energy_wallet_base
energy_wallet_diff_percent = (energy_wallet_alt - energy_wallet_base) / energy_wallet_base × 100
energy_wallet_vehicle_diff_absolute = energy_wallet_vehicle_alt - energy_wallet_vehicle_base
energy_wallet_home_diff_absolute = energy_wallet_home_alt - energy_wallet_home_base
```

A negative difference indicates the alternative configuration is cheaper; a positive difference indicates it is more expensive.

#### 4.8 Output Structure

Step 4 adds the following categories of columns to the model inputs table:

- **Per-vehicle-slot intermediates** (×2 slots × 2 suffixes): `vehicle_{N}_{s}_annual_capital`, `vehicle_{N}_{s}_annual_maintenance`, `vehicle_{N}_{s}_gas_energy_gj`, `vehicle_{N}_{s}_gas_cost`, `vehicle_{N}_{s}_ev_energy_gj`, `vehicle_{N}_{s}_ev_cost`, `vehicle_{N}_{s}_ev_cost_home`, `vehicle_{N}_{s}_ev_cost_public`, `vehicle_{N}_{s}_fuel_cost`, `vehicle_{N}_{s}_total_cost`
- **HVAC intermediates** (×2 suffixes): `hvac_{s}_annual_capital`, `hvac_{s}_annual_maintenance`, `hvac_{s}_heating_{fuel}_energy_gj` (×5 fuels), `hvac_{s}_heating_{fuel}_cost` (×5 fuels), `hvac_{s}_cooling_energy_gj`, `hvac_{s}_cooling_cost`, `hvac_{s}_heating_cost`, `hvac_{s}_total_cost`
- **DHW intermediates** (×2 suffixes): `dhw_{s}_annual_capital`, `dhw_{s}_annual_maintenance`, `dhw_{s}_{fuel}_energy_gj` (×5 fuels), `dhw_{s}_{fuel}_cost` (×5 fuels), `dhw_{s}_fuel_cost`, `dhw_{s}_total_cost`
- **Other cost intermediates** (×2 suffixes): `other_{s}_electricity_cost`, `other_{s}_natural_gas_cost`, `other_{s}_electricity_fixed_charge`, `other_{s}_natural_gas_fixed_charge`, `other_{s}_panel_annual_capital`, `other_{s}_total_cost`
- **Aggregates** (×2 suffixes): `vehicles_{s}_total_cost`, `energy_wallet_vehicle_{s}`, `energy_wallet_home_{s}`, `energy_wallet_{s}`
- **Comparison**: `energy_wallet_diff_absolute`, `energy_wallet_diff_percent`, `energy_wallet_vehicle_diff_absolute`, `energy_wallet_home_diff_absolute`

#### 4.9 Validation

- All intermediate cost values should be ≥ 0
- `energy_wallet_{s}` should equal the sum of its four component totals
- `energy_wallet_diff_absolute` should equal `energy_wallet_alt - energy_wallet_base`
- Population weights are unchanged — they pass through Step 4 without modification

### Step 5: Utility Bill Perspective Analysis

**Goal:** Re-aggregate the cost intermediates from Step 4 into categories that correspond to real-world utility bills and expense categories, enabling analysis from the perspective of what a household actually pays on each bill.

#### 5.1 Conceptual Framework

While Step 4 organizes costs by equipment system (vehicles, HVAC, DHW, other), households experience costs through their utility bills and payment categories. Step 5 re-slices the same total cost into categories that answer: "How much does this household pay on their electricity bill? Their natural gas bill? At the gas pump?"

This perspective is valuable for:
- **Policy analysis**: Understanding how electricity rates affect household costs when combined with electrification
- **Utility planning**: Projecting changes in electricity and gas demand from technology transitions
- **Consumer impact**: Showing households which bills increase or decrease
- **Equity analysis**: Identifying which energy cost categories disproportionately affect specific household types

#### 5.2 Utility Bill Categories

For each configuration (base and alt), Step 5 produces the following categories:

**`utility_bill_electricity_{s}`** — The household electricity bill:
- HVAC electric heating cost
- HVAC cooling cost (always electric)
- DHW electric heating cost
- Other household electricity cost
- Electricity fixed charge
- Home EV charging cost (both vehicle slots)
- **Excludes** public EV charging (L2 and fast charger costs)

**`utility_bill_natural_gas_{s}`** — The household natural gas bill:
- HVAC gas heating cost
- DHW gas heating cost
- Other household natural gas cost
- Natural gas fixed charge (conditional — only if gas is used)

**`utility_bill_oil_{s}`** — Oil/heating fuel delivery:
- HVAC oil heating cost
- DHW oil heating cost

**`utility_bill_propane_{s}`** — Propane delivery:
- HVAC propane heating cost
- DHW propane heating cost

**`utility_bill_wood_{s}`** — Wood fuel:
- HVAC wood heating cost
- DHW wood heating cost

**`utility_bill_gasoline_{s}`** — Gasoline purchases:
- Vehicle gasoline costs (both vehicle slots)

**`utility_bill_public_ev_charging_{s}`** — Public EV charging:
- Level 2 and fast charging costs (both vehicle slots)
- Separated from the electricity bill because these are paid at charging stations, not on the home electricity bill

#### 5.3 Reconciliation

Step 5 computes capital and maintenance totals *internally* for cross-step verification (they are NOT output columns, since they are not utility bills). The reconciliation check verifies:

```
utility_bill_total_{s} + capital + maintenance = energy_wallet_{s}
```

where `utility_bill_total_{s}` is the sum of the 7 energy bill categories, and capital/maintenance are computed locally from Step 4 intermediate columns. The model checks this automatically and logs a warning if the maximum discrepancy exceeds $0.01.

#### 5.4 Comparison Metrics

For each utility bill category, Step 5 also computes the difference between configurations:

```
utility_bill_{category}_diff = utility_bill_{category}_alt - utility_bill_{category}_base
```

This enables analysis of which specific bills increase or decrease under the alternative configuration. For example, a household switching from a gas furnace to a heat pump would typically see:
- `utility_bill_electricity_diff > 0` (electricity bill increases)
- `utility_bill_natural_gas_diff < 0` (gas bill decreases or disappears)
- The net effect depends on relative fuel prices and equipment efficiencies

#### 5.5 Output Structure

Step 5 adds the following columns to the Step 4 output:

- **Per-category costs** (×2 suffixes each): `utility_bill_electricity_{s}`, `utility_bill_natural_gas_{s}`, `utility_bill_oil_{s}`, `utility_bill_propane_{s}`, `utility_bill_wood_{s}`, `utility_bill_gasoline_{s}`, `utility_bill_public_ev_charging_{s}`, `utility_bill_total_{s}`
- **Difference columns** (one per category): `utility_bill_{category}_diff` for each of the 8 categories above (7 energy types + total)

---

## Appendix A: Data Dictionary

All model parameters and outputs. `{N}` = vehicle slot (1 or 2), `{s}` = configuration suffix (`base` or `alt`), `{fuel}` = one of {gas, electric, oil, propane, wood}.

### A.1 Input Parameters (Step 3)

#### Shared Parameters (no _base/_alt suffix)

| Parameter | Description | Units |
|-----------|-------------|-------|
| `cost_electricity_home` | Cost of electricity at home | $/GJ |
| `cost_natural_gas_home` | Cost of natural gas at home | $/GJ |
| `cost_oil_home` | Cost of heating oil at home | $/GJ |
| `cost_propane_home` | Cost of propane at home | $/GJ |
| `cost_wood_home` | Cost of wood fuel at home | $/GJ |
| `cost_gasoline` | Cost of gasoline | $/GJ |
| `cost_electricity_level2` | Cost of electricity at Level 2 public charger | $/GJ |
| `cost_electricity_fast` | Cost of electricity at DC fast charger | $/GJ |
| `discount_rate` | Discount rate for annualizing capital costs | decimal |
| `electricity_fixed_charge_monthly` | Monthly electricity service fixed charge | $/month |
| `natural_gas_fixed_charge_monthly` | Monthly natural gas service fixed charge | $/month |

#### Vehicle Parameters (per slot N, per configuration s)

| Parameter | Description | Units |
|-----------|-------------|-------|
| `vehicle_{N}_purchase_cost_{s}` | Upfront vehicle purchase cost | $ |
| `vehicle_{N}_assumed_life_{s}` | Expected vehicle lifespan | years |
| `vehicle_{N}_maintenance_cost_per_km_{s}` | Vehicle maintenance cost per kilometer | $/km |
| `vehicle_{N}_efficiency_gas_{s}` | Gasoline energy consumption per km (0 for EVs) | GJ/km |
| `vehicle_{N}_efficiency_electric_{s}` | Electric energy consumption per km (0 for ICE) | kWh/km |
| `ev_{N}_efficiency_factor_{s}` | Cold climate EV efficiency derating factor | decimal (0-1) |
| `ev_{N}_pct_charged_home_{s}` | Proportion of EV charging at home | decimal (0-1) |
| `ev_{N}_pct_charged_level2_{s}` | Proportion of EV charging at Level 2 public | decimal (0-1) |
| `ev_{N}_pct_charged_fast_{s}` | Proportion of EV charging at DC fast charger | decimal (0-1) |
| `vkt_{N}_annual_{s}` | Annual vehicle kilometers traveled | km/year |

#### HVAC Parameters (per configuration s)

| Parameter | Description | Units |
|-----------|-------------|-------|
| `hvac_equipment_cost_{s}` | HVAC equipment purchase + installation cost | $ |
| `hvac_assumed_life_{s}` | Expected HVAC equipment lifespan | years |
| `hvac_maintenance_cost_annual_{s}` | Annual HVAC maintenance cost | $/year |
| `heating_load_annual_{s}` | Annual heating load (independent of system efficiency) | GJ/year |
| `cooling_load_annual_{s}` | Annual cooling load (independent of system efficiency) | GJ/year |
| `heating_system_proportion_{fuel}_{s}` | Proportion of heating load met by fuel type | decimal (0-1) |
| `heating_system_efficiency_{fuel}_{s}` | Heating system efficiency for fuel type | decimal |
| `cooling_system_efficiency_{s}` | Cooling system efficiency (COP) | decimal |

#### DHW Parameters (per configuration s)

| Parameter | Description | Units |
|-----------|-------------|-------|
| `dhw_equipment_cost_{s}` | DHW equipment purchase + installation cost | $ |
| `dhw_assumed_life_{s}` | Expected DHW equipment lifespan | years |
| `dhw_maintenance_cost_annual_{s}` | Annual DHW maintenance cost | $/year |
| `dhw_load_annual_{s}` | Annual hot water load (independent of system efficiency) | GJ/year |
| `dhw_system_proportion_{fuel}_{s}` | Proportion of DHW load met by fuel type | decimal (0-1) |
| `dhw_system_efficiency_{fuel}_{s}` | DHW system efficiency for fuel type | decimal |

#### Other Energy Use and Miscellaneous (per configuration s)

| Parameter | Description | Units |
|-----------|-------------|-------|
| `other_electricity_annual_{s}` | Other annual electricity consumption | GJ/year |
| `other_natural_gas_annual_{s}` | Other annual natural gas consumption | GJ/year |
| `panel_upgrade_cost_{s}` | Electrical panel upgrade cost (if required) | $ |
| `panel_assumed_life_{s}` | Panel upgrade expected useful life | years |

### A.2 Step 4 Outputs: Energy Wallet Calculations

#### Vehicle Intermediates (per slot N, per configuration s)

| Output | Description | Units |
|--------|-------------|-------|
| `vehicle_{N}_{s}_annual_capital` | Annualized vehicle purchase cost (PMT) | $/year |
| `vehicle_{N}_{s}_annual_maintenance` | Annual vehicle maintenance cost | $/year |
| `vehicle_{N}_{s}_gas_energy_gj` | Annual gasoline energy consumption | GJ/year |
| `vehicle_{N}_{s}_gas_cost` | Annual gasoline cost | $/year |
| `vehicle_{N}_{s}_ev_energy_gj` | Annual EV energy consumption (climate-derated) | GJ/year |
| `vehicle_{N}_{s}_ev_cost` | Total annual EV electricity cost | $/year |
| `vehicle_{N}_{s}_ev_cost_home` | Annual EV home charging cost | $/year |
| `vehicle_{N}_{s}_ev_cost_public` | Annual EV public charging cost (L2 + fast) | $/year |
| `vehicle_{N}_{s}_fuel_cost` | Total annual vehicle fuel cost (gas + EV) | $/year |
| `vehicle_{N}_{s}_total_cost` | Total annual vehicle cost | $/year |

#### HVAC Intermediates (per configuration s)

| Output | Description | Units |
|--------|-------------|-------|
| `hvac_{s}_annual_capital` | Annualized HVAC equipment cost (PMT) | $/year |
| `hvac_{s}_annual_maintenance` | Annual HVAC maintenance cost | $/year |
| `hvac_{s}_heating_{fuel}_energy_gj` | Annual heating energy by fuel type | GJ/year |
| `hvac_{s}_heating_{fuel}_cost` | Annual heating cost by fuel type | $/year |
| `hvac_{s}_heating_cost` | Total annual heating cost (all fuels) | $/year |
| `hvac_{s}_cooling_energy_gj` | Annual cooling energy consumption | GJ/year |
| `hvac_{s}_cooling_cost` | Annual cooling cost | $/year |
| `hvac_{s}_total_cost` | Total annual HVAC cost | $/year |

#### DHW Intermediates (per configuration s)

| Output | Description | Units |
|--------|-------------|-------|
| `dhw_{s}_annual_capital` | Annualized DHW equipment cost (PMT) | $/year |
| `dhw_{s}_annual_maintenance` | Annual DHW maintenance cost | $/year |
| `dhw_{s}_{fuel}_energy_gj` | Annual DHW energy by fuel type | GJ/year |
| `dhw_{s}_{fuel}_cost` | Annual DHW cost by fuel type | $/year |
| `dhw_{s}_fuel_cost` | Total annual DHW fuel cost (all fuels) | $/year |
| `dhw_{s}_total_cost` | Total annual DHW cost | $/year |

#### Other Cost Intermediates (per configuration s)

| Output | Description | Units |
|--------|-------------|-------|
| `other_{s}_electricity_cost` | Annual other electricity cost | $/year |
| `other_{s}_natural_gas_cost` | Annual other natural gas cost | $/year |
| `other_{s}_electricity_fixed_charge` | Annual electricity fixed charge | $/year |
| `other_{s}_natural_gas_fixed_charge` | Annual NG fixed charge (0 if no gas usage) | $/year |
| `other_{s}_panel_annual_capital` | Annualized panel upgrade cost (PMT) | $/year |
| `other_{s}_total_cost` | Total annual other costs | $/year |

#### Aggregates and Comparison

| Output | Description | Units |
|--------|-------------|-------|
| `vehicles_{s}_total_cost` | Total annual cost for both vehicle slots | $/year |
| `energy_wallet_vehicle_{s}` | Energy wallet vehicle sub-total | $/year |
| `energy_wallet_home_{s}` | Energy wallet home sub-total (HVAC + DHW + Other) | $/year |
| `energy_wallet_{s}` | Grand total annual energy cost | $/year |
| `energy_wallet_diff_absolute` | Alt minus base total energy wallet | $/year |
| `energy_wallet_diff_percent` | Percent change from base to alt | % |
| `energy_wallet_vehicle_diff_absolute` | Alt minus base vehicle sub-total | $/year |
| `energy_wallet_home_diff_absolute` | Alt minus base home sub-total | $/year |

### A.3 Step 5 Outputs: Utility Bill Perspective

#### Per-Category Costs (per configuration s)

| Output | Description | Units |
|--------|-------------|-------|
| `utility_bill_electricity_{s}` | Home electricity bill (HVAC electric + cooling + DHW electric + other electricity + home EV charging + electricity fixed charge) | $/year |
| `utility_bill_natural_gas_{s}` | Natural gas bill (HVAC gas + DHW gas + other NG + NG fixed charge) | $/year |
| `utility_bill_oil_{s}` | Heating oil bill (HVAC oil + DHW oil) | $/year |
| `utility_bill_propane_{s}` | Propane bill (HVAC propane + DHW propane) | $/year |
| `utility_bill_wood_{s}` | Wood fuel bill (HVAC wood + DHW wood) | $/year |
| `utility_bill_gasoline_{s}` | Gasoline purchases (both vehicle slots) | $/year |
| `utility_bill_public_ev_charging_{s}` | Public EV charging (L2 + fast, both slots) | $/year |
| `utility_bill_total_{s}` | Sum of 7 energy bill categories | $/year |

#### Difference Columns

| Output | Description | Units |
|--------|-------------|-------|
| `utility_bill_electricity_diff` | Alt minus base electricity bill | $/year |
| `utility_bill_natural_gas_diff` | Alt minus base natural gas bill | $/year |
| `utility_bill_oil_diff` | Alt minus base oil bill | $/year |
| `utility_bill_propane_diff` | Alt minus base propane bill | $/year |
| `utility_bill_wood_diff` | Alt minus base wood bill | $/year |
| `utility_bill_gasoline_diff` | Alt minus base gasoline purchases | $/year |
| `utility_bill_public_ev_charging_diff` | Alt minus base public EV charging | $/year |
| `utility_bill_total_diff` | Alt minus base total energy bills | $/year |