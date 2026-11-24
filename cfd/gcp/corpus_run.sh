#!/bin/bash
# Runs ON the VM. Corpus runner: for every case folder under ~/cases/<shape>/<case>/:
#   mesh (4 at a time, 8 cores each) -> mesh gate -> solve (2 at a time, 16 cores each, stop when drag settles or
#   at the iteration cap) -> result gate -> sample planes -> pack the full case (binary, compressed) -> upload to
#   the bucket -> keep a small copy (logs, forces, planes) in ~/out/small.
# Resumable: a case whose archive is already in the bucket is skipped.
#   bash corpus_run.sh gs://BUCKET/PREFIX
DEST=${1:?usage: corpus_run.sh gs://bucket/prefix}
OF=$(ls -d /usr/lib/openfoam/openfoam* | sort | head -1); source $OF/etc/bashrc
export OMPI_MCA_btl_vader_single_copy_mechanism=none DEST
mkdir -p ~/out/small; export LOG=~/out/summary.txt; echo "--- corpus $(date -u +%H:%M) -> $DEST" >> $LOG

uploaded() { gcloud storage ls "$DEST/$1.tgz" > /dev/null 2>&1; }

mesh() {
  source $(ls -d /usr/lib/openfoam/openfoam* | sort | head -1)/etc/bashrc
  d=$1; id=$(basename $(dirname $d))/$(basename $d); cd $d
  uploaded $id && { echo "SKIP $id already in bucket" >> $LOG; touch skip.flag; return; }
  rm -rf constant/polyMesh processor* postProcessing; find . -maxdepth 1 -regextype posix-extended -regex './[0-9.]+' -exec rm -rf {} +
  cp system/decomposeParDict.mesh system/decomposeParDict
  surfaceFeatureExtract > log.sfe 2>&1; blockMesh > log.blockMesh 2>&1; decomposePar -force > log.dec 2>&1
  mpirun -np 8 snappyHexMesh -parallel -overwrite > log.snappyHexMesh 2>&1
  reconstructParMesh -constant > log.rec 2>&1; rm -rf processor*; checkMesh > log.checkMesh 2>&1
  cells=$(grep -m1 'cells:' log.checkMesh | awk '{print $2}')
  cov=$(grep -h "^body " log.snappyHexMesh | tail -1 | awk '{print $5}')
  ok=$(grep -q 'Mesh OK' log.checkMesh && echo yes || echo no)
  nfail=$(grep -c '^ \*\*\*' log.checkMesh); nskew=$(grep -oE '[0-9]+ highly skew' log.checkMesh | awk '{print $1}')
  # only failure = a few highly skewed faces (snappy's own quality limits accepted them): pass, logged
  [ "$ok" = no ] && [ "$nfail" -eq 1 ] && [ -n "$nskew" ] && [ "$nskew" -le 50 ] && ok="skew$nskew"
  gate=PASS; [ "$ok" = no ] && gate=FAIL_checkMesh
  awk -v c="${cov:-0}" 'BEGIN{exit !(c+0 < 85)}' && gate="WARN_layers${cov}"     # 75-85 %: kept, flagged
  awk -v c="${cov:-0}" 'BEGIN{exit !(c+0 < 75)}' && gate="FAIL_layers${cov}"
  echo "$gate" > mesh_gate.txt
  echo "MESHED $id cells ${cells:-0} layers% ${cov:-?} checkMesh_ok $ok gate $gate" >> $LOG
}

settled() {
  f=$(ls postProcessing/coeffs/*/coefficient.dat 2>/dev/null | tail -1); [ -z "$f" ] && return 1
  grep -v '^#' "$f" | awk 'NF{c[NR]=$2; n=NR} END{ if(n<200) exit 1; mx=-1e30; mn=1e30; s=0;
     for(i=n-99;i<=n;i++){s+=c[i]; if(c[i]>mx)mx=c[i]; if(c[i]<mn)mn=c[i]} m=s/100; exit !((mx-mn)/(m<0?-m:m)<0.001) }'
}

band() {   # drag band over the last 100 iterations, % of mean
  f=$(ls postProcessing/coeffs/*/coefficient.dat 2>/dev/null | tail -1)
  grep -v '^#' "$f" | awk 'NF{c[NR]=$2; n=NR} END{ mx=-1e30; mn=1e30; s=0; k=(n<100?n:100);
     for(i=n-k+1;i<=n;i++){s+=c[i]; if(c[i]>mx)mx=c[i]; if(c[i]<mn)mn=c[i]} m=s/k; printf "%.3f", 100*(mx-mn)/(m<0?-m:m) }'
}

solve() {
  source $(ls -d /usr/lib/openfoam/openfoam* | sort | head -1)/etc/bashrc; export -f settled
  d=$1; id=$(basename $(dirname $d))/$(basename $d); cd $d
  [ -f skip.flag ] && return
  [ -s constant/polyMesh/owner ] || { echo "NOMESH $id" >> $LOG; return; }
  cp system/decomposeParDict.solve system/decomposeParDict
  rm -rf 0 processor*; cp -r 0.orig 0; decomposePar -force > log.dec 2>&1
  t0=$(date +%s); mpirun -np 16 simpleFoam -parallel > log.simpleFoam 2>&1 & pid=$!
  while kill -0 $pid 2>/dev/null; do sleep 15; settled && { sed -i 's/stopAt endTime;/stopAt writeNow;/' system/controlDict; wait $pid; }; done
  reconstructPar -latestTime > log.recpar 2>&1; rm -rf processor*
  postProcess -dict system/planes -fields '(p U)' -latestTime > log.sample 2>&1
  it=$(grep -c '^Time =' log.simpleFoam); b=$(band)
  yp=$(grep -A3 'patch body' log.simpleFoam | grep -m1 -o 'average = [0-9.e+-]*' | tail -1 | awk '{print $3}')
  [ -z "$yp" ] && yp=$(grep -h 'body y+ : min' -A0 log.simpleFoam | tail -1 | grep -o 'average = [0-9.e+-]*' | awk '{print $3}')
  gate=PASS; awk -v b="$b" 'BEGIN{exit !(b+0 >= 1)}' && gate=FAIL_band
  [ "$it" -eq 0 ] && gate=FAIL_crash
  echo "$gate" > result_gate.txt
  echo "SOLVED $id iters $it wall $(( $(date +%s)-t0 )) s band% $b yplus ${yp:-?} gate $gate mesh_gate $(cat mesh_gate.txt)" >> $LOG
  [ "$it" -eq 0 ] && return
  cd ..; s=$(basename $d)
  tar czf ~/out/pack_${s}.tgz --exclude='processor*' --exclude='0.orig' $s
  if gcloud storage cp ~/out/pack_${s}.tgz "$DEST/$id.tgz" > /dev/null 2>&1; then echo "UPLOADED $id $(du -h ~/out/pack_${s}.tgz | cut -f1)" >> $LOG; rm -f ~/out/pack_${s}.tgz; else echo "UPLOAD_FAILED $id (archive kept in ~/out)" >> $LOG; fi
  mkdir -p ~/out/small/$id; cp -r $s/postProcessing $s/log.* $s/case.json $s/*_gate.txt ~/out/small/$id/ 2>/dev/null
}
export -f mesh solve settled band uploaded
ls -d ~/cases/*/*/ | xargs -P 4 -I{} bash -c 'mesh {}'
ls -d ~/cases/*/*/ | xargs -P 2 -I{} bash -c 'solve {}'
cd ~/out && tar czf small.tgz small summary.txt
echo ALL_DONE >> $LOG
