# 01 · Paper breakdown

**Vardhan et al. 2023, "Sample-Efficient and Surrogate-Based Design Optimization of Underwater Vehicle Hulls"**
([arXiv 2304.12420](https://arxiv.org/html/2304.12420)); companion: data-efficient surrogate modelling
([arXiv 2211.10360](https://arxiv.org/pdf/2211.10360)). Code: [vardhah/UUV-design-optimization](https://github.com/vardhah/UUV-design-optimization) (GPL-3.0), cloned read-only in `reference/`.

## Pipeline
1. **Parametric CAD (FreeCAD, Docker):** Myring hull = nose + cylindrical body + tail.
2. **CFD (OpenFOAM via the "DEXOF" Docker):** `snappyHexMesh` 3D mesh around the hull, `simpleFoam` steady RANS
   (k-ω SST per the companion paper), 8 cores, 500 iterations, `forceCoeffs` for drag.
   Template case: `reference/.../cfd_sim/dir_rough_mesh_8cores_swordfish1_aoa_0/`.
3. **Optimisation with CFD in the loop:** Bayesian optimisation (GPyOpt), GA and Nelder–Mead (pymoo); sample-efficiency comparison.
4. **DNN surrogate:** hull parameters → drag; reported mean absolute percentage error ≈ **1.85 %** vs CFD; used for
   optimisation ~100,000× faster than CFD in the loop.

## What we replicate
- Train the surrogate on their data; reach a similar error (target: within a few tenths of 1.85 % MAPE).
- Run **one** of their designs ourselves in OpenFOAM and match their drag (cross-check our CFD setup).

## What we add (see 03)
Flow conditions beyond their single case; more architectures (GP with uncertainty, gradient boosting, physics-based
features, field prediction); condition-aware design.
