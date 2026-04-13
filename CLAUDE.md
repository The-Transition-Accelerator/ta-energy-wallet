# CLAUDE.md - Energy Wallet Codebase Guide

## What This Project Is

Energy Wallet is a 5-step pipeline model for analyzing household energy affordability. It compares baseline household archetypes against alternative technology/behavior configurations (e.g., gas furnace -> heat pump, ICE -> EV) and computes population-weighted cost impacts. All costs are annualized to $/year.

## Quick Reference

```bash
# Run the full pipeline
python -m energy_wallet.main --input-set ontario

# Run the DSPM-to-EW converter (Ontario example)
python -m energy_wallet.dspm_converter --config configs/dspm_ontario.yaml

# Dry-run the converter (no files written)
python -m energy_wallet.dspm_converter --config configs/dspm_ontario.yaml --dry-run

# Launch the dashboard
python dashboard_v3/app.py

# Run tests (takes ~9 minutes on Python 3.14; all 74 should pass)
pytest -q

# Run a specific test suite
pytest -q tests/test_calculations.py

# Install (editable)
pip install -e .
pip install -r requirements.txt
```

**Python version:** 3.14 (venv at `.venv/`). Minimum supported: 3.10.

**Core runtime dependencies:** `pandas`, `numpy-financial` (declared but not imported at runtime; hand-rolled PMT in `annualize.py`).

**Dashboard dependencies:** `dash`, `dash-ag-grid`, `plotly`, `pyyaml`.

**Dev/test dependencies (requirements-dev.txt):** `pytest`, `openpyxl`, `numpy`, `seaborn`, `pyarrow`.

## Pipeline Architecture (5 Steps)

Each step reads the previous step's CSV output. Steps are chained in `main.py`.

| Step | Module | Input | Output | What It Does |
|------|--------|-------|--------|-------------|
| 1 | `archetypes/` | `inputs/<set>/archetypes/*.csv` | `step1_archetypes_merged.csv` | Cross-join archetype tables, compute population weights |
| 2 | `alternative_configurations/` | Step 1 output + `inputs/<set>/alternative_configurations/*.csv` | `step2_archetypes_expanded.csv` | Expand archetypes with alt configs, split weights by adoption share |
| 3 | `input_parameters/` | Step 2 output + `inputs/<set>/input_parameters/*.csv` | `step3_model_inputs.csv` | Attach cost/efficiency/load parameters via multi-lookup joins |
| 4 | `calculations/` | Step 3 output | `step4_energy_wallet.csv` | Compute annualized costs (vehicles, HVAC, DHW, other) |
| 5 | `energy_type_analysis/` | Step 4 output | `step5_utility_bills.csv` | Re-aggregate by utility bill category |

**Typical output scale:** 720 archetypes -> 5,100 expanded rows -> ~288 output columns.

## Source Code Layout

