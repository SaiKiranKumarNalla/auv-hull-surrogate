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


def _smooth(v, k):
    """Moving average with edge padding (k odd); used to round the bill-body blend."""
    if k < 3:
        return v
    pad = np.pad(v, k // 2, mode='edge')
    return np.convolve(pad, np.ones(k) / k, mode='valid')


TAIL_TIP_R = 0.005          # tail-tip radius / hull length: prism layers cannot wrap a mathematical point


def hull_sections(spec):
    """Stations x with half-width ry(x) (y) and half-height rz(x) (z) of the whole body, bill included.

    The bill is not a separate part: bill and body are blended into one profile. Ahead of the body's maximum
    thickness, ry and rz are made non-decreasing (no waist or collar where the bill meets the head) and then
    smoothed, which acts as a fillet. A fish body whose stern ends at a finite peduncle radius is closed with a
    rounded cap instead of a flat disc."""
    x, r = hull_profile(spec)
    w, h = spec.get('width', 1.0), spec.get('height', 1.0)
    ry, rz = r * w, r * h
    if spec['family'] == 'fish_like' and r[-1] > 1e-6:          # rounded peduncle cap
        rp = r[-1]
        u = np.linspace(0, 1, 12)[1:]
        x = np.concatenate([x, x[-1] + 1.5 * rp * u])
        cap = np.sqrt(np.clip(1 - u ** 2, 0, None))
        ry, rz = np.concatenate([ry, ry[-1] * cap]), np.concatenate([rz, rz[-1] * cap])
    Lh = x[-1] - x[0]; rt = TAIL_TIP_R * Lh                      # pointed tail -> rounded tip of radius ~rt
    if not (spec['family'] == 'fish_like' and r[-1] > 1e-6) and max(ry[-1], rz[-1]) < rt and max(ry.max(), rz.max()) > 2 * rt:
        # cut the tail where it is rt thick and close it with r = r0 sqrt(1 - u): the cap starts with the hull's
        # own slope (cap length chosen to match it) and ends vertical, so the outline has no corner
        xf = np.linspace(x[np.argmax(np.maximum(ry, rz))], x[-1], 2000)
        yf, zf = np.interp(xf, x, ry), np.interp(xf, x, rz); rf = np.maximum(yf, zf)
        i = int(np.nonzero(rf >= rt)[0][-1])
        s0 = max(-(rf[i] - rf[i - 1]) / (xf[1] - xf[0]), 1e-3)
        Lc = rf[i] / (2 * s0)
        u = 1 - (1 - np.linspace(0, 1, 25)[1:]) ** 2              # points clustered at the closed end
        cap = np.sqrt(np.clip(1 - u, 0, None))
        keep = x < xf[0]
        x = np.concatenate([x[keep], xf[:i + 1], xf[i] + Lc * u])
        ry = np.concatenate([ry[keep], yf[:i + 1], yf[i] * cap]); rz = np.concatenate([rz[keep], zf[:i + 1], zf[i] * cap])
    bill = spec.get('bill')
    if bill:
        Lb, rb, bw = bill['length'], bill['base_radius'], bill.get('width', 1.0)
        body_y, body_z = (lambda xx: np.interp(xx, x, ry, left=0.0)), (lambda xx: np.interp(xx, x, rz, left=0.0))
        xu = np.linspace(-Lb, x[-1], 900)                        # even spacing so smoothing has a fixed length
        tip = (xu + Lb) / Lb
        zb_u = np.where(xu <= 0, rb * np.clip(tip, 1e-4, 1.0) ** 0.8, 0.0)
        ry, rz = np.maximum(bw * zb_u, body_y(xu)), np.maximum(zb_u, body_z(xu))
        fore = xu <= xu[np.argmax(rz)]                           # up to the body's maximum thickness
        for v in (ry, rz):
            v[fore] = np.maximum.accumulate(v[fore])
        k = int(0.06 * x[-1] / (xu[1] - xu[0])) | 1              # fillet length ~6 % of body length
        sm_y, sm_z = _smooth(ry, k), _smooth(rz, k)
        blend = (xu > -0.3 * Lb) & fore                          # only round the junction region
        w = np.clip((xu + 0.3 * Lb) / (0.1 * Lb), 0, 1)          # fade the smoothing in, no seam
        ry[blend] = (1 - w[blend]) * ry[blend] + w[blend] * sm_y[blend]
        rz[blend] = (1 - w[blend]) * rz[blend] + w[blend] * sm_z[blend]
        x = xu
    return x, ry, rz


def hull_manifold(spec, n_phi=96):
    x, ry, rz = hull_sections(spec)
    ry, rz = np.maximum(ry, 1e-6), np.maximum(rz, 1e-6)        # pointed ends -> tiny loops, then fan caps
    p = spec.get('p', 2.0)
    phi = np.linspace(0, 2 * np.pi, n_phi, endpoint=False)
    c, s_ = np.cos(phi), np.sin(phi)
    cy, sz = np.sign(c) * np.abs(c) ** (2 / p), np.sign(s_) * np.abs(s_) ** (2 / p)   # superellipse (p = 2: ellipse)
    Y, Z = np.outer(ry, cy), np.outer(rz, sz)
    X = np.repeat(x[:, None], n_phi, axis=1)
    return to_manifold(*grid_mesh(np.stack([X, Y, Z], -1)))


def hull_radius(spec, x0, roll):
    """Distance from the axis to the hull surface at station x0 in direction `roll`."""
    x, ry, rz = hull_sections(spec)
    a, b = np.interp(x0, x, ry), np.interp(x0, x, rz)
    p = spec.get('p', 2.0)
    return 1.0 / (np.abs(np.cos(roll) / max(a, 1e-9)) ** p + np.abs(np.sin(roll) / max(b, 1e-9)) ** p) ** (1.0 / p)


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


def fin_manifold(fin, hull_spec, roll_deg, n_span=14, fillet=0.12, n_fillet=5, n_tip=5):
    """One fin. Root: embedded in the hull and flared over `fillet` x root chord (thicker and longer sections near
    the hull, a fillet without a boolean). Tip: rounded in planform and thickness over the outer part of the span,
    so no flat, knife-edged tip face. Total span is unchanged."""
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
    hf_ = min(fillet * cr, 0.3 * span)                   # fillet height
    cap = min(0.5 * ct, 0.25 * span)                     # tip rounding length
    q = np.concatenate([np.linspace(0, 1, n_fillet) * hf_ / span,
                        np.linspace(hf_ / span, 1 - cap / span, n_span)[1:],
                        1 - cap / span + cap / span * np.sin(np.linspace(0, np.pi / 2, n_tip + 1)[1:] * 0.97)])
    stations = np.concatenate([[r_root, r_surf - 0.02 * r_surf], r_surf + span * q])
    loops = []
    for rr in stations:
        s = np.clip((rr - r_surf) / span, 0, 1)
        c = cr + (ct - cr) * s
        le = x_le + s * span * sweep
        f = np.clip(1 - (rr - r_surf) / max(hf_, 1e-9), 0, 1) ** 2        # 1 at/below the hull, 0 above the fillet
        mt, mc = 1 + 1.5 * f, 1 + 0.25 * f                                 # fillet: thicker, slightly longer
        u = np.clip((rr - r_surf - (span - cap)) / max(cap, 1e-9), 0, 1)  # 0 below the tip zone, 1 at the tip
        g = np.sqrt(np.clip(1 - u ** 2, 0.02, 1))                          # elliptic tip rounding
        cm = c * mc * g
        le = le + 0.5 * (c - cm)                                           # shrink/grow about mid-chord
        X = le + cm * xs0
        T = c * ys0 * mt * g                             # thickness direction (tangential)
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
def build(design, repair=True):
    """Fuse hull (bill included) and fins into one solid. With repair=True (default) the design first goes through
    the geometry gate (design/quality.py), which clamps parameters that give needle tips or knife edges."""
    if repair:
        import quality
        design, _ = quality.repair(design)
    body = hull_manifold(design['hull'])
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
