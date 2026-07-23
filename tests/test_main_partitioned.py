"""CLI-level tests for partitioned execution and output format resolution."""
from __future__ import annotations

import filecmp
from pathlib import Path
import sys

import polars as pl
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from energy_wallet.main import main  # noqa: E402
from energy_wallet.calculations import CalculationError  # noqa: E402
import energy_wallet.main as main_module  # noqa: E402

_INPUTS_ROOT = Path(__file__).resolve().parents[1] / "inputs" / "test_input_set_1"
_STEP2_ROWS = 1_962  # measured for test_input_set_1


def _run(tmp_dir: Path, extra: list[str]) -> int:
    argv = [
        "--inputs-root", str(_INPUTS_ROOT),
        "--output", str(tmp_dir / "step1.csv"),
        "--step2-output", str(tmp_dir / "step2.csv"),
        "--step3-output", str(tmp_dir / "step3.csv"),
        "--step4-output", str(tmp_dir / "step4.csv"),
        "--step5-output", str(tmp_dir / "step5.csv"),
    ] + extra
    return main(argv)


def test_auto_single_partition_produces_csv(tmp_path):
    assert _run(tmp_path, []) == 0  # default partition-rows >> 1,962 rows
    for name in ("step1", "step2", "step3", "step4", "step5"):
        assert (tmp_path / f"{name}.csv").is_file(), name
        assert not (tmp_path / name).exists()  # no parquet dirs


def test_auto_partitioned_produces_parquet_dirs(tmp_path, capsys):
    assert _run(tmp_path, ["--partition-rows", "500"]) == 0  # 1,962 rows -> 4 partitions
    # Steps 1-2 are single artifacts; steps 3-5 are part-file directories.
    assert (tmp_path / "step1.parquet").is_file()
    assert (tmp_path / "step2.parquet").is_file()
    for name in ("step3", "step4", "step5"):
        d = tmp_path / name
        assert d.is_dir(), name
        parts = sorted(f.name for f in d.iterdir())
        assert parts == [f"part-{k:04d}.parquet" for k in range(4)]
        rows = pl.scan_parquet(str(d / "*.parquet")).select(pl.len()).collect().item()
        assert rows == _STEP2_ROWS
    out = capsys.readouterr().out
    assert "4 partitions" in out
    assert "auto-selected" in out


def test_partitioned_skip_step4_writes_only_step3(tmp_path):
    assert _run(tmp_path, ["--partition-rows", "500", "--skip-step4"]) == 0
    step3 = tmp_path / "step3"
    assert step3.is_dir()
    assert sorted(f.name for f in step3.iterdir()) == [
        f"part-{k:04d}.parquet" for k in range(4)
    ]
    assert not (tmp_path / "step3.partial").exists()
    for name in ("step4", "step5"):
        assert not (tmp_path / name).exists()
        assert not (tmp_path / f"{name}.parquet").exists()
        assert not (tmp_path / f"{name}.partial").exists()


def test_partitioned_csv_byte_identical_to_unpartitioned(tmp_path):
    single_dir = tmp_path / "single"
    parts_dir = tmp_path / "parts"
    single_dir.mkdir()
    parts_dir.mkdir()

    assert _run(single_dir, ["--output-format", "csv"]) == 0
    assert _run(parts_dir, ["--output-format", "csv", "--partition-rows", "500"]) == 0

    for name in ("step3", "step4", "step5"):
        assert filecmp.cmp(
            single_dir / f"{name}.csv", parts_dir / f"{name}.csv", shallow=False
        ), f"{name} output differs between partitioned and unpartitioned runs"


def test_failed_partition_leaves_only_partial_artifacts(tmp_path, monkeypatch, capsys):
    real_run_step4 = main_module.run_step4
    calls = {"n": 0}

    def flaky_run_step4(*, model_inputs):
        calls["n"] += 1
        if calls["n"] == 2:
            raise CalculationError("injected failure for atomicity test")
        return real_run_step4(model_inputs=model_inputs)

    monkeypatch.setattr(main_module, "run_step4", flaky_run_step4)

    rc = _run(tmp_path, ["--partition-rows", "500"])  # 4 partitions, auto -> parquet
    assert rc == 5

    err = capsys.readouterr().err
    assert "[partition 2/4]" in err
    assert "injected failure" in err

    # Steps 1-2 finished before the loop: final artifacts exist.
    assert (tmp_path / "step1.parquet").is_file()
    assert (tmp_path / "step2.parquet").is_file()
    # Steps 3-5: no final artifacts, only .partial leftovers for inspection.
    for name in ("step3", "step4", "step5"):
        assert not (tmp_path / name).exists(), f"{name} final dir should not exist"
        assert not (tmp_path / f"{name}.parquet").exists()
        assert not (tmp_path / f"{name}.csv").exists()
    assert (tmp_path / "step3.partial").is_dir()
    assert (tmp_path / "step4.partial").is_dir()
