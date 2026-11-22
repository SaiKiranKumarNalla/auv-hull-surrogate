# 06 · Related work and data

## Key reference for Phase 2 (manoeuvring + control)
**Lin, Chen, Xiong, Yu, Zhu, Xing & Zheng 2025, "Hydrodynamics Model Identification and Model-Based Control
Application of a New Type of AUV", J. Mar. Sci. Eng. 13(2):310** ([doi:10.3390/jmse13020310](https://doi.org/10.3390/jmse13020310)).
- Negative-lift AUV with a single vector thruster; CFD in **STAR-CCM+** (Marine trial) using the **spatially
  constrained (captive) motion method** — one model setup gives all coefficients of the standard manoeuvring equations.
- **Neural networks identify all 88 hydrodynamic coefficients**; goodness-of-fit significance analysis reduces them to
  **20 key terms**.
- Coefficients → 6-DOF nonlinear model → **nonlinear MPC** (input constraints of the vector thruster) → simulation and
  **pool tests**: errors exist but the controller works.
- Limitation they state: no precise experimental coefficients to validate the CFD method.
- `TODO (owner): download the PDF to knowledge/papers/pdf/ and note their validation model, mesh and turbulence model.`

How we use it: after the drag study (Phase 1), Phase 2 computes manoeuvring coefficients of our Myring hulls under
conditions C1–C6 with OpenFOAM captive-motion runs, identifies them with NNs / sparse regression, plugs them into
Fossen's simulator, and compares MPC vs PID across conditions — the robotics half of the project.

## Other
- [WAKESET](https://arxiv.org/html/2602.01379v2) — large CFD dataset of AUV wakes during recovery.
- [SHIP-D](https://arxiv.org/html/2305.08279v2) — 30,000 ship hulls with drag (ships, not AUVs).
- [Search for minimum-drag underwater hull with CFD](https://arxiv.org/pdf/2302.09441).
- [Hybrid AUV manoeuvring models from sea-trial data](https://arxiv.org/html/2606.19711).
- [AI-enhanced underwater glider design](https://arxiv.org/pdf/2505.00222).
- [CFD surrogate for a duct-jet AUV](https://www.preprints.org/manuscript/202509.0043).
- Fossen's [Python Vehicle Simulator](https://github.com/cybergalactic/PythonVehicleSimulator) — for later coupling of coefficients to manoeuvring.
