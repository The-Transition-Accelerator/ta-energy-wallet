# Energy Wallet

> **Alpha version (v0.1.0) — under active development.** This model and its data inputs are provided as-is for exploration and research purposes. We make no representation as to the accuracy of the model outputs or the completeness of the underlying data. Results should not be used as the sole basis for policy decisions without independent validation.

## What is Energy Wallet?

Energy Wallet is an open-source scenario model for analyzing how technology transitions and behavioral shifts impact household energy costs and affordability.

A household's **energy wallet** is the total annual cost of meeting its direct energy needs — fuel and electricity costs, equipment operating and maintenance costs, and the annualized capital cost of energy-consuming equipment (vehicles, heating systems, water heaters, etc.). Examining all three cost components together is important because different technology choices shift costs between categories. For example, switching from a gas furnace to a heat pump may increase electricity costs but eliminate natural gas costs and change capital costs.

The model works by constructing **household archetypes** — representative combinations of dwelling type, location, income, heating system, vehicles, and other characteristics — and comparing a baseline configuration against alternative technology or behavioral scenarios. Each archetype carries a population weight, so results can be aggregated to estimate impacts across a region's population.

This enables:

- **Distributional analysis** — which household types face cost increases vs. decreases under different scenarios
- **Population-level impacts** — weighted aggregation to estimate economy-wide effects
- **Equity assessments** — comparison of impacts across income groups, geographies, and dwelling types
- **Policy scenario testing** — evaluation of how different technology adoption patterns affect household affordability

## How It Works

The model runs a 5-step pipeline, where each step reads the previous step's output:

| Step | What It Does | Output |
|------|-------------|--------|
| 1 | Construct population-weighted baseline household archetypes from input tables | `step1_archetypes_merged.csv` |
| 2 | Expand archetypes with alternative technology/behavior configurations and adoption shares | `step2_archetypes_expanded.csv` |
| 3 | Attach cost, efficiency, and load parameters via multi-lookup joins | `step3_model_inputs.csv` |
| 4 | Compute annualized energy wallet costs (capital, fuel, maintenance, fixed charges) for baseline and alternative | `step4_energy_wallet.csv` |
| 5 | Re-aggregate costs by utility bill category (electricity, natural gas, gasoline, etc.) | `step5_utility_bills.csv` |

For the complete technical specification — including all formulas, validation rules, worked examples, and a full data dictionary — see **[Model Architecture.md](Model%20Architecture.md)**.

## Getting Started

### Prerequisites

- Python 3.10 or later
- Git

### 1. Clone the repository

```bash
git clone <repository-url>
cd energy_wallet2
```

### 2. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -U pip
pip install -e .
pip install -r requirements.txt
```

### 4. Run the model

```bash
python -m energy_wallet.main --input-set ontario
```

This runs all five pipeline steps. Outputs are written to `outputs/ontario/`.

To run on the included test data:

```bash
python -m energy_wallet.main --input-set test_input_set_1
```

### 5. View results

Pipeline outputs are CSV files in `outputs/<input-set>/`. Open them in any spreadsheet application or use pandas:

```python
import pandas as pd
df = pd.read_csv("outputs/ontario/step4_energy_wallet.csv")
```

### CLI options

```
--input-set NAME          Named input set under inputs/ (required)
--skip-step2              Run Step 1 only
--skip-step3              Run through Step 2 only
--skip-step4              Run through Step 3 only
--skip-step5              Run through Step 4 only
```

## Input Sets

The model is configured entirely through input data files. Each **input set** is a directory under `inputs/` with three subdirectories:

```
inputs/<name>/
  archetypes/                      # One CSV per archetype variable (e.g., dwelling_type, heating_system)
  alternative_configurations/      # One CSV per alternative scenario (e.g., furnace -> heat pump)
  input_parameters/                # Cost, efficiency, and load tables
```

To create a new scenario, create a new directory under `inputs/` with these three subdirectories and populate them with CSV files. The model auto-discovers files — no code changes needed.

The included `ontario` input set provides a complete example with full metadata documentation. See `inputs/ontario/README.md` for details.

## Claude Code Skills

Energy Wallet ships with a set of [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skills that help analysts manage input data without writing code. These skills enforce data integrity rules, validate inputs, and auto-generate documentation.

To use a skill, type its name in Claude Code (e.g., `/edit-input ontario`).

### Data editing skills

| Skill | What It Does |
|-------|-------------|
| `/edit-input` | **Start here.** Entry point for any data change. Identifies which files need editing and routes to the appropriate skill below. Detects cross-cutting changes (e.g., adding a new technology that requires updates to archetypes, alternative configurations, and input parameters). |
| `/edit-archetype` | Edit or create archetype CSV files (population distributions). Guides you through updating shares, validates they sum to 1.0, and checks downstream impacts. |
| `/edit-alt-config` | Edit or create alternative configuration CSV files (baseline-to-alternative technology mappings with adoption shares). |
| `/edit-input-parameter` | Edit or create input parameter CSV files (costs, efficiencies, loads). Validates units against the model's unit specification and checks coverage against all archetype/alt-config combinations. |

### Data management skills

| Skill | What It Does |
|-------|-------------|
| `/scaffold-table` | Create a new CSV and metadata template for an input set. Pre-fills column definitions where possible. |
| `/validate-data-product` | Run completeness and consistency checks on an input set — verifies every CSV has metadata, columns are documented, categorical values match, and numeric ranges are reasonable. |
| `/generate-readmes` | Regenerate all README files for an input set from its metadata. READMEs are auto-generated and should not be edited by hand. |
| `/release-data` | Version and release a data library. Bumps the version number, drafts a changelog entry, regenerates documentation, and creates a git commit and tag. |

## Model Documentation

**[Model Architecture.md](Model%20Architecture.md)** is the authoritative technical reference. It contains:

- Detailed specification of each pipeline step
- All calculation formulas (annualized capital costs, fuel costs, HVAC, DHW, vehicles, other)
- Validation rules and construction constraints
- Worked examples with sample data
- Complete data dictionary (Appendix A) covering all 139 input parameters and output columns

## Running Tests

```bash
pytest -q
```

The test suite validates the calculation engine (annualization formulas, vehicle/HVAC/DHW/other cost calculations), pipeline integration (end-to-end runs), and input processing (archetype merging, alternative configuration expansion, parameter lookup).

## License

See [LICENSE](LICENSE) for details.
