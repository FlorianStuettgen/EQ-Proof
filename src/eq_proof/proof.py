"""Proof construction, Ed25519 attestation, verification, and Markdown rendering."""

from __future__ import annotations

import base64
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from .core import (InvalidProof, ProofResult, RepairResult, Specification, canonical_json_bytes, sha256_hex, as_dict)

PROOF_SCHEMA = "eq-proof/proof@1"
ENGINE_VERSION = "1.0.0"


def generate_keypair(private_path: str | Path, public_path: str | Path, *, force: bool = False) -> None:
    private_file = Path(private_path)
    public_file = Path(public_path)
    if not force and (private_file.exists() or public_file.exists()):
        raise FileExistsError("Refusing to overwrite an existing key; pass force=True to replace it")
    private_file.parent.mkdir(parents=True, exist_ok=True)
    public_file.parent.mkdir(parents=True, exist_ok=True)
    private_key = Ed25519PrivateKey.generate()
    private_file.write_bytes(private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ))
    public_file.write_bytes(private_key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    ))


def _load_private_key(path: str | Path) -> Ed25519PrivateKey:
    key = serialization.load_pem_private_key(Path(path).read_bytes(), password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise TypeError("Private key is not Ed25519")
    return key


def _load_public_key(path: str | Path) -> Ed25519PublicKey:
    key = serialization.load_pem_public_key(Path(path).read_bytes())
    if not isinstance(key, Ed25519PublicKey):
        raise TypeError("Public key is not Ed25519")
    return key


def _raw_public_key(public_key: Ed25519PublicKey) -> bytes:
    return public_key.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)


def _fingerprint(public_key: Ed25519PublicKey) -> str:
    return sha256_hex({"ed25519_public_key": base64.b64encode(_raw_public_key(public_key)).decode("ascii")})


def build_proof(
    specification: Specification,
    result: RepairResult,
    *,
    private_key_path: str | Path | None = None,
    created_utc: str | None = None,
) -> dict[str, Any]:
    timestamp = created_utc or datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    core: dict[str, Any] = {
        "proof_schema": PROOF_SCHEMA,
        "created_utc": timestamp,
        "engine": {
            "name": "EQ-Proof",
            "version": ENGINE_VERSION,
            "algorithm": "Dykstra Euclidean projection",
            "tolerance": result.tolerance,
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
            "max_violation_before": result.max_violation_before,
            "max_violation_after": result.max_violation_after,
        },
        "diagnostics": {
            "before": [as_dict(item) for item in result.checks_before],
            "after": [as_dict(item) for item in result.checks_after],
        },
    }
    payload_digest = sha256_hex(core)
    proof: dict[str, Any] = dict(core)

    if private_key_path is None:
        proof["attestation"] = {
            "mode": "digest-only",
            "payload_sha256": payload_digest,
            "warning": "Integrity digest only; no signer identity is asserted.",
        }
        return proof

    private_key = _load_private_key(private_key_path)
    public_key = private_key.public_key()
    signature = private_key.sign(canonical_json_bytes(core))
    proof["attestation"] = {
        "mode": "Ed25519",
        "payload_sha256": payload_digest,
        "signature_base64": base64.b64encode(signature).decode("ascii"),
        "public_key_base64": base64.b64encode(_raw_public_key(public_key)).decode("ascii"),
        "signer_fingerprint_sha256": _fingerprint(public_key),
        "trust_note": "Verification proves possession of this key. Identity requires an independently trusted fingerprint.",
    }
    return proof


def verify_proof(proof: dict[str, Any], public_key_path: str | Path | None = None) -> ProofResult:
    if not isinstance(proof, dict) or proof.get("proof_schema") != PROOF_SCHEMA:
        raise InvalidProof("Unsupported or missing proof_schema")
    attestation = proof.get("attestation")
    if not isinstance(attestation, dict):
        raise InvalidProof("Missing attestation object")
    core = {key: value for key, value in proof.items() if key != "attestation"}
    expected_digest = sha256_hex(core)
    if attestation.get("payload_sha256") != expected_digest:
        raise InvalidProof("Payload digest mismatch")

    mode = attestation.get("mode")
    if mode == "digest-only":
        return ProofResult(proof, True, None)
    if mode != "Ed25519":
        raise InvalidProof(f"Unsupported attestation mode: {mode!r}")

    try:
        embedded_raw = base64.b64decode(attestation["public_key_base64"], validate=True)
        signature = base64.b64decode(attestation["signature_base64"], validate=True)
        embedded_key = Ed25519PublicKey.from_public_bytes(embedded_raw)
    except (KeyError, TypeError, ValueError) as exc:
        raise InvalidProof("Malformed Ed25519 attestation") from exc

    verification_key = _load_public_key(public_key_path) if public_key_path else embedded_key
    if public_key_path and _raw_public_key(verification_key) != embedded_raw:
        raise InvalidProof("Embedded public key does not match the trusted public key")
    fingerprint = _fingerprint(verification_key)
    if attestation.get("signer_fingerprint_sha256") != fingerprint:
        raise InvalidProof("Signer fingerprint mismatch")
    try:
        verification_key.verify(signature, canonical_json_bytes(core))
    except InvalidSignature as exc:
        raise InvalidProof("Ed25519 signature verification failed") from exc
    return ProofResult(proof, True, fingerprint)

def _number(value: float) -> str:
    return f"{value:.12g}"


def render_markdown(proof: dict[str, Any]) -> str:
    result = proof["result"]
    submission = proof["submission"]["values"]
    repaired = result["values"]
    rows = []
    for name in submission:
        before = float(submission[name])
        after = float(repaired[name])
        rows.append(f"| `{name}` | {_number(before)} | {_number(after)} | {_number(after - before)} |")

    failed_before = [item for item in proof["diagnostics"]["before"] if not item["satisfied"]]
    checks = "\n".join(
        f"- `{item['id']}`: violation `{_number(float(item['violation']))}` — `{item['source']}`"
        for item in failed_before
    ) or "- None"

    attestation = proof["attestation"]
    signer = attestation.get("signer_fingerprint_sha256", "not signed")
    return f"""# EQ-Proof Repair Report

## Decision record

| Field | Value |
| --- | --- |
| Specification | `{proof['specification']['name']}` |
| Status | `{result['status']}` |
| Euclidean movement | `{_number(float(result['movement_l2']))}` |
| Maximum violation before | `{_number(float(result['max_violation_before']))}` |
| Maximum violation after | `{_number(float(result['max_violation_after']))}` |
| Algorithm | `{proof['engine']['algorithm']}` |
| Iterations | `{proof['engine']['iterations']}` |
| Attestation | `{attestation['mode']}` |
| Signer fingerprint | `{signer}` |

## Values

| Variable | Submitted | Repaired | Delta |
| --- | ---: | ---: | ---: |
{chr(10).join(rows)}

## Violations detected before repair

{checks}

## Verification boundary

This report is a convenience view. The JSON proof is authoritative. Verification establishes artifact integrity and, for Ed25519 mode, possession of the corresponding private key. It does not establish that the business rules are correct or that the key belongs to a particular organization unless the fingerprint is trusted independently.
"""
