"""Command-line interface for validation, repair, and offline verification."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Sequence

from . import __version__
from .diagnostics import checks, max_violation
from .errors import EQProofError
from .proof import build_proof, generate_keypair, load_proof, render_markdown, verify_proof
from .solver import DEFAULT_MAX_ITERATIONS, DEFAULT_TOLERANCE, input_vector, repair
from .specification import load_specification

EXIT_OK = 0
EXIT_ERROR = 2
EXIT_CONSTRAINT_VIOLATION = 3


def _load_json_object(path: str | Path) -> dict[str, Any]:
    try:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Unable to read JSON object {path}: {exc}") from exc
    if not isinstance(document, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return document


def _atomic_write(path: str | Path, content: str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, target)
    except Exception:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def _write_json(path: str | Path, value: object) -> None:
    _atomic_write(
        path,
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="eq-proof",
        description="Repair numeric outputs and emit independently verifiable proof artifacts",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser(
        "validate",
        help="Diagnose whether submitted values satisfy the specification",
    )
    validate_parser.add_argument("--spec", required=True)
    validate_parser.add_argument("--input", required=True)
    validate_parser.add_argument("--tolerance", type=float, default=DEFAULT_TOLERANCE)
    validate_parser.add_argument("--json", action="store_true", dest="as_json")

    repair_parser = subparsers.add_parser(
        "repair",
        help="Validate, minimally repair, and emit a proof",
    )
    repair_parser.add_argument("--spec", required=True)
    repair_parser.add_argument("--input", required=True)
    repair_parser.add_argument("--proof", required=True)
    repair_parser.add_argument("--report")
    repair_parser.add_argument("--private-key")
    repair_parser.add_argument("--tolerance", type=float, default=DEFAULT_TOLERANCE)
    repair_parser.add_argument("--max-iterations", type=int, default=DEFAULT_MAX_ITERATIONS)

    verify_parser = subparsers.add_parser(
        "verify",
        help="Verify proof integrity, signature, and semantic replay",
    )
    verify_parser.add_argument("proof")
    verify_parser.add_argument("--public-key")
    verify_parser.add_argument(
        "--integrity-only",
        action="store_true",
        help="Skip semantic replay; verify only digest and optional signature",
    )

    keygen_parser = subparsers.add_parser("keygen", help="Generate an Ed25519 keypair")
    keygen_parser.add_argument("--private-key", required=True)
    keygen_parser.add_argument("--public-key", required=True)
    keygen_parser.add_argument("--force", action="store_true")
    return parser


def _run_validate(args: argparse.Namespace) -> int:
    specification = load_specification(args.spec)
    submitted = _load_json_object(args.input)
    vector = input_vector(specification, submitted)
    diagnostics = checks(specification, vector, args.tolerance)
    maximum = max_violation(diagnostics)
    failed = [item for item in diagnostics if not item.satisfied]
    feasible = maximum <= args.tolerance
    if args.as_json:
        print(
            json.dumps(
                {
                    "feasible": feasible,
                    "max_violation": maximum,
                    "violations": [
                        {
                            "id": item.identifier,
                            "source": item.source,
                            "violation": item.violation,
                        }
                        for item in failed
                    ],
                },
                indent=2,
                sort_keys=True,
            )
        )
    else:
        label = "FEASIBLE" if feasible else "VIOLATION"
        print(f"{label} max_violation={maximum:.3e} failed_constraints={len(failed)}")
        for item in failed:
            print(f"- {item.identifier}: violation={item.violation:.12g} rule={item.source}")
    return EXIT_OK if feasible else EXIT_CONSTRAINT_VIOLATION


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "keygen":
            generate_keypair(args.private_key, args.public_key, force=args.force)
            print(f"GENERATED private={args.private_key} public={args.public_key}")
            return EXIT_OK
        if args.command == "validate":
            return _run_validate(args)
        if args.command == "verify":
            proof = load_proof(args.proof)
            verification = verify_proof(
                proof,
                args.public_key,
                semantic_replay=not args.integrity_only,
            )
            signature = (
                "pass" if verification.signature_verified else "none"
                if verification.signature_verified is None
                else "fail"
            )
            semantics = "pass" if verification.semantics_verified is True else "skipped"
            fingerprint = verification.signer_fingerprint or "none"
            print(
                "VERIFIED integrity=pass "
                f"signature={signature} semantics={semantics} fingerprint={fingerprint}"
            )
            return EXIT_OK

        specification = load_specification(args.spec)
        submitted = _load_json_object(args.input)
        result = repair(
            specification,
            submitted,
            tolerance=args.tolerance,
            max_iterations=args.max_iterations,
        )
        proof = build_proof(
            specification,
            result,
            private_key_path=args.private_key,
        )
        _write_json(args.proof, proof)
        if args.report:
            _atomic_write(args.report, render_markdown(proof))
        print(
            f"{result.status.upper()} movement_l2={result.movement_l2:.12g} "
            f"max_violation_after={result.max_violation_after:.3e} proof={args.proof}"
        )
        return EXIT_OK
    except (EQProofError, FileExistsError, OSError, ValueError, TypeError) as exc:
        print(f"eq-proof: error: {exc}", file=sys.stderr)
        return EXIT_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
