# Core concepts

## Feasibility

A submitted vector is feasible when it satisfies every declared bound and linear equation within the configured tolerance.

## Repair

A repair is not an arbitrary correction. EQ-Proof computes the Euclidean projection of the submitted vector onto the supported feasible set.

## Fixed values

`"fixed": true` preserves the submitted value exactly. Fixed coordinates are removed from solver space rather than constrained approximately.

## Diagnostics

Every bound and equation produces a before/after record containing the left side, right side, relation, violation magnitude, and satisfaction flag.

## Proof

A proof preserves the rules, input, output, diagnostics, engine parameters, digest, and optional signature.

## Semantic replay

The verifier distrusts the result inside the proof. It reruns the encoded problem and compares the claims. This is stronger than signature verification alone.
