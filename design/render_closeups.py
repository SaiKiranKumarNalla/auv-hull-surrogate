"""Close-up renders of the designs most affected by geometry quality (bill junction, fin roots, fin tips).

    python design/render_closeups.py before|after   -> design/quality/closeups_<tag>.png
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import appendages as ap
from registry import REFERENCES

HERE = os.path.dirname(__file__)
NAMES = ['swordfish_like', 'sailfish_like', 'tuna_like', 'x_tail_flaps']
# (design, zoom box in x) for the second row: the worst junction of each design
ZOOM = {'swordfish_like': (-0.25, 0.25), 'sailfish_like': (-0.12, 0.2), 'tuna_like': (0.75, 1.05), 'x_tail_flaps': (1.05, 1.4)}


def tris(man):
    m = man.to_mesh(); V = np.asarray(m.vert_properties)[:, :3]
    return V, V[np.asarray(m.tri_verts)]


def draw(ax, V, T, xlim=None, view=(18, -60)):
    nrm = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); nrm /= np.linalg.norm(nrm, axis=1, keepdims=True).clip(1e-30)
    if xlim is not None:
        keep = (T[:, :, 0].mean(1) > xlim[0]) & (T[:, :, 0].mean(1) < xlim[1]); T, nrm = T[keep], nrm[keep]
        V = T.reshape(-1, 3)
    shade = 0.25 + 0.75 * np.clip(nrm @ np.array([0.3, -0.5, 0.8]), 0, 1)
    ax.add_collection3d(Poly3DCollection(T, facecolors=plt.cm.Blues(0.2 + 0.7 * shade), edgecolors=(0, 0, 0, 0.08),
                                         linewidths=0.15))
    lo, hi = V.min(0), V.max(0)
    ax.set_xlim(lo[0], hi[0]); ax.set_ylim(lo[1], hi[1]); ax.set_zlim(lo[2], hi[2])
    ax.set_box_aspect(tuple(np.maximum(hi - lo, 1e-3))); ax.view_init(*view); ax.set_axis_off()


if __name__ == '__main__':
    tag = sys.argv[1] if len(sys.argv) > 1 else 'after'
    os.makedirs(os.path.join(HERE, 'quality'), exist_ok=True)
    fig = plt.figure(figsize=(18, 8))
    for i, n in enumerate(NAMES):
        V, T = tris(ap.build(REFERENCES[n]))
        draw(fig.add_subplot(2, 4, i + 1, projection='3d'), V, T)
        fig.axes[-1].set_title(n, fontsize=11)
        draw(fig.add_subplot(2, 4, i + 5, projection='3d'), V, T, ZOOM[n], view=(25, -35))
        fig.axes[-1].set_title(f'zoom x = {ZOOM[n][0]}..{ZOOM[n][1]} m', fontsize=9)
    fig.suptitle(f'Geometry close-ups ({tag})', fontsize=14)
    plt.tight_layout(); plt.savefig(os.path.join(HERE, 'quality', f'closeups_{tag}.png'), dpi=100)
    print('saved', tag)
