"""Render the 20 reference designs from the registry and export their STL files to design/references/."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import appendages as ap
from registry import REFERENCES

HERE = os.path.dirname(__file__)
COL = {'verified': '#2a9d8f', 'cited': '#457b9d', 'unverified': '#e9c46a', 'assumption': '#e76f51'}
os.makedirs(os.path.join(HERE, 'references'), exist_ok=True)
fig = plt.figure(figsize=(20, 13))
for i, (name, r) in enumerate(REFERENCES.items()):
    man = ap.build(r)
    ap.save_stl(man, os.path.join(HERE, 'references', f'{name}.stl'), name)
    m = man.to_mesh(); V = np.asarray(m.vert_properties)[:, :3]; T = V[np.asarray(m.tri_verts)]
    nrm = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); nrm /= np.linalg.norm(nrm, axis=1, keepdims=True).clip(1e-30)
    shade = 0.3 + 0.7 * np.clip(nrm @ np.array([0.3, -0.5, 0.8]), 0, 1)
    ax = fig.add_subplot(4, 5, i + 1, projection='3d')
    ax.add_collection3d(Poly3DCollection(T, facecolors=plt.cm.Blues(0.25 + 0.65 * shade), linewidths=0))
    lo, hi = V.min(0), V.max(0)
    ax.set_xlim(lo[0], hi[0]); ax.set_ylim(lo[1], hi[1]); ax.set_zlim(lo[2], hi[2])
    ax.set_box_aspect(tuple(hi - lo)); ax.view_init(22, -55); ax.set_axis_off()
    st = r['provenance']['status']
    ax.set_title(f'{name}\n{r["category"]} · L = {hi[0] - lo[0]:.2f} m · {st}', fontsize=9, color=COL[st])
fig.suptitle('20 reference designs (title colour = provenance: green verified, blue cited, yellow unverified, red assumption)',
             fontsize=13)
plt.tight_layout(); plt.savefig(os.path.join(HERE, 'references_20.png'), dpi=110)
