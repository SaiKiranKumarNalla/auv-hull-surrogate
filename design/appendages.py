"""Parametric appendages: control fins, flaps and fish-like fins, joined to a hull into one watertight mesh.

A design is a plain dict (JSON-serialisable), so a corpus sampler can generate thousands of them:

    {"hull": {"family": "myring", "params": {...}, "width": 1.0, "height": 1.0},
     "fins": [{"name": "tail", "rolls_deg": [0, 90, 180, 270], "x_le": 1.10, "root_chord": 0.10,
               "tip_chord": 0.06, "span": 0.08, "sweep_deg": 20, "thickness": 0.12,
               "deflection_deg": 0, "flap_fraction": 0.0, "flap_deg": 0}]}

Fin model (all lengths in metres):
  - planform: trapezoid with root chord, tip chord, span (measured from the hull surface) and leading-edge sweep;
  - section: symmetric NACA 00tt (thickness = t/c);
  - all-moving deflection about the quarter-chord, plus an optional trailing-edge flap
    (aft `flap_fraction` of the chord rotated by `flap_deg` about its hinge; no hinge gap is modelled);
  - roll angles place several copies around the body (cruciform, X-tail, dorsal, pectoral pair, caudal lobes).
The root is embedded inside the hull and the parts are fused with a boolean union (manifold3d).
"""
import json
import numpy as np
import manifold3d as m3d

import hull_families as hf

FAMILIES = {'myring': hf.myring, 'naca_body': hf.naca_body, 'haack': hf.haack, 'elliptic': hf.elliptic,
            'flat_stern': hf.flat_stern, 'fish_like': hf.fish_like, 'suboff_approx': hf.suboff_approx}


# ---------- mesh helpers ----------
def grid_mesh(P, cap_start=True, cap_end=True):
    """P: (n_rows, n_loop, 3) closed loops stacked along a path -> (vertices, triangles), capped with fans."""
    n, m, _ = P.shape
    V = [P.reshape(-1, 3)]
    F = []
    idx = np.arange(n * m).reshape(n, m)
    for i in range(n - 1):
        for j in range(m):
            k = (j + 1) % m
            F += [(idx[i, j], idx[i + 1, j], idx[i + 1, k]), (idx[i, j], idx[i + 1, k], idx[i, k])]
    base = n * m
    for row, flip, do in ((0, False, cap_start), (n - 1, True, cap_end)):
        if not do:
            continue
        V.append(P[row].mean(0, keepdims=True))
        c = base; base += 1
        for j in range(m):
            k = (j + 1) % m
            F.append((c, idx[row, k], idx[row, j]) if flip else (c, idx[row, j], idx[row, k]))
    return np.concatenate(V), np.array(F)


def to_manifold(V, F):
    V, F = np.asarray(V, np.float32), np.asarray(F, np.uint32)
    man = m3d.Manifold(m3d.Mesh(vert_properties=V, tri_verts=F))
    if man.status() != m3d.Error.NoError:
        raise ValueError(f'part is not a closed manifold: {man.status()}')
    if man.volume() < 0:                                 # inside-out -> flip the winding
        man = m3d.Manifold(m3d.Mesh(vert_properties=V, tri_verts=F[:, ::-1].copy()))
    return man


# ---------- hull ----------
def hull_profile(spec):
    x, r = FAMILIES[spec['family']](**spec['params'])
    return hf.resample(x, r, 220) if len(x) > 220 else (x, r)


def hull_manifold(spec, n_phi=96):
    x, r = hull_profile(spec)
    r = r.copy()
    r[r < 1e-6] = 1e-6                                   # pointed ends -> tiny loops, then fan caps
    X, Y, Z = hf.surface(x, r, n_phi, spec.get('width', 1.0), spec.get('height', 1.0), spec.get('p', 2.0))
    return to_manifold(*grid_mesh(np.stack([X, Y, Z], -1)))


def hull_radius(spec, x0, roll):
    """Distance from the axis to the hull surface at station x0 in direction `roll` (elliptic sections allowed)."""
    x, r = hull_profile(spec)
    return np.interp(x0, x, r) * hf.section_scale(roll, spec.get('width', 1.0), spec.get('height', 1.0), spec.get('p', 2.0))


