
import json, datetime
from . import no_net as _no_net  # noqa: F401
def render_markdown(spec_path: str, inputs_path: str, result: dict, attestation: dict) -> str:
    ts = datetime.datetime.utcnow().isoformat()+"Z"
    o=result["original"]; r=result["repaired"]; steps=result["report"]["steps"]
    md = [f"# EQ-PROOF Report", f"- Generated: {ts}", f"- Spec: `{spec_path}`  ", f"- Inputs: `{inputs_path}`", "## Original vs Repaired"]
    for k in sorted(set(o)|set(r)): md.append(f"- **{k}**: {o.get(k)} → **{r.get(k)}**")
    md.append("## Steps"); md += (["- "+json.dumps(s) for s in steps] or ["- none"])
    md.append("## Attestation"); md.append(f"- algorithm: {attestation.get('algo')}"); md.append(f"- signature: `{attestation.get('signature')}`")
    return "\n".join(md)
def report_lines(spec_path: str, inputs_path: str, result: dict, attestation: dict) -> list:
    lines=[f"Spec: {spec_path}", f"Inputs: {inputs_path}", ""]
    o=result["original"]; r=result["repaired"]; steps=result["report"]["steps"]
    lines.append("Original vs Repaired"); [lines.append(f"- {k}: {o.get(k)} -> {r.get(k)}") for k in sorted(set(o)|set(r))]
    lines.append(""); lines.append("Steps:"); lines += [json.dumps(s) for s in steps]
    lines.append(""); lines.append(f"Attestation: {attestation.get('algo')} {attestation.get('signature')}"); return lines
