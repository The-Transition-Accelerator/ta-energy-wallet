---
name: release-data
description: |
  Release a new version of an Energy Wallet data library. Guides the user
  through version bumping, changelog updates, README regeneration, validation,
  and git tagging. Enforces semantic versioning conventions.
---

# Release Data Library

You are releasing a new version of an Energy Wallet data library. The user will specify a data library name (e.g., `ontario`) and optionally a version bump type or explicit version.

The data library lives at `inputs/<name>/`.

## Invocation

```
/release-data <name>                    # Auto-detect bump type from changes
/release-data <name> patch              # Metadata-only fix
/release-data <name> minor              # Data updates (new prices, corrected values)
/release-data <name> major              # Structural changes (new variables, schema changes)
/release-data <name> 0.2.0              # Explicit version
```

## Versioning Convention

This project uses semantic versioning for data libraries:

| Bump | When | Examples |
|------|------|----------|
| **Major** (X.0.0) | Structural changes that alter the shape of the data | New archetype variables, new alt config pathways, added/removed columns from input parameter tables, model-breaking schema changes |
| **Minor** (0.X.0) | Data updates that change values but not structure | Updated energy prices, revised equipment costs, corrected population shares, new source data |
| **Patch** (0.0.X) | Metadata and documentation fixes only | Typos in meta.yaml, corrected source attribution, range fixes, README regeneration |

## Process

### Phase 1: Pre-flight Checks

1. **Read current state:**
   - Read `inputs/<name>/datapackage.yaml` to get current version
   - Read `inputs/<name>/CHANGELOG.md` to get release history
   - If CHANGELOG.md doesn't exist, create it (see template below)

2. **Detect what changed since last release:**
   - Run `git diff --name-only` on the data library directory to see uncommitted changes
   - Run `git log --oneline` to see recent commits touching this directory
   - Categorize changes:
     - **Structural**: new/deleted CSV files, new columns in existing CSVs, changed keys
     - **Data**: modified values in CSV files, updated meta.yaml ranges
     - **Metadata**: meta.yaml description/source/notes changes, README changes

3. **Determine version bump:**
   - If user specified a bump type or explicit version, use that
   - Otherwise, recommend based on detected changes:
     - Any structural changes → suggest major
     - Any data value changes → suggest minor
     - Only metadata changes → suggest patch
   - Present the recommendation and ask user to confirm

### Phase 2: Changelog Entry

4. **Draft changelog entry:**

   Read all modified files and draft a changelog entry. Present it to the user for review before writing.

   Entry format:
   ```markdown
   ## vX.Y.Z — YYYY-MM-DD

   {Brief summary sentence.}

   ### Changes
   - {Bullet per meaningful change, grouped logically}
   - {Reference specific files/tables when helpful}

   ### Data sources
   - {Only include if sources were added or changed}

   ### Known limitations
   - {Only include if new limitations were introduced}
   ```

   Rules for changelog entries:
   - Write in past tense ("Updated energy prices" not "Update energy prices")
   - Be specific: "Updated HVAC costs from Hydro One OSM data" not "Changed some costs"
   - Group related changes: "Updated all CER 2026 energy prices (electricity, natural gas, oil, gasoline)"
   - Don't list every file — summarize thematically
   - Include the "why" when it's not obvious

5. **Get user confirmation** on the changelog entry. Revise if needed.

### Phase 3: Apply Release

6. **Bump version in datapackage.yaml:**
   - Update the `version` field to the new version
   - Update `last_updated` to today's date

7. **Prepend changelog entry** to `inputs/<name>/CHANGELOG.md`
   - New entry goes at the top, after the file header

8. **Regenerate READMEs:**
   - Invoke the generate-readmes skill logic: read all datapackage.yaml and .meta.yaml files, write all 4 README files
   - This ensures version number in README matches

9. **Run validation:**
   - Invoke the validate-data-product skill logic against the data library
   - Report any errors or warnings
   - If there are errors (✗), warn the user and ask whether to proceed

### Phase 4: Commit and Tag

10. **Stage and commit:**
    - Stage all changed files in `inputs/<name>/`
    - Create commit with message: `data(<name>): release v{version}`
    - Include `Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>`

11. **Create git tag:**
    - Tag: `data/<name>/v{version}`
    - Message: First line of the changelog entry summary

12. **Report completion:**
    ```
    Released <name> v{version}

    Commit: {short hash}
    Tag:    data/<name>/v{version}

    Files changed:
      • datapackage.yaml (version bump)
      • CHANGELOG.md (new entry)
      • README.md (4 files regenerated)

    Run `git push && git push --tags` to publish.
    ```

## CHANGELOG.md Template

If CHANGELOG.md doesn't exist, create it with this header:

```markdown
<!-- Version history for the {title} data library. -->
<!-- Update this file whenever datapackage.yaml version is bumped. -->

# Changelog — {title}
```

Then add the first entry below the header.

## Important Rules

- **Never skip the changelog.** Every version bump must have a changelog entry.
- **Never auto-commit without user seeing the changelog.** Always present the draft and wait for confirmation.
- **Never push.** Only commit and tag locally. Tell the user to push when ready.
- **Validate before releasing.** If validation finds errors, the user should fix them first.
- **One release at a time.** Don't batch multiple data libraries into one release.
