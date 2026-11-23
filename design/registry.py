"""Single source of truth for every design and flow parameter, and the 20 reference designs.

Every number carries a SOURCE key and a STATUS:
  verified      checked here against a primary source or the paper's own data/files
  cited         taken from a published source, read via a secondary summary; primary not yet checked
  unverified    recalled from a known source but not yet checked against it (must be checked before CFD)
  assumption    our choice; `note` says why and what motivates it
`python design/registry.py` checks that every entry has a valid source and status and that all 20 references build
into single watertight solids. Literature notes: knowledge/07-design-references.md.
"""
import numpy as np

STATUSES = ('verified', 'cited', 'unverified', 'assumption')

SOURCES = {
    'vardhan2023': 'Vardhan et al. 2023, arXiv 2304.12420 (Table 1 design space; dataset files in reference/)',
    'vardhan_data': 'Vardhan dataset, 3,021 hulls (min/max computed from train_2400.txt + test_data.txt)',
    'vardhan_case': 'Vardhan OpenFOAM template case swordfish1 (problem_def.json, transportProperties)',
    'myring1976': 'Myring 1976, "A theoretical study of body drag in subcritical axisymmetric flow", Aeronaut. Q. 27(3)',
    'prestero2001': 'Prestero 2001, MIT SM thesis, REMUS 6-DOF model (dspace.mit.edu/handle/1721.1/65068), Table 2.1',
    'groves1989': 'Groves, Huang & Chang 1989, DTRC/SHD-1298-01 (DTIC ADA210642), DARPA SUBOFF geometry',
    'suboff_secondary': 'SUBOFF breakpoints in ft (3.333/10.646/13.979/14.292) via secondary reconstructions of groves1989',
    'jmse2026_review': 'AUV hull design review, J. Mar. Sci. Eng. 2026, doi 10.3390/jmse14201883 (Myring/DREA/Haack families)',
    'jmse2026_flatstern': 'Compact AUV with Myring forebody and flat stern, JMSE 2026, doi 10.3390/jmse14161456 (nose n 1-3)',
    'naca_tr824': 'Abbott, von Doenhoff & Stivers 1945, NACA TR-824 (4-digit thickness law)',
    'haack_series': 'Haack/Sears-Haack minimum-drag body series (standard nose-cone definitions)',
    'vanwassenbergh2015': 'Van Wassenbergh et al. 2015, boxfish carapace CFD, J. R. Soc. Interface (PMC4305415)',
    'fish_fineness': 'Tuna/scombrid fineness ratios ~4.5 (Thunnus) to 8.4 (Acanthocybium), Magnuson 1978 via secondary summary',
    'caudal_ar': 'Caudal-fin aspect ratio: anguilliform 0-1.61, thunniform 5.5-7.9 (Coastal Carolina Univ. thesis, digitalcommons.coastal.edu etd 1188)',
    'manta_uuv': 'Manta-ray UUV CFD: 1 m span, pectoral-fin aspect ratio 2.5 (Bardera Mora et al. 2023, MARINE conf.)',
    'teos10': 'IOC/SCOR/IAPSO 2010, TEOS-10 manual: seawater properties valid for these T, S ranges',
    'ittc_water': 'ITTC Recommended Procedure 7.5-02-01-03, fresh and seawater density and viscosity',
    'knowledge03': 'knowledge/03-flow-conditions.md (project notes, motivated by REMUS-class operations)',
    'sagong2013': 'Sagong et al. 2013, sailfish and swordfish hydrodynamics in gliding posture, PLOS ONE 8(12) e81323 (PMC3846759): '
                  'C_D (wetted area) 0.0075 sailfish, 0.009 swordfish; bills ~17 % (sailfish) to 44 % (swordfish) of total length; '
                  'swordfish pectoral fins ~15 % of wetted area but +51 % drag; FR of marlins/swordfish near drag-optimal',
}


def P(value, unit, source, status, note=''):
    assert status in STATUSES and source in SOURCES, (source, status)
    return dict(value=value, unit=unit, source=source, status=status, note=note)


