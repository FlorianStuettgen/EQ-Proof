"""Proof construction, semantic replay, verification, and reporting."""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .attestation import attest_core, generate_keypair, verify_attestation
from .canonical import sha256_hex
from .diagnostics import check_to_dict
from .domain import RepairResult, Specification, VerificationResult
from .errors import InvalidProof
from .solver import repair
from .specification import parse_specification

PROOF_SCHEMA = "eq-proof/proof@1"
ENGINE_NAME = "EQ-Proof"
ENGINE_VERSION = "1.1.0"
ALGORITHM_ID = "dykstra-l2-v1"


def build_proof(
    specification: Specification,
    result: RepairResult,
    *,
    private_key_path: str | Path | None = None,
    created_utc: str | None = None,
) -> dict[str, Any]:
    timestamp = created_utc or (
        datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    )
    core: dict[str, Any] = {
        "proof_schema": PROOF_SCHEMA,
        "created_utc": timestamp,
        "engine": {
            "name": ENGINE_NAME,
            "version": ENGINE_VERSION,
            "algorithm": ALGORITHM_ID,
            "tolerance": result.tolerance,
            "max_iterations": result.max_iterations,
            "iterations": result.iterations,
        },
        "specification": {
            "name": specification.name,
            "schema_version": specification.schema_version,
            "digest_sha256": sha256_hex(specification.source_document),
            "document": specification.source_document,
        },
        "submission": {
            "digest_sha256": sha256_hex(result.submitted),
            "values": result.submitted,
        },
        "result": {
            "status": result.status,
            "values": result.repaired,
            "movement_l2": result.movement_l2,
            "objective_value": result.objective_value,
            "max_violation_before": result.max_violation_before,
            "max_violation_after": result.max_violation_after,
        },
        "diagnostics": {
            "before": [check_to_dict(item) for item in result.checks_before],
            "after": [check_to_dict(item) for item in result.checks_after],
        },
    }
    proof = dict(core)
    proof["attestation"] = attest_core(core, private_key_path)
    return proof


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise InvalidProof(f"{label} must be an object")
    return value


def _finite_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InvalidProof(f"{label} must be a finite number")
    number = float(value)
    if not math.isfinite(number):
        raise InvalidProof(f"{label} must be finite")
    return number


def _assert_close(actual: Any, expected: float, label: str, tolerance: float) -> None:
    number = _finite_number(actual, label)
    if not math.isclose(number, expected, rel_tol=1e-9, abs_tol=tolerance):
        raise InvalidProof(f"Semantic replay mismatch for {label}")


def _compare_diagnostics(
    claimed: Any,
    expected: tuple[Any, ...],
    label: str,
    tolerance: float,
) -> None:
    if not isinstance(claimed, list) or len(claimed) != len(expected):
        raise InvalidProof(f"Semantic replay mismatch for diagnostics.{label}")
    for index, (claimed_item, expected_item) in enumerate(zip(claimed, expected, strict=True)):
        item = _mapping(claimed_item, f"diagnostics.{label}[{index}]")
        if item.get("id") != expected_item.identifier or item.get("source") != expected_item.source:
            raise InvalidProof(f"Semantic replay mismatch for diagnostics.{label}[{index}]")
        if item.get("relation") != expected_item.relation or item.get("satisfied") is not expected_item.satisfied:
            raise InvalidProof(f"Semantic replay mismatch for diagnostics.{label}[{index}]")
        _assert_close(item.get("lhs"), expected_item.lhs, f"diagnostics.{label}[{index}].lhs", tolerance)
        _assert_close(item.get("rhs"), expected_item.rhs, f"diagnostics.{label}[{index}].rhs", tolerance)
        _assert_close(
            item.get("violation"), expected_item.violation,
            f"diagnostics.{label}[{index}].violation", tolerance,
        )


