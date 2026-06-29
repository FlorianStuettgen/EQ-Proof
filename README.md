# EQ-PROOF

EQ-PROOF turns written numeric constraints into an offline repair-and-attestation workflow.

The finished workflow is in [notebooks/EQ_Proof.ipynb](notebooks/EQ_Proof.ipynb):

1. Write constraints such as `0 <= p1 <= 1`, `p1 + p2 + p3 = 1`, or `fixed(cap)`.
2. Compile those constraints into an EQ-PROOF spec.
3. Project numeric outputs onto the feasible set with minimal Euclidean change.
4. Produce a signed proof artifact entirely offline.
5. Verify that proof offline.

## Install

```bash
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e .[dev]
```

## Notebook

Open `notebooks/EQ_Proof.ipynb` in Jupyter, VS Code, or another notebook UI and run top to bottom. It creates an example written spec, repairs an infeasible output vector, signs the result, verifies the signature, and writes proof artifacts under `outputs/`.

## CLI

```bash
.venv\Scripts\python.exe cli.py examples\spec_budget_cap.json examples\inputs_budget_bad.json --out outputs\proof_budget.json --md outputs\proof_budget.md
.venv\Scripts\python.exe verify_cli.py outputs\proof_budget.json
```

## Constraint Types

- `bounds`: lower/upper limits on a variable.
- `linear_eq` and `linear_leq`: compiled linear relations.
- `equality`: SymPy equality fallback for symbolic or nonlinear expressions.
- `sum_leq`: sum of variables is no larger than a cap.
- `simplex`: variables are nonnegative and sum to one.
- `monotone`: variables are nondecreasing.
- `fixed`: top-level list of variables treated as constants during projection.

## Attestation

Proofs are signed locally. If `keys/ed25519_sk.hex` exists and PyNaCl is installed, EQ-PROOF uses Ed25519. Otherwise it uses an HMAC-SHA256 fallback with `EQPROOF_KEY`, `keys/attest_key.txt`, or the demo key.

Real keys are ignored by git. Do not commit production keys.
