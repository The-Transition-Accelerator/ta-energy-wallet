"""Partitioned execution support for Steps 3-5.

Steps 3-5 are row-local (joins + per-row arithmetic; the only cross-row
computations in the pipeline are the weight-sum validations in Steps 1-2),
so running them on contiguous row ranges and concatenating the results is
exactly equivalent to a single full-table run. Partitioning bounds peak
memory by partition size instead of input size.
"""
from __future__ import annotations

import math
import os
import shutil
from pathlib import Path
from typing import IO, Optional

import polars as pl

DEFAULT_PARTITION_ROWS = 400_000
"""~plain-ontario scale; measured ~2.2 GB peak through Steps 3-5 at ~288 cols."""

CSV_PROJECTION_FACTOR = 95
"""Measured on ontario_modified (2026-06-10): step3+4+5 CSV bytes are ~95x the
step2 CSV bytes for the same rows. Order-of-magnitude only."""


def compute_partition_count(n_rows: int, partition_rows: int) -> int:
    """Number of contiguous row-range partitions for *n_rows*."""
    if partition_rows < 1:
        raise ValueError(f"partition_rows must be >= 1, got {partition_rows}")
    return max(1, math.ceil(n_rows / partition_rows))


def resolve_output_format(requested: str, n_partitions: int) -> str:
    """Resolve the ``--output-format`` value to a concrete format.

    ``auto`` becomes ``csv`` for single-partition runs (today's artifact,
    dashboard/Excel friendly) and ``parquet`` for partitioned runs.
    """
    if requested != "auto":
        return requested
    return "csv" if n_partitions == 1 else "parquet"


def estimate_csv_output_gb(step2_df: pl.DataFrame) -> float:
    """Rough projected total CSV size (GB) of Steps 3-5 outputs."""
    sample = step2_df.head(1_000)
    if len(sample) == 0:
        return 0.0
    bytes_per_row = len(sample.write_csv()) / len(sample)
    return len(step2_df) * bytes_per_row * CSV_PROJECTION_FACTOR / 1e9


class StepOutputWriter:
    """Incrementally writes one step's output across partitions.

    Layouts (``path`` is the CLI-provided ``.csv`` output path):

    - ``csv``: single file at ``path``; header from partition 0 only.
    - ``parquet``, 1 partition: single file at ``path.with_suffix(".parquet")``.
    - ``parquet``, >1 partitions: directory at ``path.with_suffix("")``
      containing ``part-0000.parquet``, ``part-0001.parquet``, ...

    All output builds at ``<final>.partial`` and moves to the final path only
    on :meth:`finalize`, so a failed run never leaves a readable final
    artifact. Stale ``.partial`` leftovers from a crashed run are removed on
    construction. :meth:`abort` closes handles and leaves the ``.partial``
    artifact in place for post-mortem inspection.
    """

    def __init__(self, path: Path, fmt: str, n_partitions: int) -> None:
        if fmt not in ("csv", "parquet"):
            raise ValueError(f"fmt must be 'csv' or 'parquet', got {fmt!r}")
        self.fmt = fmt
        self.n_partitions = n_partitions
        if fmt == "parquet":
            base = path.with_suffix(".parquet") if n_partitions == 1 else path.with_suffix("")
        else:
            base = path
        self.final_path = base
        self.partial_path = base.with_name(base.name + ".partial")
        self._csv_handle: Optional[IO[bytes]] = None
        self._finalized = False

        self.final_path.parent.mkdir(parents=True, exist_ok=True)
        if self.partial_path.is_dir():
            shutil.rmtree(self.partial_path)
        elif self.partial_path.exists():
            self.partial_path.unlink()

    def write_partition(self, df: pl.DataFrame, k: int) -> None:
        if self._finalized:
            raise RuntimeError(f"write_partition() called after finalize() for {self.final_path}")
        if self.fmt == "csv":
            if self._csv_handle is None:
                self._csv_handle = open(self.partial_path, "wb")
            df.write_csv(self._csv_handle, include_header=(k == 0))
        elif self.n_partitions == 1:
            df.write_parquet(self.partial_path)
        else:
            self.partial_path.mkdir(parents=True, exist_ok=True)
            df.write_parquet(self.partial_path / f"part-{k:04d}.parquet")

    def finalize(self) -> Path:
        if self._finalized:
            return self.final_path
        self._close_handle()
        if not self.partial_path.exists():
            raise RuntimeError(
                f"finalize() called before any write_partition() for {self.final_path}"
            )
        if self.final_path.is_dir():
            shutil.rmtree(self.final_path)
        if self.partial_path.is_dir():
            # A directory swap cannot be atomic; the half-written data was
            # only ever visible at the .partial path, which is the guarantee
            # that matters.
            if self.final_path.exists():
                self.final_path.unlink()
            self.partial_path.rename(self.final_path)
        else:
            # Atomically replaces an existing final file (same filesystem).
            os.replace(self.partial_path, self.final_path)
        self._finalized = True
        return self.final_path

    def abort(self) -> None:
        self._close_handle()

    def _close_handle(self) -> None:
        if self._csv_handle is not None:
            self._csv_handle.close()
            self._csv_handle = None
