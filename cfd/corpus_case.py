"""Dimensionless corpus cases: every shape scaled to length L = 1, one fixed box, flow always along +x.

A case = (design, orientation, Re). The body is scaled to unit length (body-axis length), centred at the origin and
then rotated: yaw turns it about z (flow arrives from the side), pitch about y (flow arrives from above or below).
U_inf = 1, rho = 1, nu = 1/Re, so OpenFOAM's forces are already coefficients times the reference area.

Mesh = the validated ~700K recipe expressed in units of L:
  base cell 0.107 L in a fixed box x in [-2, 4], y and z in [-2, 2];
  'core' box at level 1 (= the old base cell 0.0535 L), 'wake' box at level 2, 'nearWake' at level 4,
  body surface at levels (5 6) (= the old (4 5)), 2 prism layers with the first height set for y+ = 30 at this Re.
Output files are binary and compressed.

    python cfd/corpus_case.py remus100_finned 0 --out runs/pilot
        -> runs/pilot/remus100_finned_v00/<orientation>_Re<..>/ for every orientation x Re in PILOT
"""
import argparse, json, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'design'))
sys.path.insert(0, HERE)
import numpy as np
import appendages as ap
from casegen import head, write, field

BOX = dict(x=(-2.0, 4.0), y=(-2.0, 2.0), z=(-2.0, 2.0))
BASE = 0.107
TURB_I, NUT_RATIO = 0.041, 100.0           # inlet intensity and nu_t/nu as in the paper case (k 0.01, omega 57 at 2 m/s)
ORIENTATIONS = {'front': (0, 0), 'yaw10': (10, 0), 'yaw30': (30, 0), 'side': (90, 0), 'top': (0, 90)}
RES = (1e6, 3e6, 1e7)
ITER_CAP, ITER_MIN = 600, 200


def rot(yaw, pitch):
    a, b = np.radians(yaw), np.radians(pitch)
    Rz = np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])
    Ry = np.array([[np.cos(b), 0, np.sin(b)], [0, 1, 0], [-np.sin(b), 0, np.cos(b)]])
    return Rz @ Ry


def body(design, yaw, pitch):
    """Unit-length body, centred at its bounding-box centre, rotated. Returns (V, F, info)."""
    man = ap.build(design)
    m = man.to_mesh(); V = np.asarray(m.vert_properties)[:, :3].astype(float); F = np.asarray(m.tri_verts)
    L = V[:, 0].max() - V[:, 0].min()
    V = (V - (V.min(0) + V.max(0)) / 2) / L
    R = rot(yaw, pitch); V = V @ R.T
    tri = V[F]; area = float(0.5 * np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1).sum())
    vol = float(man.volume()) / L ** 3
    return V, F, dict(L_phys=float(L), S_wet=area, volume=vol, R=R.tolist())


def save_stl(V, F, path):
    T = V[F].astype(np.float32)
    n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); n /= np.linalg.norm(n, axis=1, keepdims=True).clip(1e-30)
    rec = np.zeros(len(T), dtype=[('n', '<f4', 3), ('v', '<f4', (3, 3)), ('a', '<u2')]); rec['n'], rec['v'] = n, T
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb') as f:
        f.write(b'body'.ljust(80, b' ')); f.write(np.uint32(len(T)).tobytes()); f.write(rec.tobytes())


def first_layer(Re, y_plus=30):
    cf = 0.026 * Re ** (-1 / 7); ut = math.sqrt(cf / 2)
    return 2 * y_plus / (Re * ut)


