"""EQ-Proof public API."""

from .api import prove_document, repair_document, verify_document
from .compiler import compile_equation
from .control_room import build_control_room
from .controls import Analysis, ControlsError, Equation, Finding, analyze, parse_xer
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

__version__ = "1.3.0"

__all__ = [
    "Analysis",
    "ConstraintCheck",
    "ControlsError",
    "EQProofError",
    "Equation",
    "Finding",
    "InfeasibleProblem",
    "InvalidProof",
    "InvalidSpecification",
    "LinearConstraint",
    "RepairResult",
    "Specification",
    "VariableRule",
    "VerificationResult",
    "analyze",
    "build_control_room",
    "build_proof",
    "compile_equation",
    "generate_keypair",
    "load_specification",
    "parse_specification",
    "parse_xer",
    "prove_document",
    "render_markdown",
    "repair",
    "repair_document",
    "verify_document",
    "verify_proof",
]
