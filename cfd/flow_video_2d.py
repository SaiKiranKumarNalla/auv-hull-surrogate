"""2D flow video on the mid-plane through the body: speed as background colour, particles injected upstream and
moved with the in-plane velocity, drawn with short fading trails. Steady RANS field, so particles follow the
time-averaged flow (no shedding).

    python cfd/flow_video_2d.py runs/pilot_pics/remus100_finned_v00/front_Re3e6 results/pilot/video2d_front_Re3e6.mp4
"""
import glob, json, os, sys
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.tri as mtri
from matplotlib.collections import LineCollection
import imageio.v2 as imageio

FRAMES, FPS, DT, TRAIL, N_NEW = 300, 30, 0.012, 8, 9
BOX = (-0.8, 2.2, -0.55, 0.55)


def load(case):
    m = json.load(open(os.path.join(case, 'case.json')))
    plane, ij = ('sideView', (0, 2)) if m['pitch_deg'] else ('topView', (0, 1))
    t = sorted(glob.glob(os.path.join(case, 'postProcessing', 'planes', '*')), key=lambda p: float(os.path.basename(p)))[-1]
    A = np.loadtxt(os.path.join(t, f'U_{plane}.raw'), comments='#')
    x, y = A[:, ij[0]], A[:, ij[1]]; u, v = A[:, 3 + ij[0]], A[:, 3 + ij[1]]
    k = (x > BOX[0] - 0.1) & (x < BOX[1] + 0.1) & (y > BOX[2] - 0.1) & (y < BOX[3] + 0.1)
    tri = mtri.Triangulation(x[k], y[k]); tt = tri.triangles
    edge = np.max(np.ptp(np.stack([x[k][tt], y[k][tt]], -1), axis=1), axis=1)
    tri.set_mask(edge > 0.15)                                  # far-field cells are ~0.1; no triangles across the body (D ~ 0.18)
    return m, tri, mtri.LinearTriInterpolator(tri, u[k]), mtri.LinearTriInterpolator(tri, v[k]), np.hypot(u, v)[k]


def main(case, out):
    m, tri, fu, fv, speed = load(case)
    vel = lambda p: np.stack([np.asarray(fu(p[:, 0], p[:, 1]).filled(np.nan)),
                              np.asarray(fv(p[:, 0], p[:, 1]).filled(np.nan))], 1)
    rng = np.random.default_rng(0)
    hist = np.empty((0, TRAIL, 2))
    fig, ax = plt.subplots(figsize=(12.8, 5.2), dpi=100)
    fig.subplots_adjust(0.03, 0.06, 0.97, 0.9)
    ax.tricontourf(tri, speed, levels=np.linspace(0, 1.3, 40), cmap='Blues_r', extend='both', alpha=0.9)
    ax.set_xlim(BOX[0], BOX[1]); ax.set_ylim(BOX[2], BOX[3]); ax.set_aspect('equal'); ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_title(f"Flow past an AUV hull · {m['orientation']} (yaw {m['yaw_deg']}°, pitch {m['pitch_deg']}°) · "
                 f"Re = {m['Re']:.0e} · mid-plane, flow left to right", fontsize=12)
    lc = LineCollection([], cmap='turbo', linewidths=1.6); lc.set_clim(0.4, 1.2); ax.add_collection(lc)
    sm = plt.cm.ScalarMappable(cmap='turbo', norm=plt.Normalize(0.4, 1.2))
    cb = fig.colorbar(sm, ax=ax, fraction=0.025, pad=0.01); cb.set_label('particle speed |U| / U∞')
    w = imageio.get_writer(out, fps=FPS, quality=8, macro_block_size=8)
    for f in range(FRAMES):
        new = np.column_stack([np.full(N_NEW, BOX[0] + 0.01), rng.uniform(BOX[2], BOX[3], N_NEW)])
        extra = np.column_stack([rng.uniform(BOX[0], BOX[1], 10),
                                 np.r_[rng.uniform(BOX[2], BOX[3], 4), rng.normal(0, 0.06, 6)]])   # bias toward the wake line
        extra = extra[np.isfinite(vel(extra)).all(1)]                    # also release inside the field (fills the wake)
        new = np.concatenate([new, extra])
        hist = np.concatenate([hist, np.repeat(new[:, None], TRAIL, 1)])
        p = hist[:, -1]
        k1 = vel(p); k2 = vel(p + 0.5 * DT * np.nan_to_num(k1))           # midpoint (RK2) step
        p = p + DT * k2
        alive = np.isfinite(p).all(1) & (p[:, 0] < BOX[1])
        hist = np.concatenate([hist[:, 1:], p[:, None]], 1)[alive]
        segs = np.stack([hist[:, :-1], hist[:, 1:]], 2).reshape(-1, 2, 2)
        sp = np.linalg.norm(np.diff(hist, axis=1), axis=2).reshape(-1) / DT
        if len(hist):
            lc.set_segments(segs); lc.set_array(sp)
            lc.set_alpha(np.tile(np.linspace(0.05, 1, TRAIL - 1), len(hist)))
        fig.canvas.draw()
        w.append_data(np.asarray(fig.canvas.buffer_rgba())[:, :, :3])
    w.close(); plt.close(fig)
    print('saved', out)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