def make_case(design, name, orient, Re, out):
    yaw, pitch = ORIENTATIONS[orient]
    case = os.path.join(out, name, f'{orient}_Re{Re:.0e}'.replace('+0', '').replace('+', ''))
    V, F, info = body(design, yaw, pitch)
    save_stl(V, F, os.path.join(case, 'constant', 'triSurface', 'body.stl'))
    lo, hi = V.min(0), V.max(0); half = (hi - lo) / 2
    nu = 1.0 / Re; k = 1.5 * TURB_I ** 2; om = k / (NUT_RATIO * nu); h1 = first_layer(Re)
    surf = BASE / 2 ** 6                                   # body surface cell (level 6)
    n_layers = max(2, math.ceil(math.log(0.4 * surf / h1) / math.log(1.15)))   # grow layers up to ~0.4 cell; 2 at Re <= 3e6 as validated
    n = [math.ceil((BOX[a][1] - BOX[a][0]) / BASE) for a in 'xyz']
    pad = lambda v, p: v + p
    core = ([lo[0] - 0.8, -max(half[1] + 0.35, 0.6), -max(half[2] + 0.35, 0.6)],
            [hi[0] + 2.0, max(half[1] + 0.35, 0.6), max(half[2] + 0.35, 0.6)])
    wake = ([lo[0] - 0.2, -(2 * half[1] + 0.05), -(2 * half[2] + 0.05)], [hi[0] + 1.0, 2 * half[1] + 0.05, 2 * half[2] + 0.05])
    wy, wz = max(0.85 * half[1], 0.1), max(0.85 * half[2], 0.1)
    near = ([hi[0] - 0.3, -wy, -wz], [hi[0] + 0.6, wy, wz])
    box = lambda nm, b: f'    {nm} {{ type searchableBox; min ({b[0][0]:.5f} {b[0][1]:.5f} {b[0][2]:.5f}); max ({b[1][0]:.5f} {b[1][1]:.5f} {b[1][2]:.5f}); }}\n'
    meta = dict(design=design.get('variant', {}).get('base', name), variant=design.get('variant', {}).get('index'),
                orientation=orient, yaw_deg=yaw, pitch_deg=pitch, Re=Re, nu=nu, U=1.0, rho=1.0, L=1.0,
                bbox_lo=lo.tolist(), bbox_hi=hi.tolist(), first_layer=h1, n_layers=n_layers, base_cell=BASE, box=BOX, recipe='nd-700K-v1',
                **info, recipe_json=design)
    write(os.path.join(case, 'case.json'), json.dumps(meta, indent=1, default=float))

    write(os.path.join(case, 'system', 'controlDict'), head('dictionary', 'controlDict', 'system') + f"""application simpleFoam;
startFrom latestTime;
startTime 0;
stopAt endTime;
endTime {ITER_CAP};
deltaT 1;
writeControl timeStep;
writeInterval {ITER_CAP};
purgeWrite 1;
writeFormat binary;
writeCompression on;
writePrecision 8;
runTimeModifiable true;
functions
{{
    forces {{ type forces; libs (forces); writeControl timeStep; writeInterval 1; patches (body);
              rho rhoInf; rhoInf 1; CofR (0 0 0); log false; }}
    coeffs {{ type forceCoeffs; libs (forces); writeControl timeStep; writeInterval 1; patches (body);
              rho rhoInf; rhoInf 1; magUInf 1; lRef 1; Aref {info['S_wet']:.6f}; CofR (0 0 0);
              liftDir (0 0 1); dragDir (1 0 0); pitchAxis (0 1 0); log true; }}
    yPlus {{ type yPlus; libs (fieldFunctionObjects); writeControl writeTime; }}
}}
""")
    (x0, x1), (y0, y1), (z0, z1) = BOX['x'], BOX['y'], BOX['z']
    write(os.path.join(case, 'system', 'blockMeshDict'), head('dictionary', 'blockMeshDict', 'system') + f"""scale 1;
vertices ( ({x0} {y0} {z0}) ({x1} {y0} {z0}) ({x1} {y1} {z0}) ({x0} {y1} {z0})
           ({x0} {y0} {z1}) ({x1} {y0} {z1}) ({x1} {y1} {z1}) ({x0} {y1} {z1}) );
blocks ( hex (0 1 2 3 4 5 6 7) ({n[0]} {n[1]} {n[2]}) simpleGrading (1 1 1) );
boundary
(
    inlet  {{ type patch; faces ((0 4 7 3)); }}
    outlet {{ type patch; faces ((1 2 6 5)); }}
    sides  {{ type patch; faces ((0 1 5 4) (3 7 6 2) (0 3 2 1) (4 5 6 7)); }}
);
""")
    write(os.path.join(case, 'system', 'snappyHexMeshDict'), head('dictionary', 'snappyHexMeshDict', 'system') + f"""castellatedMesh true;
snap true;
addLayers true;
geometry
{{
    body.stl {{ type triSurfaceMesh; name body; }}
{box('core', core)}{box('wake', wake)}{box('nearWake', near)}}}
castellatedMeshControls
{{
    maxLocalCells 2000000;
    maxGlobalCells 4000000;
    minRefinementCells 10;
    nCellsBetweenLevels 4;
    features ( {{ file "body.eMesh"; level 5; }} );
    refinementSurfaces {{ body {{ level (5 6); patchInfo {{ type wall; }} }} }}
    resolveFeatureAngle 30;
    refinementRegions
    {{
        core {{ mode inside; levels ((1e15 1)); }}
        wake {{ mode inside; levels ((1e15 2)); }}
        nearWake {{ mode inside; levels ((1e15 4)); }}
    }}
    locationInMesh ({BOX['x'][1] - 0.48269:.5f} {BOX['y'][1] - 0.19483:.5f} {BOX['z'][1] - 0.20389:.5f});
    allowFreeStandingZoneFaces true;
}}
snapControls
{{
    nSmoothPatch 3; tolerance 2.0; nSolveIter 30; nRelaxIter 5; nFeatureSnapIter 10;
    implicitFeatureSnap false; explicitFeatureSnap true; multiRegionFeatureSnap false;
}}
addLayersControls
{{
    relativeSizes false;
    layers {{ body {{ nSurfaceLayers {n_layers}; }} }}
    firstLayerThickness {h1:.4e};
    expansionRatio 1.15;
    minThickness {0.2 * h1:.4e};
    nGrow 0; featureAngle 150; slipFeatureAngle 45; nRelaxIter 5;
    nSmoothSurfaceNormals 3; nSmoothNormals 3; nSmoothThickness 10;
    maxFaceThicknessRatio 0.8; maxThicknessToMedialRatio 0.6; minMedialAxisAngle 90;
    nBufferCellsNoExtrude 0; nLayerIter 50; nOuterIter 2; layerTerminationAngle -180;
}}
meshQualityControls
{{
    #includeEtc "caseDicts/mesh/generation/meshQualityDict.cfg"
    maxNonOrtho 65;
}}
mergeTolerance 1e-6;
""")
    write(os.path.join(case, 'system', 'surfaceFeatureExtractDict'), head('dictionary', 'surfaceFeatureExtractDict', 'system')
          + 'body.stl\n{\n    extractionMethod extractFromSurface;\n    includedAngle 150;\n    writeObj no;\n}\n')
    write(os.path.join(case, 'system', 'decomposeParDict.mesh'), head('dictionary', 'decomposeParDict', 'system')
          + 'numberOfSubdomains 8;\nmethod simple;\nsimpleCoeffs { n (8 1 1); delta 0.001; }\n')
    write(os.path.join(case, 'system', 'decomposeParDict.solve'), head('dictionary', 'decomposeParDict', 'system')
          + 'numberOfSubdomains 16;\nmethod scotch;\n')
    write(os.path.join(case, 'system', 'fvSchemes'), head('dictionary', 'fvSchemes', 'system') + """ddtSchemes { default steadyState; }
gradSchemes { default cellLimited Gauss linear 0.95; grad(p) Gauss linear; grad(k) cellLimited Gauss linear 0.9; grad(omega) cellLimited Gauss linear 0.9; }
divSchemes
{
    default none;
    div(phi,U) bounded Gauss linearUpwindV grad(U);
    div((nuEff*dev2(T(grad(U))))) Gauss linear;
    div(phi,k) bounded Gauss upwind;
    div(phi,omega) bounded Gauss upwind;
}
laplacianSchemes { default Gauss linear limited 0.3; }
interpolationSchemes { default linear; }
snGradSchemes { default limited 0.3; }
wallDist { method meshWave; }
""")
    write(os.path.join(case, 'system', 'fvSolution'), head('dictionary', 'fvSolution', 'system') + """solvers
{
    p { solver GAMG; tolerance 1e-7; relTol 0.01; smoother symGaussSeidel; nPreSweeps 0; nPostSweeps 2; cacheAgglomeration on; }
    "(U|k|omega)" { solver smoothSolver; smoother GaussSeidel; tolerance 1e-7; relTol 0.1; }
}
SIMPLE { nNonOrthogonalCorrectors 2; consistent no; residualControl { p 1e-12; U 1e-12; "(k|omega)" 1e-12; } }
relaxationFactors { equations { U 0.6; k 0.5; omega 0.5; } fields { p 0.3; } }
""")
    write(os.path.join(case, 'system', 'planes'), head('dictionary', 'planes', 'system') + """functions
{
planes
{
    type surfaces; libs (sampling); surfaceFormat raw; fields (p U); interpolationScheme cellPoint;
    surfaces
    {
        sideView { type cuttingPlane; planeType pointAndNormal; pointAndNormalDict { point (0 0 0); normal (0 1 0); } interpolate true; }
        topView  { type cuttingPlane; planeType pointAndNormal; pointAndNormalDict { point (0 0 0); normal (0 0 1); } interpolate true; }
        hull     { type patch; patches (body); interpolate true; }
    }
}
}
""")
    write(os.path.join(case, 'constant', 'transportProperties'), head('dictionary', 'transportProperties', 'constant')
          + f'transportModel Newtonian;\nnu {nu:.6e};\n')
    write(os.path.join(case, 'constant', 'turbulenceProperties'), head('dictionary', 'turbulenceProperties', 'constant')
          + 'simulationType RAS;\nRAS\n{\n    RASModel kOmegaSST;\n    turbulence on;\n    printCoeffs on;\n}\n')
    io = lambda v: f'        type inletOutlet;\n        inletValue uniform {v};\n        value uniform {v};\n'
    write(os.path.join(case, '0.orig', 'U'), field('U', 'volVectorField', '[0 1 -1 0 0 0 0]', '(1 0 0)',
          '        type freestreamVelocity;\n        freestreamValue uniform (1 0 0);\n', '        type noSlip;\n'))
    write(os.path.join(case, '0.orig', 'p'), field('p', 'volScalarField', '[0 2 -2 0 0 0 0]', '0',
          '        type freestreamPressure;\n        freestreamValue uniform 0;\n', '        type zeroGradient;\n'))
    write(os.path.join(case, '0.orig', 'k'), field('k', 'volScalarField', '[0 2 -2 0 0 0 0]', f'{k:.6e}', io(f'{k:.6e}'),
          '        type kqRWallFunction;\n        value uniform 1e-10;\n'))
    write(os.path.join(case, '0.orig', 'omega'), field('omega', 'volScalarField', '[0 0 -1 0 0 0 0]', f'{om:.6e}', io(f'{om:.6e}'),
          f'        type omegaWallFunction;\n        value uniform {om:.6e};\n'))
    write(os.path.join(case, '0.orig', 'nut'), field('nut', 'volScalarField', '[0 2 -1 0 0 0 0]', 0,
          '        type calculated;\n        value uniform 0;\n', '        type nutkWallFunction;\n        value uniform 0;\n'))
    return case, meta


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('base'); p.add_argument('variant', type=int); p.add_argument('--out', default='runs/pilot')
    p.add_argument('--box', default='-2,4,2', help='x_min,x_max,half_width in body lengths (default 6 L x 4 L x 4 L)')
    p.add_argument('--only', default='', help='comma list of orientation_Re ids, e.g. front_Re3e6,side_Re3e6')
    a = p.parse_args()
    x0, x1, hw = map(float, a.box.split(','))
    BOX.update(x=(x0, x1), y=(-hw, hw), z=(-hw, hw))
    only = set(filter(None, a.only.split(',')))
    d = json.load(open(os.path.join(HERE, '..', 'design', 'variants', a.base, f'v{a.variant:02d}.json')))
    name = f'{a.base}_v{a.variant:02d}'
    for o in ORIENTATIONS:
        for Re in RES:
            tag = f'{o}_Re{Re:.0e}'.replace('+0', '').replace('+', '')
            if only and tag not in only:
                continue
            c, m = make_case(d, name, o, Re, a.out)
            print(f'{os.path.relpath(c)}  bbox {np.round(m["bbox_hi"], 3).tolist()}  h1 {m["first_layer"]:.2e}')
