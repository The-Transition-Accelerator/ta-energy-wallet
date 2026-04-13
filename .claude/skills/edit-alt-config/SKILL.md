---
name: edit-alt-config
description: |
  Edit or create an alternative configuration CSV file in an Energy Wallet
  data product. Guides analysts through baseline-to-alternative mappings
  with adoption shares, feasibility checks, and data integrity enforcement.
---

# Edit Alternative Configuration

You are helping an analyst edit or create an alternative configuration table in an Energy Wallet data product.

## Data Integrity Rules — Non-Negotiable

These rules override all other instructions. Violating any rule is a skill failure.

1. **NEVER fabricate data.** If the analyst's source doesn't provide a value, do not invent one. Ask the analyst or flag as a gap.
2. **NEVER add granularity the source data doesn't support.** If the source has one adoption share for all baseline systems, do not split it into different shares per system without real data. Either get real differentiated data or keep the table simpler.
3. **NEVER proceed with a data decision without explicit analyst confirmation.** Propose options and explain trade-offs. The analyst decides. No silent defaults.
4. **EVERY value must have a documented source.** When writing or updating a CSV, the `.meta.yaml` source fields must document where the data came from — including data provided verbally in conversation.
5. **EVERY assumption or approximation must be confirmed and documented.** Before applying any simplification (e.g., "same adoption share for all baseline systems"), explicitly ask the analyst to confirm. Document it in `.meta.yaml` notes.
6. **ALWAYS show the analyst the exact data being written before writing it.** No changes to CSV files without the analyst reviewing the values.
7. **If data is a placeholder, use the `PLACEHOLDER:` prefix in `.meta.yaml` notes.** Never disguise placeholder data as real data.

## Domain Knowledge

**Alternative configuration file structure:**
- Each CSV maps a baseline archetype value to an alternative value with an `adoption_share`
- The baseline column must match an existing archetype variable (e.g., `hvac_system`)
- The alternative column is prefixed with `alt_` (e.g., `alt_hvac_system`)
- Adoption shares can vary by `year` column (for time-varying transitions)
- Not every baseline value needs an upgrade path — values without rows keep their baseline configuration at 100%
- For a given baseline value (and year, if year-varying), adoption shares across all alternative rows should sum to ≤ 1.0

**Example:** `alternative_configurations/alt_hvac_system.csv` maps `hvac_system` → `alt_hvac_system` with `adoption_share`. A row like `non-condensing gas wo AC, ashp w gas backup, 1.0` means 100% of households with that baseline system adopt the heat pump alternative.

**Downstream relationships:**
- Baseline values must be a subset of values in the corresponding archetype table
- Alternative values must have matching entries in relevant input parameter tables (costs, efficiencies, loads)
- Adoption shares interact with population weights in Step 2 — they split the weight
- Adding new alternative values increases the expanded archetype count

## Workflow: Editing an Existing Alt Config File

### Phase 1: Understand Current State

1. Read the target CSV file, its `.meta.yaml`, and `inputs/<data_product>/datapackage.yaml`
2. Read the corresponding archetype table (the one that defines the baseline variable). For example, if editing `alt_hvac_system.csv`, read `archetypes/hvac_system.csv` and its `.meta.yaml`
3. Use Glob to find input parameter `.meta.yaml` files in `input_parameters/`. Read each and check if any column's values include the alternative values from this table
4. Summarize to the analyst:
   - "This table maps **{baseline_variable}** → **{alt_variable}**"
   - "Current mappings:" (show baseline → alternative → adoption_share)
   - "Baseline values with NO upgrade path: {list}" (these keep 100% baseline configuration)
   - "Source: {source.name} — {source.detail}"
   - "Input parameter tables that need data for alternative values: {list}"
   - If year-varying: "Adoption shares vary by year: {years}"

### Phase 2: Understand the Change

5. Ask the analyst what they want to change (one question at a time):
   - Adding a new upgrade pathway? (new baseline → alternative mapping)
   - Changing adoption shares? (different rates)
   - Changing the alternative technology? (different upgrade target)
   - Adding year-varying adoption where it was static?
   - Removing an upgrade pathway?

