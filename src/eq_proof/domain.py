"""Immutable domain models used across the EQ-Proof engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

Relation = Literal["==", "<="]


@dataclass(frozen=True)
class VariableRule:
    name: str
    lower: float | None = None
    upper: float | None = None
    fixed: bool = False
    label: str | None = None
    unit: str | None = None


@dataclass(frozen=True)
class LinearConstraint:
    identifier: str
    coefficients: tuple[float, ...]
    relation: Relation
    rhs: float
    source: str
    description: str = ""


@dataclass(frozen=True)
class Specification:
    schema_version: str
    name: str
    description: str
    variables: tuple[VariableRule, ...]
    constraints: tuple[LinearConstraint, ...]
    source_document: dict[str, Any]

    @property
    def variable_names(self) -> tuple[str, ...]:
        return tuple(variable.name for variable in self.variables)


@dataclass(frozen=True)
class ConstraintCheck:
    identifier: str
    source: str
    relation: str
    lhs: float
    rhs: float
    violation: float
    satisfied: bool


@dataclass(frozen=True)
class RepairResult:
    status: Literal["already_feasible", "repaired"]
    submitted: dict[str, float]
    repaired: dict[str, float]
    movement_l2: float
    objective_value: float
    iterations: int
    tolerance: float
    max_iterations: int
    max_violation_before: float
    max_violation_after: float
    checks_before: tuple[ConstraintCheck, ...] = field(default_factory=tuple)
    checks_after: tuple[ConstraintCheck, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class VerificationResult:
    proof: dict[str, Any]
    integrity_verified: bool
    semantics_verified: bool | None
    signature_verified: bool | None
    signer_fingerprint: str | None

    @property
    def verified(self) -> bool:
        """Return true when every verification layer that was performed passed."""
        return (
            self.integrity_verified
            and self.semantics_verified is not False
            and self.signature_verified is not False
        )

    @property
    def fully_verified(self) -> bool:
        """Return true only when integrity and semantic replay passed."""
        return self.verified and self.semantics_verified is True
