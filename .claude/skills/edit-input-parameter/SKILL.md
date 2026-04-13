---
name: edit-input-parameter
description: |
  Edit or create an input parameter CSV file in an Energy Wallet data product.
  Guides analysts through technology-type and context tables with coverage
  validation, unit checking, and data integrity enforcement.
---

# Edit Input Parameter

You are helping an analyst edit or create an input parameter table in an Energy Wallet data product.

## Data Integrity Rules — Non-Negotiable

These rules override all other instructions. Violating any rule is a skill failure.

1. **NEVER fabricate data.** If the analyst's source doesn't provide a value, do not invent one. Ask the analyst or flag as a gap.
2. **NEVER add granularity the source data doesn't support.** If the source has one cost for all dwelling types, do not replicate it into four identical rows. Either get real differentiated data or keep the table simpler.
3. **NEVER proceed with a data decision without explicit analyst confirmation.** Propose options and explain trade-offs. The analyst decides. No silent defaults.
4. **EVERY value must have a documented source.** When writing or updating a CSV, the `.meta.yaml` source fields must document where the data came from — including data provided verbally in conversation.
5. **EVERY assumption or approximation must be confirmed and documented.** Before applying any simplification (e.g., "same cost for all dwelling types"), explicitly ask the analyst to confirm. Document it in `.meta.yaml` notes.
6. **ALWAYS show the analyst the exact data being written before writing it.** No changes to CSV files without the analyst reviewing the values.
7. **If data is a placeholder, use the `PLACEHOLDER:` prefix in `.meta.yaml` notes.** Never disguise placeholder data as real data.

## Domain Knowledge

**Two table types:**

1. **Technology-type tables** (e.g., `hvac_costs.csv`, `heating_loads.csv`): Keyed by generic archetype variable names (e.g., `hvac_system`, not `hvac_system_base`). The Step 3 multi-lookup engine auto-expands these into `_base`/`_alt` suffixed columns. Column names do NOT have slot numbers or `_base`/`_alt` suffixes.
   - Example: `hvac_costs.csv` with keys `[dwelling_type, hvac_system]` — the pipeline joins this once for baseline systems and once for alternative systems.

2. **Context tables** (e.g., `costs_home_energy.csv`, `discount_rate.csv`): Have explicit value columns (not keyed by technology variables). Joined once as passthrough.
   - Example: `costs_home_energy.csv` with key `[year]` — energy prices that apply to all archetypes.

**Key relationships:**
- Technology-type table join keys must match values from archetype tables (for baseline) AND alt config tables (for alternative)
- Every combination of key values that appears in the expanded archetypes must have a matching row
- Some tables are year-varying (have a `year` column), others are static

**Authoritative unit specification:** `configs/model_units.json` defines the required unit for every numeric parameter the model uses in calculations. **Always read this file** when validating or converting units — do not rely on meta.yaml unit labels, which may be outdated or incorrect.

## Workflow: Editing an Existing Input Parameter File

### Phase 1: Understand Current State

1. Read the target CSV file and its `.meta.yaml`
2. Determine table type:
   - Read the `.meta.yaml` keys. If keys include a variable that also exists as an archetype table (e.g., `hvac_system`, `dwelling_type`), it's a **technology-type table**.
   - If keys are only context variables (e.g., `year` alone, or no archetype variables), it's a **context table**.
3. For technology-type tables, identify which archetype and alt config values need coverage:
   - Read the corresponding archetype `.meta.yaml` to get baseline values
   - Use Glob to find alt config `.meta.yaml` files; read any that introduce alternative values for the same variable
   - Build the complete list of values that need rows in this table
4. Summarize to the analyst:
   - "This is a **{technology-type / context}** table with keys **{keys}**"
   - "Value columns: {list with units}"
   - "Source: {source.name} — {source.detail}"
   - For technology-type tables: "This table needs rows for these {variable} values: {complete list including both baseline and alternative values}"
   - Current coverage: "Has data for {N} of {M} required values. Missing: {list}" (or "Full coverage" if complete)
   - If notes contain `PLACEHOLDER:` prefix, flag it

### Phase 2: Understand the Change

5. Ask the analyst what they want to change (one question at a time):
   - New values for existing rows? (updated data)
   - Adding rows for new technologies? (e.g., a new HVAC system was added to archetypes)
   - Adding a new conditioning variable? (e.g., making costs vary by climate zone)
   - Adding year-varying data where it was static? (adding a `year` column)
   - Changing units or methodology?

### Phase 3: Check Coverage

6. For technology-type tables, check that the analyst's data covers all required key combinations:
   - Read the archetype table(s) for each key variable to get the full value lists
   - Read alt config tables to get alternative values
   - Compute the Cartesian product of all key values — this is the set of required rows
   - Compare against the analyst's data
   - Report gaps explicitly: "Your data covers {N} of {M} required {variable} values. These {M-N} need values: {list}"
   - Options for gaps (present to analyst — do NOT choose for them):
     - Analyst provides the missing data
     - Use a documented proxy value with analyst approval (document in `.meta.yaml` notes with explanation)
     - Flag as `PLACEHOLDER:` in notes for later resolution
   - **Never fill gaps with fabricated values**

