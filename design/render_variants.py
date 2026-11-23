"""Gallery of the variant spread: each panel overlays the side and top silhouettes of a base's 10 variants
(thin coloured outlines) on the base design (dark).

    python design/render_variants.py   -> design/variants_gallery.png
"""
import glob, json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
import appendages as ap
from registry import REFERENCES
from variants import TEST_BASES

HERE = os.path.dirname(__file__)


def silhouette(ax, design, axes, color, alpha, z0):
    m = ap.build(design).to_mesh()
    V = np.asarray(m.vert_properties)[:, :3]; T = V[np.asarray(m.tri_verts)][:, :, axes]
    ax.add_collection(PolyCollection(T, facecolors=color, edgecolors='none', alpha=alpha, zorder=z0))
    return V[:, axes].min(0), V[:, axes].max(0)


fig, axs = plt.subplots(10, 4, figsize=(20, 26))
cmap = plt.cm.viridis
for k, (name, base) in enumerate(REFERENCES.items()):
    for j, (axes, label) in enumerate((([0, 2], 'side'), ([0, 1], 'top'))):
        ax = axs[k // 2, 2 * (k % 2) + j]
        lo, hi = silhouette(ax, base, axes, '#222222', 0.9, 3)
        for i, f in enumerate(sorted(glob.glob(os.path.join(HERE, 'variants', name, 'v*.json')))):
            d = json.load(open(f))
            l2, h2 = silhouette(ax, d, axes, cmap(i / 9), 0.10, 1)
            lo, hi = np.minimum(lo, l2), np.maximum(hi, h2)
        pad = 0.04 * (hi - lo).max()
        ax.set_xlim(lo[0] - pad, hi[0] + pad); ax.set_ylim(lo[1] - pad, hi[1] + pad)
        ax.set_aspect('equal'); ax.set_xticks([]); ax.set_yticks([])
        for s in ax.spines.values():
            s.set_visible(False)
        held = '  [held-out base]' if name in TEST_BASES else ''
        ax.set_title(f'{name} · {label}{held}', fontsize=9, color='#A32D2D' if held else 'black')
fig.suptitle('20 core designs (dark) with their 10 parametric variants each (coloured overlay)', fontsize=15)
plt.tight_layout(rect=(0, 0, 1, 0.985))
plt.savefig(os.path.join(HERE, 'variants_gallery.png'), dpi=80)
print('saved')
