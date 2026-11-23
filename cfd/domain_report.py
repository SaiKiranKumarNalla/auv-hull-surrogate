"""Domain-independence report: one case in several box sizes -> coefficients vs box size.

    python cfd/domain_report.py runs/domain_results/small results/domain
"""
import glob, json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pilot_report import load

src, out = sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else 'results/domain'
os.makedirs(out, exist_ok=True)
rows = []
for d in sorted(glob.glob(os.path.join(src, '*', '*'))):
    r = load(d)
    if r:
        m = json.load(open(os.path.join(d, 'case.json'))); B = m['box']
        r['box_len'] = B['x'][1] - B['x'][0]; r['box_half'] = B['y'][1]; r['name'] = os.path.basename(os.path.dirname(d))
        rows.append(r)
rows.sort(key=lambda r: r['box_len'])
ref = rows[-1]
print(f"{'box':>6} {'half-width':>10} {'cells':>9} {'iters':>5} {'C_drag':>9} {'dC vs largest':>14} {'C_lift':>9} {'band%':>6}")
for r in rows:
    print(f"{r['box_len']:5.0f}L {r['box_half']:9.1f}L {r['cells']:>9} {r['iters']:5d} {r['C_drag']:9.5f} "
          f"{100 * (r['C_drag'] / ref['C_drag'] - 1):+13.2f}% {r['C_lift']:+9.5f} {r['band_pct']:6.2f}")
fig, ax = plt.subplots(figsize=(7, 4))
L = [r['box_len'] for r in rows]
ax.plot(L, [100 * (r['C_drag'] / ref['C_drag'] - 1) for r in rows], 'o-', label='drag')
ax.axhspan(-1, 1, color='#1D9E75', alpha=0.12, label='±1 % band')
ax.set_xlabel('box length (body lengths)'); ax.set_ylabel('change vs largest box (%)'); ax.grid(alpha=0.3); ax.legend()
ax.set_title('Domain independence: manta_like v05, front, Re 3×10⁶')
plt.tight_layout(); plt.savefig(os.path.join(out, 'domain_independence.png'), dpi=110)
