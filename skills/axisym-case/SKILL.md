---
name: axisym-case
description: Build and verify the 2D axisymmetric (wedge) OpenFOAM case for a Myring hull at zero angle of attack, cross-checked against the paper's 3D drag and the empirical L0 estimate. Use before any sweep.
---
# Axisymmetric case
1. Write `cfd/myring.py`: Myring profile (a, b, c, d, n, θ) → curve points (formula from Myring 1976; `TODO: cite`).
2. Mesh a 5° wedge around the profile (blockMesh with a graded boundary layer; y+ target per wall treatment).
3. `simpleFoam`, k-ω SST, inlet U from the case, `forceCoeffs` → drag (scale wedge force to the full body).
4. Mesh study on 3 meshes (< 2 % change in C_D).
5. Cross-check one of their designs at 2 m/s against their D, and against L0.
Done when: our drag is within a few % of theirs (or the difference is explained) — record in REVIEW_QUEUE.
