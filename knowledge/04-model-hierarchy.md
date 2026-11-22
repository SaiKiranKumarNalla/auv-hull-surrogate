# 04 · Model hierarchy

## Simulation levels
| Level | Model | Cost | Role |
|---|---|---|---|
| L0 | Empirical drag: ITTC-1957 friction line × form factor (hull fineness), plus a simple roughness correction | µs | Baseline, physics features for the surrogate, sanity check |
| **L1** | **2D axisymmetric RANS** (OpenFOAM wedge, `simpleFoam`, k-ω SST; k-ω SST-LM for transition) | ~minutes per run on 2–4 cores | Main dataset: hull shape × C1–C5 (target ~1,000–2,000 runs) |
| L2 | 3D RANS (their snappyHexMesh template) at angle of attack | ~hour(s) per run on 4 cores | ~50–100 runs for C6 (lift, moment) |
| L3 | 3D two-phase / unsteady (C8, C9) | heavy | Future |
Cross-check: L1 at 0° vs their 3D drag for the same hull (and vs L0).

## Surrogates
| ID | Inputs | Outputs | Models |
|---|---|---|---|
| S0 | hull (a, b, c, d, n, θ) | drag at 2 m/s | replicate their DNN; add GP, gradient boosting |
| S1 | hull + condition (U, ν, ρ, Tu, roughness) | C_D (and friction/pressure split) | MLP with physics features (Re, fineness, wetted area), GP with uncertainty, multi-fidelity (L0 + learned correction) |
| S2 | hull + angle of attack | C_D, C_L, C_M | MLP / GP on the L2 set; multi-fidelity with S1 |
| S3 (stretch) | hull + condition | surface pressure / wall shear along the hull | 1D neural operator along the hull profile |

## Use
Condition-aware design: "best hull for cold-water slow surveys" vs "best hull for warm-water fast transits"; how much the
optimum shifts with condition and roughness; uncertainty from GP.
