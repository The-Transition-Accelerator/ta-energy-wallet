"""Tests for partitioned execution of Steps 3-5."""
from __future__ import annotations

from pathlib import Path
import sys

import polars as pl
import polars.testing
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from energy_wallet.partitioning import (  # noqa: E402
    compute_partition_count,
    estimate_csv_output_gb,
    resolve_output_format,
    StepOutputWriter,
)


class TestComputePartitionCount:
    def test_exact_multiple(self):
        assert compute_partition_count(800_000, 400_000) == 2

    def test_remainder_rounds_up(self):
        assert compute_partition_count(5_433_120, 400_000) == 14

    def test_small_input_single_partition(self):
        assert compute_partition_count(1_962, 400_000) == 1

    def test_zero_rows_is_one_partition(self):
        assert compute_partition_count(0, 400_000) == 1

    def test_invalid_partition_rows_raises(self):
        with pytest.raises(ValueError, match="partition_rows"):
            compute_partition_count(100, 0)


class TestResolveOutputFormat:
    def test_explicit_csv_honored_when_partitioned(self):
        assert resolve_output_format("csv", 5) == "csv"

    def test_explicit_parquet_honored_when_single(self):
        assert resolve_output_format("parquet", 1) == "parquet"

    def test_auto_single_partition_is_csv(self):
        assert resolve_output_format("auto", 1) == "csv"

    def test_auto_multi_partition_is_parquet(self):
        assert resolve_output_format("auto", 2) == "parquet"


class TestEstimateCsvOutputGb:
    def test_scales_linearly_with_rows(self):
        small = pl.DataFrame({"a": list(range(1_000)), "b": ["xyz"] * 1_000})
        big = pl.concat([small, small])
        est_small = estimate_csv_output_gb(small)
        est_big = estimate_csv_output_gb(big)
        assert est_small > 0
        assert est_big == pytest.approx(2 * est_small, rel=0.05)

    def test_empty_frame_is_zero(self):
        assert estimate_csv_output_gb(pl.DataFrame({"a": []})) == 0.0


def _df(start: int, n: int) -> pl.DataFrame:
    return pl.DataFrame({"id": list(range(start, start + n)), "val": [1.5] * n})


class TestStepOutputWriterCsv:
    def test_single_partition_matches_plain_write_csv(self, tmp_path):
        df = _df(0, 5)
        w = StepOutputWriter(tmp_path / "out.csv", "csv", n_partitions=1)
        w.write_partition(df, 0)
        final = w.finalize()
        assert final == tmp_path / "out.csv"
        assert final.read_bytes() == df.write_csv().encode()

    def test_append_writes_header_once(self, tmp_path):
        w = StepOutputWriter(tmp_path / "out.csv", "csv", n_partitions=3)
        for k in range(3):
            w.write_partition(_df(k * 4, 4), k)
        final = w.finalize()
        lines = final.read_text().strip().splitlines()
        assert lines[0] == "id,val"
        assert len(lines) == 1 + 12  # one header + 3 partitions x 4 rows
        assert sum(1 for ln in lines if ln == "id,val") == 1

    def test_partial_until_finalize(self, tmp_path):
        w = StepOutputWriter(tmp_path / "out.csv", "csv", n_partitions=2)
        w.write_partition(_df(0, 2), 0)
        assert (tmp_path / "out.csv.partial").exists()
        assert not (tmp_path / "out.csv").exists()
        w.write_partition(_df(2, 2), 1)
        w.finalize()
        assert (tmp_path / "out.csv").exists()
        assert not (tmp_path / "out.csv.partial").exists()

    def test_finalize_overwrites_previous_final(self, tmp_path):
        (tmp_path / "out.csv").write_text("stale")
        w = StepOutputWriter(tmp_path / "out.csv", "csv", n_partitions=1)
        w.write_partition(_df(0, 1), 0)
        w.finalize()
        assert "stale" not in (tmp_path / "out.csv").read_text()

    def test_abort_leaves_partial_csv(self, tmp_path):
        w = StepOutputWriter(tmp_path / "out.csv", "csv", n_partitions=2)
        w.write_partition(_df(0, 2), 0)
        w.abort()
        assert (tmp_path / "out.csv.partial").exists()
        assert not (tmp_path / "out.csv").exists()

    def test_finalize_without_writes_raises(self, tmp_path):
        w = StepOutputWriter(tmp_path / "out.csv", "csv", n_partitions=1)
        with pytest.raises(RuntimeError, match="before any write_partition"):
            w.finalize()

    def test_finalize_twice_is_idempotent(self, tmp_path):
        w = StepOutputWriter(tmp_path / "out.csv", "csv", n_partitions=1)
        w.write_partition(_df(0, 1), 0)
        first = w.finalize()
        assert w.finalize() == first

    def test_write_after_finalize_raises(self, tmp_path):
        w = StepOutputWriter(tmp_path / "out.csv", "csv", n_partitions=1)
        w.write_partition(_df(0, 1), 0)
        w.finalize()
        with pytest.raises(RuntimeError, match="after finalize"):
            w.write_partition(_df(1, 1), 1)


