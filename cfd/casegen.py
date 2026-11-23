"""Write an OpenFOAM (ESI v2112+) steady RANS k-omega SST case for any registry design.

Settings reproduce the Vardhan et al. swordfish1 case numerically (knowledge/08-nondimensional-model.md), written
from scratch (no files copied from the GPL reference). Mesh sizes scale with the body length L.

    python cfd/casegen.py --all --out runs/sample_paper   # 20 reference designs, paper conditions
"""
import argparse, json, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'design'))
import numpy as np
import appendages as ap
from registry import REFERENCES

PAPER = dict(U=2.0, rho=1027.0, nu=1.736124635e-6, k=0.01, omega=57.0, iters=500)   # verified from their case files


def head(cls, obj, loc=''):
    return ('FoamFile\n{\n    version 2.0;\n    format ascii;\n    class ' + cls + ';\n'
            + (f'    location "{loc}";\n' if loc else '') + f'    object {obj};\n}}\n\n')


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        f.write(text)


def field(name, cls, dims, internal, walls_bc, body_bc):
    sides = ''.join(f'    {p}\n    {{\n{walls_bc}    }}\n' for p in ('inlet', 'outlet', 'sides'))
    return (head(cls, name, '0') + f'dimensions {dims};\ninternalField uniform {internal};\n\nboundaryField\n{{\n'
            + sides + f'    body\n    {{\n{body_bc}    }}\n}}\n')