### Phase 4: Validate Units

7. Confirm the analyst's data matches required units:
   - Read `configs/model_units.json` to get the **authoritative required unit** for each value column. Match column names against parameter keys (using `{N}` for slot and `{s}` for suffix template patterns).
   - Ask the analyst what units their source data is in
   - If units match: confirm explicitly ("Your data is in {unit}, which matches the model's required unit from model_units.json.")
   - If conversion needed: show the conversion formula and result for a sample value, ask the analyst to confirm before applying. Example: "Your data is in kWh/year. The model requires GJ/year (per model_units.json). Converting: {value} kWh × 0.0036 GJ/kWh = {result} GJ. Apply this conversion to all values?"
   - **Never silently convert units**
   - If the `.meta.yaml` unit label disagrees with `model_units.json`, trust `model_units.json` and update the `.meta.yaml` to match

### Phase 5: Explain Downstream Impact

8. Before making changes, explain:
   - For technology-type tables: "These parameters are used in Step 4 calculations for {domain: vehicle costs / HVAC costs / DHW costs / other costs}."
   - If adding a conditioning variable: "This changes how Step 3 joins this table — it will now match on {keys} instead of {old_keys}."
   - For value changes: characterize the magnitude. Example: "Changing electricity rate from $0.124 to $0.15/kWh increases the rate by ~21%. This will affect all electric heating and cooling cost calculations."

### Phase 6: Build, Confirm, and Write

9. Generate the complete CSV content.
   - For small tables (≤20 rows): show the complete table
   - For large tables (>20 rows): show a summary of the structure + highlight the specific rows that changed or were added
10. **Wait for explicit analyst approval before writing.**
11. Write the CSV file.

### Phase 7: Update Metadata

12. Update the `.meta.yaml` file:
    - `source.name` and `source.detail` — from the analyst's data source
    - For categorical columns: update `values` lists to match the CSV's unique values (sorted)
    - For numeric columns: update `range` to match actual [min, max] in the CSV
    - `unit` — update if units changed (with analyst confirmation)
    - `notes` — add any caveats, conversion details, proxy explanations; remove `PLACEHOLDER:` prefix if real data replaces placeholder
    - `description` — update if the scope changed
    - Do NOT change `title`, `question`, or `topic` unless the analyst explicitly requests it

### Phase 8: Validate and Report

13. Run `/validate-data-product <data_product_name>` — report results to the analyst
14. Run `/generate-readmes <data_product_name>` — report results
15. Summarize:
    - Files modified: {list}
    - Validation result: pass/fail with details
    - Coverage status: "Full coverage" or "Gaps remaining for: {list}"
    - If gaps remain, list what needs to be done to resolve them

## Workflow: Creating a New Input Parameter File

### Phase 1: Gather Requirements

1. Read `inputs/<data_product>/datapackage.yaml` for topics
2. Use Glob to list existing input parameter CSVs
3. Read archetype and alt config `.meta.yaml` files to understand available variables
4. Ask the analyst (one question at a time):
   - "What parameter are you adding?" (e.g., "insulation costs")
   - "What are the join keys?" (which archetype variables does it depend on?)
   - "Is this year-varying?" (does it have a `year` column?)
   - "What are the value columns and their units?" (e.g., `insulation_cost` in `$`, `insulation_life` in `years`)

### Phase 2: Validate Structure

5. Check that key variables exist as archetype tables or are recognized context variables (`year`)
6. Check that the column names don't conflict with existing columns in other input parameter CSVs
7. Compute the required row count from the Cartesian product of key values (including both baseline and alternative values for technology-type keys)
8. Report: "This table will need {N} rows to cover all key combinations."

### Phase 3: Build the Table

9. Follow the same coverage checks as editing (Phase 3 above)
10. Follow the same unit validation (Phase 4 above)
11. Show the complete CSV for analyst approval

### Phase 4: Create Files

12. Write the CSV file to `inputs/<data_product>/input_parameters/{parameter_name}.csv`
13. Run `/scaffold-table inputs/<data_product>/input_parameters/{parameter_name}.csv` to generate the `.meta.yaml` template
14. Fill in the `.meta.yaml` from conversation context:
    - `title`, `question`, `topic` — ask the analyst if not obvious from context
    - `source.name`, `source.detail` — from the analyst's data source
    - `description` — what parameter this provides
    - Column values, units, ranges — from the actual data

### Phase 5: Validate and Report

15. Run `/validate-data-product <data_product_name>` — report results
16. Run `/generate-readmes <data_product_name>` — report results
17. Summarize files created and coverage status
