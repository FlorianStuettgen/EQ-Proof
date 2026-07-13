import json
from pathlib import Path

from jsonschema import Draft202012Validator

from eq_proof import prove_document

ROOT = Path(__file__).resolve().parents[1]


def test_examples_and_generated_proof_validate_against_published_schemas():
    specification_schema = json.loads((ROOT / "schemas/specification.schema.json").read_text())
    proof_schema = json.loads((ROOT / "schemas/proof.schema.json").read_text())
    specification_validator = Draft202012Validator(specification_schema)
    proof_validator = Draft202012Validator(proof_schema)

    for spec_path in sorted((ROOT / "examples").glob("*/spec.json")):
        specification = json.loads(spec_path.read_text())
        specification_validator.validate(specification)
        values = json.loads((spec_path.parent / "input.json").read_text())
        proof = prove_document(specification, values, created_utc="2026-01-01T00:00:00Z")
        proof_validator.validate(proof)


def test_checked_in_evidence_validates_and_verifies():
    from eq_proof.proof import verify_proof

    proof_schema = json.loads((ROOT / "schemas/proof.schema.json").read_text())
    proof = json.loads((ROOT / "evidence/portfolio-allocation.proof.json").read_text())
    Draft202012Validator(proof_schema).validate(proof)
    verification = verify_proof(proof, ROOT / "evidence/demo-public-key.pem")
    assert verification.fully_verified
