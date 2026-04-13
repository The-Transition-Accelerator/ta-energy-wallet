---
name: generate-readmes
description: |
  Regenerate all README files for an Energy Wallet data product from its
  datapackage.yaml and .meta.yaml metadata files. READMEs are always
  auto-generated, never hand-edited.
---

# Generate READMEs

You are generating README documentation for an Energy Wallet data product. The user will specify an input set name (e.g., `ontario`). The data product lives at `inputs/<name>/`.

## Process

### 1. Read All Metadata

- Read `inputs/<name>/datapackage.yaml` for product identity and topic taxonomy
- Use Glob to find all `*.meta.yaml` files in `archetypes/`, `alternative_configurations/`, `input_parameters/`
- Read every `.meta.yaml` file
- Group the tables by their `topic` field
- Within each topic group, order tables by the order they appear across folders: archetypes first, then alternative_configurations, then input_parameters

### 2. Generate Top-Level README

Write to `inputs/<name>/README.md` with this structure:

```markdown
<!-- AUTO-GENERATED from datapackage.yaml and .meta.yaml files. Do not edit directly. -->

# {datapackage.title}

{datapackage.description}

| | |
|---|---|
| **Geography** | {geography.province}, {geography.country} |
| **Climate Zones** | {geography.climate_zones joined with ", "} |
| **Projection Years** | {projection_years joined with ", "} |
| **Currency** | {currency_year} {currency} |
| **Version** | {version} |

## Sources

{for each source in datapackage.sources:}
- **{source.name}** — {source.description}

---

{for each topic in datapackage.topics where at least one table has this topic:}
## {topic.title}

| Question | File | Source |
|----------|------|--------|
{for each table in this topic group:}
| {table.question, or "What are the {table.title}?"} | [`{folder}/{filename}.csv`]({folder}/{filename}.csv) | {table.source.name} |

{end topics}

---

## Placeholders & Known Limitations

{for each .meta.yaml with notes starting with "PLACEHOLDER:":}
- **`{folder}/{filename}.csv`** — {placeholder note text without the PLACEHOLDER: prefix}

{if no placeholders: "No placeholder data. All tables use real, sourced values."}
```

### 3. Generate Subfolder READMEs

For each of the three subfolders (`archetypes/`, `alternative_configurations/`, `input_parameters/`), write a README with this structure:

```markdown
<!-- AUTO-GENERATED from .meta.yaml files. Do not edit directly. -->

# {Folder display name: "Archetypes", "Alternative Configurations", or "Input Parameters"}

{for each .meta.yaml in this folder, ordered by topic:}
## {table.title}

`{filename}.csv`

{table.description}

**Source:** {table.source.name} — {table.source.detail}

**Keys:** {table.keys joined with "`, `" and wrapped in backticks, or "None (single-row table)" if empty}

| Column | Description | Unit | Type |
|--------|-------------|------|------|
{for each column in table.columns:}
| `{column_name}` | {column.description} | {column.unit or "—"} | {column.type}: {column.values joined or column.range} |

{if table.notes:}
{for each note:}
> {note text}

{end if}
---

{end tables}
```

### 4. Formatting Rules

- Use `—` (em dash) for empty unit cells, not blank
- For categorical type columns, show values as comma-separated list in the Type column
- For numeric type columns, show range as "(min–max)" in the Type column if range is declared, otherwise just "numeric"
- Relative links for CSV files (e.g., `[climate_zone.csv](climate_zone.csv)` in subfolder READMEs)
- In the top-level README, use full relative paths (e.g., `[archetypes/climate_zone.csv](archetypes/climate_zone.csv)`)
- Separate each table section with a horizontal rule `---`

### 5. After Generation

Report what was generated:
```
Generated 4 README files for <name>:
  ✓ inputs/<name>/README.md (N topic sections, M tables)
  ✓ inputs/<name>/archetypes/README.md (N tables)
  ✓ inputs/<name>/alternative_configurations/README.md (N tables)
  ✓ inputs/<name>/input_parameters/README.md (N tables)
```

Do NOT commit — let the user decide when to commit.
