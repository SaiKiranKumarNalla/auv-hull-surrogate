"""Tier-1 hull families as parametric profiles r(x), plus STL export by revolution.

Every function returns (x, r) in metres with x from nose (0) to stern (L).
Families:
  myring      Myring 1976 (same formulas as the Vardhan dataset; models/physics.py)
  naca_body   NACA 4-digit symmetric thickness law used as a body of revolution (00xx)
  haack       Haack-series nose and tail (C = 0 Von Kármán, C = 1/3 LV-Haack) with a cylinder
  elliptic    elliptic nose + cylinder + parabolic tail ("Jackson-style"; approximate, check literature)
  flat_stern  Myring nose/body with the tail cut at a stern radius (blunt, high-volume vehicles)
  fish_like   Tier-3 preview: smooth fusiform profile used with an elliptic cross-section
These are sketches for the corpus design; verify each family's exact definition against its source before CFD.
"""
import numpy as np


def myring(a, b, c, d, n, theta_deg, num=200):
    th = np.radians(theta_deg)
    xn = np.linspace(0, a, num)
    rn = 0.5 * d * np.clip(1 - ((xn - a) / a) ** 2, 0, None) ** (1 / n)
    xb = np.linspace(a, a + b, num)[1:]
    s = np.linspace(0, c, num)[1:]
    rt = 0.5 * d - (3 * d / (2 * c**2) - np.tan(th) / c) * s**2 + (d / c**3 - np.tan(th) / c**2) * s**3
    return np.concatenate([xn, xb, a + b + s]), np.concatenate([rn, np.full_like(xb, d / 2), rt])


def naca_body(L, t, num=400):
    """Radius = NACA 00xx half-thickness; max diameter = t*L at 30 % of L. Closed trailing edge."""
    xi = 0.5 * (1 - np.cos(np.linspace(0, np.pi, num)))          # cosine spacing
    yt = 5 * t * (0.2969 * np.sqrt(xi) - 0.1260 * xi - 0.3516 * xi**2 + 0.2843 * xi**3 - 0.1036 * xi**4)
    return xi * L, yt * L


def _haack(xi, C):
    """Haack ogive radius (normalised to 1 at xi = 1)."""
    th = np.arccos(1 - 2 * np.clip(xi, 0, 1))
    f = lambda t: np.sqrt(np.clip(t - np.sin(2 * t) / 2 + C * np.sin(t) ** 3, 0, None))
    return f(th) / f(np.pi)


def haack(a, b, c, d, C=0.0, num=200):
    xn = np.linspace(0, a, num)
    xb = np.linspace(a, a + b, num)[1:]
    s = np.linspace(0, c, num)[1:]
    return (np.concatenate([xn, xb, a + b + s]),
            np.concatenate([d / 2 * _haack(xn / a, C), np.full_like(xb, d / 2), d / 2 * _haack(1 - s / c, C)]))


def elliptic(a, b, c, d, tail_power=2.0, num=200):
    xn = np.linspace(0, a, num)
    xb = np.linspace(a, a + b, num)[1:]
    s = np.linspace(0, c, num)[1:]
    rn = d / 2 * np.sqrt(np.clip(1 - ((a - xn) / a) ** 2, 0, None))
    rt = d / 2 * (1 - (s / c) ** tail_power)
    return np.concatenate([xn, xb, a + b + s]), np.concatenate([rn, np.full_like(xb, d / 2), rt])


def flat_stern(a, b, c, d, n, theta_deg, stern_ratio=0.5, num=200):
    """Myring profile truncated where the tail radius falls to stern_ratio * d/2 (blunt base)."""
    x, r = myring(a, b, c, d, n, theta_deg, num)
    cut = np.argmax((x > a + b) & (r <= stern_ratio * d / 2))
    return x[:cut + 1], r[:cut + 1]


def fish_like(L, t, x_max=0.35, tail=0.04, num=300):
    """Fusiform body: max thickness t*L at x_max*L, narrow caudal peduncle (radius tail*L) at the stern."""
    xi = np.linspace(0, 1, num)
    rear = np.cos(0.5 * np.pi * np.clip((xi - x_max) / (1 - x_max), 0, 1)) ** 1.5
    front = np.sin(0.5 * np.pi * np.clip(xi / x_max, 0, 1)) ** 0.6
    R, rp = t * L / 2, tail * L                    # max radius, caudal-peduncle radius
    r = np.where(xi <= x_max, R * front, rp + (R - rp) * rear)
    r[0] = 0.0
    return xi * L, r


