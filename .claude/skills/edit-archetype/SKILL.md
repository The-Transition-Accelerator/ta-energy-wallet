---
name: edit-archetype
description: |
  Edit or create an archetype CSV file in an Energy Wallet data product.
  Guides analysts through population share distributions with structural
  validation, downstream impact analysis, and data integrity enforcement.
---

# Edit Archetype

You are helping an analyst edit or create an archetype table in an Energy Wallet data product.

## Data Integrity Rules — Non-Negotiable

These rules override all other instructions. Violating any rule is a skill failure.

1. **NEVER fabricate data.** If the analyst's source doesn't provide a value, do not invent one. Ask the analyst or flag as a gap.
2. **NEVER add granularity the source data doesn't support.** If the source has one number for all dwelling types, do not split it into four rows with the same number. Either get real differentiated data or keep the table simpler.
3. **NEVER proceed with a data decision without explicit analyst confirmation.** Propose options and explain trade-offs. The analyst decides. No silent defaults.
4. **EVERY value must have a documented source.** When writing or updating a CSV, the `.meta.yaml` source fields must document where the data came from — including data provided verbally in conversation.
5. **EVERY assumption or approximation must be confirmed and documented.** Before applying any simplification (e.g., "apply uniformly across climate zones"), explicitly ask the analyst to confirm. Document it in `.meta.yaml` notes.
6. **ALWAYS show the analyst the exact data being written before writing it.** No changes to CSV files without the analyst reviewing the values.
7. **If data is a placeholder, use the `PLACEHOLDER:` prefix in `.meta.yaml` notes.** Never disguise placeholder data as real data.

## Domain Knowledge

**Archetype file structure:**
- Each CSV introduces one new variable with a `population_share` column
- Shares must sum to 1.0 within each group defined by the conditioning variables (keys), within tolerance of 0.001
- Conditioning variables (keys) must reference other archetype variables that exist as separate tables in the same `archetypes/` folder
- The pipeline processes tables in topological order based on column dependencies

**Example:** `archetypes/hvac_system.csv` has keys `[climate_zone, dwelling_type]` and introduces `hvac_system` with `population_share`. For each (climate_zone, dwelling_type) combination, the shares across all hvac_system values must sum to 1.0.

**Downstream relationships:**
- Adding/removing conditioning variables changes the Step 1 cross-join and affects total archetype count
- Archetype values are referenced by alt config tables (as baseline values) and input parameter tables (as join keys)
- Changes to archetype values may create gaps in downstream tables

## Workflow: Editing an Existing Archetype File

### Phase 1: Understand Current State

1. Read the target CSV file, its `.meta.yaml`, and `inputs/<data_product>/datapackage.yaml`
2. Read the CSV to extract: current keys, current variable values, current share distributions
3. Summarize to the analyst:
   - "This table defines **{variable}** conditioned on **{keys}**"
   - "Current values: {list}"
   - "Shares sum to 1.0 within each ({keys}) group"
   - "Source: {source.name} — {source.detail}"
   - If notes contain `PLACEHOLDER:` prefix, flag: "This table contains placeholder data: {note}"
4. Identify downstream dependencies:
   - Use Glob to find `.meta.yaml` files in `alternative_configurations/` and `input_parameters/`
   - Read each and check if any column's `values` list references this variable's values
   - Report: "These tables reference {variable}: {list of files}"

### Phase 2: Understand the New Data

5. Accept the analyst's source data in any form (pasted numbers, file references, descriptions, verbal summaries)
6. Ask clarifying questions **one at a time**:
   - If the source data has different conditioning than the current table: "Your source data breaks this down by {X}. The current table is keyed by {Y}. Should we change the conditioning?"
   - If the source data has different categories: "Your source provides values for {A, B, C}. The current table has {D, E, F}. How do these map?"
   - If the source data lacks a conditioning dimension: "Your source doesn't differentiate by {variable}. Should we apply uniformly (same shares for all groups), or drop {variable} as a conditioning variable?"
   - **STOP.** Do not proceed to table construction until all clarifying questions are resolved and the analyst has confirmed the mapping.

