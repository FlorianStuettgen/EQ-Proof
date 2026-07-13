# ADR 0001: Use Dykstra projection for the 1.x repair objective

- Status: Accepted
- Date: 2026-07-13

## Context

EQ-Proof must define “minimal change” precisely and compute it using inspectable primitives. The supported constraints are intersections of boxes, hyperplanes, half-spaces, and fixed coordinates.

## Decision

Use Dykstra's algorithm with closed-form projectors. Define the objective as minimum Euclidean distance from the submitted vector.

## Consequences

- The numerical contract is explicit and replayable.
- Fixed coordinates can be eliminated exactly.
- Dense complexity is acceptable for the intended prototype scale.
- The engine does not support integer, nonlinear, or non-convex constraints.
- A future weighted norm requires a new algorithm identifier and compatibility decision.
