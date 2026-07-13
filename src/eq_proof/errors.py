"""Domain exceptions exposed by EQ-Proof."""


class EQProofError(Exception):
    """Base class for expected EQ-Proof failures."""


class InvalidSpecification(EQProofError):
    """The specification is malformed, unsafe, or unsupported."""


class InfeasibleProblem(EQProofError):
    """A feasible repair could not be established."""


class InvalidProof(EQProofError):
    """The proof artifact is malformed or fails verification."""