# ---------- global parameter ranges (used by the sampler and perturbations) ----------
PARAMETERS = {
    # Myring design space of the paper's dataset (mm in the data, metres here)
    'myring.a': P((0.050, 0.600), 'm', 'vardhan_data', 'verified', 'nose length; data min/max 53-597 mm'),
    'myring.c': P((0.050, 0.600), 'm', 'vardhan_data', 'verified', 'tail length; data min/max 53-592 mm'),
    'myring.d': P((0.050, 0.200), 'm', 'vardhan_data', 'verified', 'max diameter; data 50-200 mm'),
    'myring.L': P((1.0, 2.0), 'm', 'vardhan_data', 'verified', 'total length a+b+c; data 1001-2000 mm'),
    'myring.n': P((1.0, 5.0), '-', 'vardhan_data', 'verified', 'nose exponent; stored n is the real exponent'),
    'myring.theta': P((1.0, 50.0), 'deg', 'vardhan_data', 'verified', 'tail semi-angle'),
    'fineness': P((5.1, 38.9), '-', 'vardhan_data', 'verified', 'L/d covered by the existing data'),
    'haack.C': P((0.0, 1 / 3), '-', 'haack_series', 'cited', '0 = Von Kármán, 1/3 = LV-Haack'),
    'flat_stern.ratio': P((0.3, 0.6), '-', 'jmse2026_flatstern', 'assumption', 'stern/max radius; flat-stern study motivates, values ours'),
    # perturbation around each reference
    'perturb.geometry': P(0.15, 'fraction', 'knowledge03', 'assumption', '+-15 % on each length; wide enough that same-family references overlap'),
    # appendages
    'fin.thickness': P((0.08, 0.20), 't/c', 'naca_tr824', 'assumption', 'NACA 0008-0020; 0012 (REMUS, unverified) and 0020 (SUBOFF, unverified) inside'),
    'fin.sweep': P((0.0, 50.0), 'deg', 'knowledge03', 'assumption', 'leading-edge sweep'),
    'fin.deflection': P((-25.0, 25.0), 'deg', 'knowledge03', 'assumption', 'control limits; REMUS about +-13.6 deg (prestero2001, unverified)'),
    'fin.flap_fraction': P((0.2, 0.4), 'chord', 'knowledge03', 'assumption', 'trailing-edge flap chord fraction'),
    # flow and environment
    'flow.U': P((0.5, 3.0), 'm/s', 'knowledge03', 'assumption', 'survey to transit speeds; paper fixed 2.0 m/s (vardhan_case, verified)'),
    'flow.aoa': P((0.0, 15.0), 'deg', 'knowledge03', 'assumption', 'manoeuvring angles of attack / sideslip'),
    'water.T': P((0.0, 30.0), 'degC', 'teos10', 'cited', 'polar to tropical'),
    'water.S': P((0.0, 40.0), 'g/kg', 'teos10', 'cited', 'fresh to open ocean'),
    'water.rho_nu': P('from T,S', '-', 'ittc_water', 'cited', 'rho and nu computed from T and S tables; paper: rho 1027, nu 1.736e-6 (vardhan_case, verified)'),
    'wall.ks': P((0.0, 1.0e-3), 'm', 'knowledge03', 'assumption', 'equivalent sand roughness: clean to fouled hull'),
    'inflow.Tu': P((0.001, 0.10), '-', 'knowledge03', 'assumption', 'turbulence intensity: open ocean to tidal channel'),
    # depth: enters only through T and S (incompressible flow; uniform pressure does not change drag)
    'depth': P((0.0, 300.0), 'm', 'knowledge03', 'assumption', 'mapped to T,S profile; cavitation check only'),
}


def fin(name, rolls, x_le, cr, ct, span, sweep, t, src, status, defl=0.0, flap_f=0.0, flap=0.0, note=''):
    return dict(name=name, rolls_deg=rolls, x_le=x_le, root_chord=cr, tip_chord=ct, span=span, sweep_deg=sweep,
                thickness=t, deflection_deg=defl, flap_fraction=flap_f, flap_deg=flap,
                provenance=dict(source=src, status=status, note=note))


def ref(category, hull, fins, src, status, note):
    assert status in STATUSES and src in SOURCES
    return dict(category=category, hull=hull, fins=fins, provenance=dict(source=src, status=status, note=note))


def tail_fins(hull, rolls=(0, 90, 180, 270), name='tail', flap_f=0.0, flap=0.0):
    """Default control fins sized from the hull (ASSUMPTION: span 0.45 D, root chord 0.5 D, tip chord 0.35 D, at 35 %
    into the tail) - REMUS-class proportions, to be replaced by cited ratios once Prestero's fin data are read."""
    p = hull['params']
    if 'a' in p:
        D, x_le = p['d'], p['a'] + p['b'] + 0.35 * p['c']
    else:
        D, x_le = p['t'] * p['L'], 0.78 * p['L']
    return [fin(name, list(rolls), x_le, 0.5 * D, 0.35 * D, 0.45 * D, 20, 0.12, 'knowledge03', 'assumption',
                flap_f=flap_f, flap=flap, note='default control fins sized from D')]


