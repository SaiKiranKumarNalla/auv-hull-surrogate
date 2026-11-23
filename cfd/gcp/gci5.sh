#!/bin/bash
OF=$(ls -d /usr/lib/openfoam/openfoam* | sort | head -1); source $OF/etc/bashrc
export OMPI_MCA_btl_vader_single_copy_mechanism=none
source <(sed -n '/^mesh() {/,/^}/p' ~/gciL.sh); export -f mesh
cd ~/gci; echo "--- local $(date +%H:%M)" >> summary.txt
printf "%s\n" 0.6 0.77 1.0 1.3 1.69 | xargs -P 4 -I{} bash -c "mesh {}"
settled() {  # Cd band over last 100 iterations < 0.2 % of mean, at least 150 iterations
  f=$(ls postProcessing/coeffsWetted/*/coefficient.dat 2>/dev/null | tail -1); [ -z "$f" ] && return 1
  grep -v '^#' "$f" | awk 'NF{c[NR]=$2; n=NR} END{ if(n<300) exit 1; mx=-1e9; mn=1e9; s=0;
     for(i=n-99;i<=n;i++){s+=c[i]; if(c[i]>mx)mx=c[i]; if(c[i]<mn)mn=c[i]} m=s/100; exit !((mx-mn)/m<0.001) }'
}
prev=""
for s in 0.6 0.77 1.0 1.3 1.69; do
  cd ~/gci/sf_s$s
  python3 - <<'PY'
import re; p='system/controlDict'; t=open(p).read()
t=re.sub(r'\n    stopWhenSettled\n    \{.*?\n    \}\n', '\n', t, flags=re.S)
if 'endTime 2000' not in t: t=re.sub(r'\nendTime \d+;', '\nendTime 2000;', t)
t=re.sub(r'\nwriteInterval \d+;', '\nwriteInterval 100;', t, count=1)
t=t.replace('stopAt writeNow;','stopAt endTime;'); t=t.rstrip(); t=t[:-1]+open('/home/'+__import__('getpass').getuser()+'/probes.txt').read()+'}\n' if 'probeLocations' not in t else t
open(p,'w').write(t)
q='system/fvSolution'; u=open(q).read(); u=re.sub(r'residualControl \{[^}]*\}', 'residualControl { p 1e-12; U 1e-12; "(k|omega)" 1e-12; }', u); open(q,'w').write(u)
PY
  sed -i "s/numberOfSubdomains [0-9]*/numberOfSubdomains 16/" system/decomposeParDict
  rm -rf 0 [1-9]* processor* postProcessing; cp -r 0.orig 0
  [ -n "$prev" ] && mapFields ../$prev -consistent -sourceTime latestTime > log.mapFields 2>&1
  decomposePar -force > log.dec 2>&1
  t0=$(date +%s); mpirun -np 16 simpleFoam -parallel > log.simpleFoam 2>&1 &
  pid=$!
  while kill -0 $pid 2>/dev/null; do sleep 20; settled && { sed -i 's/stopAt endTime;/stopAt writeNow;/' system/controlDict; wait $pid; }; done
  t1=$(date +%s)
  reconstructPar -latestTime > log.recpar 2>&1; rm -rf processor*
  cd_last=$(grep -v '^#' $(ls postProcessing/coeffsWetted/*/coefficient.dat|tail -1) | tail -100 | awk '{s+=$2} END{print s/NR}')
  cp ~/sample_local.dict system/local; postProcess -dict system/local -fields '(p U)' -latestTime > log.local 2>&1
  yp=$(grep -A3 "^yPlus" log.simpleFoam | grep -m1 -o "y+ : min.*" | tail -1); cov=$(grep -h "body " log.snappyHexMesh | tail -1 | awk "{print \$5}"); echo "SOLVED sf_s$s cells $(grep -m1 'cells:' log.checkMesh | awk '{print $2}') iters $(grep -c '^Time =' log.simpleFoam) wall $((t1-t0)) s Cd100 $cd_last layers% $cov $yp" >> ~/gci/summary.txt
  prev=sf_s$s
done
cd ~; tar czf gci.tgz gci/*/postProcessing gci/*/log.* gci/*/case.json gci/*/system/controlDict gci/summary.txt
echo ALL_DONE5 >> ~/gci/summary.txt
