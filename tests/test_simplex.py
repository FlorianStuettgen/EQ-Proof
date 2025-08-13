
from eq_proof.repair import project_simplex
v = project_simplex([0.7,0.4,0.2])
assert abs(sum(v)-1.0)<1e-9 and all(x>=-1e-12 for x in v)
