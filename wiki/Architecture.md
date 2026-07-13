# Architecture

The implementation is split into explicit layers:

- compiler;
- specification validation;
- diagnostics;
- projection solver;
- proof/attestation/replay;
- high-level API;
- CLI.

Key invariants are: no code execution, exact fixed values, deterministic repair, no proof before feasibility, and independent replay.

See `docs/ARCHITECTURE.md` and `docs/adr/` for the detailed design record.
