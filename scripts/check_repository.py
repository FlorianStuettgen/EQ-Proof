"""One-command local verification matching CI."""

from __future__ import annotations

import compileall
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    if not compileall.compile_dir(ROOT / "src", quiet=1):
        return 1
    return subprocess.call([sys.executable, "-m", "pytest", "--cov=eq_proof", "--cov-report=term-missing"], cwd=ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
