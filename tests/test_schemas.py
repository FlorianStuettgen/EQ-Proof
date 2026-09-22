import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

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


def _period_comparison_contract():
    schema = json.loads((ROOT / "schemas/period-comparison.schema.json").read_text())
    fixture = json.loads((ROOT / "examples/period-comparison/valid.json").read_text())
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema), fixture


def test_period_comparison_fixture_validates_and_closes_its_movement_bridge():
    validator, fixture = _period_comparison_contract()
    validator.validate(fixture)

    movement = fixture["portfolio_movement"]
    classified = sum(
        movement[field]
        for field in (
            "reconciled_movement",
            "governance_movement",
            "source_structure_movement",
            "unreconciled_movement",
            "not_comparable_movement",
            "bridge_residual",
        )
    )
    assert movement["reported_eac_delta"] == classified
    assert fixture["comparison_gate"]["bridge_closed"] is True
    assert fixture["comparison_gate"]["unresolved_count"] == len(
        fixture["unreconciled_movements"]
    )


def test_period_comparison_contract_rejects_silent_fuzzy_identity_matching():
    validator, fixture = _period_comparison_contract()
    invalid = copy.deepcopy(fixture)
    invalid["identity_map"][0]["match_method"] = "fuzzy"

    with pytest.raises(ValidationError):
        validator.validate(invalid)


def test_period_comparison_contract_rejects_missing_governance_evidence():
    validator, fixture = _period_comparison_contract()
    invalid = copy.deepcopy(fixture)
    invalid.pop("equation_manifests")

    with pytest.raises(ValidationError):
        validator.validate(invalid)
