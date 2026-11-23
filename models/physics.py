"""Myring hull geometry and the analytic drag baseline (M0).
Lengths in mm in the dataset; converted to metres for physics.
Formulas follow knowledge/02-dataset.md (their CAD script) and standard ITTC-1957 / Hoerner."""
import numpy as np

RHO = 1027.0              # kg/m^3, from their forceCoeffs
U = 2.0                   # m/s, inlet velocity of every case
NU = 1.736124635e-6       # m^2/s, their transportProperties


def radius_profile(a, b, c, d, n, theta_deg, num=400):
    """Return x (m) and r(x) (m) along the hull: nose, cylinder, tail."""
    a, b, c, d = (v / 1000.0 for v in (a, b, c, d))      # mm -> m
    th = np.radians(theta_deg)
    xn = np.linspace(0, a, num)
    rn = 0.5 * d * np.clip(1 - ((xn - a) / a) ** 2, 0, None) ** (1 / n)
    xb = np.linspace(a, a + b, num)
    rb = np.full_like(xb, 0.5 * d)
    s = np.linspace(0, c, num)
    rt = 0.5 * d - (3 * d / (2 * c**2) - np.tan(th) / c) * s**2 + (d / c**3 - np.tan(th) / c**2) * s**3
    return np.concatenate([xn, xb[1:], a + b + s[1:]]), np.concatenate([rn, rb[1:], rt[1:]])


def wetted_area_and_volume(a, b, c, d, n, theta_deg):
    x, r = radius_profile(a, b, c, d, n, theta_deg)
    r = np.clip(r, 0, None)
    drdx = np.gradient(r, x)
    S = 2 * np.pi * np.trapezoid(r * np.sqrt(1 + drdx**2), x)
    V = np.pi * np.trapezoid(r**2, x)
    return S, V


def drag_m0(a, b, c, d, n, theta_deg):
    """Analytic drag (N): ITTC-1957 friction x Hoerner form factor x wetted area."""
    L = (a + b + c) / 1000.0
    S, _ = wetted_area_and_volume(a, b, c, d, n, theta_deg)
    Re = U * L / NU
    cf = 0.075 / (np.log10(Re) - 2) ** 2
    dl = (d / 1000.0) / L
    form = 1 + 1.5 * dl**1.5 + 7 * dl**3
    return 0.5 * RHO * U**2 * S * cf * form