# ---------- fins ----------
def naca_loop(t, n=40):
    """Closed loop of a NACA 00tt section, chord 0..1, small finite trailing edge (no duplicate points)."""
    xc = 0.5 * (1 - np.cos(np.linspace(0, np.pi, n)))
    yt = 5 * t * (0.2969 * np.sqrt(xc) - 0.1260 * xc - 0.3516 * xc**2 + 0.2843 * xc**3 - 0.1015 * xc**4)
    xs = np.concatenate([xc[::-1], xc[1:]])
    ys = np.concatenate([yt[::-1], -yt[1:]])
    return xs, ys


def _rotate(xs, ys, x0, deg, mask=None):
    a = np.radians(deg)
    m = np.ones_like(xs, bool) if mask is None else mask
    dx, dy = xs[m] - x0, ys[m]
    xs, ys = xs.copy(), ys.copy()
    xs[m], ys[m] = x0 + dx * np.cos(a) + dy * np.sin(a), -dx * np.sin(a) + dy * np.cos(a)
    return xs, ys


def fin_manifold(fin, hull_spec, roll_deg, n_span=12):
    roll = np.radians(roll_deg)
    cr, ct, span = fin['root_chord'], fin['tip_chord'], fin['span']
    sweep = np.tan(np.radians(fin.get('sweep_deg', 0.0)))
    x_le = fin['x_le']
    r_surf = hull_radius(hull_spec, x_le + 0.5 * cr, roll)
    r_root = 0.45 * r_surf                               # embed the root well inside the hull
    xs0, ys0 = naca_loop(fin.get('thickness', 0.12))
    if fin.get('flap_fraction', 0) > 0 and fin.get('flap_deg', 0):
        hinge = 1 - fin['flap_fraction']
        xs0, ys0 = _rotate(xs0, ys0, hinge, fin['flap_deg'], xs0 > hinge)
    xs0, ys0 = _rotate(xs0, ys0, 0.25, fin.get('deflection_deg', 0.0))
    stations = np.concatenate([[r_root], r_surf + span * np.linspace(0, 1, n_span)])
    loops = []
    for rr in stations:
        s = np.clip((rr - r_surf) / span, 0, 1)
        c = cr + (ct - cr) * s
        le = x_le + s * span * sweep
        X = le + c * xs0
        T = c * ys0                                      # thickness direction (tangential)
        loops.append(np.stack([X, rr * np.cos(roll) - T * np.sin(roll), rr * np.sin(roll) + T * np.cos(roll)], -1))
    return to_manifold(*grid_mesh(np.array(loops)))


def bill_manifold(bill, hull_spec, n=24, n_phi=48):
    """Rostrum (swordfish/sailfish bill): a tapered superellipse spike ahead of the nose.
    bill = {length, base_radius, width (y/z flattening, >1 = flat like a swordfish), embed (into the nose)}."""
    Lb, rb = bill['length'], bill['base_radius']
    x = np.linspace(-Lb, bill.get('embed', 0.03), n)
    r = rb * np.clip((x + Lb) / Lb, 1e-4, 1.0) ** 0.8
    X, Y, Z = hf.surface(x, r, n_phi, bill.get('width', 1.0), 1.0)
    return to_manifold(*grid_mesh(np.stack([X, Y, Z], -1)))


# ---------- assembly ----------
def build(design):
    body = hull_manifold(design['hull'])
    if design['hull'].get('bill'):
        body = body + bill_manifold(design['hull']['bill'], design['hull'])
    for fin in design.get('fins', []):
        for roll in fin['rolls_deg']:
            body = body + fin_manifold(fin, design['hull'], roll)
    return body


def save_stl(man, path, name='design'):
    mesh = man.to_mesh()
    V = np.asarray(mesh.vert_properties)[:, :3]
    T = V[np.asarray(mesh.tri_verts)].astype(np.float32)
    nrm = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
    nrm /= np.linalg.norm(nrm, axis=1, keepdims=True).clip(1e-30)
    rec = np.zeros(len(T), dtype=[('n', '<f4', 3), ('v', '<f4', (3, 3)), ('a', '<u2')])
    rec['n'], rec['v'] = nrm, T
    with open(path, 'wb') as f:
        f.write(name.encode()[:80].ljust(80, b' ')); f.write(np.uint32(len(T)).tobytes()); f.write(rec.tobytes())
    return len(T)


def load_design(path):
    with open(path) as f:
        return json.load(f)
