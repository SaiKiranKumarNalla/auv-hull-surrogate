"""Report for one shape run at every orientation x Re (dimensionless cases from cfd/corpus_case.py).

    python cfd/pilot_report.py runs/pilot_results/small/remus100_finned_v00  results/pilot
writes results/pilot/: pilot_table.csv, pilot_coefficients.png, pilot_fields.png, pilot_convergence.png
Coefficients use U = 1, rho = 1 and the wetted area S of the unit-length body: C = F / (0.5 S).
Wind axes: drag along the flow (+x), side force y, lift z. Body axes: X along the body, Y to the side, Z up.
"""
import csv, glob, json, os, sys
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.tri as mtri

ORDER = ['front', 'yaw10', 'yaw30', 'side', 'top']
COL = {'front': '#185FA5', 'yaw10': '#1D9E75', 'yaw30': '#BA7517', 'side': '#D85A30', 'top': '#7F77DD'}


def last_vec(path, start):
    rows = [l for l in open(path) if l.strip() and not l.startswith('#')]
    v = rows[-1].replace('(', ' ').replace(')', ' ').split()
    return np.array([float(x) for x in v[start:start + 3]]), len(rows)


def load(case):
    m = json.load(open(os.path.join(case, 'case.json')))
    f = sorted(glob.glob(os.path.join(case, 'postProcessing', 'forces', '*', 'force.dat')))
    mo = sorted(glob.glob(os.path.join(case, 'postProcessing', 'forces', '*', 'moment.dat')))
    if not f:
        return None
    F, n = last_vec(f[-1], 1); M, _ = last_vec(mo[-1], 1)
    q = 0.5 * m['S_wet']                                   # 0.5 rho U^2 S with rho = U = 1
    R = np.array(m['R'])
    Fb, Mb = R.T @ F, R.T @ M                              # back to body axes
    cf = sorted(glob.glob(os.path.join(case, 'postProcessing', 'coeffs', '*', 'coefficient.dat')))
    cd = np.array([float(l.split()[1]) for l in open(cf[-1]) if l.strip() and not l.startswith('#')]) if cf else np.array([])
    band = 100 * np.ptp(cd[-100:]) / abs(cd[-100:].mean()) if len(cd) >= 2 else np.nan
    gate = lambda n: open(os.path.join(case, n)).read().strip() if os.path.exists(os.path.join(case, n)) else '?'
    cells = next((l.split()[1] for l in open(os.path.join(case, 'log.checkMesh')) if l.strip().startswith('cells:')), '?') \
        if os.path.exists(os.path.join(case, 'log.checkMesh')) else '?'
    return dict(orientation=m['orientation'], Re=m['Re'], cells=cells, iters=n,
                C_drag=F[0] / q, C_side=F[1] / q, C_lift=F[2] / q,
                C_X=Fb[0] / q, C_Y=Fb[1] / q, C_Z=Fb[2] / q,
                Cm_roll=Mb[0] / q, Cm_pitch=Mb[1] / q, Cm_yaw=Mb[2] / q,
                band_pct=band, mesh_gate=gate('mesh_gate.txt'), result_gate=gate('result_gate.txt'), cd_hist=cd, case=case)


