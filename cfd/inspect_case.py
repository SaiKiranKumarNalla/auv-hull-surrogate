"""Inspection picture per dimensionless case: mesh (whole box and close-up) and flow (|U| and Cp) on the plane that
contains the body axis.

    python cfd/inspect_case.py runs/pilot_pics/remus100_finned_v00 results/pilot/inspect
"""
import glob, json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.tri as mtri
from matplotlib.collections import PolyCollection
from plot_mesh import read_vtk


def plane_for(meta):
    # plane holding the body axis: x-y (normal z) unless the body is pitched up, then x-z (normal y)
    return ('sideCells', 'sideView', (0, 2), 'x-z plane') if meta['pitch_deg'] else ('topCells', 'topView', (0, 1), 'x-y plane')


def latest(case, kind):
    t = sorted(glob.glob(os.path.join(case, 'postProcessing', kind, '*')), key=lambda p: float(os.path.basename(p)))
    return t[-1] if t else None


def draw_mesh(ax, pts, polys, ij, box):
    keep = []
    for p in polys:
        c = pts[p][:, list(ij)]
        if box[0] < c[:, 0].mean() < box[1] and box[2] < c[:, 1].mean() < box[3]:
            keep.append(c)
    ax.add_collection(PolyCollection(keep, facecolors='none', edgecolors='#33414c', linewidths=0.15))
    ax.set_xlim(box[0], box[1]); ax.set_ylim(box[2], box[3]); ax.set_aspect('equal'); ax.tick_params(labelsize=7)
    return len(keep)


def draw_field(ax, case, plane, ij, box, key):
    t = latest(case, 'planes')
    f = os.path.join(t, f'{"U" if key == "U" else "p"}_{plane}.raw') if t else ''
    if not os.path.exists(f):
        ax.text(0.5, 0.5, 'no data', ha='center', transform=ax.transAxes); return None
    A = np.loadtxt(f, comments='#'); x, y = A[:, ij[0]], A[:, ij[1]]
    v = np.linalg.norm(A[:, 3:6], axis=1) if key == 'U' else 2 * A[:, 3]          # U_inf = rho = 1: Cp = 2 p
    k = (x > box[0]) & (x < box[1]) & (y > box[2]) & (y < box[3])
    tri = mtri.Triangulation(x[k], y[k]); tt = tri.triangles
    edge = np.max(np.ptp(np.stack([x[k][tt], y[k][tt]], -1), axis=1), axis=1)
    tri.set_mask(edge > 0.06)
    lv, cm = (np.linspace(0, 1.3, 27), 'viridis') if key == 'U' else (np.linspace(-0.8, 1.0, 37), 'RdBu_r')
    cs = ax.tricontourf(tri, v[k], levels=lv, cmap=cm, extend='both')
    ax.set_xlim(box[0], box[1]); ax.set_ylim(box[2], box[3]); ax.set_aspect('equal'); ax.tick_params(labelsize=7)
    return cs


def main(src, out):
    os.makedirs(out, exist_ok=True)
    for case in sorted(glob.glob(os.path.join(src, '*'))):
        if not os.path.exists(os.path.join(case, 'case.json')):
            continue
        m = json.load(open(os.path.join(case, 'case.json')))
        cut, plane, ij, lab = plane_for(m)
        t = latest(case, 'meshcut')
        if not t:
            continue
        pts, polys, _ = read_vtk(os.path.join(t, f'{cut}.vtk'))
        B = m['box']; whole = (B['x'][0], B['x'][1], B['y'][0], B['y'][1])
        lo, hi = np.array(m['bbox_lo']), np.array(m['bbox_hi'])
        a, b = ij
        zoom = (hi[0] - 0.35, hi[0] + 0.25, -0.22, 0.22) if hi[b] < 0.3 else (lo[0] - 0.15, hi[0] + 0.35, lo[b] - 0.15, hi[b] + 0.15)
        near = (-0.8, 2.2, -0.75, 0.75)
        fig, axs = plt.subplots(2, 2, figsize=(15, 8.5))
        n1 = draw_mesh(axs[0, 0], pts, polys, ij, whole); axs[0, 0].set_title(f'Mesh, whole box ({lab})', fontsize=10)
        n2 = draw_mesh(axs[0, 1], pts, polys, ij, zoom); axs[0, 1].set_title('Mesh close-up: tail, fins and prism layers', fontsize=10)
        cs = draw_field(axs[1, 0], case, plane, ij, near, 'U'); axs[1, 0].set_title('Velocity |U| / U∞', fontsize=10)
        if cs: fig.colorbar(cs, ax=axs[1, 0], shrink=0.8)
        cs = draw_field(axs[1, 1], case, plane, ij, near, 'p'); axs[1, 1].set_title('Pressure coefficient Cp', fontsize=10)
        if cs: fig.colorbar(cs, ax=axs[1, 1], shrink=0.8)
        gate = open(os.path.join(case, 'result_gate.txt')).read().strip() if os.path.exists(os.path.join(case, 'result_gate.txt')) else '?'
        fig.suptitle(f'{os.path.basename(src)} · {m["orientation"]} (yaw {m["yaw_deg"]}°, pitch {m["pitch_deg"]}°) · '
                     f'Re = {m["Re"]:.0e} · flow from the left · result check {gate}', fontsize=12)
        plt.tight_layout(); p = os.path.join(out, f'{os.path.basename(case)}.png'); plt.savefig(p, dpi=95); plt.close()
        print('saved', p)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else 'results/pilot/inspect')