# ---------- STL export ----------
def section_scale(phi, width=1.0, height=1.0, p=2.0):
    """Radius of a superellipse |y/w|^p + |z/h|^p = 1 in direction phi (p = 2 ellipse, p > 2 boxy, e.g. boxfish)."""
    return 1.0 / (np.abs(np.cos(phi) / width) ** p + np.abs(np.sin(phi) / height) ** p) ** (1.0 / p)


def surface(x, r, n_phi=72, width=1.0, height=1.0, p=2.0):
    """Sweep r(x) along the x axis with a superellipse cross-section (width = height = 1, p = 2: body of revolution)."""
    phi = np.linspace(0, 2 * np.pi, n_phi, endpoint=False)
    rho = section_scale(phi, width, height, p)
    Y = np.outer(r, np.cos(phi) * rho)
    Z = np.outer(r, np.sin(phi) * rho)
    X = np.repeat(x[:, None], n_phi, axis=1)
    return X, Y, Z


def write_stl(path, x, r, n_phi=72, width=1.0, height=1.0, name='hull'):
    """ASCII STL, closed: skips zero-area triangles at pointed ends and caps a blunt stern with a disc."""
    X, Y, Z = surface(x, r, n_phi, width, height)
    P = np.stack([X, Y, Z], -1)
    tris = []
    for i in range(len(x) - 1):
        for j in range(n_phi):
            k = (j + 1) % n_phi
            a, b, c, d = P[i, j], P[i + 1, j], P[i + 1, k], P[i, k]
            if r[i] > 1e-12 and r[i + 1] > 1e-12:
                tris += [(a, b, c), (a, c, d)]
            elif r[i] > 1e-12:                         # closing to a point
                tris.append((a, b, d))
            elif r[i + 1] > 1e-12:                     # opening from a point
                tris.append((a, b, c))
    for end, sign in ((0, -1), (-1, 1)):                      # cap any blunt end
        if r[end] > 1e-12:
            centre = np.array([x[end], 0.0, 0.0])
            for j in range(n_phi):
                k = (j + 1) % n_phi
                tris.append((centre, P[end, k], P[end, j]) if sign > 0 else (centre, P[end, j], P[end, k]))
    T = np.array(tris, dtype=np.float32)[:, [0, 2, 1]]            # (n, 3, 3), outward normals
    nrm = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
    nrm /= np.linalg.norm(nrm, axis=1, keepdims=True).clip(1e-30)
    rec = np.zeros(len(T), dtype=[('n', '<f4', 3), ('v', '<f4', (3, 3)), ('attr', '<u2')])
    rec['n'], rec['v'] = nrm, T
    with open(path, 'wb') as f:                                   # binary STL
        f.write(name.encode()[:80].ljust(80, b' '))
        f.write(np.uint32(len(T)).tobytes())
        f.write(rec.tobytes())
    return len(T)


def resample(x, r, num=160):
    """Cosine-spaced resampling (dense at nose and stern) to keep STL files small."""
    xs = x[0] + (x[-1] - x[0]) * 0.5 * (1 - np.cos(np.linspace(0, np.pi, num)))
    return xs, np.interp(xs, x, r)


def volume_area(x, r):
    S = 2 * np.pi * np.trapezoid(r * np.sqrt(1 + np.gradient(r, x) ** 2), x)
    return np.pi * np.trapezoid(r**2, x), S


def suboff_approx(L=4.356, d=0.508, x_fore=1.016, x_aft=3.245, x_cap=4.261, num=300):
    """APPROXIMATE DARPA SUBOFF bare hull: cited section breakpoints, placeholder curves.
    Breakpoints (bow end 1.016 m, parallel body to 3.245 m, afterbody to 4.261 m, cap to 4.356 m; D = 0.508 m) from
    Groves, Huang & Chang 1989 (DTRC/SHD-1298-01) as transcribed by secondary sources. The bow/stern curves here are
    an elliptic bow and a cubic stern taper, NOT the report's polynomials: replace with the exact equations
    (report Table/Eqs.) before any validation run."""
    R = d / 2
    xb = np.linspace(0, x_fore, num)
    rb = R * np.sqrt(np.clip(1 - ((x_fore - xb) / x_fore) ** 2, 0, None)) ** 0.75
    xm = np.linspace(x_fore, x_aft, num)[1:]
    xa = np.linspace(x_aft, x_cap, num)[1:]
    s = (xa - x_aft) / (x_cap - x_aft)
    r_cap0 = 0.1 * R
    ra = r_cap0 + (R - r_cap0) * (1 - 3 * s**2 + 2 * s**3)
    xc = np.linspace(x_cap, L, num // 3)[1:]
    rc = r_cap0 * np.sqrt(np.clip(1 - ((xc - x_cap) / (L - x_cap)) ** 2, 0, None))
    return np.concatenate([xb, xm, xa, xc]), np.concatenate([rb, np.full_like(xm, R), ra, rc])
