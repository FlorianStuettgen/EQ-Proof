
from typing import Dict, Any, Tuple
import numpy as np, sympy as sp, platform, hashlib, time, json
from . import no_net as _no_net  # noqa: F401
from .spec import Spec
from .constraints import equality_residual, equality_solve_for
from .repair import project_simplex, clip_bounds, isotonic_increasing
from .qp import alternating_proj_equality_bounds
from .units import coerce_inputs_to_spec_units

TOLS = {
    "equality": 1e-9,
    "simplex_sum": 1e-9,
    "simplex_neg": -1e-12,
    "monotone_slack": -1e-12,
    "altproj_iters": 200,
    "altproj_tol": 1e-9,
    "sum_slack_frac": 0.005,  # +0.5% slack allowed (balanced softness)
    "simplex_sum_soft": 1e-6  # +/- window
}

def _hash_file(path: str) -> str:
    try:
        with open(path,'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()
    except Exception:
        return ""

def diagnose_and_repair(spec: Spec, values: Dict[str, float], *, spec_path: str = "", inputs_path: str = "") -> Dict[str, Any]:
    started = time.time()
    # Units normalize (P100)
    coerced, unit_steps = coerce_inputs_to_spec_units(values, getattr(spec,"units",{}))
    original = dict(coerced); repaired = dict(coerced)
    report = {"violations": [], "steps": []}
    report["steps"].extend(unit_steps)

    # Collect bounds upfront
    bounds={}
    for c in spec.constraints:
        if c.get("type")=="bounds":
            bounds[c["var"]] = (c.get("lower",None), c.get("upper",None))

    # P90: bounds
    if bounds:
        before={k:repaired.get(k) for k in bounds}
        repaired=clip_bounds(repaired, bounds)
        after={k:repaired.get(k) for k in bounds}
        if before!=after: report["steps"].append({"op":"bounds_clip","before":before,"after":after})

    # P80: equality (solve_for then fallback)
    for c in spec.constraints:
        if c.get("type")=="equality":
            expr=c["expr"]; tol=float(c.get("tol", TOLS["equality"]))
            res=abs(equality_residual(expr, repaired))
            if res<=tol: continue
            target=c.get("solve_for")
            if target:
                new=equality_solve_for(expr, target, repaired)
                if new is not None and np.isfinite(new):
                    before=repaired.get(target); repaired[target]=float(new)
                    report["steps"].append({"op":"equality_solve_for","expr":expr,"target":target,"before":before,"after":new,"residual_before":res})
            res2=abs(equality_residual(expr, repaired))
            if res2>tol:
                sym_list=c.get("symbols",[v for v in spec.variables if v in expr])
                loc={s: sp.symbols(s, real=True) for s in sym_list}
                eq=sp.sympify(expr, locals={"Eq": sp.Eq, **loc})
                expr0=sp.simplify(eq.lhs - eq.rhs)
                A_row=[float(sp.N(sp.diff(expr0, loc[s]).subs({loc[k]: repaired.get(k,0.0) for k in sym_list}))) for s in sym_list]
                const=float(sp.N(expr0.subs({loc[k]: 0 for k in sym_list})))
                b_val=-const
                idx_bounds={i: bounds.get(s,(None,None)) for i,s in enumerate(sym_list)}
                x0=[float(repaired.get(s,0.0)) for s in sym_list]
                xhat=alternating_proj_equality_bounds(x0, [A_row], [b_val], idx_bounds, iters=TOLS["altproj_iters"], tol=TOLS["altproj_tol"])
                for s,val in zip(sym_list, xhat): repaired[s]=float(val)
                res3=abs(equality_residual(expr, repaired))
                report["steps"].append({"op":"equality_qp_fallback","expr":expr,"symbols":sym_list,"before":x0,"after":[repaired[s] for s in sym_list],"residual_before":res2,"residual_after":res3})
                if res3>tol: report["violations"].append({"type":"equality","expr":expr,"residual":res3})

    # P70: sum_leq caps (balanced softness: allow +0.5% slack before scaling)
    for c in spec.constraints:
        if c.get("type")=="sum_leq":
            vars_=c["vars"]; cap=float(repaired.get(c.get("cap_var","cap"), c.get("cap",0.0)))
            y=[float(repaired.get(v,0.0)) for v in vars_]; s=sum(y)
            if s > cap*(1.0 + TOLS["sum_slack_frac"]):
                scale=cap/s if s>0 else 0.0
                yhat=[max(0.0, scale*v) for v in y]
                for v,val in zip(vars_, yhat): repaired[v]=float(val)
                report["steps"].append({"op":"sum_leq_scale","vars":vars_,"cap":cap,"before":y,"after":yhat,"scale":scale})
            elif s>cap:
                report["steps"].append({"op":"sum_leq_soft_allow","vars":vars_,"cap":cap,"sum":s,"slack_frac":(s/cap-1.0)})

    # P60: simplex (balanced softness: allow sum within ±1e-6)
    for c in spec.constraints:
        if c.get("type")=="simplex":
            vars_=c["vars"]; y=[float(repaired.get(v,0.0)) for v in vars_]
            s=sum(y)
            if (s < 1.0 - TOLS["simplex_sum_soft"]) or (s > 1.0 + TOLS["simplex_sum_soft"]) or any(v<TOLS["simplex_neg"] for v in y):
                yhat=project_simplex(y)
                for v,val in zip(vars_, yhat): repaired[v]=float(val)
                report["steps"].append({"op":"simplex_project","vars":vars_,"before":y,"after":yhat})
            else:
                report["steps"].append({"op":"simplex_soft_allow","vars":vars_,"sum":s})

    # P50: monotone (non-decreasing)
    for c in spec.constraints:
        if c.get("type")=="monotone":
            vars_=c["vars"]; seq=[float(repaired.get(v,0.0)) for v in vars_]
            bad=any(seq[i]>seq[i+1]+(-TOLS["monotone_slack"]) for i in range(len(seq)-1))
            if bad:
                yhat=isotonic_increasing(seq)
                for v,val in zip(vars_, yhat): repaired[v]=float(val)
                report["steps"].append({"op":"isotonic","vars":vars_,"before":seq,"after":yhat})

    elapsed_ms = int((time.time()-started)*1000)
    report["meta"] = {
        "elapsed_ms": elapsed_ms,
        "env": {"python": platform.python_version(), "platform": platform.platform()}
    }
    return {"original":original,"repaired":repaired,"report":report}
