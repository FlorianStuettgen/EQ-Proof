"""Run the same repository proof used by CI."""

from __future__ import annotations

import compileall
import shutil
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
    run(sys.executable, "scripts/regenerate_control_room_demo.py")
    if shutil.which("node"):
        for script in ("app.js", "renderers.js", "workflow.js"):
            run("node", "--check", f"src/eq_proof/web/{script}")
    if (ROOT / ".git").exists():
        run("git", "diff", "--exit-code")
    print(
        "Repository proof passed: tests, coverage, compilation, "
        "browser syntax, and deterministic evidence."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
