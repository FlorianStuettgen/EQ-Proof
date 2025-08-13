
from dataclasses import dataclass, field
from typing import List, Dict, Any
import json
from . import no_net as _no_net  # noqa: F401

@dataclass
class Spec:
    name: str
    version: str
    variables: List[str]
    constraints: List[Dict[str, Any]]
    probes: List[Dict[str, Any]]
    alternates: List[str]
    units: Dict[str, str] = field(default_factory=dict)

def load_spec(path: str) -> "Spec":
    with open(path, "r") as f:
        d = json.load(f)
    for k in ["name","version","variables","constraints"]:
        if k not in d: raise ValueError(f"Spec missing {k}")
    return Spec(d["name"], d["version"], d["variables"], d["constraints"], d.get("probes",[]), d.get("alternates",[]), d.get("units",{}))
