<!-- Version history for the Ontario Energy Wallet data library. -->
<!-- Update this file whenever datapackage.yaml version is bumped. -->

# Changelog — Ontario Data Library

## v0.1.0 — 2026-04-12

Initial proof-of-concept release.

### Data sources
- **Building stock & loads**: DSPM Canada Reference Library (CEUD 2021)
- **Equipment costs**: TA Energy Wallet Analysis — Ontario Utility (OSM outputs, no-rebate)
- **Energy prices**: CER Canada's Energy Future 2026 (electricity, natural gas, oil, gasoline)
- **Vehicle data**: Statistics Canada (SHS PUMF 2019, Table 23-10-0308-01), CEUD, EPRI

### Scenario
- Full electrification: all baseline HVAC → ccASHP w electric backup, DHW → 80% electric resistance / 20% HPWH, all ICE → EV
- 3 projection years: 2025, 2030, 2035

### Key decisions
- 5 income quintiles at 20% each
- 23 HVAC system configurations with dwelling-type-differentiated costs
- EULs differentiated by equipment type (15–30 years)
- Maintenance costs differentiated by system type ($0–$550/year)
- Energy prices are average rates inclusive of fixed charges; fixed charge columns set to zero
- Panel upgrade ($5,000) triggered by HP + EV combination
- Second vehicle slot intentionally set to none

### Known limitations
- Condensing and non-condensing gas furnace costs are identical (source does not distinguish)
- Home charging access rates based on limited data quality
- EV charging behaviour figures based on sparse evidence
- Panel upgrade trigger logic (HP + EV) should be reviewed in future iterations
