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

## The DNN: paper text vs their code (checked 2026-11-23)
| Item | Paper (Sec. 5) | Code (`student_model.py`, `nn_train.py`, `utils.py`) | Our M1 versions |
|---|---|---|---|
| Layers | 9, ReLU, skip at an inner hidden layer | 6→128→64→64→32→32→64→64→8→1; skip `h + relu(h)` after layer 3 | same |
| Parameters | 22,249 | 23,249 (counted) | 23,249; the paper's figure is probably a typo |
| Dropout | 0.2, two layers | `nn.Dropout(p=0.2)` created but never applied | M1a: none · M1b: 0.2 |
| Input scaling | min–max | min–max on fixed design ranges | min–max on the training data |
| Init | Xavier-normal, zero bias | same | same (M1a/M1b) |
| Optimiser, loss | Adam, lr **0.0003**, L1 | Adam, lr **0.001**, L1, batch 32, 400 epochs | M1a: 1e-3 · M1b: 3e-4 |
| Checkpoint | "early stopping" on a 90/10 split | keeps the epoch with the smallest train–val loss gap (after epoch 25) | M1a: gap · M1b: lowest val loss |
| Restarts | not mentioned | up to 5 warm-started retrains, kept if **test** failures (>5 % error) drop; grows data 100→2,400 | not copied (test leakage) |
| Reported result | MAPE **1.85 %** on 621 test hulls; 14 outliers | | |