### Phase 3: Check Data Completeness

7. Before building the table, verify:
   - Do the shares sum to 1.0 within each conditioning group? If not, report the gap and ask the analyst how to handle it.
   - Are there missing combinations? (e.g., data for CZ_5 and CZ_6 but not CZ_7A) If so, list the gaps explicitly and ask the analyst. **Never interpolate or fill with assumptions.**
   - If the analyst provides shares that don't sum to 1.0: show the sums and ask whether to normalize or whether a category is missing.

### Phase 4: Explain Downstream Impact

8. Before making changes, explain to the analyst:
   - How does the archetype count change? (e.g., "Adding 2 new values increases total archetypes from 720 to 840")
   - Which input parameter tables join on this variable? Will they need new rows for new values?
   - Which alt config tables reference this variable? Will they need updated baseline mappings?
   - Do any other archetype tables condition on this one? Will their share groups change?

### Phase 5: Build, Confirm, and Write

9. Generate the complete CSV content. Show it to the analyst in a formatted table.
   - For small tables (≤30 rows): show the complete table
   - For large tables (>30 rows): show a summary of the structure plus any rows that changed
10. **Wait for explicit analyst approval before writing.**
11. Write the CSV file.

### Phase 6: Update Metadata

12. Update the `.meta.yaml` file:
    - `source.name` and `source.detail` — from the analyst's data source
    - `columns.{variable}.values` — updated to match the new CSV's unique values (sorted)
    - `notes` — add any caveats from the conversation; remove `PLACEHOLDER:` prefix if real data replaces placeholder
    - `description` — update if the scope changed (e.g., new conditioning variable added)
    - Do NOT change `title`, `question`, or `topic` unless the analyst explicitly requests it

### Phase 7: Validate and Report

13. Run `/validate-data-product <data_product_name>` — report results to the analyst
14. Run `/generate-readmes <data_product_name>` — report results
15. Summarize:
    - Files modified: {list}
    - Validation result: pass/fail with details
    - Downstream actions needed: {list of tables that may need updates due to changed values}

## Workflow: Creating a New Archetype File

### Phase 1: Gather Requirements

1. Read `inputs/<data_product>/datapackage.yaml` to understand existing topics and structure
2. Use Glob to list all existing archetype CSVs in `inputs/<data_product>/archetypes/`
3. Read each archetype `.meta.yaml` to understand existing variables
4. Ask the analyst (one question at a time):
   - "What variable are you introducing?" (e.g., `heating_fuel_type`)
   - "What are the possible values?"
   - "Should this be conditioned on any existing archetype variables? Current variables are: {list}"
   - "What's your data source for the population shares?"

### Phase 2: Validate Structure

5. Check that any conditioning variables the analyst specified exist as archetype tables:
   - If not: "You want to condition on {X}, but there's no archetype table for {X}. You'll need to create that first, or choose different conditioning."
6. Check that the variable name doesn't conflict with existing columns across all CSVs

### Phase 3: Build the Table

7. Follow the same data completeness checks as editing (Phase 3 above)
8. Follow the same downstream impact explanation (Phase 4 above)
9. Show the complete CSV for analyst approval

### Phase 4: Create Files

10. Write the CSV file to `inputs/<data_product>/archetypes/{variable_name}.csv`
11. Run `/scaffold-table inputs/<data_product>/archetypes/{variable_name}.csv` to generate the `.meta.yaml` template
12. Fill in the `.meta.yaml` from conversation context:
    - `title`, `question`, `topic` — ask the analyst if not obvious from context
    - `source.name`, `source.detail` — from the analyst's data source
    - `description` — what this variable represents
    - Column values, units, ranges — from the actual data

### Phase 5: Validate and Report

13. Run `/validate-data-product <data_product_name>` — report results
14. Run `/generate-readmes <data_product_name>` — report results
15. Summarize files created and any downstream tables that need to be created or updated
