# Changelog

All notable changes to the Energy Wallet project will be documented in this file.

---

## [0.1.1.0] - 2026-07-22

### Added
- **Partitioned execution** for Steps 3–5 (`partitioning.py`). When the expanded
  archetype table exceeds `--partition-rows` (default 400k), Steps 3–5 run per
  row-range partition with incremental, atomic output writers, bounding peak memory
  regardless of input scale. Results are byte-identical to unpartitioned runs.
- New CLI flags: `--partition-rows N` and `--output-format {auto,csv,parquet}`
  (`auto` = CSV for single-partition runs, Parquet part-files for partitioned runs).
- Parameter tables are loaded once and reused across partitions.

### Fixed
- Declared `polars` as a runtime dependency (it was imported but undeclared, breaking
  fresh installs). Promoted `numpy` to a runtime dependency; removed unused `numpy-financial`.
- DSPM converter dry-run: removed stale committed converter output from the fixture
  library and gitignored it; the dry-run test now verifies the input library tree is
  unchanged across a run.

### Changed
- Documentation (`CLAUDE.md`) updated for Polars, partitioning, and the accurate test count.

## [0.1.0.0] - 2026-04-13

Initial alpha release.
