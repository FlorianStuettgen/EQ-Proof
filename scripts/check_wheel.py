"""Verify browser assets and routes from the built wheel, not an editable install."""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "src" / "eq_proof" / "web"

PROBE = """
import sys
from pathlib import Path

installed = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(installed))
from eq_proof.webapp import WEB_ROOT, create_app
from fastapi.testclient import TestClient

assert WEB_ROOT.resolve().is_relative_to(installed), WEB_ROOT
with TestClient(create_app()) as client:
    assert client.get('/').status_code == 200
    assert client.get('/api/health').json() == {'status': 'ok', 'mode': 'local-first'}
    assets = sorted(path for path in WEB_ROOT.rglob('*') if path.is_file())
    for asset in assets:
        route = '/' + asset.relative_to(WEB_ROOT).as_posix()
        response = client.get(route)
        assert response.status_code == 200, (route, response.status_code)
        assert response.content == asset.read_bytes(), route
    print(f'Wheel runtime passed: {len(assets)} browser assets and health endpoint.')
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel", type=Path, nargs="?")
    args = parser.parse_args()
    if args.wheel is None:
        wheels = sorted((ROOT / "dist").glob("eq_proof-*.whl"))
        if len(wheels) != 1:
            parser.error("Supply one wheel path, or build exactly one wheel in dist/.")
        wheel = wheels[0]
    else:
        wheel = args.wheel

    with ZipFile(wheel) as archive:
        members = set(archive.namelist())
        expected = {
            path.relative_to(ROOT / "src").as_posix(): path
            for path in WEB.rglob("*")
            if path.is_file()
        }
        missing = sorted(expected.keys() - members)
        if missing:
            raise SystemExit("Wheel is missing browser assets: " + ", ".join(missing))
        for name, source in expected.items():
            if archive.read(name) != source.read_bytes():
                raise SystemExit(f"Wheel browser asset differs from source: {name}")
        with tempfile.TemporaryDirectory(prefix="eq-proof-wheel-") as directory:
            archive.extractall(directory)
            subprocess.run(
                [sys.executable, "-I", "-c", PROBE, directory],
                cwd=directory,
                check=True,
            )
    print(f"Wheel proof passed: {wheel.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
