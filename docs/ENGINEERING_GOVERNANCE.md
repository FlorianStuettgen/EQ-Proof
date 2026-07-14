# Engineering Governance

## Default-branch policy

All substantive changes should reach `main` through a pull request. Direct pushes, force pushes, and branch deletion should be blocked by a repository ruleset.

Required status checks:

- `repository-proof`
- `ui-audit`
- `CodeQL`

For changes that affect the hosted application, the Pages bundle must validate during review and the production deployment must report `github-pages/live: success` after merge.

## Review ownership

`CODEOWNERS` assigns the repository to `@FlorianStuettgen`, with explicit ownership of:

- the Control Room web surface;
- GitHub Actions workflows;
- semantic and architecture contracts;
- deterministic evidence;
- the core Control Room and proof engines.

A repository ruleset should require code-owner review when contributors other than the owner are involved.

## Control Room UI freeze

The functional, responsive, and accessibility baseline established by PR #11 is frozen for the cross-period intelligence cycle.

The freeze does not prohibit functional development. It prohibits ungrounded redesign and cosmetic churn.

A change to the audited shell is justified only when at least one of the following is true:

1. a new product requirement cannot be expressed coherently through the existing interaction model;
2. a reproducible browser, accessibility, responsive, or usability defect is demonstrated;
3. a semantic distinction cannot be communicated accurately with the current components;
4. a security or operational boundary requires a change.

Any justified change must preserve or improve:

- keyboard navigation;
- focus management;
- mobile and narrow-screen behavior;
- reduced-motion behavior;
- empty and error states;
- export behavior;
- public-versus-local runtime honesty;
- automated browser and accessibility coverage.

## Semantic integrity

EQ-Proof must continue to distinguish:

- deterministic contradiction;
- declared change and configured risk;
- probabilistic analysis;
- source or governance change;
- inferred versus explicitly supplied causal relationships.

The product must not convert schedule findings into financial exposure without an explicit supplied equation, present an arithmetic risk bridge as a Monte Carlo percentile, or treat an uncalibrated assurance score as a probability.

## Evidence integrity

Changes affecting generated evidence must retain:

- source SHA-256 manifests;
- equation manifests;
- explicit applicability results;
- versioned schemas;
- canonical serialization;
- byte-stable deterministic regeneration;
- backward compatibility or an explicit migration path.

## Merge procedure

1. Open a focused pull request.
2. Complete the repository pull-request checklist.
3. Resolve review threads.
4. Require green repository-proof, UI audit when applicable, and CodeQL.
5. Squash-merge with a precise product-level commit message.
6. Verify deterministic evidence and the live Pages status after merge.
7. Record any remaining boundary or administrative action explicitly rather than implying it is complete.

## Next product cycle

Cross-period forecast intelligence is tracked in issue #12 and draft PR #13. The comparison engine and evidence contract should be implemented before extending the UI.
