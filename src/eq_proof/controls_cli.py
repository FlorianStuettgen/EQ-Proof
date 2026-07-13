"""Command-line interface for the project-controls equation workbench."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .controls import CATALOGUE, ControlsError, analyze, load_csv, load_equations, parse_xer, write_outputs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="eq-controls",
        description="Run tested and user-supplied project-controls equations against P6 and cost exports.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    catalogue = subparsers.add_parser("catalogue", help="List the tested equation catalogue")
    catalogue.add_argument("--json", action="store_true", dest="as_json")

    run = subparsers.add_parser("analyze", help="Analyze P6 XER and/or cost CSV exports")
    run.add_argument("--p6-xer", action="append", default=[], help="Primavera P6 XER export")
    run.add_argument("--cost-csv", action="append", default=[], help="Cost/control-account CSV export")
    run.add_argument("--equations", action="append", default=[], help="Additional user equation pack JSON")
    run.add_argument("--output", required=True, help="Output directory")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "catalogue":
            payload = [equation.__dict__ for equation in CATALOGUE]
            if args.as_json:
                print(json.dumps(payload, indent=2, sort_keys=True))
            else:
                for equation in CATALOGUE:
                    print(
                        f"{equation.id:28} {equation.severity:7} "
                        f"{equation.record_type:15} {equation.expression}"
                    )
            return 0

        records = []
        sources = []
        for source in args.p6_xer:
            records.extend(parse_xer(source))
            sources.append(str(Path(source)))
        for source in args.cost_csv:
            records.extend(load_csv(source))
            sources.append(str(Path(source)))
        if not records:
            raise ControlsError("Supply at least one --p6-xer or --cost-csv input")

        equations = list(CATALOGUE)
        for pack in args.equations:
            equations.extend(load_equations(pack))
        result = analyze(records, equations=equations, sources=sources)
        write_outputs(result, args.output)
        print(
            f"{'CLOSE_READY' if result.close_ready else 'CLOSE_BLOCKED'} "
            f"records={result.records_analyzed} executed={result.equations_executed} "
            f"blockers={len(result.blockers)} failures={len(result.failures)} "
            f"output={args.output}"
        )
        return 0 if result.close_ready else 3
    except (ControlsError, OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        print(f"eq-controls: error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