def make_case(name, design, out, n_proc=8, cond=PAPER, base_frac=0.08 / 1.107, levels=(5, 7), max_cells=3_000_000):
    case = os.path.join(out, name)
    man = ap.build(design)
    os.makedirs(os.path.join(case, 'constant', 'triSurface'), exist_ok=True)
    stl = os.path.join(case, 'constant', 'triSurface', 'body.stl')
    if design.get('stl_override'):                            # e.g. the paper's own swordfish1 STL (local only, GPL)
        import shutil, trimesh
        shutil.copy(os.path.join(HERE, '..', design['stl_override']), stl)
        tm = trimesh.load(stl)
        import manifold3d as m3d
        man = m3d.Manifold(m3d.Mesh(vert_properties=np.asarray(tm.vertices, np.float32), tri_verts=np.asarray(tm.faces, np.uint32)))
    else:
        ap.save_stl(man, stl, 'body')
    mesh = man.to_mesh()
    V = np.asarray(mesh.vert_properties)[:, :3]
    lo, hi = V.min(0), V.max(0)
    L = float(hi[0] - lo[0]); xc = float((lo[0] + hi[0]) / 2)
    hmax = float(max(abs(lo[1]), abs(hi[1]), abs(lo[2]), abs(hi[2])))
    cell = base_frac * max(L, 2 * hmax)                       # base cell ~ 0.0723 L (paper), wider bodies use span
    x0, x1 = xc - L, xc + 3 * L
    side = 8 * hmax                                           # paper rule: +-4 D sideways
    nx, ny = math.ceil((x1 - x0) / cell), math.ceil(2 * side / cell)
    U, rho, nu = cond['U'], cond['rho'], cond['nu']
    S, Vol = float(man.surface_area()), float(man.volume())
    meta = dict(name=name, L=L, x_centre=xc, half_width=hmax, S_wet=S, volume=Vol, Re=U * L / nu, base_cell=cell,
                blocks=[nx, ny, ny], condition=cond, design=design)

    # ---------- system ----------
    write(os.path.join(case, 'system', 'controlDict'), head('dictionary', 'controlDict', 'system') + f"""application simpleFoam;
startFrom latestTime;
startTime 0;
stopAt endTime;
endTime {cond['iters']};
deltaT 1;
writeControl timeStep;
writeInterval {cond['iters']};
purgeWrite 1;
writeFormat binary;
writePrecision 8;
runTimeModifiable true;

functions
{{
    forces
    {{
        type forces;
        libs (forces);
        writeControl timeStep;
        writeInterval 1;
        patches (body);
        rho rhoInf;
        rhoInf {rho};
        CofR ({xc} 0 0);
        log true;
    }}
    coeffsWetted
    {{
        type forceCoeffs;
        libs (forces);
        writeControl timeStep;
        writeInterval 1;
        patches (body);
        rho rhoInf;
        rhoInf {rho};
        magUInf {U};
        lRef {L};
        Aref {S};
        CofR ({xc} 0 0);
        liftDir (0 0 1);
        dragDir (1 0 0);
        pitchAxis (0 1 0);
        log true;
    }}
    yPlus
    {{
        type yPlus;
        libs (fieldFunctionObjects);
        writeControl writeTime;
    }}
}}
""")
    write(os.path.join(case, 'system', 'blockMeshDict'), head('dictionary', 'blockMeshDict', 'system') + f"""scale 1;
vertices
(
    ({x0} {-side} {-side}) ({x1} {-side} {-side}) ({x1} {side} {-side}) ({x0} {side} {-side})
    ({x0} {-side} {side}) ({x1} {-side} {side}) ({x1} {side} {side}) ({x0} {side} {side})
);
blocks ( hex (0 1 2 3 4 5 6 7) ({nx} {ny} {ny}) simpleGrading (1 1 1) );
boundary
(
    inlet  {{ type patch; faces ((0 4 7 3)); }}
    outlet {{ type patch; faces ((1 2 6 5)); }}
    sides  {{ type patch; faces ((0 1 5 4) (3 7 6 2) (0 3 2 1) (4 5 6 7)); }}
);
""")
    bx0, bx1, bs = lo[0] - 0.2 * L, hi[0] + 1.0 * L, 2.0 * hmax + 0.05 * L
    inside = (float(xc), 0.0, float(side * 0.9))               # a point in the fluid, away from the body
    write(os.path.join(case, 'system', 'snappyHexMeshDict'), head('dictionary', 'snappyHexMeshDict', 'system') + f"""castellatedMesh true;
snap true;
addLayers true;

geometry
{{
    body.stl {{ type triSurfaceMesh; name body; }}
    wake {{ type searchableBox; min ({bx0} {-bs} {-bs}); max ({bx1} {bs} {bs}); }}
}}

castellatedMeshControls
{{
    maxLocalCells 1000000;
    maxGlobalCells {max_cells};
    minRefinementCells 10;
    nCellsBetweenLevels 4;
    features ( {{ file "body.eMesh"; level {levels[0]}; }} );
    refinementSurfaces {{ body {{ level ({levels[0]} {levels[1]}); patchInfo {{ type wall; }} }} }}
    resolveFeatureAngle 30;
    refinementRegions {{ wake {{ mode inside; levels ((1e15 2)); }} }}
    locationInMesh ({inside[0]} {inside[1]} {inside[2]});
    allowFreeStandingZoneFaces true;
}}

snapControls
{{
    nSmoothPatch 3;
    tolerance 2.0;
    nSolveIter 30;
    nRelaxIter 5;
    nFeatureSnapIter 10;
    implicitFeatureSnap false;
    explicitFeatureSnap true;
    multiRegionFeatureSnap false;
}}

addLayersControls
{{
    relativeSizes true;
    layers {{ body {{ nSurfaceLayers 2; }} }}
    expansionRatio 1.3;
    finalLayerThickness 0.7;
    minThickness 0.25;
    nGrow 0;
    featureAngle 60;
    slipFeatureAngle 30;
    nRelaxIter 3;
    nSmoothSurfaceNormals 1;
    nSmoothNormals 3;
    nSmoothThickness 10;
    maxFaceThicknessRatio 0.5;
    maxThicknessToMedialRatio 0.3;
    minMedialAxisAngle 90;
    nBufferCellsNoExtrude 0;
    nLayerIter 50;
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
    write(os.path.join(case, 'system', 'decomposeParDict'), head('dictionary', 'decomposeParDict', 'system')
          + f'numberOfSubdomains {n_proc};\nmethod scotch;\n')
    write(os.path.join(case, 'system', 'fvSchemes'), head('dictionary', 'fvSchemes', 'system') + """ddtSchemes { default steadyState; }
gradSchemes
{
    default cellLimited Gauss linear 0.95;
    grad(p) Gauss linear;
    grad(k) cellLimited Gauss linear 0.9;
    grad(omega) cellLimited Gauss linear 0.9;
}
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
SIMPLE
{
    nNonOrthogonalCorrectors 5;
    consistent no;
    residualControl { p 1e-4; U 1e-4; "(k|omega)" 1e-4; }
}
relaxationFactors
{
    equations { U 0.6; k 0.5; omega 0.5; }
    fields { p 0.3; }
}
""")
    # ---------- constant ----------
    write(os.path.join(case, 'constant', 'transportProperties'), head('dictionary', 'transportProperties', 'constant')
          + f'transportModel Newtonian;\nnu {nu};\n')
    write(os.path.join(case, 'constant', 'turbulenceProperties'), head('dictionary', 'turbulenceProperties', 'constant')
          + 'simulationType RAS;\nRAS\n{\n    RASModel kOmegaSST;\n    turbulence on;\n    printCoeffs on;\n}\n')
    # ---------- 0 (freestream boundaries, wall functions: as the paper) ----------
    k, om = cond['k'], cond['omega']
    io = lambda v: f'        type inletOutlet;\n        inletValue uniform {v};\n        value uniform {v};\n'
    write(os.path.join(case, '0.orig', 'U'), field('U', 'volVectorField', '[0 1 -1 0 0 0 0]', f'({U} 0 0)',
          f'        type freestreamVelocity;\n        freestreamValue uniform ({U} 0 0);\n', '        type noSlip;\n'))
    write(os.path.join(case, '0.orig', 'p'), field('p', 'volScalarField', '[0 2 -2 0 0 0 0]', '0',
          '        type freestreamPressure;\n        freestreamValue uniform 0;\n', '        type zeroGradient;\n'))
    write(os.path.join(case, '0.orig', 'k'), field('k', 'volScalarField', '[0 2 -2 0 0 0 0]', k, io(k),
          '        type kqRWallFunction;\n        value uniform 1e-10;\n'))
    write(os.path.join(case, '0.orig', 'omega'), field('omega', 'volScalarField', '[0 0 -1 0 0 0 0]', om, io(om),
          f'        type omegaWallFunction;\n        value uniform {om};\n'))
    write(os.path.join(case, '0.orig', 'nut'), field('nut', 'volScalarField', '[0 2 -1 0 0 0 0]', 0,
          '        type calculated;\n        value uniform 0;\n', '        type nutkWallFunction;\n        value uniform 0;\n'))
    write(os.path.join(case, 'Allrun'), f"""#!/bin/bash
# Mesh and solve; logs in log.*. Usage: ./Allrun  (needs OpenFOAM v2112+ sourced)
cd "${{0%/*}}" || exit 1
. ${{WM_PROJECT_DIR:?}}/bin/tools/RunFunctions
set -o pipefail
runApplication surfaceFeatureExtract
runApplication blockMesh
runApplication decomposePar -force
runParallel snappyHexMesh -overwrite
runParallel checkMesh
restore0Dir -processor
runParallel simpleFoam
runApplication reconstructPar -latestTime
touch done.flag
""")
    os.chmod(os.path.join(case, 'Allrun'), 0o755)
    write(os.path.join(case, 'case.json'), json.dumps(meta, indent=1, default=float))
    return meta


if __name__ == '__main__':
    ap_ = argparse.ArgumentParser()
    ap_.add_argument('--out', default='runs/sample_paper')
    ap_.add_argument('--nproc', type=int, default=8)
    ap_.add_argument('--all', action='store_true')
    ap_.add_argument('names', nargs='*')
    a = ap_.parse_args()
    names = list(REFERENCES) if a.all else a.names
    PAPER_STL = 'reference/UUV-design-optimization/cad_cfd_pipeline_surrogate_data_generation/cfd_sim/' \
                'dir_rough_mesh_8cores_swordfish1_aoa_0/constant/triSurface/UUV.stl'
    for n in names:
        d = dict(REFERENCES[n], stl_override=PAPER_STL) if n == 'vardhan_swordfish1' else REFERENCES[n]
        m = make_case(n, d, a.out, a.nproc)
        print(f"{n:22s} L {m['L']:5.2f} m  Re {m['Re']:.2e}  base blocks {m['blocks']}  S {m['S_wet']:.3f} m^2")
