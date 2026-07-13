"""EQ-Proof public API."""

from .core import EQProofError, InfeasibleProblem, InvalidProof, InvalidSpecification, RepairResult, Specification, load_specification, parse_specification, repair
from .proof import build_proof, generate_keypair, verify_proof

__all__ = [
    "EQProofError", "InfeasibleProblem", "InvalidProof", "InvalidSpecification",
    "RepairResult", "Specification", "build_proof", "generate_keypair",
    "load_specification", "parse_specification", "repair", "verify_proof",
]

__version__ = "1.0.0"
