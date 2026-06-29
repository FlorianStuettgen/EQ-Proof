#!/usr/bin/env python3
import argparse
import json
import os

from eq_proof import load_spec
from eq_proof.attest import attest
from eq_proof.compiler import spec_to_dict
from eq_proof.diagnose import diagnose_and_repair
from eq_proof.report import render_markdown, report_lines


def main():
    parser = argparse.ArgumentParser(description="EQ-PROOF: validate/repair numeric outputs offline.")
    parser.add_argument("spec")
    parser.add_argument("inputs")
    parser.add_argument("--out", default="outputs/proof.json")
    parser.add_argument("--md", default="outputs/proof.md")
    parser.add_argument("--pdf", default=None)
    args = parser.parse_args()

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    os.makedirs(os.path.dirname(args.md) or ".", exist_ok=True)

    spec = load_spec(args.spec)
    with open(args.inputs, "r", encoding="utf-8") as f:
        values = json.load(f)

    result = diagnose_and_repair(spec, values, spec_path=args.spec, inputs_path=args.inputs)
    attestation = attest(spec_to_dict(spec), result, spec_path=args.spec, inputs_path=args.inputs)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(attestation, f, indent=2)
    with open(args.md, "w", encoding="utf-8") as f:
        f.write(render_markdown(args.spec, args.inputs, result, attestation))

    if args.pdf:
        try:
            from eq_proof.pdf import save_text_pdf

            save_text_pdf(report_lines(args.spec, args.inputs, result, attestation), args.pdf)
        except Exception as exc:
            print(f"[WARN] PDF not created: {exc}")

    print(f"[OK] -> {args.out} | {args.md}" + (f" | {args.pdf}" if args.pdf else ""))


if __name__ == "__main__":
    main()
