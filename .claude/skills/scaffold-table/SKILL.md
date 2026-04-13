---
name: scaffold-table
description: |
  Scaffold a new CSV + .meta.yaml pair for an Energy Wallet data product.
  Infers column types and values from existing CSV data, generates a
  .meta.yaml template, then validates and regenerates READMEs.
---

# Scaffold Table

You are adding a new table to an Energy Wallet data product. The user will provide a path like `inputs/<name>/<folder>/<table>.csv`.

## Process

### 1. Determine Context

- Parse the input set name and folder from the path
- Read `inputs/<name>/datapackage.yaml` to get valid topic keys
- List the valid topics for the user to choose from

### 2. If CSV Already Exists

- Read the CSV file
- Extract column names from the header row
- Read `configs/model_units.json` for authoritative unit definitions
- For each column, determine type:
  - Read unique values using a short Python/bash script
  - If all values are numeric (parseable as float): `type: numeric`
  - Otherwise: `type: categorical` with `values` set to the sorted unique values list
- Identify likely key columns: all categorical columns except the last one (which is typically the value column)
- Generate the `.meta.yaml` file with all inferred data
- For numeric columns, check if the column name matches a parameter in `model_units.json` (stripping `_base`/`_alt` suffixes and slot numbers to match template patterns like `vehicle_{N}_purchase_cost_{s}`):
  - If match found: pre-fill `unit` from `model_units.json` (mark as `✓ Unit from model_units.json`)
  - If no match: mark as `unit: "TODO: Add unit"`
- Mark other fields needing human input:
  - `title: "TODO: Add table title"`
  - `question: "TODO: Add navigation question"`
  - `topic: "TODO: Choose from: {list of valid topic keys}"`
  - `description: "TODO: Add table description"`
  - `source.name: "TODO: Add source name"`
  - `source.detail: "TODO: Add source detail"`
  - For numeric columns: `range` is auto-filled from actual [min, max] in the data

### 3. If CSV Does Not Exist

- Ask the user to describe the table: what it contains, what columns it needs, what it's keyed on
- Generate both a template CSV (header + example rows) and the `.meta.yaml`
- Mark all fields as TODO

### 4. After Scaffolding

- Show the user what was generated and what needs manual input
- Ask the user to fill in the TODO fields
- Once TODOs are resolved, run `/validate-data-product <name>` to verify
- Run `/generate-readmes <name>` to update documentation

### Output Format

```
Scaffolded: <folder>/<table>.meta.yaml

Pre-filled from CSV:
  ✓ N columns detected: col1, col2, ...
  ✓ Keys inferred: [key1, key2]
  ✓ Categorical values detected for col1, col2
  ✓ Numeric ranges detected for col3 (min–max)

Needs human input:
  TODO: title — Add a human-readable table title
  TODO: question — Add a navigation question for the README
  TODO: topic — Choose from: {topic_key_1, topic_key_2, ...}
  TODO: description — Describe what this table contains
  TODO: source.name — Primary data source
  TODO: source.detail — Specific reference
  TODO: unit for 'col3' — e.g., "GJ/year", "$/kWh", "proportion"
```
