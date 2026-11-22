---
name: flow-sweep
description: Run the L1 axisymmetric sweep over hull shapes and practical flow conditions C1–C5 (speed, water type, transition, inflow turbulence, roughness) in parallel, with a manifest. Use after axisym-case passes.
---
# Flow-condition sweep
1. `cfd/sample.py`: Sobol over hull params (their ranges) × conditions from `knowledge/03` (C1–C5).
2. `cfd/run_case.py <id>`: write case from template, mesh, solve, extract forces (friction and pressure parts), delete fields.
3. Run in parallel (GNU parallel in the Codespace; Kaggle CPU notebook for the big batch); append to `data/manifest.csv`.
4. Check: residual convergence, force convergence, y+ range; re-run failures once.
Done when: ≥ 95 % converged runs; summary table committed (`data/l1_summary.csv` small).