```
src/energy_wallet/
  main.py                          # CLI entrypoint, run_step1..5 functions
  archetypes/                      # Step 1
    spec.py                        #   ArchetypeTableSpec dataclass
    io.py                          #   discover, infer_spec, load CSV files
    validate.py                    #   share sum-to-1, bounds checks
    join.py                        #   toposort + cross-join merge (multiplicative weights)
    errors.py                      #   ArchetypeTableError, ArchetypeJoinError
  alternative_configurations/      # Step 2
    spec.py                        #   AlternativeConfigTableSpec dataclass
    io.py                          #   discover, infer_spec, load CSV files
    validate.py                    #   adoption share validation + expanded output checks
    join.py                        #   toposort + conditional join (weight splitting)
    pipeline.py                    #   build_expanded_archetype_table() orchestrator
    errors.py                      #   AlternativeConfigTableError, AlternativeConfigJoinError
  input_parameters/                # Step 3
    spec.py                        #   InputParameterTableSpec dataclass (incl. multi-lookup fields)
    io.py                          #   discover, infer_spec (legacy + Phase 3B modes), load
    lookup.py                      #   Multi-lookup engine: TechTypeExpansion, LookupSpec, LookupPlan
    join.py                        #   attach_input_parameters() - passthrough + multi-lookup
    validate.py                    #   Table, cross-table, and final output validation
    required.py                    #   Registry of 139 required parameters (generated programmatically)
    pipeline.py                    #   build_model_input_table() orchestrator
    errors.py                      #   InputParameterTableError, InputParameterJoinError
  calculations/                    # Step 4
    annualize.py                   #   PMT formula for capital cost annualization
    vehicle.py                     #   compute_vehicle_slot_costs(df, slot, suffix)
    hvac.py                        #   compute_hvac_costs(df, suffix) - 5 fuel types
    dhw.py                         #   compute_dhw_costs(df, suffix) - 5 fuel types
    other.py                       #   compute_other_costs(df, suffix) - fixed charges, panel
    pipeline.py                    #   compute_energy_wallet(model_inputs) orchestrator
    errors.py                      #   CalculationError
  energy_type_analysis/            # Step 5
    pipeline.py                    #   compute_utility_bill_perspective(step4_output) orchestrator
    errors.py                      #   EnergyTypeAnalysisError
  dspm_converter/                  # Standalone converter: DSPM → EW input set
    __main__.py                    #   python -m energy_wallet.dspm_converter entrypoint
    cli.py                         #   Argument parsing, exit codes (0=success, 1=config, 2=conversion)
    config.py                      #   ConverterConfig dataclass + YAML loader + config validation
    pipeline.py                    #   convert_dspm_to_input_set() — 11-step orchestrator
    reader.py                      #   DSPM CSV loaders (building stock, HVAC/DHW specs, equipment shares, etc.)
    archetypes_builder.py          #   Build archetype CSVs from building stock + equipment shares
    alt_configs_builder.py         #   Build alternative_configurations CSVs from config
    params_builder.py              #   Build input_parameter CSVs (costs, loads, efficiencies)
    aggregation.py                 #   Envelope bin aggregation (10 DSPM bins → 3 EW tiers)
    efficiency.py                  #   COP curve collapse to annual-average heating/cooling efficiency
    fuel_proportions.py            #   Compute fuel proportion vectors per HVAC system
    unit_conversion.py             #   kWh ↔ GJ conversions
    mapping.py                     #   Climate zone mapping, fuel name normalization
    mapping_helper.py              #   CLI helper for building province YAML configs
    provenance.py                  #   Per-column provenance tracking + Markdown report generator
    errors.py                      #   DSPMConverterError, DSPMValidationError

configs/
  dspm_ontario.yaml                # Ontario converter config (climate zones, HVAC maps, alt configs)

dashboard_v3/
  app.py                           # Dash entrypoint
  pages/
    home.py                        # Landing page
    inputs.py                      # Input data browser with AG Grid
    results.py                     # Results explorer with charts and filters
  components/
    filter_sidebar.py              # Dimension filter controls
    metric_cards.py                # Summary metric display cards
    charts/                        # Plotly chart components
      overview.py                  #   Population-weighted overview bar chart
      waterfall.py                 #   Waterfall cost breakdown
      distribution.py              #   Distribution histogram
      comparator.py                #   Scenario comparison chart
      time_series.py               #   Time series trends
      cost_breakdown.py            #   Detailed cost breakdown
  data/
    loader.py                      # Input/output CSV discovery and loading
    constants.py                   # Colors, dimension columns, Plotly template
    summary.py                     # Weighted aggregation helpers
    input_browser.py               # Meta.yaml reader for input file info
```

## Key Concepts

### Input Set Structure
Each named input set is a directory under `inputs/` with three subdirectories:
```
inputs/<set_name>/
  archetypes/                      # One CSV per archetype variable
  alternative_configurations/      # One CSV per alt config variable
  input_parameters/                # Cost, efficiency, and load tables
```
Available sets: `ontario`, `test_input_set_1`.

### Column Naming Conventions
- **`_base` / `_alt`** suffixes: baseline vs. alternative configuration values
- **`_{N}_`** (N=1,2): vehicle slot number
- **`alt_`** prefix: alternative archetype variables (e.g., `alt_heating_system`)
- **`scn_`** prefix: scenario variables (e.g., `scn_adoption`). Detected by `startswith("scn_")`
- **`population_share`**: share column in archetype tables
- **`adoption_share`**: share column in alt config tables
- **`population_weight`**: final weight in merged output

### Two-Level Vehicle Taxonomy
Vehicles use type + category: `vehicle_{N}_type` (car, truck, none) and `vehicle_{N}_category` (ICE, EV, none). Two vehicle "slots" per household; slot 2 can be `none`.

### Input Parameter Table Types
1. **Technology-type tables** (e.g., `vehicle_costs.csv`): Keyed by generic type column (e.g., `vehicle_type`). No `_base`/`_alt` suffix on values. Step 3 multi-lookup system joins them multiple times to produce suffixed output.
2. **Context tables** (e.g., `shared_parameters.csv`): Already have explicit `_base`/`_alt` value columns. Joined once (passthrough).
3. **Unsuffixed context values**: If a required parameter exists in `_base`/`_alt` form but the input column has no suffix, Step 3 auto-duplicates it into both.

### Multi-Lookup System (`input_parameters/lookup.py`)
The core of Step 3. Detects how input join columns map to expanded archetype columns:
- **Slot detection** (`_detect_slot_variants`): `vehicle_type` -> finds `vehicle_1_type`, `vehicle_2_type` via `{prefix}_{N}_{suffix}` regex
- **Alt detection** (`_detect_alt_variant`): `heating_system` -> finds `alt_heating_system`
- **Value renaming** (`_rename_value_col_for_slot`): inserts slot number after first word: `vehicle_purchase_cost` -> `vehicle_1_purchase_cost`
- Generates `LookupPlan` with multiple `LookupSpec` entries (one per slot/suffix combo)

### Weight Calculation
- **Step 1**: Multiplicative across archetype tables: `final_weight = product(all shares)`
- **Step 2**: Splits existing weights by adoption share: `expanded_weight = baseline_weight * adoption_share`
- Weights must sum to 1.0 per (year, scenario) group at every step

