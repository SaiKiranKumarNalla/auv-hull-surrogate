#!/bin/bash
# Spot launcher with automatic relaunch: runs launch.sh on a spot VM until all cases are done.
# Finished cases are already in the bucket and are skipped, so a preemption only loses the cases in progress.
#   VM=auv-cfd-a bash cfd/gcp/spot_run.sh runs/myring_a myring 8h
HERE=$(cd "$(dirname "$0")" && pwd)
for try in 1 2 3 4 5 6; do
  echo "=== attempt $try $(date +%H:%M)"
  SPOT=1 bash $HERE/launch.sh "$@" && exit 0
  sleep 60
done
echo "GAVE UP after 6 attempts"; exit 1
