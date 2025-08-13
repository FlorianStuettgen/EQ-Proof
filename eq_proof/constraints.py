
from typing import Dict, Optional
import sympy as sp
from . import no_net as _no_net  # noqa: F401

def _locals_from_values(values: Dict[str, float]):
    syms = {k: sp.symbols(k, real=True) for k in values}
    ctx = {"Eq": sp.Eq}
    ctx.update(syms)
    return ctx, syms

def equality_residual(expr_str: str, values: Dict[str, float]) -> float:
    locals_, syms = _locals_from_values(values)
    eq = sp.sympify(expr_str, locals=locals_)
    subs_map = {syms[k]: float(v) for k,v in values.items() if k in syms}
    res = sp.simplify(eq.lhs - eq.rhs).subs(subs_map)
    return float(sp.N(res))

def equality_solve_for(expr_str: str, target: str, values: Dict[str, float]) -> Optional[float]:
    all_names = set(values) | {target}
    syms = {k: sp.symbols(k, real=True) for k in all_names}
    locals_ = {"Eq": sp.Eq, **syms}
    eq = sp.sympify(expr_str, locals=locals_)
    t = syms[target]
    try:
        sol = sp.solve(eq, t, dict=True)
        if not sol: return None
        subs_map = {syms[k]: float(v) for k,v in values.items() if k in syms}
        v = float(sp.N(sol[0][t].subs(subs_map)))
        return v
    except Exception:
        return None
