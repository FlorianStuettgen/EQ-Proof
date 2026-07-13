import base64
import copy
import json
import os
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from eq_proof import InvalidProof, parse_specification, repair
from eq_proof.canonical import canonical_json_bytes, sha256_hex
from eq_proof.proof import build_proof, generate_keypair, render_markdown, verify_proof


def sample():
    spec = parse_specification(
        {
            "schema_version": "1.0",
            "name": "signed-sample",
            "variables": {"x": {"lower": 0}, "y": {"lower": 0}},
            "equations": [{"id": "total", "expression": "x + y == 1"}],
        }
    )
    return spec, repair(spec, {"x": 0.8, "y": 0.5})


def test_signed_proof_verifies_integrity_signature_and_semantics(tmp_path):
    private_key = tmp_path / "private.pem"
    public_key = tmp_path / "public.pem"
    generate_keypair(private_key, public_key)
    spec, result = sample()
    proof = build_proof(spec, result, private_key_path=private_key, created_utc="2026-01-01T00:00:00Z")
    verification = verify_proof(proof, public_key)
    assert verification.verified
    assert verification.integrity_verified
    assert verification.signature_verified is True
    assert verification.semantics_verified
    assert verification.signer_fingerprint


def test_digest_only_proof_verifies_semantics_without_identity_claim():
    spec, result = sample()
    proof = build_proof(spec, result, created_utc="2026-01-01T00:00:00Z")
    verification = verify_proof(proof)
    assert verification.verified
    assert verification.signature_verified is None
    assert verification.signer_fingerprint is None


def test_integrity_only_mode_is_explicit():
    spec, result = sample()
    proof = build_proof(spec, result)
    verification = verify_proof(proof, semantic_replay=False)
    assert verification.verified
    assert verification.semantics_verified is None
    assert not verification.fully_verified


def test_tampering_breaks_digest_before_semantic_replay():
    spec, result = sample()
    proof = build_proof(spec, result)
    tampered = copy.deepcopy(proof)
    tampered["result"]["values"]["x"] = 0.123
    with pytest.raises(InvalidProof, match="digest"):
        verify_proof(tampered)


def test_semantic_replay_rejects_self_consistent_but_false_digest_only_proof():
    spec, result = sample()
    proof = build_proof(spec, result)
    proof["result"]["values"]["x"] = 0.4
    core = {key: value for key, value in proof.items() if key != "attestation"}
    proof["attestation"]["payload_sha256"] = sha256_hex(core)
    with pytest.raises(InvalidProof, match="Semantic replay"):
        verify_proof(proof)


def test_semantic_replay_rejects_signed_false_result_even_with_valid_signature(tmp_path):
    private_path = tmp_path / "private.pem"
    public_path = tmp_path / "public.pem"
    generate_keypair(private_path, public_path)
    spec, result = sample()
    proof = build_proof(spec, result, private_key_path=private_path)
    proof["result"]["values"]["x"] = 0.4
    core = {key: value for key, value in proof.items() if key != "attestation"}
    private_key = serialization.load_pem_private_key(private_path.read_bytes(), password=None)
    assert isinstance(private_key, Ed25519PrivateKey)
    proof["attestation"]["payload_sha256"] = sha256_hex(core)
    proof["attestation"]["signature_base64"] = base64.b64encode(
        private_key.sign(canonical_json_bytes(core))
    ).decode("ascii")
    with pytest.raises(InvalidProof, match="Semantic replay"):
        verify_proof(proof, public_path)


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


def test_digest_only_rejects_external_public_key(tmp_path):
    private_key = tmp_path / "private.pem"
    public_key = tmp_path / "public.pem"
    generate_keypair(private_key, public_key)
    spec, result = sample()
    proof = build_proof(spec, result)
    with pytest.raises(InvalidProof, match="digest-only"):
        verify_proof(proof, public_key)


def test_keygen_refuses_overwrite_and_sets_private_permissions(tmp_path):
    private_key = tmp_path / "private.pem"
    public_key = tmp_path / "public.pem"
    generate_keypair(private_key, public_key)
    with pytest.raises(FileExistsError):
        generate_keypair(private_key, public_key)
    if os.name == "posix":
        assert private_key.stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize(
    "proof, message",
    [
        ({}, "proof_schema"),
        ({"proof_schema": "eq-proof/proof@1"}, "attestation"),
        (
            {
                "proof_schema": "eq-proof/proof@1",
                "attestation": {"payload_sha256": "x", "mode": "other"},
            },
            "digest",
        ),
    ],
)
def test_malformed_proofs_are_rejected(proof, message):
    with pytest.raises(InvalidProof, match=message):
        verify_proof(proof)


