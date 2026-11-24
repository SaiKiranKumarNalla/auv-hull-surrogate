#!/bin/bash
# Runs on the Mac. Creates the bucket (once), starts an on-demand c2d-highcpu-32 VM that deletes itself after
# MAXRUN, uploads the cases and the runner, runs it, pulls the small results back and deletes the VM.
#   bash cfd/gcp/launch.sh runs/pilot pilot [MAXRUN]
# SPOT=1 uses spot VMs (about 65 % cheaper; run spot_run.sh to relaunch after preemption). VM=name picks the VM.
# Results: runs/<prefix>_results/summary.txt and small/; full cases in gs://$BUCKET/<prefix>/.
set -euo pipefail
CASES=${1:?cases folder}; PREFIX=${2:?bucket prefix}; MAXRUN=${3:-3h}
VM=${VM:-auv-cfd-1}; BUCKET=auv-corpus-38d46958; ZONE=
HERE=$(cd "$(dirname "$0")" && pwd); OUT=runs/${PREFIX}_${VM}_results; mkdir -p $OUT; TGZ=$(mktemp -t auv_cases).tgz

gcloud storage buckets describe gs://$BUCKET > /dev/null 2>&1 || \
  gcloud storage buckets create gs://$BUCKET --location=europe-west4 --default-storage-class=STANDARD --uniform-bucket-level-access
for MT in c2d-highcpu-32 n2d-highcpu-32 n2-highcpu-32; do              # same region as the bucket: free uploads
  for Z in europe-west4-a europe-west4-b europe-west4-c; do
    if gcloud compute instances create $VM --zone $Z --machine-type $MT \
        --image-family ubuntu-2204-lts --image-project ubuntu-os-cloud --boot-disk-size 100GB \
        --scopes storage-rw ${SPOT:+--provisioning-model=SPOT} --max-run-duration $MAXRUN --instance-termination-action DELETE > /dev/null 2>&1; then
      ZONE=$Z; break 2; fi
  done
done
[ -n "$ZONE" ] || { echo "NO CAPACITY in europe-west4 for any 32-core type"; exit 1; }
echo "machine $MT in $ZONE"
echo "VM started $(date +%H:%M)"
for i in $(seq 30); do gcloud compute ssh $VM --zone $ZONE --command true > /dev/null 2>&1 && break; sleep 10; done
tar czf $TGZ -C "$(dirname $CASES)" "$(basename $CASES)"
gcloud compute scp --zone $ZONE $TGZ $VM:~/auv_cases.tgz > /dev/null
gcloud compute scp --zone $ZONE $HERE/vm_setup.sh $HERE/corpus_run.sh $VM:~ > /dev/null
gcloud compute ssh $VM --zone $ZONE --command "mkdir -p cases && tar xzf auv_cases.tgz && mv $(basename $CASES)/* cases/ && \
  bash vm_setup.sh > setup.log 2>&1 && nohup bash corpus_run.sh gs://$BUCKET/$PREFIX > run.log 2>&1 &" > /dev/null
echo "runner started $(date +%H:%M)"
until gcloud compute ssh $VM --zone $ZONE --command "grep -q ALL_DONE out/summary.txt" > /dev/null 2>&1; do
  gcloud compute ssh $VM --zone $ZONE --command "tail -1 out/summary.txt" 2>/dev/null | sed "s/^/$(date +%H:%M) /" || true
  sleep 120
  gcloud compute instances describe $VM --zone $ZONE > /dev/null 2>&1 || { echo "VM GONE (max run time or preemption)"; exit 1; }
done
gcloud compute scp --zone $ZONE $VM:~/out/small.tgz $OUT/ > /dev/null && tar xzf $OUT/small.tgz -C $OUT
cat $OUT/summary.txt
gcloud compute instances delete $VM --zone $ZONE --quiet
gcloud compute instances list --format="value(name)"; gcloud compute disks list --format="value(name)"
echo DOWNLOADED_AND_DELETED