class TestStepOutputWriterParquet:
    def test_single_partition_single_file(self, tmp_path):
        df = _df(0, 5)
        w = StepOutputWriter(tmp_path / "out.csv", "parquet", n_partitions=1)
        w.write_partition(df, 0)
        final = w.finalize()
        assert final == tmp_path / "out.parquet"
        assert final.is_file()
        pl.testing.assert_frame_equal(pl.read_parquet(final), df)

    def test_multi_partition_directory_roundtrip(self, tmp_path):
        w = StepOutputWriter(tmp_path / "out.csv", "parquet", n_partitions=3)
        parts = [_df(k * 4, 4) for k in range(3)]
        for k, p in enumerate(parts):
            w.write_partition(p, k)
        final = w.finalize()
        assert final == tmp_path / "out"
        assert final.is_dir()
        names = sorted(f.name for f in final.iterdir())
        assert names == ["part-0000.parquet", "part-0001.parquet", "part-0002.parquet"]
        scanned = pl.scan_parquet(str(final / "*.parquet")).collect()
        pl.testing.assert_frame_equal(scanned, pl.concat(parts))

    def test_partial_until_finalize(self, tmp_path):
        w = StepOutputWriter(tmp_path / "out.csv", "parquet", n_partitions=2)
        w.write_partition(_df(0, 2), 0)
        assert (tmp_path / "out.partial").is_dir()
        assert not (tmp_path / "out").exists()

    def test_stale_partial_removed_on_init(self, tmp_path):
        stale = tmp_path / "out.partial"
        stale.mkdir()
        (stale / "part-0000.parquet").write_bytes(b"junk")
        w = StepOutputWriter(tmp_path / "out.csv", "parquet", n_partitions=2)
        assert not stale.exists()

    def test_abort_leaves_partial_only(self, tmp_path):
        w = StepOutputWriter(tmp_path / "out.csv", "parquet", n_partitions=2)
        w.write_partition(_df(0, 2), 0)
        w.abort()
        assert (tmp_path / "out.partial").is_dir()
        assert not (tmp_path / "out").exists()

    def test_finalize_overwrites_stale_final_dir(self, tmp_path):
        stale = tmp_path / "out"
        stale.mkdir()
        (stale / "part-0099.parquet").write_bytes(b"orphan")  # from a larger prior run
        w = StepOutputWriter(tmp_path / "out.csv", "parquet", n_partitions=2)
        for k, p in enumerate([_df(0, 2), _df(2, 2)]):
            w.write_partition(p, k)
        final = w.finalize()
        names = sorted(f.name for f in final.iterdir())
        assert names == ["part-0000.parquet", "part-0001.parquet"]  # orphan gone
        scanned = pl.scan_parquet(str(final / "*.parquet")).collect()
        pl.testing.assert_frame_equal(scanned, pl.concat([_df(0, 2), _df(2, 2)]))


from energy_wallet.archetypes import load_all_archetype_tables, merge_archetypes  # noqa: E402
from energy_wallet.alternative_configurations import build_expanded_archetype_table  # noqa: E402
from energy_wallet.input_parameters import (  # noqa: E402
    build_model_input_table,
    load_model_input_tables,
)

_INPUTS_ROOT = Path(__file__).resolve().parents[1] / "inputs" / "test_input_set_1"


@pytest.fixture(scope="module")
def expanded_df() -> pl.DataFrame:
    tables_list, specs_list = load_all_archetype_tables(_INPUTS_ROOT / "archetypes")
    tables = {s.path.stem: t for t, s in zip(tables_list, specs_list)}
    specs = {s.path.stem: s for s in specs_list}
    merged = merge_archetypes(tables, specs)
    return build_expanded_archetype_table(merged, inputs_root=_INPUTS_ROOT)


class TestLoadModelInputTables:
    def test_returns_aligned_dicts(self, expanded_df):
        tables, specs = load_model_input_tables(
            _INPUTS_ROOT / "input_parameters", set(expanded_df.columns)
        )
        assert set(tables.keys()) == set(specs.keys())
        assert len(tables) > 0
        for name, table in tables.items():
            assert isinstance(table, pl.DataFrame)
            assert specs[name].path.stem == name

    def test_preloaded_tables_give_identical_output(self, expanded_df):
        via_default = build_model_input_table(expanded_df, inputs_root=_INPUTS_ROOT)
        preloaded = load_model_input_tables(
            _INPUTS_ROOT / "input_parameters", set(expanded_df.columns)
        )
        via_preloaded = build_model_input_table(
            expanded_df, inputs_root=_INPUTS_ROOT, tables_and_specs=preloaded
        )
        pl.testing.assert_frame_equal(via_default, via_preloaded)
