"""Build the Tier-1 sample set: 2D sketches, 3D views and binary STL files in design/samples/."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
import hull_families as hf

L, D = 1.33, 0.191      # REMUS-100-like envelope (the paper's optimisation case)
SAMPLES = {   # file: (title, (x, r), width, height, colour)
    'myring_remus':       ('Myring (REMUS-like)', hf.myring(0.19, 0.85, 0.29, D, 2.0, 20), 1, 1, '#1f77b4'),
    'myring_blunt_n5':    ('Myring, blunt nose n = 5', hf.myring(0.12, 0.90, 0.31, D, 5.0, 30), 1, 1, '#1f77b4'),
    'naca0014_body':      ('NACA 0014 body of revolution', hf.naca_body(L, D / L), 1, 1, '#2ca02c'),
    'haack_von_karman':   ('Von Kármán nose/tail (Haack C = 0)', hf.haack(0.30, 0.65, 0.38, D, 0.0), 1, 1, '#9467bd'),
    'haack_lv':           ('LV-Haack nose/tail (C = 1/3)', hf.haack(0.30, 0.65, 0.38, D, 1 / 3), 1, 1, '#9467bd'),
    'elliptic_parabolic': ('Elliptic nose, parabolic tail', hf.elliptic(0.15, 0.88, 0.30, D, 2.0), 1, 1, '#ff7f0e'),
    'flat_stern':         ('Flat stern (compact AUV)', hf.flat_stern(0.15, 0.80, 0.38, D, 2.0, 25, 0.45), 1, 1, '#d62728'),
    'fish_like_elliptic': ('Fish-like, elliptic section (Tier-3 preview)', hf.fish_like(L, D / L, 0.35, 0.012), 0.65, 1.0, '#8c564b'),
}

out = os.path.dirname(__file__)
os.makedirs(os.path.join(out, 'samples'), exist_ok=True)

fig, axs = plt.subplots(4, 2, figsize=(14, 10))
for ax, (title, (x, r), w, h, col) in zip(axs.ravel(), SAMPLES.values()):
    ax.fill_between(x, -r * h, r * h, color=col, alpha=0.35)
    ax.plot(x, r * h, x, -r * h, c=col, lw=1.2)
    V, _ = hf.volume_area(x, r * np.sqrt(w * h))
    ax.set_title(f'{title}\nL = {x[-1]:.2f} m, D = {2 * r.max() * h:.3f} m, L/D = {x[-1] / (2 * r.max() * h):.1f}, '
                 f'volume ≈ {V * 1e3:.1f} L', fontsize=9)
    ax.set_aspect('equal'); ax.set_ylim(-0.16, 0.16); ax.set_xlim(-0.02, 1.37); ax.tick_params(labelsize=7)
fig.suptitle('Tier-1 hull families: side profiles in the same envelope (L ≈ 1.33 m, D = 0.191 m)', fontsize=12)
plt.tight_layout(); plt.savefig(os.path.join(out, 'tier1_sketches.png'), dpi=130); plt.close()

fig = plt.figure(figsize=(16, 7))
for i, (title, (x, r), w, h, col) in enumerate(SAMPLES.values()):
    ax = fig.add_subplot(2, 4, i + 1, projection='3d')
    xs, rs = hf.resample(x, r, 60)
    X, Y, Z = hf.surface(xs, rs, 48, w, h)
    ax.plot_surface(X, Y, Z, color=col, alpha=0.95, linewidth=0, shade=True)
    ax.set_box_aspect((1.4, 0.22, 0.22)); ax.view_init(18, -60); ax.set_axis_off(); ax.set_title(title, fontsize=9)
plt.tight_layout(); plt.savefig(os.path.join(out, 'tier1_3d.png'), dpi=120); plt.close()

for name, (title, (x, r), w, h, _) in SAMPLES.items():
    xs, rs = hf.resample(x, r)
    rs[-1] = r[-1]                                   # keep a blunt stern exact
    n = hf.write_stl(os.path.join(out, 'samples', f'{name}.stl'), xs, rs, 72, w, h, name)
    print(f'{name:22s} {n:6d} triangles')
