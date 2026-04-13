---
name: validate-data-product
description: |
  Validate an Energy Wallet data product for completeness and consistency.
  Checks CSV/meta.yaml pairing, column documentation, topic references,
  categorical values, numeric ranges, and placeholder flags.
---

# Validate Data Product

You are validating an Energy Wallet data product. The user will specify an input set name (e.g., `ontario`). The data product lives at `inputs/<name>/`.

## What to Validate

Run every check below against the data product directory. Collect all results before reporting.

### 1. Structure Checks

**datapackage.yaml exists and has required fields:**
- Read `inputs/<name>/datapackage.yaml`
- Verify these fields are present and non-empty: `name`, `title`, `description`, `version`, `geography`, `currency`, `currency_year`, `projection_years`, `sources`, `topics`
- Verify `name` matches the folder name
- Collect the list of valid topic keys from `topics[].key`

**Every CSV has a matching .meta.yaml:**
- Use Glob to find all `*.csv` files in `archetypes/`, `alternative_configurations/`, `input_parameters/`
- For each CSV, check that a `.meta.yaml` with the same base name exists in the same directory
- Report any CSVs missing their companion

**Every .meta.yaml has a matching CSV:**
- Use Glob to find all `*.meta.yaml` files
- For each, check that a `.csv` with the same base name exists
- Report any orphaned .meta.yaml files

### 2. Content Checks (per table)

For each CSV + .meta.yaml pair:

**Read the .meta.yaml file** and verify required fields exist:
- `title`, `topic`, `description`, `source.name`, `source.detail`, `keys`, `columns`

**Topic reference:**
- Verify `topic` value is in the valid topic keys collected from datapackage.yaml

**Column coverage:**
- Read the CSV header row (first line)
- Parse the column names from the CSV
- Verify every CSV column appears in `.meta.yaml` `columns`
- Verify every `.meta.yaml` column exists in the CSV

**Keys reference existing columns:**
- Verify every entry in `keys` is a column name that exists in both the CSV and the .meta.yaml

**Column type checks:**
- For columns with `type: categorical`: verify `values` list is present
- For columns with `type: numeric`: verify `unit` is present and non-empty

**Categorical value validation:**
- For each categorical column, read the unique values from the CSV
- Compare against the declared `values` list in .meta.yaml
- Report any values in the CSV not in the declared list, or declared values not in the CSV

**Numeric range validation (warning only):**
- For each numeric column with a `range` declared, read the CSV values
- Report any values outside the declared [min, max] range as warnings

### 3. README Checks

**READMEs exist:**
- Check that `inputs/<name>/README.md` exists
- Check that `inputs/<name>/archetypes/README.md` exists
- Check that `inputs/<name>/alternative_configurations/README.md` exists
- Check that `inputs/<name>/input_parameters/README.md` exists

**Auto-generated header:**
- For each README that exists, read the first line
- Verify it starts with `<!-- AUTO-GENERATED`

### 4. Placeholder Summary

- Scan all .meta.yaml files for `notes` entries starting with `PLACEHOLDER:`
- Collect and report them

## Output Format

Present results in this structure:

```
## Data Product Validation: <name>

### Structure
✓ datapackage.yaml — valid (version X.Y.Z)
✓ N/N CSVs have matching .meta.yaml
✓ No orphaned .meta.yaml files
✗ [or list specific issues]

### Content
✓ All columns documented across N tables
✓ All topic references valid
✓ All categorical values match
⚠ [warnings for range violations]
✗ [errors for missing units, etc.]

### Documentation
✓ All READMEs present and auto-generated
⚠ [or list missing READMEs]

### Placeholders
⚠ N tables have PLACEHOLDER notes:
  - folder/file.csv — description
```

## Important

- Read CSV files with `head -1` to get headers — do NOT read entire large CSVs
- For categorical value checks, use a short Python script or `cut` + `sort -u` to extract unique values efficiently
- Report ALL issues found, not just the first one
- Distinguish severity: ✗ = Error (must fix), ⚠ = Warning (should fix), ✓ = Pass
