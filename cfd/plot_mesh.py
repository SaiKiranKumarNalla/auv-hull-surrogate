"""Geometry and mesh pictures from the sampled VTK files (cfd/sample_mesh.dict), no ParaView needed.

    python cfd/plot_mesh.py runs/sample_paper
per case -> mesh_domain.png (whole domain + bounding box), mesh_zoom.png (nose / mid-body wall / tail),
            geometry.png (snapped OpenFOAM hull surface coloured by Cp)
"""
import glob, json, os, sys
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from mpl_toolkits.mplot3d.art3d import Poly3DCollection


def read_vtk(path):
    """Legacy ASCII POLYDATA -> points (n,3), list of polygons (index arrays), cell field dict."""
    tok = open(path).read().split()
    i = 0; pts = None; polys = []; fields = {}
    while i < len(tok):
        t = tok[i]
        if t == 'POINTS':
            n = int(tok[i + 1]); pts = np.array(tok[i + 3:i + 3 + 3 * n], float).reshape(n, 3); i += 3 + 3 * n; continue
        if t == 'POLYGONS':
            n, size = int(tok[i + 1]), int(tok[i + 2]); j = i + 3
            if tok[j] == 'OFFSETS':                         # VTK 5.1 style
                no = n; j += 2; off = np.array(tok[j:j + no], int); j += no
                j += 2; nc = off[-1]; con = np.array(tok[j:j + nc], int); j += nc
                polys = [con[off[k]:off[k + 1]] for k in range(no - 1)]
            else:
                arr = np.array(tok[j:j + size], int); k = 0
                while k < size:
                    m = arr[k]; polys.append(arr[k + 1:k + 1 + m]); k += m + 1
                j += size
            i = j; continue
        if t == 'CELL_DATA':
            i += 2; continue
        if t == 'FIELD':
            nf = int(tok[i + 2]); j = i + 3
            for _ in range(nf):
                name, nc, nt = tok[j], int(tok[j + 1]), int(tok[j + 2]); j += 4
                fields[name] = np.array(tok[j:j + nc * nt], float).reshape(nt, nc); j += nc * nt
            i = j; continue
        if t == 'SCALARS':
            name = tok[i + 1]; j = i + 3
            if tok[j] == 'LOOKUP_TABLE': j += 2
            n = len(polys); fields[name] = np.array(tok[j:j + n], float)[:, None]; i = j + n; continue
        i += 1
    return pts, polys, fields


def find(case, name):
    f = sorted(glob.glob(os.path.join(case, 'postProcessing', 'meshcut', '*', f'{name}*.vtk')))
    return f[-1] if f else None