### Phase 3: Check Feasibility

6. Before making changes, verify:
   - **Baseline values exist in archetype table:** Read the archetype CSV and compare. If the analyst references a baseline value that doesn't exist: "The value '{value}' doesn't exist in the archetype table `archetypes/{variable}.csv`. Current values are: {list}."
   - **Alternative values have input parameter coverage:** For each new alternative value, check if it exists in the relevant input parameter tables. If not: "There's no cost or efficiency data for '{value}' in the input parameter tables. You'll need to add that data (using `/edit-input-parameter`) before this alt config will work in the pipeline. Tables that need it: {list}"
   - **Adoption shares are valid:** For each baseline value (and year), sum adoption shares across all alternative rows. Must be ≤ 1.0. If not: "Adoption shares for baseline '{value}' sum to {sum}, which exceeds 1.0. Please adjust."

### Phase 4: Explain Downstream Impact

7. Before making changes, explain:
   - How does the expanded archetype count change? (e.g., "Adding 3 new upgrade paths increases expanded archetypes from 5,100 to 5,400")
   - Which input parameter tables need data for new alternative values?
   - If year-varying: how many additional rows in Step 2 output?

### Phase 5: Build, Confirm, and Write

8. Generate the complete CSV content. Show it to the analyst in a formatted table.
9. **Wait for explicit analyst approval before writing.**
10. Write the CSV file.

### Phase 6: Update Metadata

11. Update the `.meta.yaml` file:
    - `source.name` and `source.detail` — from the analyst's data source
    - `columns.{baseline_variable}.values` — updated to match baseline values in CSV (sorted)
    - `columns.{alt_variable}.values` — updated to match alternative values in CSV (sorted)
    - `notes` — add any caveats; remove `PLACEHOLDER:` prefix if real data replaces placeholder
    - `description` — update if the scope changed
    - Do NOT change `title`, `question`, or `topic` unless the analyst explicitly requests it

### Phase 7: Validate and Report

12. Run `/validate-data-product <data_product_name>` — report results to the analyst
13. Run `/generate-readmes <data_product_name>` — report results
14. Summarize:
    - Files modified: {list}
    - Validation result: pass/fail with details
    - Downstream actions needed: {list of input parameter tables needing data for new alternative values}

## Workflow: Creating a New Alt Config File

### Phase 1: Gather Requirements

1. Read `inputs/<data_product>/datapackage.yaml` for topics
2. Use Glob to list existing archetype CSVs and alt config CSVs
3. Read archetype `.meta.yaml` files to understand available variables
4. Ask the analyst (one question at a time):
   - "Which archetype variable are you creating an alternative for?" Show available variables.
   - "What's the upgrade pathway?" (baseline → alternative mapping for each baseline value)
   - "What adoption share? Uniform across all baseline values, or different per baseline value?"
   - "Is adoption static or year-varying? If year-varying, for which years?"

### Phase 2: Validate Structure

5. Check that the baseline variable exists as an archetype table
6. Check that the `alt_` column name doesn't conflict with existing columns
7. Check input parameter coverage for all alternative values (same as editing Phase 3)
8. Report any input parameter gaps — the analyst will need to add data before the pipeline will run

### Phase 3: Build the Table

9. Follow the same feasibility checks as editing (Phase 3 above)
10. Show the complete CSV for analyst approval

### Phase 4: Create Files

11. Write the CSV file to `inputs/<data_product>/alternative_configurations/alt_{variable_name}.csv`
12. Run `/scaffold-table inputs/<data_product>/alternative_configurations/alt_{variable_name}.csv` to generate the `.meta.yaml` template
13. Fill in the `.meta.yaml` from conversation context:
    - `title`, `question`, `topic` — ask the analyst if not obvious from context
    - `source.name`, `source.detail` — from the analyst's data source
    - `description` — what transition this models
    - Column values — from the actual data

### Phase 5: Validate and Report

14. Run `/validate-data-product <data_product_name>` — report results
15. Run `/generate-readmes <data_product_name>` — report results
16. Summarize files created and any input parameter tables that still need data
