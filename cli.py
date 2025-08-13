
#!/usr/bin/env python3
import argparse, json, os
from eq_proof import load_spec
from eq_proof.diagnose import diagnose_and_repair
from eq_proof.attest import attest
from eq_proof.report import render_markdown, report_lines
def main():
    p=argparse.ArgumentParser(description="EQ-PROOF: validate/repair numeric outputs (offline).")
    p.add_argument("spec"); p.add_argument("inputs")
    p.add_argument("--out", default="outputs/proof.json"); p.add_argument("--md", default="outputs/proof.md")
    p.add_argument("--pdf", default=None)
    a=p.parse_args()
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True); os.makedirs(os.path.dirname(a.md) or ".", exist_ok=True)
    spec=load_spec(a.spec); values=json.load(open(a.inputs))
    result=diagnose_and_repair(spec, values, spec_path=a.spec, inputs_path=a.inputs)
    spec_dict = {"name":spec.name,"version":spec.version,"variables":spec.variables,"constraints":spec.constraints,"probes":spec.probes,"alternates":spec.alternates,"units":getattr(spec,"units",{})}
    att=attest(spec_dict, result, spec_path=a.spec, inputs_path=a.inputs)
    json.dump(att, open(a.out,"w"), indent=2); open(a.md,"w").write(render_markdown(a.spec, a.inputs, result, att))
    if a.pdf:
        try:
            from eq_proof.pdf import save_text_pdf
            save_text_pdf(report_lines(a.spec, a.inputs, result, att), a.pdf)
        except Exception as e:
            print(f"[WARN] PDF not created: {e}")
    print(f"[OK] → {a.out} | {a.md}" + (f" | {a.pdf}" if a.pdf else ""))
if __name__=="__main__": main()
