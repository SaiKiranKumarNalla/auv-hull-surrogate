#!/bin/bash
# Runs ON the VM: run every case folder in $1, $2 cases at a time (each case uses the nproc in its decomposeParDict).
set -uo pipefail
ROOT=${1:-sample_paper}; PAR=${2:-4}
OF=$(ls -d /usr/lib/openfoam/openfoam* | sort | head -1)
export OMPI_MCA_btl_vader_single_copy_mechanism=none
run_one() { source "$2/etc/bashrc"; cd "$1" && ./Allrun > allrun.log 2>&1; echo "$(basename "$1") exit $?"; }
export -f run_one
ls -d "$ROOT"/*/ | xargs -P "$PAR" -I{} bash -c "run_one {} $OF"
echo BATCH_DONE
