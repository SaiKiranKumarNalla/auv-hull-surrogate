"""Pressure-coefficient and velocity pictures from the sampled planes (raw files from cfd/sample_planes.dict).

    python cfd/plot_fields.py runs/sample_paper      -> runs/sample_paper/<case>/fields.png + gallery PNGs
simpleFoam pressure is kinematic (p/rho), so Cp = p / (0.5 U^2).
"""
import glob, json, os, sys
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.tri as mtri


def find(case, surface, field):
    hits = [f for f in glob.glob(os.path.join(case, 'postProcessing', 'planes', '*', '**', '*'), recursive=True)
            if os.path.isfile(f) and surface in f and os.path.basename(f).split('_')[0].split('.')[0] == field]
    hits += [f for f in glob.glob(os.path.join(case, 'postProcessing', 'planes', '*', f'{field}_{surface}.raw'))]
    return sorted(set(hits))[-1] if hits else None


def load(path):
    return np.loadtxt(path, comments='#')


def panel(ax, x, y, v, title, cmap, vmin, vmax, box, wall=None):
    tri = mtri.Triangulation(x, y)
    keep = (x > box[0]) & (x < box[1]) & (np.abs(y) < box[2])
    # mask triangles outside the box or spanning the body (very long edges)
    t = tri.triangles
    bad = ~keep[t].all(1)
    if wall is not None:                       # triangles spanning the body interior join wall points only
        bad |= wall[t].all(1)
    tri.set_mask(bad)
    cs = ax.tricontourf(tri, v, levels=np.linspace(vmin, vmax, 41), cmap=cmap, extend='both')
    ax.set_aspect('equal'); ax.set_xlim(box[0], box[1]); ax.set_ylim(-box[2], box[2])
    ax.set_title(title, fontsize=9); ax.tick_params(labelsize=7)
    return cs


def case_fields(case):
    meta = json.load(open(os.path.join(case, 'case.json')))
    U = meta['condition']['U']; L = meta['L']; xc = meta['x_centre']; h = meta['half_width']
    box = (xc - 0.65 * L, xc + 1.1 * L, max(2.5 * h, 0.18 * L))
    out = {}
    for surf, axes in (('sideView', (0, 2)), ('topView', (0, 1))):
        fp, fu = find(case, surf, 'p'), find(case, surf, 'U')
        if not fp or not fu:
            continue
        P, V = load(fp), load(fu)
        out[surf] = dict(x=P[:, axes[0]], y=P[:, axes[1]], cp=P[:, 3] / (0.5 * U ** 2),
                         xu=V[:, axes[0]], yu=V[:, axes[1]], umag=np.linalg.norm(V[:, 3:6], axis=1) / U)
        out[surf]['wall'] = out[surf]['umag'] < 0.02 if len(P) == len(V) else None
    return meta, box, out


def plot_case(case):
    meta, box, F = case_fields(case)
    if not F:
        return None
    fig, axs = plt.subplots(len(F), 2, figsize=(14, 3.2 * len(F)), squeeze=False)
    for row, (surf, d) in enumerate(F.items()):
        c1 = panel(axs[row, 0], d['x'], d['y'], d['cp'], f'{surf}: pressure coefficient Cp', 'RdBu_r', -0.6, 1.0, box, d['wall'])
        c2 = panel(axs[row, 1], d['xu'], d['yu'], d['umag'], f'{surf}: |U| / U∞', 'viridis', 0.0, 1.25, box, d['wall'])
        fig.colorbar(c1, ax=axs[row, 0], shrink=0.8); fig.colorbar(c2, ax=axs[row, 1], shrink=0.8)
    fig.suptitle(f"{meta['name']}   L = {meta['L']:.2f} m, Re = {meta['Re']:.2e}, U∞ = {meta['condition']['U']} m/s", fontsize=11)
    plt.tight_layout(); fn = os.path.join(case, 'fields.png'); plt.savefig(fn, dpi=110); plt.close()
    return fn


def gallery(root, key, cmap, vmin, vmax, label, fname):
    cases = [c for c in sorted(glob.glob(os.path.join(root, '*/'))) if os.path.exists(os.path.join(c, 'case.json'))]
    fig, axs = plt.subplots(5, 4, figsize=(20, 14)); cs = None
    for ax, case in zip(axs.ravel(), cases):
        meta, box, F = case_fields(case)
        ax.set_title(meta['name'], fontsize=9)
        if 'sideView' in F:
            d = F['sideView']
            x, y, v = (d['x'], d['y'], d['cp']) if key == 'cp' else (d['xu'], d['yu'], d['umag'])
            cs = panel(ax, x, y, v, meta['name'], cmap, vmin, vmax, box, d['wall'])
        else:
            ax.text(0.5, 0.5, 'no data', ha='center', transform=ax.transAxes); ax.set_axis_off()
    if cs is not None:
        fig.colorbar(cs, ax=axs, shrink=0.5, label=label)
    fig.suptitle(f'{label}, side view (x-z plane), paper conditions U∞ = 2 m/s', fontsize=13)
    plt.savefig(os.path.join(root, fname), dpi=100); plt.close()


if __name__ == '__main__':
    root = sys.argv[1] if len(sys.argv) > 1 else 'runs/sample_paper'
    for c in sorted(glob.glob(os.path.join(root, '*/'))):
        if os.path.exists(os.path.join(c, 'case.json')):
            print(os.path.basename(c.rstrip('/')), plot_case(c))
    gallery(root, 'umag', 'viridis', 0.0, 1.25, '|U| / U∞', 'gallery_velocity.png')
    gallery(root, 'cp', 'RdBu_r', -0.6, 1.0, 'Cp', 'gallery_pressure.png')
