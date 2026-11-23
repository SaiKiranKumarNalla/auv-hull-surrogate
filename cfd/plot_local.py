"""Local mesh-independence check: probes, profile lines and slices across a grid family.

    python cfd/plot_local.py runs/gci5/gci        (folders sf_s<scale> from cfd/gcp/gci5.sh)
writes into that folder:
    local_probes_history.png   |U|/U and Cp at every probe vs iteration, one line per grid (iterative stability)
    local_probes_table.csv     final probe values and difference vs the finest grid (% of U, Cp points)
    local_lines.png            profile overlays; title gives max |dU|/U vs finest per grid
    local_lines_table.csv      mean / max |dU|/U and max |dCp| vs finest, PASS if max |dU|/U < 5 %
    local_slices_U.png, local_slices_Cp.png   side-view tail zoom + caudal / fin cross-sections per grid
"""
import csv, glob, os, sys
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.tri as mtri

U0 = 2.0
LIMIT = 0.05
PROBES = ['P1 ahead of bill', 'P2 bill-body junction', 'P3 mid-body 1 cm off wall', 'P4 behind dorsal TE',
          'P5 behind pectoral', 'P6 caudal TE mid-span', 'P7 caudal tip vortex', 'P8 near wake', 'P9 wake 0.5 L']


def grids(root):
    out = []
    for d in glob.glob(os.path.join(root, 'sf_s*')):
        log = os.path.join(d, 'log.checkMesh')
        if os.path.exists(log):
            out.append((int(open(log).read().split('cells:')[1].split()[0]), d))
    return sorted(out)


def read_probe(d, field):
    f = sorted(glob.glob(os.path.join(d, 'postProcessing', 'probes', '*', field)))
    if not f:
        return None
    rows = []
    for line in open(f[-1]):
        if line.startswith('#') or not line.strip():
            continue
        rows.append([float(v) for v in line.replace('(', ' ').replace(')', ' ').split()])
    return np.array(rows)


def latest(d, kind):
    t = sorted(glob.glob(os.path.join(d, 'postProcessing', kind, '*')), key=lambda p: float(os.path.basename(p)))
    return t[-1] if t else None


def read_line(d, name):
    t = latest(d, 'lines')
    if not t:
        return None
    f = [p for p in glob.glob(os.path.join(t, f'{name}*')) if 'U' in os.path.basename(p) or 'p' in os.path.basename(p)]
    if not f:
        return None
    A = np.loadtxt(sorted(f)[0], comments='#')        # distance p Ux Uy Uz  (scalars first, then vectors)
    if A.ndim == 1 or A.shape[1] < 5:
        return None
    return A[:, 0], A[:, 1] / (0.5 * U0 ** 2), np.linalg.norm(A[:, 2:5], axis=1) / U0


def read_plane(d, name):
    t = latest(d, 'planes')
    if not t:
        return None
    fp = glob.glob(os.path.join(t, f'p_{name}.raw')) or glob.glob(os.path.join(t, name, 'p*'))
    fu = glob.glob(os.path.join(t, f'U_{name}.raw')) or glob.glob(os.path.join(t, name, 'U*'))
    if not fp or not fu:
        return None
    P, V = np.loadtxt(fp[0], comments='#'), np.loadtxt(fu[0], comments='#')
    return P[:, :3], P[:, 3] / (0.5 * U0 ** 2), np.linalg.norm(V[:, 3:6], axis=1) / U0


