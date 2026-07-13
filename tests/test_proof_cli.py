# ---- test_attestation.py ----
import copy
import json
from pathlib import Path

import pytest

from eq_proof.proof import build_proof, generate_keypair, verify_proof
from eq_proof.core import repair
from eq_proof.core import InvalidProof
from eq_proof.core import parse_specification


def sample():
    spec = parse_specification({
        "schema_version": "1.0",
        "name": "signed-sample",
        "variables": {"x": {"lower": 0}, "y": {"lower": 0}},
        "equations": [{"id": "total", "expression": "x + y == 1"}],
    })
    return spec, repair(spec, {"x": 0.8, "y": 0.5})


def test_signed_proof_verifies_with_embedded_and_external_key(tmp_path):
    private_key = tmp_path / "private.pem"
    public_key = tmp_path / "public.pem"
    generate_keypair(private_key, public_key)
    spec, result = sample()
    proof = build_proof(spec, result, private_key_path=private_key, created_utc="2026-01-01T00:00:00Z")
    assert verify_proof(proof).verified
    assert verify_proof(proof, public_key).verified


def test_tampering_breaks_digest_before_signature_check(tmp_path):
    private_key = tmp_path / "private.pem"
    public_key = tmp_path / "public.pem"
    generate_keypair(private_key, public_key)
    spec, result = sample()
    proof = build_proof(spec, result, private_key_path=private_key)
    tampered = copy.deepcopy(proof)
    tampered["result"]["values"]["x"] = 0.123
    with pytest.raises(InvalidProof, match="digest"):
        verify_proof(tampered, public_key)


def test_checked_in_evidence_proof_verifies():
    root = Path(__file__).resolve().parents[1]
    proof = json.loads((root / "evidence" / "portfolio-allocation.proof.json").read_text())
    public_key = root / "evidence" / "demo-public-key.pem"
    assert verify_proof(proof, public_key).verified


def test_digest_only_proof_verifies_without_identity_claim():
    spec, result = sample()
    proof = build_proof(spec, result, created_utc="2026-01-01T00:00:00Z")
    verification = verify_proof(proof)
    assert verification.verified
    assert verification.signer_fingerprint is None


def test_keygen_refuses_overwrite(tmp_path):
    private_key = tmp_path / "private.pem"
    public_key = tmp_path / "public.pem"
    generate_keypair(private_key, public_key)
    with pytest.raises(FileExistsError):
        generate_keypair(private_key, public_key)


def test_external_wrong_key_is_rejected(tmp_path):
    private_key = tmp_path / "private.pem"
    public_key = tmp_path / "public.pem"
    wrong_private = tmp_path / "wrong-private.pem"
    wrong_public = tmp_path / "wrong-public.pem"
    generate_keypair(private_key, public_key)
    generate_keypair(wrong_private, wrong_public)
    spec, result = sample()
    proof = build_proof(spec, result, private_key_path=private_key)
    with pytest.raises(InvalidProof, match="does not match"):
        verify_proof(proof, wrong_public)


@pytest.mark.parametrize(
    "proof, message",
    [
        ({}, "proof_schema"),
        ({"proof_schema": "eq-proof/proof@1"}, "attestation"),
        ({"proof_schema": "eq-proof/proof@1", "attestation": {"payload_sha256": "x", "mode": "other"}}, "digest"),
    ],
)
def test_malformed_proofs_are_rejected(proof, message):
    with pytest.raises(InvalidProof, match=message):
        verify_proof(proof)


from eq_proof.cli import main

ROOT = Path(__file__).resolve().parents[1]


def test_cli_repair_and_verify_round_trip(tmp_path):
    private_key = tmp_path / "private.pem"
    public_key = tmp_path / "public.pem"
    proof = tmp_path / "proof.json"
    report = tmp_path / "proof.md"

    assert main(["keygen", "--private-key", str(private_key), "--public-key", str(public_key)]) == 0
    assert main([
        "repair",
        "--spec", str(ROOT / "examples/portfolio_allocation/spec.json"),
        "--input", str(ROOT / "examples/portfolio_allocation/input.json"),
        "--proof", str(proof),
        "--report", str(report),
        "--private-key", str(private_key),
    ]) == 0
    assert main(["verify", str(proof), "--public-key", str(public_key)]) == 0
    assert json.loads(proof.read_text())["result"]["status"] == "repaired"
    assert "Euclidean movement" in report.read_text()
