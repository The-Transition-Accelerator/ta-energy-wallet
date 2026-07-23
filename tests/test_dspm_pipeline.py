"""Integration tests for the DSPM converter pipeline.

These tests require DSPM canada_reference data to be available locally.
They are skipped when the data is not found.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

# Default to the in-repo data library; override via DSPM_DATA_PATH env var
_REPO_ROOT = Path(__file__).resolve().parent.parent
DSPM_PATH = Path(
    os.environ.get(
        "DSPM_DATA_PATH",
        str(_REPO_ROOT / "dspm_data_libraries" / "canada_reference"),
    )
)

DSPM_AVAILABLE = DSPM_PATH.exists() and (DSPM_PATH / "building_stock_library.csv").exists()

skip_no_dspm = pytest.mark.skipif(
    not DSPM_AVAILABLE,
    reason=f"DSPM data not found at {DSPM_PATH}",
)


@skip_no_dspm
class TestPipelineIntegration:
    """Full pipeline integration tests using real DSPM data."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        """Set up a temp library copy with output dir."""
        import shutil
        # Copy library to tmp so output goes there. The converter writes its
        # output inside the library dir, so the source library may carry
        # energy_wallet_inputs/ from a previous run; exclude it so every test
        # starts from a library with no output present.
        self.lib_path = tmp_path / "canada_reference"
        shutil.copytree(
            DSPM_PATH,
            self.lib_path,
            ignore=shutil.ignore_patterns("energy_wallet_inputs"),
        )

    def test_full_pipeline_runs(self):
        """Run the full converter and verify output structure."""
        from energy_wallet.dspm_converter.pipeline import run_pipeline

        output_path = run_pipeline(
            library_path=self.lib_path,
            province="ON",
            library_name="Canada Reference",
        )

        assert output_path is not None
        assert output_path.exists()

        # Check subdirectories
        assert (output_path / "archetypes").exists()
        assert (output_path / "input_parameters").exists()
        assert (output_path / "documentation.md").exists()

        # No alternative_configurations directory
        assert not (output_path / "alternative_configurations").exists()

    def test_archetype_files_exist(self):
        from energy_wallet.dspm_converter.pipeline import run_pipeline

        output_path = run_pipeline(
            library_path=self.lib_path,
            province="ON",
        )

        expected_archetypes = [
            "climate_zone.csv",
            "dwelling_type.csv",
            "hvac_system.csv",
            "dhw_system.csv",
            "envelope_tier.csv",
        ]
        for filename in expected_archetypes:
            assert (output_path / "archetypes" / filename).exists(), f"Missing: {filename}"

        # No vehicle files
        assert not (output_path / "archetypes" / "vehicle_1_type.csv").exists()

    def test_input_parameter_files_exist(self):
        from energy_wallet.dspm_converter.pipeline import run_pipeline

        output_path = run_pipeline(
            library_path=self.lib_path,
            province="ON",
        )

        expected_params = [
            "heating_loads.csv",
            "cooling_loads.csv",
            "heating_system_efficiency.csv",
            "hvac_costs.csv",
            "other_energy_uses.csv",
            "dhw_system_efficiency.csv",
            "dhw_loads.csv",
            "dhw_costs.csv",
        ]
        for filename in expected_params:
            assert (output_path / "input_parameters" / filename).exists(), f"Missing: {filename}"

        # No shared_parameters or vehicle files
        assert not (output_path / "input_parameters" / "shared_parameters.csv").exists()
        assert not (output_path / "input_parameters" / "vehicle_costs.csv").exists()

    def test_population_shares_sum_to_one(self):
        import pandas as pd
        from energy_wallet.dspm_converter.pipeline import run_pipeline

        output_path = run_pipeline(
            library_path=self.lib_path,
            province="ON",
        )

        # Climate zone shares should sum to 1.0
        cz = pd.read_csv(output_path / "archetypes" / "climate_zone.csv")
        assert cz["population_share"].sum() == pytest.approx(1.0, abs=0.001)

        # Dwelling type shares should sum to 1.0 within each CZ
        dt = pd.read_csv(output_path / "archetypes" / "dwelling_type.csv")
        for cz_val in dt["climate_zone"].unique():
            cz_dt = dt[dt["climate_zone"] == cz_val]
            assert cz_dt["population_share"].sum() == pytest.approx(1.0, abs=0.001), \
                f"dwelling_type shares don't sum to 1.0 in {cz_val}"

        # HVAC system shares should sum to 1.0 within each (CZ, DT)
        hvac = pd.read_csv(output_path / "archetypes" / "hvac_system.csv")
        for (cz_val, dt_val), group in hvac.groupby(["climate_zone", "dwelling_type"]):
            assert group["population_share"].sum() == pytest.approx(1.0, abs=0.001), \
                f"hvac_system shares don't sum to 1.0 in ({cz_val}, {dt_val})"

    def test_heating_loads_positive(self):
        import pandas as pd
        from energy_wallet.dspm_converter.pipeline import run_pipeline

        output_path = run_pipeline(
            library_path=self.lib_path,
            province="ON",
        )

        hl = pd.read_csv(output_path / "input_parameters" / "heating_loads.csv")
        assert (hl["heating_load_annual"] > 0).all()
        # Sanity: Ontario heating loads should be 10-300 GJ/yr range
        assert hl["heating_load_annual"].min() > 10
        assert hl["heating_load_annual"].max() < 300

    def test_heating_efficiency_has_climate_zone(self):
        import pandas as pd
        from energy_wallet.dspm_converter.pipeline import run_pipeline

        output_path = run_pipeline(
            library_path=self.lib_path,
            province="ON",
        )

        eff = pd.read_csv(output_path / "input_parameters" / "heating_system_efficiency.csv")
        assert "climate_zone" in eff.columns
        assert len(eff["climate_zone"].unique()) > 1  # Multiple CZs

    def test_other_energy_uses_has_climate_zone(self):
        import pandas as pd
        from energy_wallet.dspm_converter.pipeline import run_pipeline

        output_path = run_pipeline(
            library_path=self.lib_path,
            province="ON",
        )

        other = pd.read_csv(output_path / "input_parameters" / "other_energy_uses.csv")
        assert "climate_zone" in other.columns

    def test_dhw_split_files(self):
        import pandas as pd
        from energy_wallet.dspm_converter.pipeline import run_pipeline

        output_path = run_pipeline(
            library_path=self.lib_path,
            province="ON",
        )

        # DHW efficiency
        eff = pd.read_csv(output_path / "input_parameters" / "dhw_system_efficiency.csv")
        assert "dhw_system" in eff.columns
        assert any("proportion" in c for c in eff.columns)
        assert any("efficiency" in c for c in eff.columns)
        # No climate_zone in dhw_system_efficiency
        assert "climate_zone" not in eff.columns

        # DHW loads
        loads = pd.read_csv(output_path / "input_parameters" / "dhw_loads.csv")
        assert "dwelling_type" in loads.columns
        assert "dhw_load_annual" in loads.columns

        # DHW costs
        costs = pd.read_csv(output_path / "input_parameters" / "dhw_costs.csv")
        assert "dhw_system" in costs.columns
        assert "dhw_equipment_cost" in costs.columns
        assert "dhw_assumed_life" in costs.columns

    def test_dry_run_no_output(self):
        from energy_wallet.dspm_converter.pipeline import run_pipeline

        def snapshot():
            return {
                (p.relative_to(self.lib_path), p.stat().st_size if p.is_file() else None)
                for p in self.lib_path.rglob("*")
            }

        before = snapshot()
        result = run_pipeline(
            library_path=self.lib_path,
            province="ON",
            dry_run=True,
        )
        assert result is None
        assert not (self.lib_path / "energy_wallet_inputs").exists()
        assert snapshot() == before

    def test_documentation_generated(self):
        from energy_wallet.dspm_converter.pipeline import run_pipeline

        output_path = run_pipeline(
            library_path=self.lib_path,
            province="ON",
        )

        doc_path = output_path / "documentation.md"
        assert doc_path.exists()
        content = doc_path.read_text()
        assert "Energy Wallet Input Files" in content
        assert "heating_loads.csv" in content
        assert "climate_zone" in content

    def test_single_province_no_province_column(self):
        """Single-province mode should NOT have a province column."""
        import pandas as pd
        from energy_wallet.dspm_converter.pipeline import run_pipeline

        output_path = run_pipeline(
            library_path=self.lib_path,
            province="ON",
        )

        cz = pd.read_csv(output_path / "archetypes" / "climate_zone.csv")
        assert "province" not in cz.columns

        hl = pd.read_csv(output_path / "input_parameters" / "heating_loads.csv")
        assert "province" not in hl.columns


@skip_no_dspm
class TestMultiProvincePipeline:
    """Multi-province (province=None) pipeline tests."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        import shutil
        self.lib_path = tmp_path / "canada_reference"
        shutil.copytree(DSPM_PATH, self.lib_path)

    def test_multi_province_runs(self):
        from energy_wallet.dspm_converter.pipeline import run_pipeline

        output_path = run_pipeline(
            library_path=self.lib_path,
            province=None,
            library_name="Canada Reference",
        )

        assert output_path is not None
        assert output_path.exists()
        assert (output_path / "archetypes").exists()
        assert (output_path / "input_parameters").exists()

    def test_multi_province_has_province_column(self):
        """All tables should have a 'province' column."""
        import pandas as pd
        from energy_wallet.dspm_converter.pipeline import run_pipeline

        output_path = run_pipeline(
            library_path=self.lib_path,
            province=None,
        )

        for csv_file in (output_path / "archetypes").glob("*.csv"):
            df = pd.read_csv(csv_file)
            assert "province" in df.columns, f"Missing province in {csv_file.name}"

        for csv_file in (output_path / "input_parameters").glob("*.csv"):
            df = pd.read_csv(csv_file)
            assert "province" in df.columns, f"Missing province in {csv_file.name}"

    def test_multi_province_shares_sum_to_one(self):
        """CZ shares should sum to 1.0 within each province."""
        import pandas as pd
        from energy_wallet.dspm_converter.pipeline import run_pipeline

        output_path = run_pipeline(
            library_path=self.lib_path,
            province=None,
        )

        cz = pd.read_csv(output_path / "archetypes" / "climate_zone.csv")
        for prov in cz["province"].unique():
            prov_cz = cz[cz["province"] == prov]
            assert prov_cz["population_share"].sum() == pytest.approx(1.0, abs=0.001), \
                f"CZ shares don't sum to 1.0 in province {prov}"