BARE_ALLOWED = {'suboff_bare': 'SUBOFF bare hull has published experiments (validation anchor)',
                'vardhan_swordfish1': 'the paper dataset is finless (replication link)'}

REMUS_HULL = {'family': 'myring', 'params': dict(a=0.191, b=0.654, c=0.541, d=0.191, n=2.0, theta_deg=25.0)}
SUBOFF_HULL = {'family': 'suboff_approx', 'params': {}}
REMUS_FINS = fin('remus_tail', [0, 90, 180, 270], 1.17, 0.065, 0.045, 0.070, 10, 0.12, 'prestero2001', 'unverified',
                 note='NACA 0012 cruciform; planform values to be checked in Prestero Table/appendix')

REFERENCES = {
    # --- real vehicles (validation anchors) ---
    'remus100_finned': ref('vehicle', REMUS_HULL, [REMUS_FINS], 'prestero2001', 'unverified', 'hull + cruciform tail'),
    'suboff_bare': ref('vehicle', SUBOFF_HULL, [], 'suboff_secondary', 'cited',
                       'L 4.356 m, D 0.508 m and section breakpoints cited; bow/stern curves APPROXIMATE until groves1989 is read'),
    'suboff_appended': ref('vehicle', SUBOFF_HULL,
                           [fin('suboff_stern', [0, 90, 180, 270], 3.98, 0.23, 0.23, 0.22, 0, 0.20, 'groves1989', 'assumption',
                                note='4 stern appendages; sizes are placeholders until the report is read')],
                           'groves1989', 'assumption', 'appendage geometry placeholder; sail not yet modelled'),
    'vardhan_swordfish1': ref('dataset', {'family': 'myring', 'params': dict(a=0.20, b=0.68, c=0.227, d=0.052, n=2.0, theta_deg=20)},
                              [], 'vardhan_case', 'verified',
                              'L 1.107 m, d 0.052 m verified from the paper case (problem_def lref, bounding box); a/b/c/n/theta '
                              'are our fit (assumption) - the STL itself is the ground truth'),
    # --- Myring corners of the paper's design space ---
    'myring_blunt_n5': ref('myring', {'family': 'myring', 'params': dict(a=0.12, b=0.90, c=0.31, d=0.191, n=5.0, theta_deg=30)},
                           tail_fins({'family': 'myring', 'params': dict(a=0.12, b=0.90, c=0.31, d=0.191, n=5.0, theta_deg=30)}), 'vardhan_data', 'verified', 'n at the top of the data range'),
    'myring_slender_ld15': ref('myring', {'family': 'myring', 'params': dict(a=0.25, b=1.25, c=0.40, d=0.127, n=2.0, theta_deg=15)},
                               tail_fins({'family': 'myring', 'params': dict(a=0.25, b=1.25, c=0.40, d=0.127, n=2.0, theta_deg=15)}, rolls=(45, 135, 225, 315), name='x_tail'), 'vardhan_data', 'verified', 'L/d 15, inside data range'),
    'myring_fat_ld5': ref('myring', {'family': 'myring', 'params': dict(a=0.20, b=0.40, c=0.40, d=0.200, n=2.5, theta_deg=35)},
                          tail_fins({'family': 'myring', 'params': dict(a=0.20, b=0.40, c=0.40, d=0.200, n=2.5, theta_deg=35)}), 'vardhan_data', 'verified', 'L/d 5, the Phase-1 failure region (pressure drag)'),
    # --- other analytical families ---
    'naca0014_body': ref('family', {'family': 'naca_body', 'params': dict(L=1.33, t=0.191 / 1.33)}, tail_fins({'family': 'naca_body', 'params': dict(L=1.33, t=0.191 / 1.33)}, rolls=(45, 135, 225, 315), name='x_tail'), 'naca_tr824', 'cited',
                         'NACA thickness law used as a body of revolution (our use of a standard section)'),
    'von_karman': ref('family', {'family': 'haack', 'params': dict(a=0.30, b=0.65, c=0.38, d=0.191, C=0.0)}, tail_fins({'family': 'haack', 'params': dict(a=0.30, b=0.65, c=0.38, d=0.191, C=0.0)}),
                      'haack_series', 'cited', 'Haack C = 0 nose and mirrored tail; nose/tail lengths are assumptions'),
    'lv_haack': ref('family', {'family': 'haack', 'params': dict(a=0.30, b=0.65, c=0.38, d=0.191, C=1 / 3)}, tail_fins({'family': 'haack', 'params': dict(a=0.30, b=0.65, c=0.38, d=0.191, C=1 / 3)}, rolls=(45, 135, 225, 315), name='x_tail'),
                    'haack_series', 'cited', 'Haack C = 1/3'),
    'elliptic_parabolic': ref('family', {'family': 'elliptic', 'params': dict(a=0.15, b=0.88, c=0.30, d=0.191, tail_power=2.0)},
                              tail_fins({'family': 'elliptic', 'params': dict(a=0.15, b=0.88, c=0.30, d=0.191, tail_power=2.0)}), 'jmse2026_review', 'assumption', 'Jackson-style approximation, exact family to be checked'),
    'flat_stern': ref('family', {'family': 'flat_stern', 'params': dict(a=0.15, b=0.80, c=0.38, d=0.191, n=2.0, theta_deg=25,
                                                                         stern_ratio=0.45)},
                      [fin('tail', [0, 90, 180, 270], 1.02, 0.12, 0.08, 0.08, 20, 0.12, 'knowledge03', 'assumption')],
                      'jmse2026_flatstern', 'cited', 'Myring forebody n in 1-3 cited; stern ratio our choice'),
    # --- control-surface layouts on the REMUS hull ---
    'x_tail_flaps': ref('appendage', REMUS_HULL,
                        [fin('x_tail', [45, 135, 225, 315], 1.12, 0.11, 0.07, 0.10, 25, 0.12, 'knowledge03', 'assumption',
                             flap_f=0.35, flap=20)], 'knowledge03', 'assumption', 'X-tail with trailing-edge flaps'),
    'tall_rudder': ref('appendage', REMUS_HULL,
                       [fin('rudder', [90, 270], 1.08, 0.14, 0.10, 0.22, 10, 0.12, 'knowledge03', 'assumption', flap_f=0.4, flap=15),
                        fin('elevators', [0, 180], 1.14, 0.09, 0.06, 0.08, 15, 0.12, 'knowledge03', 'assumption', defl=-5)],
                       'knowledge03', 'assumption', 'tall rudder with flap + small elevators'),
    'bow_stern_planes': ref('appendage', {'family': 'haack', 'params': dict(a=0.30, b=0.65, c=0.38, d=0.191, C=1 / 3)},
                            [fin('bow_planes', [0, 180], 0.32, 0.07, 0.05, 0.07, 5, 0.12, 'knowledge03', 'assumption', defl=10),
                             fin('stern', [0, 90, 180, 270], 1.10, 0.10, 0.06, 0.09, 30, 0.12, 'knowledge03', 'assumption')],
                            'knowledge03', 'assumption', 'forward and aft control planes'),
    # --- bio-inspired ---
    'tuna_like': ref('bio', {'family': 'fish_like', 'params': dict(L=1.0, t=1 / 4.5, x_max=0.38, tail=0.012), 'width': 0.85},
                     [fin('dorsal', [90], 0.38, 0.14, 0.04, 0.07, 45, 0.08, 'fish_fineness', 'assumption'),
                      fin('pectoral', [-20, 200], 0.28, 0.09, 0.03, 0.10, 50, 0.08, 'fish_fineness', 'assumption'),
                      fin('caudal', [90, 270], 0.90, 0.10, 0.03, 0.24, 60, 0.08, 'caudal_ar', 'assumption',
                          note='lunate tail approximated by two swept lobes; target AR about 6 (cited range 5.5-7.9)')],
                     'fish_fineness', 'cited', 'fineness 4.5 (Thunnus) cited; fin sizes are assumptions'),
    'manta_like': ref('bio', {'family': 'fish_like', 'params': dict(L=0.6, t=0.25, x_max=0.35, tail=0.005),
                              'width': 1.8, 'height': 0.45},
                      [fin('pectoral_wings', [0, 180], 0.08, 0.50, 0.05, 0.365, 40, 0.10, 'manta_uuv', 'assumption',
                           note='span ~1 m total incl. body; planform AR ~2.9 vs cited 2.5')],
                      'manta_uuv', 'cited', '1 m span and AR 2.5 cited; body flattening and chords are assumptions'),
    'swordfish_like': ref('bio', {'family': 'fish_like', 'params': dict(L=1.0, t=1 / 4.5, x_max=0.33, tail=0.01), 'width': 0.85,
                                  'bill': dict(length=0.70, base_radius=0.035, width=2.5)},
                          [fin('dorsal', [90], 0.22, 0.13, 0.02, 0.13, 50, 0.08, 'sagong2013', 'assumption'),
                           fin('pectoral', [-25, 205], 0.24, 0.08, 0.02, 0.15, 55, 0.08, 'sagong2013', 'assumption',
                               note='rigid sickle pectorals; cited: ~15 % of wetted area, +51 % drag'),
                           fin('caudal', [90, 270], 0.88, 0.10, 0.03, 0.28, 60, 0.08, 'caudal_ar', 'assumption')],
                          'sagong2013', 'cited', 'bill 41 % of total length (cited up to 44 %); C_D 0.009 is a validation '
                                                 'target; body fineness 4.5 assumption (cited: near drag-optimal)'),
    'sailfish_like': ref('bio', {'family': 'fish_like', 'params': dict(L=1.0, t=1 / 6.0, x_max=0.35, tail=0.008), 'width': 0.6,
                                 'bill': dict(length=0.205, base_radius=0.02, width=1.0)},
                         [fin('folded_sail', [90], 0.20, 0.50, 0.40, 0.03, 5, 0.06, 'sagong2013', 'assumption',
                              note='dorsal sail folded as in the gliding posture tested'),
                          fin('pectoral', [-25, 205], 0.22, 0.06, 0.02, 0.10, 55, 0.08, 'sagong2013', 'assumption'),
                          fin('caudal', [90, 270], 0.88, 0.09, 0.025, 0.22, 60, 0.08, 'caudal_ar', 'assumption')],
                         'sagong2013', 'cited', 'bill 17 % of total length cited; C_D 0.0075 validation target; fineness assumption'),
    'wahoo_like': ref('bio', {'family': 'fish_like', 'params': dict(L=1.0, t=1 / 8.4, x_max=0.40, tail=0.006), 'width': 0.8},
                      [fin('dorsal', [90], 0.18, 0.40, 0.30, 0.04, 10, 0.06, 'fish_fineness', 'assumption'),
                       fin('pectoral', [-25, 205], 0.22, 0.05, 0.02, 0.06, 45, 0.08, 'fish_fineness', 'assumption'),
                       fin('caudal', [90, 270], 0.90, 0.07, 0.02, 0.16, 60, 0.08, 'caudal_ar', 'assumption')],
                      'fish_fineness', 'cited', 'fineness 8.4 (Acanthocybium) cited; fins are assumptions'),
}


