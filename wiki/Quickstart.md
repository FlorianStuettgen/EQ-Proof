# Quickstart

## Try the Control Room in your browser

[Open EQ-Proof](https://florianstuettgen.github.io/EQ-Proof/) and select **Try three examples**. Run the submitted, reconciled and ready cases to inspect their computed gates. No account or installation is required; the supplied data is synthetic.

The hosted application processes selected files in the browser. It is session-only by default. See [Runtime Modes and Data Handling](https://github.com/FlorianStuettgen/EQ-Proof/blob/main/docs/RUNTIME_MODES.md) for the storage and execution boundaries.

## Run the Python application

Python 3.10–3.13 are covered by CI. Clone the repository and create an environment:

```bash
git clone https://github.com/FlorianStuettgen/EQ-Proof.git
cd EQ-Proof
python -m venv .venv
```

Activate with `source .venv/bin/activate` on macOS/Linux, or `.venv\Scripts\Activate.ps1` in PowerShell. Then:

```bash
python -m pip install -e '.[web]'
eq-controls serve
```

Open `http://127.0.0.1:8765`. The local application runs the Python engine on loopback.

## Reproduce a close check from the terminal

```bash
eq-controls analyze --p6-xer examples/close_walkthrough/blocked/schedule.xer --cost-csv examples/close_walkthrough/blocked/cost.csv --equations examples/close_walkthrough/blocked/custom_equations.json --currency USD --fail-on blocker --output outputs/blocked
```

**Exit code 3 is expected:** the synthetic submitted close contains three blockers and five failures. The command writes `analysis.json`, `control-room.json`, `exceptions.csv` and `report.md`.

Replace `blocked` with `review` or `ready` to run the other cases. Both return 0 with `--fail-on blocker`; the review case still has two schedule findings. Use `--fail-on minor` when automation should fail on those findings too.

`CLOSE READY` means no selected, applicable control failed. It does not establish data completeness or management approval. The [fixture guide](https://github.com/FlorianStuettgen/EQ-Proof/blob/main/examples/close_walkthrough/README.md) documents every input change.

## Optional numerical proof engine

The separate `eq-proof` command handles numerical repair, signing and semantic replay. It is not required for the Control Room workflow above. See [Architecture](https://github.com/FlorianStuettgen/EQ-Proof/blob/main/docs/ARCHITECTURE.md) and [Proof and Verification](Proof-and-Verification) for that engine and its trust boundary.
