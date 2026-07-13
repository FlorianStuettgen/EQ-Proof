"""Deterministic microbenchmark for representative bounded-simplex repairs."""

from __future__ import annotations

import argparse
import json
import platform
import statistics
import sys
import time
from pathlib import Path

import numpy as np

from eq_proof import parse_specification, repair

ROOT = Path(__file__).resolve().parents[1]


def case(size: int):
    names = [f"x{index}" for index in range(size)]
    specification = parse_specification(
        {
            "schema_version": "1.0",
            "name": f"simplex-{size}",
            "variables": {name: {"lower": 0, "upper": 1} for name in names},
            "equations": [
                {"id": "total", "expression": " + ".join(names) + " == 1"}
            ],
        }
    )
    values = {name: float(value) for name, value in zip(names, np.linspace(0.02, 0.04, size), strict=True)}
    return specification, values


def benchmark(size: int, repeats: int) -> dict[str, float | int]:
    specification, values = case(size)
    repair(specification, values)
    samples = []
    iterations = 0
    for _ in range(repeats):
        started = time.perf_counter_ns()
        result = repair(specification, values)
        samples.append((time.perf_counter_ns() - started) / 1_000_000)
        iterations = result.iterations
    return {
        "variables": size,
        "constraints": size * 2 + 1,
        "median_ms": round(statistics.median(samples), 6),
        "min_ms": round(min(samples), 6),
        "max_ms": round(max(samples), 6),
        "iterations": iterations,
        "repeats": repeats,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--repeats", type=int, default=25)
    args = parser.parse_args()
    payload = {
        "disclaimer": "Local microbenchmark only; not a throughput SLA.",
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "processor": platform.processor() or "not reported",
        },
        "method": "Median wall-clock time after one warm-up; bounded variables plus one equality.",
        "results": [benchmark(size, args.repeats) for size in (10, 50, 100, 250)],
    }
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.write:
        destination = ROOT / "benchmarks" / "baseline.json"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(text, encoding="utf-8")
        print(destination)
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
