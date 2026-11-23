#!/bin/bash
# ON the VM: stop the batch, add processor-patch constraint types to 0.orig, keep finished meshes, restart.
pkill -f run_batch.sh; pkill -f snappyHexMesh; pkill -f simpleFoam; pkill -f Allrun; sleep 3
for c in sample_paper/*/; do
  for f in $c/0.orig/*; do grep -q setConstraintTypes $f || sed -i '$ d' $f && grep -q setConstraintTypes $f || printf '    #includeEtc "caseDicts/setConstraintTypes"\n}\n' >> $f; done
  if grep -q "Finished meshing without any errors" $c/log.snappyHexMesh 2>/dev/null && [ -f $c/log.checkMesh ]; then
    rm -rf $c/log.simpleFoam $c/log.reconstructPar $c/done.flag $c/processor*/0 $c/postProcessing
  else
    rm -rf $c/log.* $c/processor* $c/done.flag $c/postProcessing $c/constant/extendedFeatureEdgeMesh $c/constant/polyMesh
  fi
done
tail -6 sample_paper/lv_haack/0.orig/p
nohup bash run_batch.sh sample_paper 4 > batch.log 2>&1 < /dev/null &
echo restarted
