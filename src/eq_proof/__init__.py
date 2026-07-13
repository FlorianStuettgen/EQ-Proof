"""EQ-Proof public API."""

from .api import prove_document, repair_document, verify_document
from .compiler import compile_equation
from .domain import (
    ConstraintCheck,
    LinearConstraint,
    RepairResult,
    Specification,
    VariableRule,
    VerificationResult,
)
from .errors import EQProofError, InfeasibleProblem, InvalidProof, InvalidSpecification
from .proof import build_proof, generate_keypair, render_markdown, verify_proof
from .solver import repair
from .specification import load_specification, parse_specification

__version__ = "1.1.0"

__all__ = [
    "ConstraintCheck",
    "EQProofError",
    "InfeasibleProblem",
    "InvalidProof",
    "InvalidSpecification",
    "LinearConstraint",
    "RepairResult",
    "Specification",
    "VariableRule",
    "VerificationResult",
    "build_proof",
    "compile_equation",
    "generate_keypair",
    "load_specification",
    "parse_specification",
    "prove_document",
    "render_markdown",
    "repair",
    "repair_document",
    "verify_document",
    "verify_proof",
]
