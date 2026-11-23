#!/bin/bash
# Grid study, swordfish_like. Mesh 4 uniform scales in parallel, then solve coarse->fine on 16 cores,
# each finer grid started from the coarser solution (mapFields), stopping when Cd settles (runTimeControl).
OF=$(ls -d /usr/lib/openfoam/openfoam* | sort | head -1); source $OF/etc/bashrc
export OMPI_MCA_btl_vader_single_copy_mechanism=none
mkdir -p ~/gci; cd ~/gci; S="0.6 0.77 1.0 1.3"
mesh() {
  source $(ls -d /usr/lib/openfoam/openfoam* | sort | head -1)/etc/bashrc
  s=$1; d=~/gci/sf_s$s; rm -rf $d; mkdir $d
  cp -r ~/custom/swordfish_like/{0.orig,constant,system,case.json} $d/; rm -rf $d/constant/polyMesh $d/constant/extendedFeatureEdgeMesh
  cd $d
  read nx ny nz < <(grep -o 'hex ([0-9 ]*) ([0-9 ]*)' system/blockMeshDict | sed 's/.*) (//; s/)//')
  N=$(python3 -c "print(*[max(4,round(v*$s)) for v in ($nx,$ny,$nz)])")
  sed -i "s/($nx $ny $nz)/($N)/" system/blockMeshDict
  sed -i "s/level (5 7)/level (4 5)/; s/levels ((1e15 2))/levels ((1e15 1))/; s/maxGlobalCells 1000000/maxGlobalCells 3000000/" system/snappyHexMeshDict
  sed -i "s/numberOfSubdomains [0-9]*/numberOfSubdomains 8/" system/decomposeParDict
  surfaceFeatureExtract > log.sfe 2>&1; blockMesh > log.blockMesh 2>&1; decomposePar -force > log.dec 2>&1
  mpirun -np 8 snappyHexMesh -parallel -overwrite > log.snappyHexMesh 2>&1
  reconstructParMesh -constant > log.rec 2>&1; rm -rf processor*; checkMesh > log.checkMesh 2>&1
  echo "MESHED sf_s$s $(grep -m1 'cells:' log.checkMesh)" >> ~/gci/summary.txt
}
export -f mesh; rm -f summary.txt
printf '%s\n' $S | xargs -P 4 -I{} bash -c 'mesh {}'
prev=""
for s in $S; do
  cd ~/gci/sf_s$s
  sed -i "s/^endTime .*/endTime 2000;/; s/^writeInterval .*/writeInterval 100;/" system/controlDict
  python3 - <<'PY'
p='system/controlDict'; t=open(p).read().rstrip(); assert t.endswith('}')
t=t[:-1]+'''    stopWhenSettled
    {
        type runTimeControl; libs (utilityFunctionObjects);
        conditions
        {
            cd { type average; functionObject coeffsWetted; fields (Cd); tolerance 1e-3; window 50; windowType approximate; }
            minIt { type minTimeStep; minValue 0; }
        }
        satisfiedAction end;
    }
}
'''
open(p,'w').write(t)
PY
  sed -i "s/numberOfSubdomains [0-9]*/numberOfSubdomains 16/" system/decomposeParDict
  rm -rf 0 processor*; cp -r 0.orig 0
  [ -n "$prev" ] && mapFields ../$prev -consistent -sourceTime latestTime > log.mapFields 2>&1
  decomposePar -force > log.dec 2>&1
  t0=$(date +%s); mpirun -np 16 simpleFoam -parallel > log.simpleFoam 2>&1; t1=$(date +%s)
  reconstructPar -latestTime > log.recpar 2>&1; rm -rf processor*
  echo "SOLVED sf_s$s iters $(grep -c '^Time =' log.simpleFoam) wall $((t1-t0)) s" >> ~/gci/summary.txt
  prev=sf_s$s
done
cd ~/gci/sf_s1.3; cp ~/sample_planes.dict system/planes; cp ~/sample_mesh.dict system/meshcut
postProcess -dict system/planes -fields '(p U)' -latestTime > log.sample 2>&1
postProcess -dict system/meshcut -fields '(p U)' -latestTime > log.meshcut 2>&1
cd ~; tar czf gci.tgz gci/*/postProcessing gci/*/log.* gci/*/case.json gci/summary.txt
echo ALL_DONE >> ~/gci/summary.txt
