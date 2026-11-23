#!/bin/bash
# Runs ON the VM after the batch: sample p,U on planes, the mesh cut and the snapped hull; pack the small outputs.
ROOT=${1:-sample_paper}
OF=$(ls -d /usr/lib/openfoam/openfoam* | sort | head -1)
one() {
  source "$2/etc/bashrc"; cd "$1" || exit
  cp ~/sample_planes.dict system/planes; cp ~/sample_mesh.dict system/meshcut
  postProcess -dict system/planes -latestTime > log.sample 2>&1
  postProcess -dict system/meshcut -latestTime > log.meshcut 2>&1
  echo "$(basename "$1") $?"
}
export -f one
ls -d "$ROOT"/*/ | xargs -P 8 -I{} bash -c "one {} $OF"
tar czf results_small.tgz $ROOT/*/postProcessing $ROOT/*/log.* $ROOT/*/case.json $ROOT/*/allrun.log 2>/dev/null
ls -la results_small.tgz
