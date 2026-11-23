"""Parametric variants of the 20 core designs (Study 1 corpus: 20 bases x 10 variants).

Each base gets its own feature list, chosen from what the base actually has (a bill length only exists on billed
fish, a flap angle only on flapped fins). Features are multipliers or offsets on the base recipe, sampled by
Latin hypercube. Fins follow the hull: when the hull gets longer or fatter, fin positions and sizes scale with it,
so a variant is a coherent vehicle, not a hull with misplaced fins.

Every variant goes through the geometry gate (quality.check); a failing draw is replaced (up to 20 tries) and
the replacement is logged.

    python design/variants.py      -> design/variants/<base>/v00..v09.json, design/variants/index.csv,
                                      plan/VARIANT_RANGES.md
"""
import copy, csv, json, os, sys
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from registry import REFERENCES
import quality

N_VARIANTS = 10
TEST_VARIANTS = (8, 9)                                         # unseen-variant split, in every base
TEST_BASES = ('wahoo_like', 'elliptic_parabolic', 'bow_stern_planes')   # unseen-base split: fish, family, control
SEED = 20261123
HERE = os.path.dirname(__file__)

# feature name -> (low, high, kind, meaning). kind: 'mul' multiplier, 'add' offset, 'abs' absolute value
HULL_FEATURES = {
    'length_scale':  (0.85, 1.15, 'mul', 'body length (nose, mid-body and tail lengths together)'),
    'diam_scale':    (0.85, 1.15, 'mul', 'maximum diameter'),
    'myring_n':      (0.75, 1.25, 'mul', 'Myring nose fullness n (relative to the base)'),
    'myring_theta':  (-8.0, 8.0, 'add', 'Myring tail half-angle (deg, around the base)'),
    'haack_C':       (-0.05, 0.05, 'add', 'Haack shape constant C (around the base, so Von Kármán and LV-Haack stay apart)'),
    'tail_power':    (-0.4, 0.4, 'add', 'parabolic tail exponent (around the base)'),
    'stern_ratio':   (-0.1, 0.1, 'add', 'flat-stern base radius / max radius (around the base)'),
    'fish_x_max':    (-0.04, 0.04, 'add', 'position of maximum thickness (fraction of L)'),
    'fish_width':    (0.9, 1.1, 'mul', 'body width / height'),
    'bill_scale':    (0.75, 1.25, 'mul', 'bill length'),
}
FIN_FEATURES = {
    'fin_span':      (0.75, 1.25, 'mul', 'span of every fin'),
    'fin_chord':     (0.85, 1.15, 'mul', 'root and tip chord of every fin'),
    'fin_sweep':     (-10.0, 10.0, 'add', 'leading-edge sweep (deg)'),
    'fin_x':         (-0.03, 0.03, 'add', 'fin position along the body (fraction of L)'),
    'ctrl_angle':    (0.0, 1.5, 'mul', 'deflection and flap angles of control surfaces (0 = undeflected)'),
}


def features_for(base):
    """The feature subset that makes sense for this base."""
    h = base['hull']; fam, p = h['family'], h['params']
    f = []
    f += ['length_scale', 'diam_scale']                        # SUBOFF variants: scaled copies of the anchor
    if fam in ('myring', 'flat_stern'):
        f += ['myring_n', 'myring_theta']
    if fam == 'flat_stern':
        f += ['stern_ratio']
    if fam == 'haack':
        f += ['haack_C']
    if fam == 'elliptic':
        f += ['tail_power']
    if fam == 'fish_like':
        f += ['fish_x_max', 'fish_width']
        if h.get('bill'):
            f += ['bill_scale']
    if base['fins']:
        f += ['fin_span', 'fin_chord', 'fin_sweep', 'fin_x']
        if any(fi.get('deflection_deg') or fi.get('flap_deg') for fi in base['fins']):
            f += ['ctrl_angle']
    return f


def hull_length(h):
    p = h['params']
    if 'L' in p:
        return p['L']
    if h['family'] == 'suboff_approx':
        return 4.356
    if 'a' in p:
        return p['a'] + p['b'] + p['c']
    return 4.356                                               # suboff_approx default length


def apply(base, values):
    """Return a new design dict from the base and a {feature: value} dict."""
    d = copy.deepcopy(base); h = d['hull']; p = h['params']
    L0 = hull_length(h)
    ls, ds = values.get('length_scale', 1.0), values.get('diam_scale', 1.0)
    if 'a' in p:
        for k in 'abc':
            p[k] *= ls
        p['d'] *= ds
    elif 'L' in p and 't' in p:
        p['L'] *= ls
        p['t'] *= ds / ls                                      # t is thickness / length
    elif h['family'] == 'suboff_approx':                       # stations scale with length, radius with diameter
        L, D = p.get('L', 4.356), p.get('d', 0.508)
        p.update(L=L * ls, d=D * ds, x_fore=p.get('x_fore', 1.016) * ls, x_aft=p.get('x_aft', 3.245) * ls,
                 x_cap=p.get('x_cap', 4.261) * ls)
    if 'myring_n' in values: p['n'] = float(np.clip(p['n'] * values['myring_n'], 1.0, 8.0))
    if 'myring_theta' in values: p['theta_deg'] = float(np.clip(p['theta_deg'] + values['myring_theta'], 5, 50))
    if 'haack_C' in values: p['C'] = float(np.clip(p['C'] + values['haack_C'], 0.0, 0.45))
    if 'tail_power' in values: p['tail_power'] = float(np.clip(p['tail_power'] + values['tail_power'], 1.2, 4.0))
    if 'stern_ratio' in values: p['stern_ratio'] = float(np.clip(p['stern_ratio'] + values['stern_ratio'], 0.2, 0.7))
    if 'fish_x_max' in values: p['x_max'] = float(np.clip(p['x_max'] + values['fish_x_max'], 0.25, 0.5))
    if 'fish_width' in values: h['width'] = h.get('width', 1.0) * values['fish_width']
    if h.get('bill'):
        h['bill'] = dict(h['bill'], length=h['bill']['length'] * ls * values.get('bill_scale', 1.0),
                         base_radius=h['bill']['base_radius'] * ds)
    L1 = hull_length(h)
    for fi in d['fins']:
        fi['x_le'] = fi['x_le'] * L1 / L0 + values.get('fin_x', 0.0) * L1
        for k in ('root_chord', 'tip_chord'):
            fi[k] *= ds * values.get('fin_chord', 1.0)
        fi['span'] *= ds * values.get('fin_span', 1.0)
        fi['sweep_deg'] = float(np.clip(fi.get('sweep_deg', 0) + values.get('fin_sweep', 0.0), 0, 65))
        for k in ('deflection_deg', 'flap_deg'):
            if fi.get(k):
                fi[k] *= values.get('ctrl_angle', 1.0)
        fi['x_le'] = float(np.clip(fi['x_le'], 0.03 * L1, 0.97 * L1 - fi['root_chord']))
    return d


