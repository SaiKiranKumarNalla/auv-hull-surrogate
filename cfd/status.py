"""One-screen status of a corpus run:  python cfd/status.py myring3 [total=150]
Reads the running VM's summary (if any) and the bucket; prints progress, gates, time per run and ETA."""
import subprocess, sys, re, time
prefix = sys.argv[1]; total = int(sys.argv[2]) if len(sys.argv) > 2 else 150
sh = lambda c: subprocess.run(c, shell=True, capture_output=True, text=True).stdout
vms = [l.split() for l in sh('gcloud compute instances list --format="value(name,zone,creationTimestamp)"').splitlines() if l.strip()]
summ = ''
for name, zone, *_ in vms:
    summ += sh(f'gcloud compute ssh {name} --zone {zone} --command "cat out/summary.txt" 2>/dev/null')
done = len([l for l in sh(f'gsutil ls gs://auv-corpus-38d46958/{prefix}/*/ 2>/dev/null').splitlines() if l.endswith('.tgz')])
mesh = re.findall(r'MESHED \S+ .* gate (\S+)', summ); solv = re.findall(r'SOLVED \S+ iters (\d+) wall (\d+) s band% (\S+) .* gate (\S+) mesh_gate', summ)
cnt = lambda xs, k: sum(1 for x in xs if x.startswith(k))
print(f'run {prefix}: {done}/{total} finished and in the bucket  ({100*done/total:.0f} %)')
print(f'VMs running: {", ".join(v[0] for v in vms) or "none"}')
if mesh: print(f'this VM: meshes {len(mesh)}  PASS {cnt(mesh,"PASS")}  WARN {cnt(mesh,"WARN")}  FAIL {cnt(mesh,"FAIL")}')
if solv:
    w = [int(s[1]) for s in solv]; g = [s[3] for s in solv]
    print(f'this VM: solves {len(solv)}  PASS {cnt(g,"PASS")}  FAIL {cnt(g,"FAIL")}  avg {sum(w)/len(w)/60:.1f} min/run (2 at a time)')
    left = total - done
    print(f'ETA: ~{left * sum(w)/len(w) / 2 / 3600:.1f} h for the remaining {left} runs (one 32-CPU VM)')
