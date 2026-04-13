---
name: edit-input
description: |
  Single entry point for editing or creating Energy Wallet data product
  input files. Routes to domain-specific skills (edit-archetype,
  edit-alt-config, edit-input-parameter) based on the target file type.
---

# Edit Input

You are helping an analyst work with Energy Wallet data product input files. This is the single entry point — you understand what the analyst wants to do and route to the appropriate domain skill.

## Data Integrity Rules — Non-Negotiable

These rules apply to this skill and all domain skills it routes to. Remind yourself of them before every routing decision.

1. **NEVER fabricate data.** If the analyst's source doesn't provide a value, do not invent one.
2. **NEVER add granularity the source data doesn't support.**
3. **NEVER proceed with a data decision without explicit analyst confirmation.**
4. **EVERY value must have a documented source.**
5. **EVERY assumption or approximation must be confirmed and documented.**
6. **ALWAYS show the analyst the exact data being written before writing it.**
7. **If data is a placeholder, use the `PLACEHOLDER:` prefix in `.meta.yaml` notes.**

You do NOT modify files directly. You do NOT make data decisions. You route to domain skills that handle the actual work.

**Unit reference:** `configs/model_units.json` is the authoritative specification for all numeric parameter units the model requires. Domain skills reference it during unit validation. If an analyst provides data in different units, the domain skill will handle conversion with analyst confirmation.

## Invocation

`/edit-input <data_product_name>`

If no data product name is given:
- Use Glob to list directories under `inputs/` that contain a `datapackage.yaml`
- If exactly one exists, use it
- If multiple exist, ask the analyst which one to work with

## Workflow

### Phase 1: Understand Intent

1. Ask the analyst what they want to change and why. Accept data in any form:
   - Pasted numbers or tables in chat
   - File references (CSV, Excel, PDF)
   - Descriptions of studies or reports
   - Verbal summaries of findings
   - A mix of the above

2. If the analyst's intent is unclear, ask a clarifying question. Do not guess.

### Phase 2: Identify the Target

3. Read `inputs/<data_product>/datapackage.yaml` for product context
4. Determine which file(s) are involved:
   - Use Glob to list all `.meta.yaml` files across `archetypes/`, `alternative_configurations/`, and `input_parameters/`
   - Read relevant `.meta.yaml` files to match the analyst's intent to specific tables
   - Determine the file type for each target:
     - Files in `archetypes/` → archetype (route to `/edit-archetype`)
     - Files in `alternative_configurations/` → alt config (route to `/edit-alt-config`)
     - Files in `input_parameters/` → input parameter (route to `/edit-input-parameter`)
   - Determine whether the file exists (edit) or needs to be created (new)
5. If you can't determine the file type or target, ask the analyst rather than guessing.

### Phase 3: Summarize Current State

6. Before routing, tell the analyst:
   - **Target file(s):** path and type (archetype / alt config / input parameter)
   - **Current structure:** keys, value columns, number of rows
   - **Current source:** from `.meta.yaml`
   - **Placeholder status:** any `PLACEHOLDER:` flags in notes
   - **Related files:** other tables that reference or are referenced by this table

### Phase 4: Detect Cross-Cutting Changes

7. Some changes span multiple file types. Detect these and explain the full sequence before starting:

   **Adding a new technology/variable value** (e.g., "add ground-source heat pump"):
   - Archetype: may need to add the value to the archetype distribution
   - Alt config: may need to add upgrade mapping
   - Input parameters: will need cost, efficiency, and load data for the new value
   - Explain: "Adding '{value}' will require changes to: (1) the archetype distribution in `archetypes/{file}.csv`, (2) the alt config upgrade mapping in `alternative_configurations/{file}.csv`, and (3) parameter tables in `input_parameters/` ({list}). Let's start with the archetype."

   **Adding a new conditioning dimension** (e.g., "break down by income quintile"):
   - Multiple tables may need new rows for the new conditioning
   - Explain which tables are affected and in what order

   **Changing adoption pathways** (e.g., "change from heat pump to ground-source"):
   - Alt config changes may require new input parameter data
   - Explain the dependency

8. For cross-cutting changes, sequence the domain skills in this order:
   1. **Archetype changes first** (they define the universe of values)
   2. **Alt config changes second** (they reference archetype values)
   3. **Input parameter changes last** (they need to cover all values from both)

### Phase 5: Route to Domain Skill

9. Hand off to the appropriate domain skill with full context. Use the Skill tool to invoke:
   - `/edit-archetype` for archetype files
   - `/edit-alt-config` for alternative configuration files
   - `/edit-input-parameter` for input parameter files

10. Provide the domain skill with context by stating clearly:
    - The data product name
    - The target file path
    - What the analyst wants to change
    - The analyst's source data (repeat it — the domain skill needs it)

### Phase 6: After Domain Skill Completes

11. If this was a cross-cutting change, invoke the next domain skill in the sequence.
12. When all changes are done, provide a final summary:
    - All files modified or created
    - Validation status (from domain skills' validate runs)
    - Any remaining gaps or downstream actions needed
    - Suggest committing the changes if everything validates

## What This Skill Does NOT Do

- Does not modify CSV or `.meta.yaml` files directly — domain skills do that
- Does not make data decisions — the analyst decides, domain skills facilitate
- Does not bypass domain skills — even for "simple" changes, route through the proper skill
- Does not skip the cross-cutting detection step — even if the analyst asks to "just change this one file", check for dependencies first
