# Plan from 2026-11-23 (tutor mode: the owner runs everything)

Rule until 2026-12-24: **no new projects**; new ideas go to `plan/IDEAS.md`. Ship something public every Sunday.

## Phase 1 — benchmark AI models on the existing 3,021 hulls (no new CFD) — Nov 23–29
| Day | Work | Done when |
|---|---|---|
| Mon 23 | IDE layout; first commit; `models/physics.py` (Myring geometry, wetted area, volume, ITTC-1957, form factor) → **M0** | M0 error on their test set; committed |
| Tue 24 | Data split done right (their test set untouched); **M2** gradient boosting, **M3** Matérn GP | 3-model results table |
| Wed 25 | **M1** clean MLP replication (their architecture, dropout fixed, no test leakage) | Replication vs their 1.85 % |
| Thu 26 | Dimensionless inputs (Π groups); **M4** physics-informed network predicting the form factor, with derivative constraints | M4 results |
| Fri 27 | Learning curves N = 50…2400; out-of-distribution split (blunt hulls, L/d < 7) | Curves + failure analysis |
| Sat 28 | `results/phase1.md`, figures, README | Repo public |
| Sun 29 | Rest / buffer | |

## Phase 2 — new CFD across practical conditions (Dec) — see knowledge/03
Axisymmetric OpenFOAM sweeps (speed, water, transition, roughness) + small 3D angle-of-attack set; learn Linux / SLURM here.

## Phase 3 — couple to Fossen's 6-DOF simulator (later)

## Evening log
| Day | Done | Blocked | Tomorrow |
|---|---|---|---|
