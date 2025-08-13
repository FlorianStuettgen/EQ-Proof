
#!/usr/bin/env python3
import argparse, csv, os, json
from eq_proof import load_spec
from eq_proof.diagnose import diagnose_and_repair
from eq_proof.attest import attest
from eq_proof.report import render_markdown
def read_csv(path):
    out={}
    with open(path, newline='') as f:
        r=csv.DictReader(f)
        for row in r:
            var=row.get("variable"); val=row.get("value"); unit=row.get("unit","")
            if var is None or val is None: continue
            try: v=float(val)
            except: continue
            out[var]={"value":v,"unit":unit} if unit else v
    return out
def write_csv(path, original, repaired, units):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path,"w",newline='') as f:
        w=csv.writer(f); w.writerow(["variable","original","repaired","unit"])
        for k in sorted(set(original)|set(repaired)):
            w.writerow([k, original.get(k), repaired.get(k), units.get(k,"")])
def main():
    p=argparse.ArgumentParser(); p.add_argument("spec"); p.add_argument("csv")
    p.add_argument("--out-csv", default="outputs/repaired.csv"); p.add_argument("--out-proof", default="outputs/proof_sheet.json"); p.add_argument("--out-md", default="outputs/proof_sheet.md")
    a=p.parse_args()
    spec=load_spec(a.spec); inputs=read_csv(a.csv)
    res=diagnose_and_repair(spec, inputs, spec_path=a.spec, inputs_path=a.csv)
    spec_dict={"name":spec.name,"version":spec.version,"variables":spec.variables,"constraints":spec.constraints,"probes":spec.probes,"alternates":spec.alternates,"units":getattr(spec,"units",{})}
    att=attest(spec_dict, res, spec_path=a.spec, inputs_path=a.csv)
    write_csv(a.out_csv, res["original"], res["repaired"], getattr(spec,"units",{}))
    with open(a.out-proof,"w") as f: json.dump(att, f, indent=2)
    with open(a.out_md,"w") as f: f.write(render_markdown(a.spec, a.csv, res, att))
if __name__=="__main__": main()
