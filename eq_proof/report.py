import datetime
import json

from . import no_net as _no_net  # noqa: F401


def render_markdown(spec_path: str, inputs_path: str, result: dict, attestation: dict) -> str:
    ts = datetime.datetime.utcnow().isoformat() + "Z"
    original = result["original"]
    repaired = result["repaired"]
    steps = result["report"].get("steps", [])

    md = [
        "# EQ-PROOF Report",
        f"- Generated: {ts}",
        f"- Spec: `{spec_path}`",
        f"- Inputs: `{inputs_path}`",
        "",
        "## Original vs Repaired",
        "| variable | original | repaired |",
        "| --- | ---: | ---: |",
    ]
    for key in sorted(set(original) | set(repaired)):
        md.append(f"| {key} | {original.get(key)} | {repaired.get(key)} |")

    md.append("")
    md.append("## Steps")
    md += (["- " + json.dumps(step, sort_keys=True) for step in steps] or ["- none"])

    projection_residuals = result["report"].get("projection_residuals", [])
    if projection_residuals:
        md.append("")
        md.append("## Projection Residuals")
        md.append("| constraint | type | residual |")
        md.append("| --- | --- | ---: |")
        for item in projection_residuals:
            md.append(f"| {item['constraint']} | {item['type']} | {item['residual']} |")

    md.append("")
    md.append("## Attestation")
    md.append(f"- algorithm: {attestation.get('algo')}")
    md.append(f"- signature: `{attestation.get('signature')}`")
    if attestation.get("pubkey"):
        md.append(f"- public key: `{attestation.get('pubkey')}`")
    return "\n".join(md)


def report_lines(spec_path: str, inputs_path: str, result: dict, attestation: dict) -> list:
    original = result["original"]
    repaired = result["repaired"]
    steps = result["report"].get("steps", [])
    lines = [f"Spec: {spec_path}", f"Inputs: {inputs_path}", "", "Original vs Repaired"]
    for key in sorted(set(original) | set(repaired)):
        lines.append(f"- {key}: {original.get(key)} -> {repaired.get(key)}")
    lines.append("")
    lines.append("Steps:")
    lines += [json.dumps(step, sort_keys=True) for step in steps]
    lines.append("")
    lines.append(f"Attestation: {attestation.get('algo')} {attestation.get('signature')}")
    return lines
