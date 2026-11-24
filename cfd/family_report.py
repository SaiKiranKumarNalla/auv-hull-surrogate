"""Family report: every variant of one base at all 15 conditions.
    python cfd/family_report.py results/family_myring runs/myring2_*_results/small
Writes family_table.csv and family_overview.png (drag vs Re, side force vs yaw, lift vs pitch, gate map)."""
import csv, glob, os, sys
import numpy as np
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
sys.path.insert(0, os.path.dirname(__file__)); from pilot_report import load

out, srcs = sys.argv[1], sys.argv[2:]
rows = []
for s in srcs:
    for v in sorted(glob.glob(os.path.join(s, '*'))):
        for c in sorted(glob.glob(os.path.join(v, '*'))):
            r = load(c)
            if r: r['variant'] = os.path.basename(v)[-3:]; rows.append(r)
os.makedirs(out, exist_ok=True)
keys = ['variant', 'orientation', 'Re', 'cells', 'iters', 'C_drag', 'C_side', 'C_lift', 'Cm_pitch', 'Cm_yaw', 'band_pct', 'mesh_gate', 'result_gate']
with open(os.path.join(out, 'family_table.csv'), 'w', newline='') as f:
    w = csv.writer(f); w.writerow(keys)
    for r in rows: w.writerow([f'{r[k]:.5g}' if isinstance(r[k], float) else r[k] for k in keys])
V = sorted({r['variant'] for r in rows}); cm = plt.cm.viridis(np.linspace(0, 0.9, len(V)))
g = lambda v, o, Re=None: [r for r in rows if r['variant'] == v and r['orientation'] == o and (Re is None or abs(r['Re'] - Re) < 1)]
fig, ax = plt.subplots(1, 4, figsize=(20, 4.6))
Re = np.logspace(6, 7, 20); ittc = 0.075 / (np.log10(Re) - 2) ** 2
ax[0].plot(Re, ittc, 'k--', lw=1, label='ITTC friction line')
for v, c in zip(V, cm):
    rs = sorted(g(v, 'front'), key=lambda r: r['Re']); ax[0].plot([r['Re'] for r in rs], [r['C_drag'] for r in rs], 'o-', color=c, label=v)
    ys = [('front', 0), ('yaw5', 5), ('yaw10', 10), ('yaw20', 20), ('yaw30', 30)]
    pts = [(a, g(v, o, 3e6)[0]) for o, a in ys if g(v, o, 3e6)]
    ax[1].plot([a for a, _ in pts], [abs(r['C_side']) for _, r in pts], 'o-', color=c)
    for a, r in pts:
        if r['result_gate'] != 'PASS': ax[1].plot(a, abs(r['C_side']), 'rx', ms=10)
    ps = [('pitchm10', -10), ('front', 0), ('pitch10', 10), ('pitch20', 20)]
    pts = [(a, g(v, o, 3e6)[0]) for o, a in ps if g(v, o, 3e6)]
    ax[2].plot([a for a, _ in pts], [r['C_lift'] for _, r in pts], 'o-', color=c)
    ax[3].plot([a for a, _ in [(a, 0) for o, a in ys]], [g(v, o, 3e6)[0]['C_drag'] if g(v, o, 3e6) else np.nan for o, a in ys], 'o-', color=c)
ax[0].set(xscale='log', xlabel='Re', title='Straight ahead: drag vs Re'); ax[0].legend(fontsize=7)
ax[1].set(xlabel='yaw angle (deg)', title='|Side force| vs yaw, Re 3e6 (x = band > 1 %)')
ax[2].set(xlabel='pitch angle (deg)', title='Lift vs pitch, Re 3e6'); ax[3].set(xlabel='yaw angle (deg)', title='Drag vs yaw, Re 3e6')
for a in ax: a.grid(alpha=.3)
fig.suptitle(f'myring_slender_ld15 family: {len(V)} variants, {len(rows)} runs (coefficients on wetted area)')
plt.tight_layout(); plt.savefig(os.path.join(out, 'family_overview.png'), dpi=105)
fr = [r for r in rows if r['orientation'] == 'front']
for r in fr: r['ff'] = r['C_drag'] / (0.075 / (np.log10(r['Re']) - 2) ** 2)
print('form factor front: ', ' '.join(f"{r['variant']}@{r['Re']:.0e}:{r['ff']:.2f}" for r in fr if abs(r['Re']-3e6)<1))
print('gates', {k: sum(1 for r in rows if r['result_gate'].startswith(k)) for k in ['PASS', 'FAIL']})
