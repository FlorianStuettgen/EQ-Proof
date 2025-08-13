
from typing import List, Tuple, Dict, Optional
import numpy as np
from . import no_net as _no_net  # noqa: F401

def project_linear_equality(x, A, b):
    At = A.T
    y = np.linalg.solve(A @ At, (A @ x) - b)
    return x - At @ y

def alternating_proj_equality_bounds(x0: List[float],
                                     A: List[List[float]],
                                     b: List[float],
                                     bounds: Dict[int, Tuple[Optional[float], Optional[float]]],
                                     iters: int = 200, tol: float = 1e-9) -> List[float]:
    x = np.array(x0, dtype=float); A_m = np.array(A, dtype=float); b_v = np.array(b, dtype=float)
    for _ in range(iters):
        prev = x.copy()
        x = project_linear_equality(x, A_m, b_v)
        for idx,(lo,hi) in bounds.items():
            if lo is not None and x[idx] < lo: x[idx]=lo
            if hi is not None and x[idx] > hi: x[idx]=hi
        if np.linalg.norm(x-prev) <= tol: break
    return list(map(float, x))