def _semantic_replay(proof: dict[str, Any]) -> None:
    engine = _mapping(proof.get("engine"), "engine")
    if engine.get("name") != ENGINE_NAME or engine.get("algorithm") != ALGORITHM_ID:
        raise InvalidProof("Unsupported proof engine or algorithm")
    tolerance = _finite_number(engine.get("tolerance"), "engine.tolerance")
    max_iterations = engine.get("max_iterations")
    if isinstance(max_iterations, bool) or not isinstance(max_iterations, int) or max_iterations < 1:
        raise InvalidProof("engine.max_iterations must be a positive integer")

    specification_section = _mapping(proof.get("specification"), "specification")
    specification_document = _mapping(specification_section.get("document"), "specification.document")
    if specification_section.get("digest_sha256") != sha256_hex(specification_document):
        raise InvalidProof("Specification digest mismatch")
    specification = parse_specification(specification_document)
    if specification_section.get("name") != specification.name:
        raise InvalidProof("Specification name mismatch")

    submission = _mapping(proof.get("submission"), "submission")
    submission_values = _mapping(submission.get("values"), "submission.values")
    if submission.get("digest_sha256") != sha256_hex(submission_values):
        raise InvalidProof("Submission digest mismatch")

    expected = repair(
        specification,
        submission_values,
        tolerance=tolerance,
        max_iterations=max_iterations,
    )
    result = _mapping(proof.get("result"), "result")
    if result.get("status") != expected.status:
        raise InvalidProof("Semantic replay mismatch for result.status")
    result_values = _mapping(result.get("values"), "result.values")
    if set(result_values) != set(expected.repaired):
        raise InvalidProof("Semantic replay mismatch for result variables")
    comparison_tolerance = max(tolerance * 100.0, 1e-9)
    for name, expected_value in expected.repaired.items():
        _assert_close(
            result_values.get(name), expected_value,
            f"result.values.{name}", comparison_tolerance,
        )
    for field in (
        "movement_l2", "objective_value", "max_violation_before", "max_violation_after"
    ):
        _assert_close(
            result.get(field), getattr(expected, field), f"result.{field}", comparison_tolerance
        )

    diagnostics = _mapping(proof.get("diagnostics"), "diagnostics")
    _compare_diagnostics(
        diagnostics.get("before"), expected.checks_before, "before", comparison_tolerance
    )
    _compare_diagnostics(
        diagnostics.get("after"), expected.checks_after, "after", comparison_tolerance
    )


def verify_proof(
    proof: dict[str, Any],
    public_key_path: str | Path | None = None,
    *,
    semantic_replay: bool = True,
) -> VerificationResult:
    if not isinstance(proof, dict) or proof.get("proof_schema") != PROOF_SCHEMA:
        raise InvalidProof("Unsupported or missing proof_schema")
    attestation = _mapping(proof.get("attestation"), "attestation")
    core = {key: value for key, value in proof.items() if key != "attestation"}
    signature_verified, fingerprint = verify_attestation(core, attestation, public_key_path)
    if semantic_replay:
        _semantic_replay(proof)
    return VerificationResult(
        proof=proof,
        integrity_verified=True,
        semantics_verified=True if semantic_replay else None,
        signature_verified=signature_verified,
        signer_fingerprint=fingerprint,
    )


def _number(value: float) -> str:
    return f"{value:.12g}"


def render_markdown(proof: dict[str, Any]) -> str:
    result = _mapping(proof.get("result"), "result")
    submission = _mapping(
        _mapping(proof.get("submission"), "submission").get("values"), "submission.values"
    )
    repaired = _mapping(result.get("values"), "result.values")
    rows = []
    for name in submission:
        before = float(submission[name])
        after = float(repaired[name])
        rows.append(f"| `{name}` | {_number(before)} | {_number(after)} | {_number(after - before)} |")

    diagnostics = _mapping(proof.get("diagnostics"), "diagnostics")
    before_checks = diagnostics.get("before")
    failed_before = (
        [item for item in before_checks if isinstance(item, dict) and not item.get("satisfied")]
        if isinstance(before_checks, list) else []
    )
    violations = "\n".join(
        f"- `{item['id']}`: violation `{_number(float(item['violation']))}` — `{item['source']}`"
        for item in failed_before
    ) or "- None"

    attestation = _mapping(proof.get("attestation"), "attestation")
    signer = attestation.get("signer_fingerprint_sha256", "not signed")
    engine = _mapping(proof.get("engine"), "engine")
    specification = _mapping(proof.get("specification"), "specification")
    return f"""# EQ-Proof Repair Report

## Decision record

| Field | Value |
| --- | --- |
| Specification | `{specification['name']}` |
| Status | `{result['status']}` |
| Euclidean movement | `{_number(float(result['movement_l2']))}` |
| Objective value | `{_number(float(result['objective_value']))}` |
| Maximum violation before | `{_number(float(result['max_violation_before']))}` |
| Maximum violation after | `{_number(float(result['max_violation_after']))}` |
| Algorithm | `{engine['algorithm']}` |
| Iterations | `{engine['iterations']}` |
| Attestation | `{attestation['mode']}` |
| Signer fingerprint | `{signer}` |

## Values

| Variable | Submitted | Repaired | Delta |
| --- | ---: | ---: | ---: |
{chr(10).join(rows)}

## Violations detected before repair

{violations}

## Verification boundary

The JSON proof is authoritative. Full verification checks payload integrity, optional Ed25519 authenticity, and semantic replay of the encoded specification and submission. It does not establish that the business rules are correct, that the source data is truthful, or that a signing key belongs to a claimed identity without an independently trusted fingerprint.
"""


def load_proof(path: str | Path) -> dict[str, Any]:
    try:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InvalidProof(f"Unable to read proof {path}: {exc}") from exc
    if not isinstance(document, dict):
        raise InvalidProof("Proof root must be a JSON object")
    return document
