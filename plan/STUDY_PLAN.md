# Study plan: CFD corpus → surrogates → PINN and operator benchmark

Goal: one validated CFD corpus of AUV designs, and on it an honest comparison of physics-AI architectures
(plain NN, PINN, FNO, graph networks, Transolver). Motion simulation comes later, only for the designs that
survive the funnel. Fixed on 2026-11-23, before any corpus run.

```mermaid
flowchart LR
    A["Study 0<br/>Validated CFD recipe<br/>(done)"] --> B["Study 1<br/>2,600-run corpus<br/>+ NN surrogate"]
    B --> C["Study 1b<br/>PINN ladder<br/>vs CFD vs surrogate"]
    B --> D["Study 2<br/>Field models<br/>GNN · FNO · Transolver"]
    C --> E["Funnel<br/>best designs"]
    D --> E
    E --> F["Later<br/>Fossen 6-DOF<br/>motion simulator"]
    style A fill:#E1F5EE,stroke:#0F6E56
    style F fill:#F1EFE8,stroke:#888780,stroke-dasharray: 4 3
```

## Study 0: CFD recipe (done)

| Item | Result |
|---|---|
| Solver | OpenFOAM v2112 `simpleFoam`, k-ω SST, wall functions, absolute prism layers at y⁺ ≈ 30 |
| Grid convergence (swordfish_like, 145K to 1.16M cells) | Observed order 1.94, GCI_fine 0.86 %, Cd monotonic |
| Local check | Every probe line within 5 % of the finest grid at 653K cells |
| Production recipe | ~700K cells, near-wake level-3 box, repeatable (simple) decomposition |
| Results | `results/cfd_gridstudy/`, `results/cfd_custom/` |

## Study 1: the corpus

```mermaid
flowchart TB
    B["20 core designs<br/>(design/registry.py)"] --> V["× 10 parametric variants each<br/>= 200 distinct shapes"]
    V --> C["× 13 flow conditions each<br/>speed 0.5–5 m/s · angle 0–10°<br/>fresh / salt water"]
    C --> R["= 2,600 CFD runs<br/>1 run = 1 training sample"]
    R --> O["Saved per run:<br/>6 forces + moments · surface p, τ_w<br/>3D fields on point cloud + 128×64×64 grid"]
```

| Decision | Choice | Why |
|---|---|---|
| Shapes vs conditions | 10 variants × 13 conditions | One mesh per shape is reused for 13 conditions; every shape gets full drag and force curves, which the later motion model needs |
| Density and velocity | Varied through the Reynolds number | In incompressible flow they only enter through Re and dynamic pressure; varying both separately repeats runs |
| Condition sampling | Latin hypercube per shape, plus a 0° cruise anchor | No shape/condition correlation, so no coverage bias |
| Mesh | One recipe for every run (~700K, 600-iteration cap) | Mixing fidelities would hide mesh error inside the design effect |
| Mesh-error check | ~50 runs repeated at ~1.2M cells | Reported as uncertainty, never used for training |
| Waves | Not in this corpus | Needs a free-surface solver (10–50× cost); later, as a depth parameter |
| Geometry | Every shape passes the quality gate (`design/quality.py`) | No bad junctions or needle tips reach the mesher |

Variant ranges per base, gallery and split assignment: [VARIANT_RANGES.md](VARIANT_RANGES.md)
(200/200 variants pass the geometry gate; 136 train, 34 unseen-variant, 30 unseen-base).

Test splits, fixed before training:

| Split | Held out | Question |
|---|---|---|
| Unseen variant | 2 of 10 variants in every base | New shape of a known kind of vehicle |
| Unseen base | 3 of the 20 bases entirely | New kind of vehicle |
| Unseen condition | Top of the speed range, angles above 9° | Extrapolation |

Budget: ~125 VM-hours on c2d-highcpu-32 (≈ €160 on demand, €55–70 on spot with a resumable runner).
A 40-shape pilot runs first to measure failure rate, runtime and convergence.

## Study 1b: PINN ladder

Data-free PINNs work for laminar, smooth problems (e.g. Gammaidoni et al., *Computers & Fluids* 2026,
microchannels). Our flows are turbulent (Re ~10⁶), 3D and finned. The ladder finds where they stop working.

```mermaid
flowchart LR
    S1["1. 2D laminar channel<br/>physics only<br/>(reproduce paper)"] --> S2["2. Axisymmetric hull<br/>laminar Re 10³–10⁴"]
    S2 --> S3["3. Same, parameterised<br/>across hull shapes"]
    S3 --> S4["4. Real Re + k-ω SST<br/>physics only"]
    S4 --> S5["5. Real Re, hybrid<br/>1–5 % CFD points"]
    S5 --> S6["6. 3D finned hull<br/>hybrid (stretch)"]
    style S4 fill:#FAECE7,stroke:#993C1D
```

Step 4 is the expected breaking point. Every step is scored against CFD and against the Study 1 surrogate on:
field error, force error, training time, and cost per new design.

## Study 2: field models

Same corpus, same splits: MeshGraphNet / graph network on the CFD mesh, FNO on the regular grid,
Transolver on the point cloud, plain MLP on forces. Output: one table of accuracy, data needed
(scaling curve over 100 / 300 / 1000 / 2600 runs), training cost and inference time.

## Reading

Karniadakis et al. 2021 (*Nat. Rev. Phys.*) · Raissi et al. 2019 (PINN) · Krishnapriyan et al. 2021 (PINN failure
modes) · Li et al. 2021 (FNO) · Pfaff et al. 2021 (MeshGraphNets) · Wu et al. 2024 (Transolver) ·
Takamoto et al. 2022 (PDEBench) · Li et al. 2026 *Appl. Ocean Res.* 175:105219 (AUV Kriging MDO).
