#!/bin/bash
# Runs whole families one after another on one spot VM, keeping local disk use small:
# generate one family's cases -> spot run -> delete the local copy -> next family.
#   bash cfd/gcp/queue.sh PREFIX base1 base2 ...
PREFIX=$1; shift
cd "$(dirname "$0")/../.."
for b in "$@"; do
  echo "=== $b $(date +%H:%M)"
  rm -rf runs/q_$b
  for v in 0 1 2 3 4 5 6 7 8 9; do .venv/bin/python cfd/corpus_case.py $b $v --out runs/q_$b > /dev/null || echo "CASEGEN_FAIL $b $v"; done
  VM=auv-cfd-a bash cfd/gcp/spot_run.sh runs/q_$b $PREFIX 10h > runs/q_$b.log 2>&1 && echo "DONE $b $(date +%H:%M)" || echo "RUN_FAIL $b"
  rm -rf runs/q_$b
done
echo QUEUE_DONE
