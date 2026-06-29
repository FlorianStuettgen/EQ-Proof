#!/usr/bin/env python3
import argparse
import csv
import json
import os

from eq_proof import load_spec
from eq_proof.attest import attest
from eq_proof.compiler import spec_to_dict
from eq_proof.diagnose import diagnose_and_repair
from eq_proof.report import render_markdown


def read_csv(path):
    out = {}
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            var = row.get("variable")
            val = row.get("value")
            unit = row.get("unit", "")
            if var is None or val is None:
                continue
            try:
                parsed = float(val)
            except ValueError:
                continue
            out[var] = {"value": parsed, "unit": unit} if unit else parsed
    return out


def write_csv(path, original, repaired, units):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["variable", "original", "repaired", "unit"])
        for key in sorted(set(original) | set(repaired)):
            writer.writerow([key, original.get(key), repaired.get(key), units.get(key, "")])


def main():
    parser = argparse.ArgumentParser(description="Repair CSV values against an EQ-PROOF spec.")
    parser.add_argument("spec")
    parser.add_argument("csv")
    parser.add_argument("--out-csv", default="outputs/repaired.csv")
    parser.add_argument("--out-proof", default="outputs/proof_sheet.json")
    parser.add_argument("--out-md", default="outputs/proof_sheet.md")
    args = parser.parse_args()

    spec = load_spec(args.spec)
    inputs = read_csv(args.csv)
    result = diagnose_and_repair(spec, inputs, spec_path=args.spec, inputs_path=args.csv)
    attestation = attest(spec_to_dict(spec), result, spec_path=args.spec, inputs_path=args.csv)

    write_csv(args.out_csv, result["original"], result["repaired"], spec.units)
    os.makedirs(os.path.dirname(args.out_proof) or ".", exist_ok=True)
    os.makedirs(os.path.dirname(args.out_md) or ".", exist_ok=True)
    with open(args.out_proof, "w", encoding="utf-8") as f:
        json.dump(attestation, f, indent=2)
    with open(args.out_md, "w", encoding="utf-8") as f:
        f.write(render_markdown(args.spec, args.csv, result, attestation))


if __name__ == "__main__":
    main()
