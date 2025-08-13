
from typing import Dict, Tuple, List
from . import no_net as _no_net  # noqa: F401

def project_simplex(y: List[float]) -> List[float]:
    u = sorted(y, reverse=True)
    cssv, csum, rho = [], 0.0, -1
    for i, ui in enumerate(u):
        csum += ui; cssv.append(csum)
        t = (cssv[i] - 1.0) / (i + 1)
        if ui - t > 0: rho = i
    theta = (cssv[rho] - 1.0) / (rho + 1)
    return [max(0.0, yi - theta) for yi in y]

def clip_bounds(vals: Dict[str, float], b: Dict[str, Tuple[float, float]]):
    out = dict(vals)
    for k,(lo,hi) in b.items():
        v = out.get(k,0.0)
        if lo is not None: v = max(lo, v)
        if hi is not None: v = min(hi, v)
        out[k]=v
    return out

def isotonic_increasing(seq: List[float]) -> List[float]:
    y = seq[:]; w=[1.0]*len(y); i=0
    while i < len(y)-1:
        if y[i] <= y[i+1]: i+=1; continue
        j=i
        while j>=0 and y[j] > y[j+1]:
            tot=w[j]+w[j+1]; avg=(w[j]*y[j]+w[j+1]*y[j+1])/tot
            y[j]=y[j+1]=avg; w[j]=w[j+1]=tot; j-=1
        i+=1
    return y
