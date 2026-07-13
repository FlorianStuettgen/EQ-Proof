"""Run the same repository proof used by CI."""

from __future__ import annotations

import compileall
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(*command: str) -> None:
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> int:
    run(
        sys.executable,
        "-m",
        "pytest",
        "--cov=eq_proof",
        "--cov-report=term-missing",
        "--cov-report=xml",
    )
    if not compileall.compile_dir(ROOT / "src", quiet=1):
        raise SystemExit("Module compilation failed")
    run(sys.executable, "scripts/regenerate_evidence.py")
    if (ROOT / ".git").exists():
        run("git", "diff", "--exit-code")
    print("Repository proof passed: tests, coverage, compilation, and deterministic evidence.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
