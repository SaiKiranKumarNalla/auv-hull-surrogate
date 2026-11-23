#!/bin/bash
# 6 custom cases with the validated recipe: base x1.35, surface (4 5), wake 1, near-wake box level 3,
# absolute prism layers (y+ 30), deterministic 'simple' decomposition for meshing. Stop when Cd settles.
OF=$(ls -d /usr/lib/openfoam/openfoam* | sort | head -1); source $OF/etc/bashrc
export OMPI_MCA_btl_vader_single_copy_mechanism=none
S=1.35; mkdir -p ~/out; LOG=~/out/summary.txt; echo "--- custom $(date +%H:%M)" >> $LOG
mesh() {
  source $(ls -d /usr/lib/openfoam/openfoam* | sort | head -1)/etc/bashrc
  d=$1; cd $d; rm -rf constant/polyMesh constant/extendedFeatureEdgeMesh processor* postProcessing; find . -maxdepth 1 -regextype posix-extended -regex './[0-9.]+' -exec rm -rf {} +
  python3 - <<'PY'
import json, math, re
m = json.load(open('case.json')); S = 1.35
L, xc, h, c = m['L'], m['x_centre'], m['half_width'], m['condition']
b = open('system/blockMeshDict').read()
nx, ny, nz = map(int, re.search(r'hex \([0-9 ]*\) \((\d+) (\d+) (\d+)\)', b).groups())
b = b.replace(f'({nx} {ny} {nz})', '(%d %d %d)' % tuple(max(4, round(v * S)) for v in (nx, ny, nz))); open('system/blockMeshDict', 'w').write(b)
t = open('system/snappyHexMeshDict').read()
t = t.replace('level (5 7)', 'level (4 5)').replace('levels ((1e15 2))', 'levels ((1e15 1))').replace('maxGlobalCells 1000000', 'maxGlobalCells 4000000')
x1 = xc + L / 2; w = max(0.85 * h, 0.1)
t = t.replace('    wake { type searchableBox;', f'    nearWake {{ type searchableBox; min ({x1 - 0.3 * L} {-w} {-w}); max ({x1 + 0.6 * L} {w} {w}); }}\n    wake {{ type searchableBox;', 1)
t = t.replace('wake { mode inside; levels ((1e15 1)); }', 'wake { mode inside; levels ((1e15 1)); }\n        nearWake { mode inside; levels ((1e15 3)); }', 1)
Re = c['U'] * L / c['nu']; ut = c['U'] * math.sqrt(0.026 * Re ** (-1 / 7) / 2); h1 = 2 * 30 * c['nu'] / ut
lb = open('/home/' + __import__('getpass').getuser() + '/layers.txt').read()
lb = re.sub(r'firstLayerThickness [0-9.e+-]+;', f'firstLayerThickness {h1:.4e};', lb); lb = re.sub(r'minThickness [0-9.e+-]+;', f'minThickness {0.2 * h1:.4e};', lb)
i, j = t.index('addLayersControls'), t.index('meshQualityControls'); t = t[:i] + lb + '\n' + t[j:]
t = re.sub(r'locationInMesh \(([-0-9.e]+) ([-0-9.e]+) ([-0-9.e]+)\)', lambda g: 'locationInMesh (%.6f %.6f %.6f)' % (float(g[1]) + 0.00731, float(g[2]) + 0.00517, float(g[3]) - 0.00389), t)
assert 'nearWake { mode' in t and 'relativeSizes false' in t; open('system/snappyHexMeshDict', 'w').write(t)
open('system/decomposeParDict', 'w').write('FoamFile { version 2.0; format ascii; class dictionary; object decomposeParDict; }\nnumberOfSubdomains 8;\nmethod simple;\nsimpleCoeffs { n (8 1 1); delta 0.001; }\n')
p = open('system/controlDict').read()
p = re.sub(r'\nendTime \d+;', '\nendTime 2000;', p); p = re.sub(r'\nwriteInterval \d+;', '\nwriteInterval 100;', p, count=1); open('system/controlDict', 'w').write(p)
q = open('system/fvSolution').read(); q = re.sub(r'residualControl \{[^}]*\}', 'residualControl { p 1e-12; U 1e-12; "(k|omega)" 1e-12; }', q); open('system/fvSolution', 'w').write(q)
m['mesh_recipe'] = dict(scale=S, surface_levels=[4, 5], wake_level=1, near_wake_level=3, y_plus=30, first_layer_m=h1); json.dump(m, open('case.json', 'w'), indent=1)
PY
  surfaceFeatureExtract > log.sfe 2>&1; blockMesh > log.blockMesh 2>&1; decomposePar -force > log.dec 2>&1
  mpirun -np 8 snappyHexMesh -parallel -overwrite > log.snappyHexMesh 2>&1
  reconstructParMesh -constant > log.rec 2>&1; rm -rf processor*; checkMesh > log.checkMesh 2>&1
  echo "MESHED $(basename $d) $(grep -m1 'cells:' log.checkMesh)" >> ~/out/summary.txt
}
settled() {
  f=$(ls postProcessing/coeffsWetted/*/coefficient.dat 2>/dev/null | tail -1); [ -z "$f" ] && return 1
  grep -v '^#' "$f" | awk 'NF{c[NR]=$2; n=NR} END{ if(n<300) exit 1; mx=-1e9; mn=1e9; s=0;
     for(i=n-99;i<=n;i++){s+=c[i]; if(c[i]>mx)mx=c[i]; if(c[i]<mn)mn=c[i]} m=s/100; exit !((mx-mn)/m<0.001) }'
}
solve() {
  source $(ls -d /usr/lib/openfoam/openfoam* | sort | head -1)/etc/bashrc; export -f settled
  d=$1; cd $d; n=$(basename $d)
  printf "FoamFile { version 2.0; format ascii; class dictionary; object decomposeParDict; }\nnumberOfSubdomains 16;\nmethod scotch;\n" > system/decomposeParDict
  rm -rf 0 processor*; cp -r 0.orig 0; decomposePar -force > log.dec 2>&1
  t0=$(date +%s); mpirun -np 16 simpleFoam -parallel > log.simpleFoam 2>&1 & pid=$!
  while kill -0 $pid 2>/dev/null; do sleep 20; settled && { sed -i 's/stopAt endTime;/stopAt writeNow;/' system/controlDict; wait $pid; }; done
  reconstructPar -latestTime > log.recpar 2>&1; rm -rf processor*
  cp ~/sample_planes.dict system/planes; cp ~/sample_mesh.dict system/meshcut
  postProcess -dict system/planes -fields '(p U)' -latestTime > log.sample 2>&1
  postProcess -dict system/meshcut -fields '(p U)' -latestTime > log.meshcut 2>&1
  cov=$(grep -h "body " log.snappyHexMesh | tail -1 | awk '{print $5}')
  echo "SOLVED $n cells $(grep -m1 'cells:' log.checkMesh | awk '{print $2}') iters $(grep -c '^Time =' log.simpleFoam) wall $(( $(date +%s)-t0 )) s layers% $cov" >> ~/out/summary.txt
  cd ~; tar czf ~/out/$n.tgz custom/$n/postProcessing custom/$n/log.* custom/$n/case.json custom/$n/system/snappyHexMeshDict 2>/dev/null
}
export -f mesh solve settled
ls -d ~/custom/*/ | xargs -P 4 -I{} bash -c 'mesh {}'
ls -d ~/custom/*/ | xargs -P 2 -I{} bash -c 'solve {}'
echo ALL_DONE >> $LOG
