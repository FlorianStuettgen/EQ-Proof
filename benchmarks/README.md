# Benchmark methodology

`baseline.json` is a reproducible local microbenchmark, not a service-level objective. It measures end-to-end parsing-independent repair time after one warm-up for bounded variables plus one equality constraint. Each case records the median, minimum, maximum, Dykstra iteration count, Python version, and host platform.

Regenerate it with:

```bash
python scripts/benchmark_solver.py --write
```

The benchmark exists to expose scaling behaviour and prevent performance claims from becoming anecdotal. It is intentionally excluded from CI pass/fail decisions because shared runners are noisy.
