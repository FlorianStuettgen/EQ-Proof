"""Command-line interface."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from .core import EQProofError, load_specification, repair
from .proof import build_proof, generate_keypair, render_markdown, verify_proof


def _load_json(path: str | Path) -> dict[str, object]:
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return document


def _write_json(path: str | Path, value: object) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="eq-proof", description="Repair numeric outputs and emit verifiable proof artifacts")
    subparsers = parser.add_subparsers(dest="command", required=True)

    repair_parser = subparsers.add_parser("repair", help="Validate and minimally repair an input")
    repair_parser.add_argument("--spec", required=True, help="Path to the JSON constraint specification")
    repair_parser.add_argument("--input", required=True, help="Path to the submitted JSON values")
    repair_parser.add_argument("--proof", required=True, help="Path for the authoritative JSON proof")
    repair_parser.add_argument("--report", help="Optional Markdown report path")
    repair_parser.add_argument("--private-key", help="Optional Ed25519 private key PEM")
    repair_parser.add_argument("--tolerance", type=float, default=1e-10)
    repair_parser.add_argument("--max-iterations", type=int, default=20_000)

    verify_parser = subparsers.add_parser("verify", help="Verify a proof digest and optional Ed25519 signature")
    verify_parser.add_argument("proof", help="Path to proof JSON")
    verify_parser.add_argument("--public-key", help="Trusted Ed25519 public key PEM")

    keygen_parser = subparsers.add_parser("keygen", help="Generate an Ed25519 keypair")
    keygen_parser.add_argument("--private-key", required=True)
    keygen_parser.add_argument("--public-key", required=True)
    keygen_parser.add_argument("--force", action="store_true")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "keygen":
            generate_keypair(args.private_key, args.public_key, force=args.force)
            print(f"generated private key: {args.private_key}")
            print(f"generated public key:  {args.public_key}")
            return 0

        if args.command == "verify":
            proof = _load_json(args.proof)
            verification = verify_proof(proof, args.public_key)
            label = verification.signer_fingerprint or "digest-only"
            print(f"VERIFIED {label}")
            return 0

        specification = load_specification(args.spec)
        submitted = _load_json(args.input)
        result = repair(
            specification,
            submitted,
            tolerance=args.tolerance,
            max_iterations=args.max_iterations,
        )
        proof = build_proof(specification, result, private_key_path=args.private_key)
        _write_json(args.proof, proof)
        if args.report:
            report_path = Path(args.report)
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(render_markdown(proof), encoding="utf-8")
        print(
            f"{result.status.upper()} movement_l2={result.movement_l2:.12g} "
            f"max_violation_after={result.max_violation_after:.3e} proof={args.proof}"
        )
        return 0
    except (EQProofError, FileExistsError, OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(f"eq-proof: error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
