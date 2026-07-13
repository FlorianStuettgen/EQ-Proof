"""Regenerate checked-in evidence with a deterministic, non-secret demonstration key."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from eq_proof.proof import build_proof  # noqa: E402
from eq_proof.core import repair  # noqa: E402
from eq_proof.proof import render_markdown  # noqa: E402
from eq_proof.core import load_specification  # noqa: E402

DEMO_SEED = bytes.fromhex("4f7b8af0f159a17dbf5cb6899f524499868f9b915acdd7f7115a0d4f4d7d67a2")


def main() -> None:
    evidence = ROOT / "evidence"
    evidence.mkdir(exist_ok=True)
    private_key = Ed25519PrivateKey.from_private_bytes(DEMO_SEED)
    private_path = evidence / ".demo-private-key.tmp.pem"
    private_path.write_bytes(private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ))
    (evidence / "demo-public-key.pem").write_bytes(private_key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    ))

    example = ROOT / "examples" / "portfolio_allocation"
    spec = load_specification(example / "spec.json")
    submitted = json.loads((example / "input.json").read_text())
    result = repair(spec, submitted)
    proof = build_proof(
        spec,
        result,
        private_key_path=private_path,
        created_utc="2026-07-13T00:00:00Z",
    )
    private_path.unlink()
    (evidence / "portfolio-allocation.proof.json").write_text(
        json.dumps(proof, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (evidence / "portfolio-allocation.report.md").write_text(render_markdown(proof), encoding="utf-8")
    print("regenerated deterministic evidence")


if __name__ == "__main__":
    main()