def mesh_pictures(case):
    meta = json.load(open(os.path.join(case, 'case.json')))
    L, xc, h, cell = meta['L'], meta['x_centre'], meta['half_width'], meta['base_cell']
    side = 8 * h; x0, x1 = xc - L, xc + 3 * L
    f = find(case, 'sideCells')
    if not f:
        return []
    P, polys, _ = read_vtk(f)
    xz = [P[p][:, [0, 2]] for p in polys]
    out = []
    # 1. whole domain with the bounding box of the block mesh and of the body
    fig, ax = plt.subplots(figsize=(14, 5))
    ax.add_collection(PolyCollection(xz, facecolors='none', edgecolors='k', linewidths=0.08))
    ax.plot([x0, x1, x1, x0, x0], [-side, -side, side, side, -side], 'r-', lw=1.2, label='domain (blockMesh)')
    bx0, bx1 = xc - L / 2, xc + L / 2
    ax.plot([bx0, bx1, bx1, bx0, bx0], [-h, -h, h, h, -h], 'b-', lw=1.0, label='body bounding box')
    ax.set_xlim(x0 - 0.05 * L, x1 + 0.05 * L); ax.set_ylim(-side * 1.1, side * 1.1); ax.set_aspect('equal')
    ax.legend(loc='upper right', fontsize=8)
    ax.set_title(f"{meta['name']}: x-z mesh cut, {len(polys):,} cells in plane; base cell {cell * 1000:.0f} mm, "
                 f"domain {x1 - x0:.2f} × {2 * side:.2f} × {2 * side:.2f} m", fontsize=10)
    fn = os.path.join(case, 'mesh_domain.png'); plt.tight_layout(); plt.savefig(fn, dpi=130); plt.close(); out.append(fn)
    # 2. zooms: nose, mid-body wall (layers), tail with fins
    nose = xc - L / 2
    zooms = [('nose', nose - 0.06 * L, nose + 0.14 * L, 0, h * 1.6),
             ('mid-body wall layers', xc - 0.03 * L, xc + 0.03 * L, h * 0.75, h * 1.25),
             ('tail and fins', xc + 0.25 * L, xc + 0.62 * L, -h * 2.2, h * 2.2)]
    fig, axs = plt.subplots(1, 3, figsize=(18, 5.5))
    for ax, (title, a, b, lo, hi) in zip(axs, zooms):
        if lo == 0:
            lo, hi = -hi, hi
        keep = [p for p in xz if (p[:, 0].max() > a) and (p[:, 0].min() < b) and (p[:, 1].max() > lo) and (p[:, 1].min() < hi)]
        ax.add_collection(PolyCollection(keep, facecolors='#dfe9f5', edgecolors='k', linewidths=0.25))
        ax.set_xlim(a, b); ax.set_ylim(lo, hi); ax.set_aspect('equal'); ax.set_title(f'zoom: {title}', fontsize=10)
        ax.tick_params(labelsize=7)
    fig.suptitle(f"{meta['name']}: mesh close-ups (snappyHexMesh, surface levels 5-7, 2 prism layers)", fontsize=11)
    fn = os.path.join(case, 'mesh_zoom.png'); plt.tight_layout(); plt.savefig(fn, dpi=130); plt.close(); out.append(fn)
    # 3. snapped hull surface as OpenFOAM sees it, coloured by Cp
    g = find(case, 'hullSurface')
    if g:
        Q, faces, F = read_vtk(g)
        tris = [Q[p] for p in faces]
        U = meta['condition']['U']
        cp = F['p'][:, 0] / (0.5 * U ** 2) if 'p' in F and len(F['p']) == len(faces) else None
        fig = plt.figure(figsize=(14, 5)); ax = fig.add_subplot(111, projection='3d')
        col = plt.cm.RdBu_r(np.clip((cp + 0.6) / 1.6, 0, 1)) if cp is not None else '#7fa7d1'
        ax.add_collection3d(Poly3DCollection(tris, facecolors=col, edgecolors='k', linewidths=0.03))
        lo_, hi_ = Q.min(0), Q.max(0)
        ax.set_xlim(lo_[0], hi_[0]); ax.set_ylim(lo_[1], hi_[1]); ax.set_zlim(lo_[2], hi_[2])
        ax.set_box_aspect(tuple(np.maximum(hi_ - lo_, 1e-3))); ax.view_init(20, -60)
        ax.set_title(f"{meta['name']}: snapped hull in OpenFOAM ({len(faces):,} faces), colour = Cp "
                     f"(blue -0.6 … red 1.0); bounding box {hi_[0] - lo_[0]:.2f} × {hi_[1] - lo_[1]:.2f} × {hi_[2] - lo_[2]:.2f} m", fontsize=9)
        fn = os.path.join(case, 'geometry.png'); plt.tight_layout(); plt.savefig(fn, dpi=120); plt.close(); out.append(fn)
    return out


if __name__ == '__main__':
    root = sys.argv[1] if len(sys.argv) > 1 else 'runs/sample_paper'
    for c in sorted(glob.glob(os.path.join(root, '*/'))):
        if os.path.exists(os.path.join(c, 'case.json')):
            try:
                print(os.path.basename(c.rstrip('/')), [os.path.basename(f) for f in mesh_pictures(c)])
            except Exception as e:
                print(os.path.basename(c.rstrip('/')), 'FAILED', e)