def test_rendered_report_identifies_semantic_verification_boundary():
    spec, result = sample()
    report = render_markdown(build_proof(spec, result))
    assert "Full verification" in report
    assert "Objective value" in report


def rehash(proof):
    core = {key: value for key, value in proof.items() if key != "attestation"}
    proof["attestation"]["payload_sha256"] = sha256_hex(core)
    return proof


@pytest.mark.parametrize(
    "mutator, message",
    [
        (lambda p: p["engine"].update({"algorithm": "other"}), "engine"),
        (lambda p: p["engine"].update({"tolerance": "bad"}), "finite number"),
        (lambda p: p["engine"].update({"max_iterations": 0}), "max_iterations"),
        (lambda p: p["specification"].update({"digest_sha256": "0" * 64}), "Specification digest"),
        (lambda p: p["specification"].update({"name": "wrong"}), "name mismatch"),
        (lambda p: p["submission"].update({"digest_sha256": "0" * 64}), "Submission digest"),
        (lambda p: p["result"].update({"status": "wrong"}), "result.status"),
        (lambda p: p["result"].update({"values": {"x": 0.5}}), "result variables"),
        (lambda p: p["diagnostics"].update({"before": []}), "diagnostics.before"),
        (lambda p: p["diagnostics"]["before"][0].update({"id": "wrong"}), "diagnostics.before"),
        (lambda p: p["diagnostics"]["before"][0].update({"satisfied": "yes"}), "diagnostics.before"),
        (lambda p: p["diagnostics"]["before"][0].update({"lhs": "bad"}), "finite number"),
    ],
)
def test_semantic_replay_rejects_self_consistent_false_claims(mutator, message):
    spec, result = sample()
    proof = build_proof(spec, result)
    mutator(proof)
    rehash(proof)
    with pytest.raises(InvalidProof, match=message):
        verify_proof(proof)


def test_malformed_signature_fingerprint_and_signature_are_rejected(tmp_path):
    private_key = tmp_path / "private.pem"
    public_key = tmp_path / "public.pem"
    generate_keypair(private_key, public_key)
    spec, result = sample()

    malformed = build_proof(spec, result, private_key_path=private_key)
    malformed["attestation"]["signature_base64"] = "***"
    with pytest.raises(InvalidProof, match="Malformed"):
        verify_proof(malformed, public_key)

    wrong_fingerprint = build_proof(spec, result, private_key_path=private_key)
    wrong_fingerprint["attestation"]["signer_fingerprint_sha256"] = "0" * 64
    with pytest.raises(InvalidProof, match="fingerprint"):
        verify_proof(wrong_fingerprint, public_key)

    wrong_signature = build_proof(spec, result, private_key_path=private_key)
    signature = base64.b64decode(wrong_signature["attestation"]["signature_base64"])
    wrong_signature["attestation"]["signature_base64"] = base64.b64encode(bytes([signature[0] ^ 1]) + signature[1:]).decode()
    with pytest.raises(InvalidProof, match="signature"):
        verify_proof(wrong_signature, public_key)


def test_invalid_key_files_and_load_proof_errors(tmp_path):
    from eq_proof.proof import load_proof

    bad_key = tmp_path / "bad.pem"
    bad_key.write_text("not a key")
    spec, result = sample()
    with pytest.raises(InvalidProof, match="private key"):
        build_proof(spec, result, private_key_path=bad_key)

    private_key = tmp_path / "private.pem"
    public_key = tmp_path / "public.pem"
    generate_keypair(private_key, public_key)
    with pytest.raises(InvalidProof, match="public key"):
        verify_proof(build_proof(spec, result, private_key_path=private_key), bad_key)

    bad_json = tmp_path / "bad.json"
    bad_json.write_text("{")
    with pytest.raises(InvalidProof, match="Unable to read"):
        load_proof(bad_json)
    array_json = tmp_path / "array.json"
    array_json.write_text("[]")
    with pytest.raises(InvalidProof, match="root"):
        load_proof(array_json)
