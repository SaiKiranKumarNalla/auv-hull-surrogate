"""Random parametric designs for the corpus: Tier-1 hull family + optional fins / flaps / fish fins.

Every parameter has an explicit range below (edit them here, nowhere else). `sample(rng)` returns a JSON-able design
dict that `appendages.build` turns into one watertight solid. Ranges are first guesses for a REMUS-class vehicle
and must be reviewed before the CFD campaign (fin sizes vs literature, deflection limits).
"""
import numpy as np

RANGES = {
    'L': (1.0, 2.0), 'D': (0.10, 0.25),                       # metres
    'nose_frac': (0.08, 0.30), 'tail_frac': (0.15, 0.35),
    'myring_n': (1.0, 5.0), 'myring_theta': (5, 45),
    'haack_C': (0.0, 1 / 3), 'stern_ratio': (0.3, 0.6),
    'fin_span_D': (0.3, 1.2), 'fin_root_D': (0.3, 0.8), 'taper': (0.4, 1.0),
    'sweep': (0, 45), 'fin_t': (0.08, 0.18),
    'deflection': (-15, 15), 'flap_frac': (0.2, 0.4), 'flap': (-25, 25),
}
FIN_LAYOUTS = {'none': [], 'cruciform': [0, 90, 180, 270], 'x_tail': [45, 135, 225, 315], 'rudder_only': [90, 270]}


def u(rng, key):
    lo, hi = RANGES[key]
    return float(rng.uniform(lo, hi))


def sample_hull(rng, family):
    L, D = u(rng, 'L'), u(rng, 'D')
    a, c = u(rng, 'nose_frac') * L, u(rng, 'tail_frac') * L
    b = L - a - c
    if family == 'myring':
        return {'family': 'myring', 'params': dict(a=a, b=b, c=c, d=D, n=u(rng, 'myring_n'), theta_deg=u(rng, 'myring_theta'))}
    if family == 'haack':
        return {'family': 'haack', 'params': dict(a=a, b=b, c=c, d=D, C=u(rng, 'haack_C'))}
    if family == 'elliptic':
        return {'family': 'elliptic', 'params': dict(a=a, b=b, c=c, d=D, tail_power=float(rng.uniform(1.5, 3.0)))}
    if family == 'naca_body':
        return {'family': 'naca_body', 'params': dict(L=L, t=D / L)}
    if family == 'flat_stern':
        return {'family': 'flat_stern', 'params': dict(a=a, b=b, c=c, d=D, n=u(rng, 'myring_n'),
                                                       theta_deg=u(rng, 'myring_theta'), stern_ratio=u(rng, 'stern_ratio'))}
    raise ValueError(family)


def hull_length(h):
    p = h['params']
    return p['L'] if 'L' in p else p['a'] + p['b'] + p['c']


def sample(rng, families=('myring', 'haack', 'elliptic', 'naca_body', 'flat_stern'), layouts=tuple(FIN_LAYOUTS)):
    hull = sample_hull(rng, str(rng.choice(families)))
    layout = str(rng.choice(layouts))
    L = hull_length(hull)
    D = hull['params'].get('d', hull['params'].get('t', 0) * L)
    fins = []
    if FIN_LAYOUTS[layout]:
        cr = u(rng, 'fin_root_D') * D
        flap_f = u(rng, 'flap_frac') if rng.random() < 0.5 else 0.0
        fins.append(dict(name=layout, rolls_deg=FIN_LAYOUTS[layout], x_le=float(L * rng.uniform(0.74, 0.86)),
                         root_chord=cr, tip_chord=cr * u(rng, 'taper'), span=u(rng, 'fin_span_D') * D,
                         sweep_deg=u(rng, 'sweep'), thickness=u(rng, 'fin_t'),
                         deflection_deg=u(rng, 'deflection') if not flap_f else 0.0,
                         flap_fraction=flap_f, flap_deg=u(rng, 'flap') if flap_f else 0.0))
    return {'hull': hull, 'fins': fins, 'meta': {'layout': layout}}


if __name__ == '__main__':
    import os, sys, json, time
    sys.path.insert(0, os.path.dirname(__file__))
    import appendages as ap
    rng = np.random.default_rng(0)
    t0, ok = time.time(), 0
    for i in range(200):
        d = sample(rng)
        man = ap.build(d)
        ok += man.genus() == 0 and man.volume() > 0
    print(f'{ok}/200 random designs built as single watertight solids in {time.time() - t0:.1f} s')