def check(build=True):
    """Fail loudly if any parameter lacks provenance or any reference does not build as one watertight solid."""
    problems = []
    for k, p in PARAMETERS.items():
        if p['source'] not in SOURCES or p['status'] not in STATUSES:
            problems.append(f'parameter {k}: bad provenance')
    for k, r in REFERENCES.items():
        for f in r['fins']:
            if f['provenance']['source'] not in SOURCES:
                problems.append(f'{k}/{f["name"]}: bad fin source')
    assert len(REFERENCES) == 20, len(REFERENCES)
    for k, r in REFERENCES.items():
        if not r['fins'] and k not in BARE_ALLOWED:
            problems.append(f'{k}: no control surfaces (practical vehicles have them); add fins or justify in BARE_ALLOWED')
    results = {}
    if build:
        import appendages as ap
        for k, r in REFERENCES.items():
            man = ap.build(r)
            results[k] = man
            if man.genus() != 0 or man.volume() <= 0:
                problems.append(f'{k}: not a single watertight solid (genus {man.genus()}, volume {man.volume()})')
    return problems, results


if __name__ == '__main__':
    import os, sys, collections
    sys.path.insert(0, os.path.dirname(__file__))
    problems, built = check()
    count = collections.Counter(p['status'] for p in PARAMETERS.values())
    count.update(r['provenance']['status'] for r in REFERENCES.values())
    for k, man in built.items():
        print(f'{k:22s} {REFERENCES[k]["category"]:10s} {REFERENCES[k]["provenance"]["status"]:11s} '
              f'volume {man.volume() * 1e3:8.2f} L  area {man.surface_area():6.3f} m^2')
    print('status counts:', dict(count))
    print('PROBLEMS:' if problems else 'all checks passed', *problems, sep='\n  ')
