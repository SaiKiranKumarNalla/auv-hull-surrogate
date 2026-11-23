"""Collect forces from finished cases -> results CSV with dimensionless coefficients (knowledge/08).

    python cfd/postprocess.py runs/sample_paper
"""
import csv, glob, json, os, sys
import numpy as np


def read_forces(case):
    """Total force vector per iteration from postProcessing/forces/0/force.dat (ESI v2112+ format)."""
    f = glob.glob(os.path.join(case, 'postProcessing', 'forces', '*', 'force.dat'))
    if not f:
        return None
    rows = []
    for line in open(sorted(f)[-1]):
        if line.startswith('#') or not line.strip():
            continue
        nums = [float(v) for v in line.replace('(', ' ').replace(')', ' ').split()]
        rows.append(nums)
    A = np.array(rows)
    # columns: iter, total(x y z), pressure(x y z), viscous(x y z)
    return A


def ittc(Re):
    return 0.075 / (np.log10(Re) - 2) ** 2


def summarise(case):
    meta = json.load(open(os.path.join(case, 'case.json')))
    A = read_forces(case)
    out = dict(name=meta['name'], L=meta['L'], Re=meta['Re'], S_wet=meta['S_wet'], volume=meta['volume'],
               status='no forces')
    if A is None or len(A) < 50:
        return out
    c = meta['condition']
    q = 0.5 * c['rho'] * c['U'] ** 2
    last = A[-50:]
    D, Dp, Dv = last[:, 1].mean(), last[:, 4].mean(), last[:, 7].mean()
    Lift = last[:, 3].mean()
    out.update(status='ok', iters=int(A[-1, 0]), drag_N=D, pressure_N=Dp, viscous_N=Dv, lift_N=Lift,
               drag_rel_std_last50=float(last[:, 1].std() / abs(D)),
               CD_S=D / (q * meta['S_wet']), CD_V=D / (q * meta['volume'] ** (2 / 3)),
               CF_ITTC=ittc(meta['Re']), pressure_frac=Dp / D)
    out['form_factor'] = out['CD_S'] / out['CF_ITTC']
    return out


if __name__ == '__main__':
    root = sys.argv[1] if len(sys.argv) > 1 else 'runs/sample_paper'
    rows = [summarise(c) for c in sorted(glob.glob(os.path.join(root, '*/'))) if os.path.exists(os.path.join(c, 'case.json'))]
    keys = sorted({k for r in rows for k in r}, key=lambda k: list(rows[0]).index(k) if k in rows[0] else 99)
    with open(os.path.join(root, 'results.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(rows)
    for r in rows:
        if r['status'] == 'ok':
            print(f"{r['name']:22s} Re {r['Re']:.2e}  D {r['drag_N']:7.3f} N  C_D,S {r['CD_S']:.5f}  "
                  f"1+k {r['form_factor']:.2f}  pressure {100 * r['pressure_frac']:4.1f} %  conv {100 * r['drag_rel_std_last50']:.2f} %")
        else:
            print(f"{r['name']:22s} {r['status']}")