def probes(root, G):
    nP = len(PROBES)
    fig, axs = plt.subplots(nP, 2, figsize=(14, 2.1 * nP), sharex=True)
    final = {}
    for n, d in G:
        U, p = read_probe(d, 'U'), read_probe(d, 'p')
        if U is None or p is None:
            continue
        it = U[:, 0]
        um = np.stack([np.linalg.norm(U[:, 1 + 3 * k:4 + 3 * k], axis=1) for k in range(nP)], 1) / U0
        cp = p[:, 1:1 + nP] / (0.5 * U0 ** 2)
        for k in range(nP):
            axs[k, 0].plot(it, um[:, k], lw=0.9, label=f'{n / 1e3:.0f}K')
            axs[k, 1].plot(p[:, 0], cp[:, k], lw=0.9)
        tail = slice(-100, None)
        final[n] = (um[tail].mean(0), cp[tail].mean(0), (um[tail].max(0) - um[tail].min(0)))
    for k in range(nP):
        axs[k, 0].set_ylabel(PROBES[k], fontsize=7, rotation=0, ha='right', va='center')
        axs[k, 0].tick_params(labelsize=6); axs[k, 1].tick_params(labelsize=6)
    axs[0, 0].set_title('|U| / U∞ at probe vs iteration'); axs[0, 1].set_title('Cp at probe vs iteration')
    axs[0, 0].legend(fontsize=6, ncol=5)
    axs[-1, 0].set_xlabel('iteration'); axs[-1, 1].set_xlabel('iteration')
    plt.tight_layout(); plt.savefig(os.path.join(root, 'local_probes_history.png'), dpi=100); plt.close()
    fine = max(final)
    with open(os.path.join(root, 'local_probes_table.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['cells', 'probe', 'U_over_Uinf', 'Cp', 'dU_vs_finest_pct_of_Uinf', 'dCp_vs_finest', 'iter_band_U_pct'])
        for n in sorted(final):
            um, cp, band = final[n]
            for k in range(nP):
                w.writerow([n, PROBES[k], f'{um[k]:.4f}', f'{cp[k]:.4f}', f'{100 * (um[k] - final[fine][0][k]):+.2f}',
                            f'{cp[k] - final[fine][1][k]:+.4f}', f'{100 * band[k]:.3f}'])
    return final


LINES = ['blMid', 'blTail', 'dorsalWake', 'pectoralWake', 'caudalWake', 'wakeY', 'wakeZ']


def lines(root, G):
    fig, axs = plt.subplots(2, len(LINES), figsize=(4 * len(LINES), 7))
    fine_n, fine_d = G[-1]
    rows = []
    for j, name in enumerate(LINES):
        ref = read_line(fine_d, name)
        msg = []
        for n, d in G:
            L = read_line(d, name)
            if L is None:
                continue
            s, cp, um = L
            axs[0, j].plot(um, s, lw=1, label=f'{n / 1e3:.0f}K'); axs[1, j].plot(cp, s, lw=1)
            if ref is not None and n != fine_n:
                um_i, cp_i = np.interp(ref[0], s, um), np.interp(ref[0], s, cp)
                du, dc = np.abs(um_i - ref[2]), np.abs(cp_i - ref[1])
                rows.append([name, n, f'{100 * du.mean():.2f}', f'{100 * du.max():.2f}', f'{dc.max():.4f}',
                             'PASS' if du.max() < LIMIT else 'FAIL'])
                msg.append(f'{n / 1e3:.0f}K {100 * du.max():.1f}%')
        axs[0, j].set_title(name + '\nmax |ΔU|/U∞ vs finest:\n' + ', '.join(msg), fontsize=7)
        axs[0, j].set_xlabel('|U| / U∞', fontsize=8); axs[1, j].set_xlabel('Cp', fontsize=8)
        axs[0, j].tick_params(labelsize=6); axs[1, j].tick_params(labelsize=6)
    axs[0, 0].set_ylabel('distance along line (m)'); axs[1, 0].set_ylabel('distance along line (m)')
    axs[0, 0].legend(fontsize=7)
    plt.tight_layout(); plt.savefig(os.path.join(root, 'local_lines.png'), dpi=100); plt.close()
    with open(os.path.join(root, 'local_lines_table.csv'), 'w', newline='') as f:
        w = csv.writer(f); w.writerow(['line', 'cells', 'mean_dU_pct', 'max_dU_pct', 'max_dCp', f'max_dU<{int(LIMIT * 100)}%'])
        w.writerows(rows)
    return rows


VIEWS = [('sideView', (0, 2), (0.6, 1.7, -0.4, 0.4), 'side view, tail + caudal fin'),
         ('crossFins', (1, 2), (-0.35, 0.35, -0.3, 0.35), 'cross-section x = 0.40 m (dorsal + pectorals)'),
         ('crossCaudal', (1, 2), (-0.3, 0.3, -0.4, 0.4), 'cross-section x = 1.42 m (caudal TE)')]


def slices(root, G, key):
    fig, axs = plt.subplots(len(VIEWS), len(G), figsize=(3.6 * len(G), 3.2 * len(VIEWS)), squeeze=False)
    cmap, lo, hi, lab = ('viridis', 0.0, 1.25, '|U| / U∞') if key == 'U' else ('RdBu_r', -0.6, 1.0, 'Cp')
    cs = None
    for c, (n, d) in enumerate(G):
        for r, (name, ax_ij, box, title) in enumerate(VIEWS):
            ax = axs[r, c]; P = read_plane(d, name)
            if P is not None:
                X, cp, um = P; x, y = X[:, ax_ij[0]], X[:, ax_ij[1]]; v = um if key == 'U' else cp
                keep = (x > box[0]) & (x < box[1]) & (y > box[2]) & (y < box[3])
                tri = mtri.Triangulation(x, y); t = tri.triangles
                bad = ~keep[t].all(1) | (um[t] < 0.02).all(1)
                tri.set_mask(bad)
                cs = ax.tricontourf(tri, v, levels=np.linspace(lo, hi, 41), cmap=cmap, extend='both')
            ax.set_xlim(box[0], box[1]); ax.set_ylim(box[2], box[3]); ax.set_aspect('equal'); ax.tick_params(labelsize=6)
            if r == 0:
                ax.set_title(f'{n / 1e3:.0f}K cells', fontsize=10, fontweight='bold')
            if c == 0:
                ax.set_ylabel(title, fontsize=8)
    if cs is not None:
        fig.colorbar(cs, ax=axs, shrink=0.6, label=lab)
    fig.suptitle(f'{lab}, swordfish_like, same slices on every grid', fontsize=12)
    plt.savefig(os.path.join(root, f'local_slices_{key}.png'), dpi=95); plt.close()


if __name__ == '__main__':
    root = sys.argv[1] if len(sys.argv) > 1 else 'runs/gci5/gci'
    G = grids(root)
    print('grids:', [n for n, _ in G])
    final = probes(root, G)
    rows = lines(root, G)
    for r in rows:
        print(*r)
    slices(root, G, 'U'); slices(root, G, 'Cp')
