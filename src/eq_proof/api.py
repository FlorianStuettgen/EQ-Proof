"""High-level Python API for embedding EQ-Proof."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from .domain import RepairResult, Specification, VerificationResult
from .proof import build_proof, verify_proof
from .solver import DEFAULT_MAX_ITERATIONS, DEFAULT_TOLERANCE, repair
from .specification import parse_specification


def repair_document(
    specification_document: dict[str, Any],
    values: Mapping[str, object],
    *,
    tolerance: float = DEFAULT_TOLERANCE,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
) -> RepairResult:
    """Parse a specification document and minimally repair submitted values."""
    specification = parse_specification(specification_document)
    return repair(
        specification,
        values,
        tolerance=tolerance,
        max_iterations=max_iterations,
    )


def prove_document(
    specification_document: dict[str, Any],
    values: Mapping[str, object],
    *,
    private_key_path: str | Path | None = None,
    created_utc: str | None = None,
    tolerance: float = DEFAULT_TOLERANCE,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
) -> dict[str, Any]:
    """Repair submitted values and return an authoritative proof artifact."""
    specification: Specification = parse_specification(specification_document)
    result = repair(
        specification,
        values,
        tolerance=tolerance,
        max_iterations=max_iterations,
    )
    return build_proof(
        specification,
        result,
        private_key_path=private_key_path,
        created_utc=created_utc,
    )


def verify_document(
    proof_document: dict[str, Any],
    *,
    public_key_path: str | Path | None = None,
    semantic_replay: bool = True,
) -> VerificationResult:
    """Verify integrity, optional signature, and encoded solution semantics."""
    return verify_proof(
        proof_document,
        public_key_path,
        semantic_replay=semantic_replay,
    )
