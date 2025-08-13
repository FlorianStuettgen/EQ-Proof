
from typing import List
try:
    import matplotlib.pyplot as plt
except Exception as e:
    plt = None
from . import no_net as _no_net  # noqa: F401
def save_text_pdf(lines: List[str], out_path: str, title: str = "EQ-PROOF Report") -> None:
    if plt is None: 
        raise RuntimeError("matplotlib not available for PDF export")
    fig = plt.figure(figsize=(8.27, 11.69)); ax = fig.add_axes([0,0,1,1]); ax.axis('off')
    ax.text(0.05, 0.95, title, va='top', ha='left', fontsize=16, family='monospace')
    ax.text(0.05, 0.90, "\n".join(lines), va='top', ha='left', fontsize=9, family='monospace')
    fig.savefig(out_path, format='pdf', bbox_inches='tight'); plt.close(fig)