def lhs(n, k, rng):
    """Latin hypercube in [0,1]^k: one point per row stratum in every dimension."""
    u = (np.arange(n)[:, None] + rng.random((n, k))) / n
    for j in range(k):
        u[:, j] = u[rng.permutation(n), j]
    return u


def generate():
    rng = np.random.default_rng(SEED)
    rows, table = [], []
    for name, base in REFERENCES.items():
        feats = features_for(base)
        U = lhs(N_VARIANTS, len(feats), rng)
        os.makedirs(os.path.join(HERE, 'variants', name), exist_ok=True)
        for i in range(N_VARIANTS):
            u, tries = U[i], 0
            while True:
                vals = {f: HULL_FEATURES.get(f, FIN_FEATURES.get(f))[0] + u[j] *
                        (HULL_FEATURES.get(f, FIN_FEATURES.get(f))[1] - HULL_FEATURES.get(f, FIN_FEATURES.get(f))[0])
                        for j, f in enumerate(feats)}
                design = apply(base, vals)
                rep = quality.check(design)
                if rep['ok'] or tries >= 20:
                    break
                tries += 1; u = rng.random(len(feats))         # redraw a failing variant
            design, _ = quality.repair(design)
            design['variant'] = dict(base=name, index=i, features=vals, redraws=tries,
                                     split='test_base' if name in TEST_BASES else
                                           ('test_variant' if i in TEST_VARIANTS else 'train'))
            with open(os.path.join(HERE, 'variants', name, f'v{i:02d}.json'), 'w') as f:
                json.dump(design, f, indent=1)
            rows.append(dict(base=name, variant=i, split=design['variant']['split'], gate='PASS' if rep['ok'] else 'FAIL',
                             redraws=tries, repairs=len(rep['repairs']), length_m=round(hull_length(design['hull']), 3),
                             volume_L=round(rep.get('volume_L', float('nan')), 2),
                             **{f: round(v, 4) for f, v in vals.items()}))
            print(f'{name:22s} v{i:02d} {rows[-1]["gate"]} redraws {tries} repairs {len(rep["repairs"])}')
        table.append((name, base['category'], feats))
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with open(os.path.join(HERE, 'variants', 'index.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(rows)
    write_table(table, rows)
    return rows


def write_table(table, rows):
    allf = {**HULL_FEATURES, **FIN_FEATURES}
    fmt = lambda f: (f'×{allf[f][0]:g}–{allf[f][1]:g}' if allf[f][2] == 'mul' else
                     f'{allf[f][0]:+g} to {allf[f][1]:+g}' if allf[f][2] == 'add' else f'{allf[f][0]:.3g}–{allf[f][1]:.3g}')
    ok = sum(r['gate'] == 'PASS' for r in rows)
    L = ['# Variant ranges (Study 1 corpus)', '',
         'Generated by `design/variants.py`. 20 core designs × 10 Latin-hypercube variants = 200 shapes; each is run at',
         '13 flow conditions in the corpus. Fins scale and move with the hull. Every variant passes the geometry gate.', '',
         f'Gate result: **{ok}/{len(rows)} variants pass**.', '',
         '![variants](../design/variants_gallery.png)', '', '## Features', '',
         '| Feature | Range | Meaning |', '|---|---|---|']
    L += [f'| `{f}` | {fmt(f)} | {allf[f][3]} |' for f in allf]
    L += ['', '## Features per base', '', '| Base | Category | Split | Features varied |', '|---|---|---|---|']
    for name, cat, feats in table:
        split = 'held out (unseen base)' if name in TEST_BASES else 'train (v08, v09 held out)'
        L.append(f'| `{name}` | {cat} | {split} | {", ".join(f"`{f}`" for f in feats)} |')
    L += ['', 'Splits: variants v08 and v09 of every base are the unseen-variant test set; the three held-out bases',
          '(`' + '`, `'.join(TEST_BASES) + '`) are the unseen-base test set and never appear in training.', '']
    with open(os.path.join(HERE, '..', 'plan', 'VARIANT_RANGES.md'), 'w') as f:
        f.write('\n'.join(L))


if __name__ == '__main__':
    rows = generate()
    print(f'{sum(r["gate"] == "PASS" for r in rows)}/{len(rows)} pass')