def main(src, out):
    os.makedirs(out, exist_ok=True)
    runs = [r for r in (load(c) for c in sorted(glob.glob(os.path.join(src, '*')))) if r]
    runs.sort(key=lambda r: (ORDER.index(r['orientation']), r['Re']))
    keys = ['orientation', 'Re', 'cells', 'iters', 'C_drag', 'C_side', 'C_lift', 'C_X', 'C_Y', 'C_Z',
            'Cm_roll', 'Cm_pitch', 'Cm_yaw', 'band_pct', 'mesh_gate', 'result_gate']
    with open(os.path.join(out, 'pilot_table.csv'), 'w', newline='') as f:
        w = csv.writer(f); w.writerow(keys)
        for r in runs:
            w.writerow([r[k] if not isinstance(r[k], float) else f'{r[k]:.5g}' for k in keys])

    fig, axs = plt.subplots(1, 3, figsize=(16, 4.6))
    for o in ORDER:
        rs = [r for r in runs if r['orientation'] == o]
        if not rs: continue
        Re = [r['Re'] for r in rs]
        axs[0].plot(Re, [r['C_drag'] for r in rs], 'o-', color=COL[o], label=o)
        axs[1].plot(Re, [r['C_side'] for r in rs], 'o-', color=COL[o], label=o)
        axs[2].plot(Re, [r['Cm_yaw'] for r in rs], 'o-', color=COL[o], label=o)
    for ax, t in zip(axs, ['Drag coefficient (along the flow)', 'Side-force coefficient', 'Yaw-moment coefficient (body axes)']):
        ax.set_xscale('log'); ax.set_xlabel('Reynolds number (based on length)'); ax.set_title(t); ax.grid(alpha=0.3)
    axs[0].set_yscale('log'); axs[0].legend()
    fig.suptitle('Coefficients vs Reynolds number for each flow direction (reference: wetted area)', fontsize=13)
    plt.tight_layout(); plt.savefig(os.path.join(out, 'pilot_coefficients.png'), dpi=110); plt.close()

    fig, ax = plt.subplots(figsize=(10, 4))
    for r in runs:
        if len(r['cd_hist']):
            ax.plot(r['cd_hist'] / r['cd_hist'][-1], color=COL[r['orientation']], lw=0.8, alpha=0.4 + 0.2 * np.log10(r['Re'] / 1e6))
    ax.set_ylim(0.8, 1.2); ax.set_xlabel('iteration'); ax.set_ylabel('C_drag / final value'); ax.grid(alpha=0.3)
    ax.set_title('Convergence of drag, all 15 runs (colour = flow direction)')
    plt.tight_layout(); plt.savefig(os.path.join(out, 'pilot_convergence.png'), dpi=110); plt.close()

    sel = [r for r in runs if abs(r['Re'] - 3e6) < 1]
    fig, axs = plt.subplots(len(sel), 2, figsize=(14, 2.6 * len(sel)), squeeze=False)
    for i, r in enumerate(sel):
        for j, (plane, ij, lab) in enumerate([('topView', (0, 1), 'top view (x-y plane)'), ('sideView', (0, 2), 'side view (x-z plane)')]):
            ax = axs[i, j]
            t = sorted(glob.glob(os.path.join(r['case'], 'postProcessing', 'planes', '*')), key=lambda p: float(os.path.basename(p)))
            fu = glob.glob(os.path.join(t[-1], f'U_{plane}.raw')) if t else []
            if fu:
                A = np.loadtxt(fu[0], comments='#'); x, y = A[:, ij[0]], A[:, ij[1]]
                um = np.linalg.norm(A[:, 3:6], axis=1)
                keep = (x > -0.9) & (x < 2.2) & (np.abs(y) < 0.75)
                tri = mtri.Triangulation(x[keep], y[keep]); tt = tri.triangles
                e = np.max(np.ptp(np.stack([x[keep][tt], y[keep][tt]], -1), axis=1), axis=1)
                tri.set_mask((um[keep][tt] < 0.02).all(1) | (e > 0.08))
                cs = ax.tricontourf(tri, um[keep], levels=np.linspace(0, 1.3, 27), cmap='viridis', extend='both')
            ax.set_xlim(-0.9, 2.2); ax.set_ylim(-0.75, 0.75); ax.set_aspect('equal'); ax.tick_params(labelsize=7)
            ax.set_title(f'{r["orientation"]} · {lab} · C_drag {r["C_drag"]:.4f}', fontsize=9)
    if sel:
        fig.colorbar(cs, ax=axs, shrink=0.6, label='|U| / U∞')
    fig.suptitle('Velocity around the same body at Re = 3×10⁶, flow from the left in every panel', fontsize=12)
    plt.savefig(os.path.join(out, 'pilot_fields.png'), dpi=100); plt.close()
    for r in runs:
        print(f"{r['orientation']:6s} Re {r['Re']:.0e} cells {r['cells']:>8} it {r['iters']:4d} Cdrag {r['C_drag']:.5f} "
              f"Cside {r['C_side']:+.5f} Clift {r['C_lift']:+.5f} band {r['band_pct']:.2f}% gates {r['mesh_gate']}/{r['result_gate']}")


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else 'results/pilot')
