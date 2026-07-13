"""Regenerate the checked-in portfolio evidence deterministically."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from eq_proof import parse_specification, repair
from eq_proof.proof import build_proof, render_markdown, verify_proof

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "portfolio_allocation"
EVIDENCE = ROOT / "evidence"
DEMO_SEED = bytes.fromhex("4f9d6db6f139f2d329caf0bc4e2e50d95c0b130b2428740773c10db7ccf1dc29")
CREATED_UTC = "2026-07-13T00:00:00Z"


def main() -> int:
    specification_document = json.loads((EXAMPLE / "spec.json").read_text(encoding="utf-8"))
    values = json.loads((EXAMPLE / "input.json").read_text(encoding="utf-8"))
    specification = parse_specification(specification_document)
    result = repair(specification, values)

    EVIDENCE.mkdir(parents=True, exist_ok=True)
    private_key = Ed25519PrivateKey.from_private_bytes(DEMO_SEED)
    public_key_bytes = private_key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    public_path = EVIDENCE / "demo-public-key.pem"
    public_path.write_bytes(public_key_bytes)

    with tempfile.TemporaryDirectory() as directory:
        private_path = Path(directory) / "demo-private-key.pem"
        private_path.write_bytes(
            private_key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            )
        )
        proof = build_proof(
            specification,
            result,
            private_key_path=private_path,
            created_utc=CREATED_UTC,
        )

    verify_proof(proof, public_path)
    (EVIDENCE / "portfolio-allocation.proof.json").write_text(
        json.dumps(proof, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    (EVIDENCE / "portfolio-allocation.report.md").write_text(
        render_markdown(proof),
        encoding="utf-8",
    )
    print("Regenerated deterministic evidence and verified semantic replay.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
