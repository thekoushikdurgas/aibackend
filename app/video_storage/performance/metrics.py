"""Shared performance metric definitions for vSQL benchmarks.

The "1M/sec" goal is intentionally measured multiple ways. Rows/sec is only
meaningful when row width is fixed, while byte throughput reveals whether the
frame/video layer itself is the bottleneck.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from time import perf_counter
from typing import Iterator


@dataclass(frozen=True)
class PerfTarget:
    """A fixed-width workload definition used to derive rows/sec from bytes/sec."""

    name: str
    row_width_bytes: int
    columns: int = 4

    @property
    def cell_width_bytes(self) -> float:
        return self.row_width_bytes / max(1, self.columns)


@dataclass
class PerfSample:
    """One benchmark result with derived throughput fields."""

    name: str
    seconds: float
    bytes_processed: int = 0
    rows_processed: int = 0
    cells_processed: int = 0
    frames_processed: int = 0

    @property
    def bytes_per_second(self) -> float:
        return self.bytes_processed / self.seconds if self.seconds > 0 else 0.0

    @property
    def megabytes_per_second(self) -> float:
        return self.bytes_per_second / (1024 * 1024)

    @property
    def rows_per_second(self) -> float:
        return self.rows_processed / self.seconds if self.seconds > 0 else 0.0

    @property
    def cells_per_second(self) -> float:
        return self.cells_processed / self.seconds if self.seconds > 0 else 0.0

    @property
    def frames_per_second(self) -> float:
        return self.frames_processed / self.seconds if self.seconds > 0 else 0.0

    def to_dict(self) -> dict[str, float | int | str]:
        data = asdict(self)
        data.update(
            {
                "bytes_per_second": self.bytes_per_second,
                "megabytes_per_second": self.megabytes_per_second,
                "rows_per_second": self.rows_per_second,
                "cells_per_second": self.cells_per_second,
                "frames_per_second": self.frames_per_second,
            }
        )
        return data


class stopwatch:
    """Small context manager for benchmark timings."""

    def __enter__(self) -> "stopwatch":
        self.start = perf_counter()
        self.end = self.start
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.end = perf_counter()

    @property
    def seconds(self) -> float:
        return max(0.0, self.end - self.start)


DEFAULT_TARGETS = (
    PerfTarget("row16", 16),
    PerfTarget("row64", 64),
    PerfTarget("row256", 256),
    PerfTarget("row1024", 1024),
)


def synthetic_fixed_rows(target: PerfTarget, row_count: int) -> Iterator[bytes]:
    """Yield deterministic fixed-width rows for repeatable throughput tests."""

    width = target.row_width_bytes
    for i in range(row_count):
        prefix = f"{i:012d}|".encode("ascii")
        if len(prefix) >= width:
            yield prefix[:width]
        else:
            yield prefix + (b"x" * (width - len(prefix)))
