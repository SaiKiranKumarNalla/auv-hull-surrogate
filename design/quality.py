"""Geometry quality gate: every design passes here before it is meshed.

Two steps:
  repair(design) -> (design, log)   clamp parameters that produce needle tips, knife edges or fragile lobes;
                                    every change is logged, nothing is silent.
  check(design)  -> report dict     build the solid and measure it; report['ok'] is False if any hard rule fails.

Hard rules (a failing design is never meshed):
  watertight closed manifold, one connected solid, genus 0 (no holes or trapped voids), positive volume,
  fin tip thickness >= T_MIN_ABS, smooth body profile (no collar / step where parts meet).
Soft metrics (logged for the corpus database): sharp-edge fraction, smallest triangle edge, fin aspect ratios.

    python design/quality.py        -> runs the gate on the 20 reference designs, writes design/quality/report.csv
"""
import copy, csv, os, sys
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))

TIP_RATIO_MIN = 0.35      # tip chord >= 0.35 x root chord (no needle tips)
T_MIN_ABS = 0.002         # m, thinnest fin section anywhere (tip), at the 1-2 m vehicle scale
FIN_T_MIN = 0.06          # minimum NACA thickness ratio
AR_LOBE_MAX = 4.5         # span / mean chord of one fin or caudal lobe
SLOPE_JUMP_MAX = 12.0     # degrees: worst concave corner allowed on the body outline (collar detector)


def repair(design):
    d, log = copy.deepcopy(design), []
    for fin in d.get('fins', []):
        n, cr = fin['name'], fin['root_chord']
        if fin.get('thickness', 0.12) < FIN_T_MIN:
            log.append(f'{n}: thickness {fin["thickness"]:.3f} -> {FIN_T_MIN}'); fin['thickness'] = FIN_T_MIN
        ct_min = max(TIP_RATIO_MIN * cr, T_MIN_ABS / fin['thickness'])
        if fin['tip_chord'] < ct_min:
            log.append(f'{n}: tip chord {fin["tip_chord"]:.3f} -> {ct_min:.3f} m'); fin['tip_chord'] = ct_min
        ar = fin['span'] / (0.5 * (cr + fin['tip_chord']))
        if ar > AR_LOBE_MAX:
            s_new = AR_LOBE_MAX * 0.5 * (cr + fin['tip_chord'])
            log.append(f'{n}: span {fin["span"]:.3f} -> {s_new:.3f} m (aspect ratio {ar:.1f} > {AR_LOBE_MAX})')
            fin['span'] = s_new
    return d, log


def _profile_slope_jump(hull):
    """Worst concave corner of the body outline, in degrees: the slope suddenly *increasing* between two stations,
    which is what a collar, step or badly merged part looks like. Convex turns (blunt noses) are legitimate and
    ignored. A waist ahead of the maximum thickness (radius shrinking then growing again) is added as a corner."""
    import appendages as ap
    x, ry, rz = ap.hull_sections(hull)
    worst = 0.0
    for r in (ry, rz):
        th = np.degrees(np.arctan2(np.diff(r), np.diff(x)))
        worst = max(worst, float(np.max(np.diff(th), initial=0.0)))
        fore = r[: int(np.argmax(r)) + 1]
        if fore.size > 2:
            dip = np.max(np.maximum.accumulate(fore) - fore) / r.max()
            if dip > 0.01:
                worst = max(worst, 90.0)
    return worst


def _mesh_metrics(man):
    m = man.to_mesh()
    V = np.asarray(m.vert_properties)[:, :3]; F = np.asarray(m.tri_verts)
    T = V[F]
    n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); n /= np.linalg.norm(n, axis=1, keepdims=True).clip(1e-30)
    edges = np.sort(np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]]), axis=1)
    face = np.repeat(np.arange(len(F))[None], 3, 0).ravel()
    order = np.lexsort((edges[:, 1], edges[:, 0])); e, f = edges[order], face[order]
    same = np.all(e[1:] == e[:-1], axis=1)
    ang = np.degrees(np.arccos(np.clip(np.einsum('ij,ij->i', n[f[:-1][same]], n[f[1:][same]]), -1, 1)))
    elen = np.linalg.norm(V[e[:, 0]] - V[e[:, 1]], axis=1)
    return dict(sharp_edge_pct=float(100 * (ang > 60).mean()), min_edge_mm=float(1e3 * elen.min()),
                n_triangles=int(len(F)))


def check(design, repair_first=True):
    import appendages as ap
    log = []
    if repair_first:
        design, log = repair(design)
    rep = dict(repairs=log, failures=[])
    try:
        man = ap.build(design, repair=False)
    except Exception as exc:                             # a part that is not a closed manifold
        rep['failures'].append(f'build failed: {exc}'); rep['ok'] = False
        return rep
    parts = len(man.decompose())
    rep.update(volume_L=1e3 * man.volume(), area_m2=man.surface_area(), genus=man.genus(), parts=parts,
               slope_jump=_profile_slope_jump(design['hull']), **_mesh_metrics(man))
    tips = [f['thickness'] * f['tip_chord'] for f in design.get('fins', [])]
    rep['min_tip_mm'] = 1e3 * min(tips) if tips else float('nan')
    if man.status() != ap.m3d.Error.NoError: rep['failures'].append('not a closed manifold')
    if parts != 1: rep['failures'].append(f'{parts} separate solids')
    if man.genus() != 0: rep['failures'].append(f'genus {man.genus()} (hole or trapped void)')
    if man.volume() <= 0: rep['failures'].append('non-positive volume')
    if tips and min(tips) < T_MIN_ABS * 0.999: rep['failures'].append(f'fin tip {rep["min_tip_mm"]:.2f} mm thick')
    if rep['slope_jump'] > SLOPE_JUMP_MAX: rep['failures'].append(f'concave corner {rep["slope_jump"]:.0f} deg (collar/step)')
    rep['ok'] = not rep['failures']
    return rep


if __name__ == '__main__':
    from registry import REFERENCES
    out = os.path.join(os.path.dirname(__file__), 'quality'); os.makedirs(out, exist_ok=True)
    rows = []
    for name, d in REFERENCES.items():
        r = check(d)
        rows.append(dict(design=name, ok=r['ok'], failures='; '.join(r['failures']), repairs='; '.join(r['repairs']),
                         **{k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()
                            if k not in ('ok', 'failures', 'repairs')}))
        print(f'{name:22s} {"PASS" if r["ok"] else "FAIL"}  repairs {len(r["repairs"])}  '
              f'kink {r.get("slope_jump", float("nan")):.3f}  tip {r.get("min_tip_mm", float("nan")):.1f} mm  '
              f'{"; ".join(r["failures"])}')
    keys = sorted({k for r in rows for k in r}, key=lambda k: list(rows[0]).index(k) if k in rows[0] else 99)
    with open(os.path.join(out, 'report.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(rows)
    print(f'{sum(r["ok"] for r in rows)}/{len(rows)} pass')