### Cost Calculations (Step 4)
For each suffix (`base`, `alt`):
- **Vehicle** (per slot): capital (PMT) + maintenance + gasoline + EV electricity
- **HVAC**: capital + maintenance + 5-fuel heating + electric cooling
- **DHW**: capital + maintenance + 5-fuel heating
- **Other**: other electricity + other NG + fixed charges + panel upgrade
- **energy_wallet_{s}** = vehicles + HVAC + DHW + other
- Comparison: `diff_absolute = alt - base`, `diff_percent = diff / base * 100`

Fuel cost formula: `load * proportion / efficiency * price` (guarded by `np.where(proportion > 0, ...)`)

PMT formula: `cost * rate / (1 - (1 + rate)^{-life})` with guards for zero cost/life/rate.

NG fixed charge is conditional: only applied when household uses any natural gas.

### Step 5 Utility Bill Categories
Re-aggregates Step 4 intermediates into 7 energy bill categories: electricity, natural gas, oil, propane, wood, gasoline, public EV charging. Capital and maintenance costs are computed internally for reconciliation only (not output columns). Reconciliation check verifies that bill total + capital + maintenance equals `energy_wallet_{s}`.

## Module Patterns

### Each subpackage follows the same structure:
- `spec.py`: Frozen dataclass describing a table's schema
- `io.py`: File discovery, column inference, CSV loading
- `validate.py`: Validation rules (table-level, cross-table, final output)
- `join.py`: Join/merge logic
- `pipeline.py`: High-level orchestrator function
- `errors.py`: Module-specific ValueError subclasses
- `__init__.py`: Re-exports public API

### Error handling:
- Each module has specific exception classes (e.g., `ArchetypeTableError`, `CalculationError`)
- `main.py` catches exceptions per step and returns specific exit codes (2-6)
- Validation provides detailed error messages with sample bad data

### File-based auto-discovery:
- Adding a new archetype variable = add a CSV to `archetypes/`
- Adding a new alt config = add a CSV to `alternative_configurations/`
- Adding new input parameters = add a CSV to `input_parameters/`
- No code changes needed; the system infers column roles from naming conventions and column order

## Tests

**74 tests total** across 8 test files in `tests/`:

| File | Tests | What It Covers |
|------|-------|---------------|
| `test_archetype.py` | 7 | Step 1: loading, validation, merging, error cases |
| `test_alternative_configurations.py` | 5 | Step 2: loading, expansion, scenario handling |
| `test_input_parameters.py` | 3 | Step 3: loading, multi-lookup, end-to-end parameter attachment |
| `test_calculations.py` | 13 | Step 4: annualize, vehicle ICE/EV/none, HVAC, DHW, other, full pipeline |
| `test_energy_type_analysis.py` | 5 | Step 5: reconciliation, column existence, fuel-type checks |
| `test_dspm_transforms.py` | 30 | Converter unit tests: unit conversions, aggregation, mapping, efficiency, fuel proportions |
| `test_dspm_pipeline.py` | 6 | Converter integration tests: end-to-end pipeline, join-key validation, atomic write |
| `test_dspm_cli.py` | 5 | Converter CLI: arg parsing, dry-run, config error handling |

Tests use `test_input_set_1` data by default. Tests are slow (~9 min) due to Python 3.14 compilation overhead.

There is also `inputs/validate_test_data.py` for validating input data integrity.

## CLI Arguments

Key flags for `python -m energy_wallet.main`:
- `--input-set NAME` (required): Named input set under `inputs/`
- `--inputs-root PATH`: Override input directory directly
- `--skip-step2/3/4/5`: Stop pipeline early
- `--keep-provenance-shares`: Retain per-table share columns (dropped by default)
- `--tolerance FLOAT`: Validation tolerance for share sums (default 0.001)
- `--step{2,3,4,5}-output PATH`: Custom output paths

Exit codes: 0=success, 1=arg error, 2=Step1, 3=Step2, 4=Step3, 5=Step4, 6=Step5.

## Important Implementation Details

1. **Topological sort**: Both Step 1 and Step 2 use toposort to determine table processing order based on column dependencies. Cycle detection is built in.

2. **Year handling**: Tables may or may not have a `year` column. When merging, if one table has years and the other doesn't, the merged result expands across those years.

3. **The `none` vehicle type**: Uses all-zero parameter values with `assumed_life=1` to avoid division-by-zero in PMT. Purchase cost of 0 means annualized capital = 0.

4. **Percentage normalization**: Alt config and archetype tables auto-convert percentages > 1 to decimals (divide by 100).

5. **Provenance shares**: Intermediate per-table shares use `{name}__share` suffix. Dropped by default after final weight calculation.

6. **Required parameters registry** (`required.py`): 139 parameters generated programmatically with `{N}` (slot) and `{s}` (base/alt) substitutions. This is the contract between Step 3 and Steps 4/5.

7. **Reconciliation**: Step 5 validates that utility bill category sums match `energy_wallet_{s}` within floating-point tolerance.

## Authoritative Reference

`Model Architecture.md` is the comprehensive technical specification with worked examples and a complete data dictionary (Appendix A) covering all input parameters and output columns.
