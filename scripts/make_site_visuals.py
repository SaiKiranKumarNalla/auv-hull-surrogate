"""Figures for the project landing page (README) -> docs/img/.

    python scripts/make_site_visuals.py
hero.png        3D renders of eight core designs after the geometry gate
pipeline.png    one design through the harness: recipe -> gate -> mesh -> flow field
flow.png        velocity fields of the six custom CFD cases (cropped from results/cfd_custom/gallery_velocity.png)
"""
import os, sys
ROOT = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, os.path.join(ROOT, 'design'))
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import appendages as ap
from registry import REFERENCES

OUT = os.path.join(ROOT, 'docs', 'img'); os.makedirs(OUT, exist_ok=True)
CAT = {'vehicle': '#378ADD', 'dataset': '#378ADD', 'myring': '#1D9E75', 'family': '#1D9E75',
       'appendage': '#7F77DD', 'bio': '#D85A30'}


def render(ax, design, color, view=(20, -58)):
    m = ap.build(design).to_mesh()
    V = np.asarray(m.vert_properties)[:, :3]; T = V[np.asarray(m.tri_verts)]
    n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); n /= np.linalg.norm(n, axis=1, keepdims=True).clip(1e-30)
    light = np.clip(n @ np.array([0.35, -0.45, 0.82]), 0, 1)
    base = np.array(matplotlib.colors.to_rgb(color))
    fc = np.clip(base[None] * (0.45 + 0.75 * light[:, None]) + 0.12 * light[:, None] ** 8, 0, 1)
    ax.add_collection3d(Poly3DCollection(T, facecolors=fc, linewidths=0))
    lo, hi = V.min(0), V.max(0)
    ax.set_xlim(lo[0], hi[0]); ax.set_ylim(lo[1], hi[1]); ax.set_zlim(lo[2], hi[2])
    ax.set_box_aspect(tuple(np.maximum(hi - lo, 1e-3))); ax.view_init(*view); ax.set_axis_off()


def hero():
    names = ['remus100_finned', 'swordfish_like', 'x_tail_flaps', 'tuna_like',
             'myring_fat_ld5', 'manta_like', 'tall_rudder', 'sailfish_like']
    fig = plt.figure(figsize=(16, 6.2))
    for i, n in enumerate(names):
        ax = fig.add_subplot(2, 4, i + 1, projection='3d')
        render(ax, REFERENCES[n], CAT[REFERENCES[n]['category']])
        ax.set_title(n.replace('_', ' '), fontsize=12, color='#444441', y=0.92)
    plt.subplots_adjust(0, 0, 1, 1, 0, 0.02)
    plt.savefig(os.path.join(OUT, 'hero.png'), dpi=110, facecolor='white'); plt.close()


def crop(f, fy, fx):
    img = mpimg.imread(os.path.join(ROOT, f)); h, w = img.shape[:2]
    return img[int(fy[0] * h):int(fy[1] * h), int(fx[0] * w):int(fx[1] * w)]


def pipeline():
    fig = plt.figure(figsize=(18, 4.6))
    ax = fig.add_axes([0.0, 0.0, 0.2, 0.86]); ax.axis('off')
    ax.text(0.04, 0.88, '{"hull": {"family": "fish_like",\n   "params": {"L": 1.0,\n              "t": 0.22},\n'
                         '   "bill": {"length": 0.70}},\n "fins": [dorsal, pectoral,\n          caudal],\n'
                         ' "condition": {"U": 2.0,\n               "alpha": 4}}', fontsize=11, family='monospace', va='top')
    panels = [('1  Recipe', None), ('2  Geometry gate', None),
              ('3  Mesh (~700K cells)', crop('results/cfd_custom/swordfish_like_mesh_zoom.png', (0.08, 0.95), (0.68, 1.0))),
              ('4  CFD flow field', crop('results/cfd_custom/swordfish_like_fields.png', (0.05, 0.5), (0.5, 0.97)))]
    fig.text(0.1, 0.93, panels[0][0], fontsize=15, weight='bold', color='#3C3489', ha='center')
    ax = fig.add_axes([0.2, 0.0, 0.28, 0.9], projection='3d')
    render(ax, REFERENCES['swordfish_like'], '#D85A30', view=(22, -40))
    fig.text(0.34, 0.93, panels[1][0], fontsize=15, weight='bold', color='#3C3489', ha='center')
    for k, (x0, w) in enumerate([(0.5, 0.2), (0.72, 0.28)]):
        ax = fig.add_axes([x0, 0.02, w, 0.86]); ax.imshow(panels[2 + k][1]); ax.axis('off')
        fig.text(x0 + w / 2, 0.93, panels[2 + k][0], fontsize=15, weight='bold', color='#3C3489', ha='center')
    plt.savefig(os.path.join(OUT, 'pipeline.png'), dpi=100, facecolor='white'); plt.close()


def flow():
    img = mpimg.imread(os.path.join(ROOT, 'results/cfd_custom/gallery_velocity.png'))
    tiles = [(160, 350, 240, 525), (175, 330, 565, 848), (185, 330, 890, 1172), (160, 350, 1212, 1495),
             (385, 580, 240, 525), (425, 525, 565, 848)]
    names = ['bow_stern_planes', 'sailfish_like', 'swordfish_like', 'tall_rudder', 'tuna_like', 'x_tail_flaps']
    fig, axs = plt.subplots(2, 3, figsize=(15, 5.6))
    for ax, (y0, y1, x0, x1), n in zip(axs.ravel(), tiles, names):
        ax.imshow(img[y0:y1, x0:x1]); ax.axis('off')
    fig.suptitle('Velocity magnitude |U|/U∞ around six designs from our OpenFOAM runs (side view, 2 m/s)', fontsize=13)
    plt.tight_layout(); plt.savefig(os.path.join(OUT, 'flow.png'), dpi=100, facecolor='white'); plt.close()


if __name__ == '__main__':
    hero(); pipeline(); flow(); print('saved to', OUT)
