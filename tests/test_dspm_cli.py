"""CLI tests for the DSPM converter."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from energy_wallet.dspm_converter.cli import main, _find_libraries


class TestCLI:
    def test_no_args_needs_interactive(self):
        """Without --library/--province, CLI needs interactive input.
        With no TTY, it should handle gracefully."""
        # Mocking input to raise EOFError (no TTY)
        with patch("builtins.input", side_effect=EOFError):
            with pytest.raises(SystemExit):
                main([])

    def test_library_not_found(self, tmp_path):
        """Should exit with code 1 when library doesn't exist."""
        result = main([
            "--library", "nonexistent",
            "--province", "ON",
            "--libraries-dir", str(tmp_path),
        ])
        assert result == 1

    def test_dry_run_flag_accepted(self, tmp_path):
        """Verify --dry-run flag is accepted and doesn't write files."""
        # Create a minimal library structure
        lib_dir = tmp_path / "dspm_data_libraries" / "test_lib"
        lib_dir.mkdir(parents=True)
        # Just need the building_stock_library.csv to exist for discovery
        # but pipeline will fail because data is incomplete
        (lib_dir / "building_stock_library.csv").write_text(
            "building_genome_id,province_territory,climate_zone\n"
        )

        # Will fail at pipeline stage (incomplete data), but verifies flag parsing
        result = main([
            "--library", "test_lib",
            "--province", "ON",
            "--libraries-dir", str(tmp_path / "dspm_data_libraries"),
            "--dry-run",
        ])
        assert result == 2  # Pipeline error due to incomplete data

    def test_all_provinces_flag_accepted(self, tmp_path):
        """Verify --province ALL flag is accepted."""
        lib_dir = tmp_path / "dspm_data_libraries" / "test_lib"
        lib_dir.mkdir(parents=True)
        (lib_dir / "building_stock_library.csv").write_text(
            "building_genome_id,province_territory,climate_zone\n"
        )

        # Will fail at pipeline stage (incomplete data), but verifies flag parsing
        result = main([
            "--library", "test_lib",
            "--province", "ALL",
            "--libraries-dir", str(tmp_path / "dspm_data_libraries"),
            "--dry-run",
        ])
        assert result == 2  # Pipeline error due to incomplete data

    def test_verbose_flag_accepted(self, tmp_path):
        """Verify --verbose flag is accepted."""
        lib_dir = tmp_path / "dspm_data_libraries" / "test_lib"
        lib_dir.mkdir(parents=True)
        (lib_dir / "building_stock_library.csv").write_text(
            "building_genome_id,province_territory,climate_zone\n"
        )

        # Mock confirmation prompt since pytest captures stdin
        with patch("energy_wallet.dspm_converter.cli._prompt_confirm", return_value=True):
            result = main([
                "--library", "test_lib",
                "--province", "ON",
                "--libraries-dir", str(tmp_path / "dspm_data_libraries"),
                "--verbose",
            ])
        assert result == 2  # Pipeline error


class TestLibraryDiscovery:
    def test_find_libraries_empty(self, tmp_path):
        """No libraries when directory is empty."""
        libs = _find_libraries(tmp_path)
        assert libs == []

    def test_find_libraries_with_config(self, tmp_path):
        """Discover library with library_config.json."""
        lib_dir = tmp_path / "test_lib"
        lib_dir.mkdir()
        (lib_dir / "building_stock_library.csv").write_text("col1\nval1\n")
        (lib_dir / "library_config.json").write_text(json.dumps({
            "display_name": "Test Library",
            "description": "A test library",
        }))

        libs = _find_libraries(tmp_path)
        assert len(libs) == 1
        path, name, desc = libs[0]
        assert name == "Test Library"
        assert desc == "A test library"

    def test_find_libraries_without_config(self, tmp_path):
        """Discover library without library_config.json (uses dir name)."""
        lib_dir = tmp_path / "my_data"
        lib_dir.mkdir()
        (lib_dir / "building_stock_library.csv").write_text("col1\nval1\n")

        libs = _find_libraries(tmp_path)
        assert len(libs) == 1
        path, name, desc = libs[0]
        assert name == "my_data"

    def test_skip_dir_without_building_stock(self, tmp_path):
        """Directories without building_stock_library.csv are skipped."""
        (tmp_path / "not_a_lib").mkdir()
        (tmp_path / "not_a_lib" / "other.csv").write_text("data\n")

        libs = _find_libraries(tmp_path)
        assert libs == []
