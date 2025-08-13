
from typing import Dict, Tuple
import sympy as sp

BASE = {"":((0,0,0,0,0,0,0),1.0),"m":((1,0,0,0,0,0,0),1.0),"kg":((0,1,0,0,0,0,0),1.0),
        "s":((0,0,1,0,0,0,0),1.0),"A":((0,0,0,1,0,0,0),1.0),"K":((0,0,0,0,1,0,0),1.0),
        "mol":((0,0,0,0,0,1,0),1.0),"cd":((0,0,0,0,0,0,1),1.0)}
DER = {
    "Hz":((0,0,-1,0,0,0,0),1.0),
    "J": ((2,1,-2,0,0,0,0),1.0),
    "V": ((2,1,-3,-1,0,0,0),1.0),
    "Ω": ((2,1,-3,-2,0,0,0),1.0),
    "ohm":((2,1,-3,-2,0,0,0),1.0),
    "eV":((2,1,-2,0,0,0,0),1.602176634e-19),
}
PREFIX={"Y":1e24,"Z":1e21,"E":1e18,"P":1e15,"T":1e12,"G":1e9,"M":1e6,"k":1e3,"h":1e2,"da":1e1,
        "d":1e-1,"c":1e-2,"m":1e-3,"u":1e-6,"μ":1e-6,"n":1e-9,"p":1e-12,"f":1e-15,"a":1e-18,"z":1e-21,"y":1e-24}
CONST={"h":("J*s",6.62607015e-34),"hbar":("J*s",1.054571817e-34),"ħ":("J*s",1.054571817e-34),
       "c":("m/s",299792458.0),"k_B":("J/K",1.380649e-23),"q_e":("C",1.602176634e-19)}

def _mul(a,b): return tuple(x+y for x,y in zip(a,b))
def _div(a,b): return tuple(x-y for x,y in zip(a,b))
def _pow(a,p): return tuple(x*p for x in a)

def _atom(tok):
    if tok in BASE: return BASE[tok]
    if tok in DER: return DER[tok]
    if len(tok)>=2 and tok[:2] in PREFIX and tok[2:] in BASE: d,f=BASE[tok[2:]]; return d,f*PREFIX[tok[:2]]
    if len(tok)>=2 and tok[:2] in PREFIX and tok[2:] in DER: d,f=DER[tok[2:]]; return d,f*PREFIX[tok[:2]]
    if tok[0:1] in PREFIX and tok[1:] in BASE: d,f=BASE[tok[1:]]; return d,f*PREFIX[tok[0:1]]
    if tok[0:1] in PREFIX and tok[1:] in DER: d,f=DER[tok[1:]]; return d,f*PREFIX[tok[0:1]]
    raise ValueError(f"Unknown unit token: {tok}")

def parse_unit(u:str):
    if not u or u=="1": return BASE[""]
    u=u.replace(" ","")
    num,*den=u.split("/"); dim=BASE[""][0]; fac=1.0
    for tok in filter(None,num.split("*")):
        base, p = tok.split("^") if "^" in tok else (tok,"1"); p=int(p)
        d,f=_atom(base); dim=_mul(dim,_pow(d,p)); fac*=f**p
    if den:
        den="*".join(den)
        for tok in filter(None,den.split("*")):
            base,p = tok.split("^") if "^" in tok else (tok,"1"); p=int(p)
            d,f=_atom(base); dim=_div(dim,_pow(d,p)); fac/=f**p
    return dim, fac

def convert(val, from_u, to_u):
    d1,f1=parse_unit(from_u); d2,f2=parse_unit(to_u)
    if d1!=d2: raise ValueError("Incompatible units")
    return (val*f1)/f2

def coerce_inputs_to_spec_units(values: dict, spec_units: Dict[str,str]):
    steps=[]; out=dict(values)
    for k,u in spec_units.items():
        if isinstance(values.get(k), dict) and "value" in values[k] and "unit" in values[k]:
            v=float(values[k]["value"]); from_u=str(values[k]["unit"]); v2=convert(v, from_u, u)
            out[k]=v2; steps.append({"op":"unit_convert","var":k,"from":from_u,"to":u,"value_in":v,"value_out":v2})
    return out, steps
