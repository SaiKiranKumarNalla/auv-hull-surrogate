# AUV Hull Surrogate & SciML Project — Complete Handoff & Context for Claude

**Prepared:** 2026-11-23  
**Owner:** Sai Kiran Kumar Nalla, PhD  
**Repo:** `/Users/nallasaikirankumar/Projects/auv-hull-surrogate`  
**Operating Mode:** Strictly **`TUTOR` mode** (see `AGENTS.md`) — the owner runs commands/edits and learns Linux, HPC, git, OpenFOAM, and PyTorch step-by-step unless they explicitly say `"you do this step"`.

---

## 1. Strategic & Career Context (Why We Are Building This)

This project is explicitly designed to close the technical proof-of-work gaps for **Mistral AI — AI Scientist, Physics Models (Paris)** (as well as Health/Scientific AI Scientist roles in France/Europe).

Key requirements from the target Mistral AI job description that this roadmap addresses:
1. **Design and run large-scale simulation campaigns** using domain-specific solvers (OpenFOAM) to build high-fidelity datasets.
2. **Develop ML methods for simulation & surrogate modeling**, investigating **multi-fidelity training**, **pretraining/physics-informed objectives**, and **scaling behavior** (low-data efficiency & transfer).
3. **Rigorously evaluate model coverage, accuracy, and robustness** against validation standards and **diagnose failure modes** arising from data gaps or architecture limitations.
4. **Clean, readable Python code & comfort in Linux / HPC environments** (Ubuntu VMs, SSH, `rsync`, SLURM `sbatch`/`squeue`/job arrays, CLI GPU workflows).

### Scientific Framing (Important Owner Insight)
The owner explicitly flagged that **pure "CFD + black-box MLP + BO/GA" shape optimization is saturated and hard to validate experimentally** without a tow tank. Therefore, this project must **NOT** be framed as *"I invented a better torpedo optimizer."* Instead, it is framed as a **Scientific ML (SciML) / Physics-Informed Surrogate & Verification Benchmark**:
- Validating the physics baseline against established experimental/empirical standards (**ITTC-1957**, **Hoerner form factors**, **Myring 1976**).
- Auditing **where black-box neural surrogates fail** (data scarcity, out-of-distribution fineness ratios, boundary-layer separation, monotonicity violations).
- Showing how **retrospective non-dimensionalization (Buckingham $\Pi$)** + **Physics-Informed Neural Networks (PINNs / physics-residual + `torch.autograd.grad` derivative constraints)** dramatically improve data efficiency and physical consistency.

---

## 2. Forensic Audit of the Base Paper & Cloned Reference Repo

**Base Paper:** Harsh Vardhan, David Hyde, Umesh Timalsina, Peter Volgyesi, & Janos Sztipanovits (Vanderbilt University), *"Sample-Efficient and Surrogate-Based Design Optimization of Underwater Vehicle Hulls"*, **arXiv:2304.12420** (*Ocean Engineering*, 2024).  
**Companion Paper:** arXiv:2211.10360 (*Ensemble-Free Deep Active Learning*).  
**Cloned Read-Only Repo:** `reference/UUV-design-optimization/` (**License: GNU GPL-3.0**).
- *License rule:* Raw simulation tables (`train_2400.txt`, `test_data.txt`) can be used with citation to Vardhan et al. (2023). Do **not** copy GPL Python code into our repo unless we license our repo GPL-3.0; write our own clean loaders, physics, and PyTorch models.

### 2.1 Confirmed Dataset & Units (Closing `TODO` in `knowledge/02-dataset.md`)
- **Files verified on disk:**
  - `reference/UUV-design-optimization/cad_cfd_pipeline_surrogate_data_generation/surrogate_data/train_2400.txt` (**2,400 rows**)
  - `reference/UUV-design-optimization/uuv_optim/data/surrogate/test_data.txt` (**621 rows**)
  - Additional files: `feasible_data_myring.csv`, `data_myring_infeasible.csv` (geometrically invalid Myring hulls where tail radius crosses $r < 0$), `vmc_cfd*.csv`.
- **7 Columns per row** (6 geometry inputs + 1 scalar output), confirmed from `range_of_interest` and `nn_train.py`:
  1. `a`: Nose length, $50\text{–}600\text{ mm}$
  2. `b`: Cylindrical body length, $1\text{–}1850\text{ mm}$
  3. `c`: Tail length, $50\text{–}600\text{ mm}$ (total length $L = a + b + c \in [1000, 2000]\text{ mm}$)
  4. `d`: Hull diameter, $50\text{–}200\text{ mm}$
  5. `n`: Myring nose shape exponent, $1\text{–}5$ (dimensionless)
  6. `t` ($\theta$): Tail closing semi-angle, $1^\circ\text{–}50^\circ$ (degrees)
  7. `D`: Total steady-state drag force in **Newtons [N]**

### 2.2 Confirmed OpenFOAM Simulation Setup & Compute Cost
Inspected from `reference/UUV-design-optimization/cad_cfd_pipeline_surrogate_data_generation/cfd_sim/dir_rough_mesh_8cores_swordfish1_aoa_0/`:
- **Solver:** OpenFOAM v2112 `simpleFoam` (steady incompressible RANS, **$k\text{-}\omega\text{ SST}$** turbulence model, `kqRWallFunction` + `omegaWallFunction`).
- **Frozen Operating Condition (identical across all 3,021 hulls):**
  - Inlet velocity: $U_\infty = (2.0, 0, 0)\text{ m/s}$, angle of attack $\alpha = 0^\circ$
  - Seawater density: $\rho = 1027.0\text{ kg/m}^3$ (`problem_def.json` / `forceCoeffs`)
  - Kinematic viscosity: $\nu = 1.736124635 \times 10^{-6}\text{ m}^2/\text{s}$ (`constant/transportProperties`, cold seawater $\approx 2^\circ\text{C}$)
  - Dynamic pressure: $q_\infty = \frac{1}{2}\rho U_\infty^2 = 2054.0\text{ Pa}$
  - Inlet turbulence: $k_{\text{inlet}} = 0.01\text{ m}^2/\text{s}^2$, $\omega_{\text{inlet}} = 57.0\text{ s}^{-1}$
- **Domain & Mesh (`blockMeshDict` + `snappyHexMeshDict`):**
  - Box: $1L$ upstream, $3L$ downstream, $4d$ on all 4 sides.
  - Background grid `55 × 5 × 5`, `snappyHexMesh` refinement `(5 7)`, `nsurfacelayers: 2` prism layers $\rightarrow$ **277,099 cells** on `swordfish1`.
- **Actual Logged Compute Time (8 CPU cores):**
  - `snappyHexMesh` (8 cores): **14.54 s**
  - `simpleFoam` (8 cores): **91.22 s** for 320 iterations (~0.285 s/iter; ~142 s for `maxiter = 500`)
  - Total per hull: **~1.8–2.7 min wall-clock on 8 cores** (~15–22 CPU-core-min/hull; ~880 CPU-core-hours for all 3,021 runs).
- **Force Decomposition (`postProcessing/force_computation/0/force.dat`, iter 319 of `swordfish1`):**
  - Total drag: `1.4999 N` = Pressure drag `0.0899 N` (6%) + Viscous skin-friction drag `1.4100 N` (94%). *(Note: their tabular dataset discarded the pressure/viscous split and saved only total `D`.)*

### 2.3 Bugs & Limitations Discovered in Vardhan et al.'s Code
1. **No physics or non-dimensionalization:** Black-box 9-layer MLP (`SNet` in `student_model.py`) maps MinMax-scaled `[a, b, c, d, n, theta]` $\rightarrow$ dimensional `D` [N]. Cannot generalize to new speeds $U$, water viscosity $\nu(T)$, or geometric scaling.
2. **Dead Dropout Bug (`student_model.py` lines 60 & 67):** `nn.Dropout(p=0.2)` is instantiated inside `forward()` without being applied to any tensor.
3. **Test-Set Selection Leakage (`nn_train.py` lines 177–225):** Saves checkpoints based on `|train_loss - validate_loss|` and selects the best of 5 random restarts (`search_itr = 5`) directly using `test_data.txt`.
4. **Weak GP Baseline (`othe_regressors.ipynb` Cell 12):** Used a linear `DotProduct() + WhiteKernel()` kernel rather than a non-linear Matérn/RBF kernel.

---

## 3. Exploratory Data Visualization Findings (`results/dataset_overview.png`)

We already linked `.venv` (symlinked to `/Users/nallasaikirankumar/Projects/rbc-shear-surrogate/.venv`, which has `PyTorch 2.15.0`, `scikit-learn 1.9.1`, `scipy 1.18.1`, `numpy 2.2.1`, `matplotlib 3.11.2`, `jax 0.12.0.1`) and generated **`results/dataset_overview.png`** across all 3,021 hulls:

1. **Skin-Friction Linear Regime (~97% of hulls):** Total 3D RANS drag scales almost linearly with the exact integrated Myring wetted surface area $S_{\text{wet}}$.
2. **3D Separation / Stall Plume (~50 hulls):** A distinct detached plume shoots up to **$10\text{–}21.17\text{ N}$** at small fineness ratios **$L/d \approx 5\text{–}7$** (blunt, fat hulls like `Max Drag = 21.17 N, d = 198 mm, L = 1.02 m`), where massive boundary-layer separation multiplies pressure drag by ~$3\times$.
3. **Classic Hydrodynamic Optimum ($D/V$ vs. $L/d$):** Plotting drag per liter of displaced payload volume ($D/V$) against fineness ratio $L/d$ reveals a crisp V-shaped minimum around **$L/d \approx 8\text{–}10$** (matching real torpedo AUVs like REMUS-100).
4. **Analytical $L_0$ Physics Agreement:** Our zero-cost ITTC-1957 + Hoerner form-factor formula aligns tightly on the 1:1 line for attached hulls ($\theta < 20^\circ$), proving that >85–90% of the drag variance is analytical boundary-layer physics and the neural model should learn the non-linear **dimensionless form/separation factor**.

---

## 4. Retrospective Non-Dimensionalization Design (Buckingham $\Pi$)

Because $\rho = 1027\text{ kg/m}^3$, $U_\infty = 2.0\text{ m/s}$, $\nu = 1.736124635 \times 10^{-6}\text{ m}^2/\text{s}$, and the exact Myring contour $r(x)$ are known for every hull, we can non-dimensionalize all 3,021 rows **retrospectively and exactly**:

- **Exact Geometric Integrals:**
  - $L = a + b + c$, $\quad S_{\text{wet}} = 2\pi \int_0^L r(x)\sqrt{1 + r'(x)^2}\,dx$, $\quad V = \pi \int_0^L r(x)^2\,dx$, $\quad A_{\text{front}} = \frac{\pi}{4}d^2$, $\quad C_p = \frac{V}{A_{\text{front}} L}$.
- **Dimensionless Inputs ($\Pi$-groups):**
  $$\Pi = \left[\frac{d}{L}, \;\; \frac{a}{L}, \;\; \frac{c}{L}, \;\; n, \;\; \tan\theta, \;\; \frac{d}{2c}, \;\; C_p, \;\; \log_{10}(\text{Re}_L)\right]$$
  *(Note: even at fixed $U_\infty = 2\text{ m/s}$, $L \in [1, 2]\text{ m}$ gives a $2\times$ Reynolds variation $\text{Re}_L \in [1.15\times 10^6, 2.30\times 10^6]$.)*
- **Dimensionless Targets:**
  - Wetted-area drag coefficient: $C_{D,\text{wet}} = \frac{D}{\frac{1}{2}\rho U_\infty^2 S_{\text{wet}}}$
  - Volumetric drag coefficient: $C_{D,\text{vol}} = \frac{D}{\frac{1}{2}\rho U_\infty^2 V^{2/3}}$
  - **3D RANS Form & Separation Factor (Primary PINN Target):**
    $$1 + k_{\text{CFD}} = \frac{C_{D,\text{wet}}}{C_{F,\text{ITTC}}(\text{Re}_L)}, \quad \text{where } C_{F,\text{ITTC}}(\text{Re}_L) = \frac{0.075}{(\log_{10}\text{Re}_L - 2)^2}$$
- **Physics-Informed Autograd Constraints (`torch.autograd.grad`):**
  - Enforce $\frac{\partial \hat{D}}{\partial b} \ge \pi d \tau_w > 0$ (extending the cylinder adds positive skin friction), $\frac{\partial \hat{D}}{\partial d} > 0$, and non-negative separation penalty as $\theta$ increases.

---

## 5. Agreed 3-Phase AUV Project Roadmap

### Phase 1: Benchmark AI Models on Existing 3,021-Hull Dataset (Zero New CFD)
1. Implement clean Myring geometry + retrospective non-dimensionalization (`models/physics.py`).
2. Benchmark **5 models** on `test_data.txt` (fixing Vardhan's test leakage & dead dropout) AND across **low-data scaling curves ($N = 50, 100, 250, 500, 1000, 2400$)** + **out-of-distribution blunt-hull splits**:
   - **M0:** Analytical $L_0$ (ITTC-1957 + Hoerner form factor)
   - **M1:** Clean Replicated Dimensional Black-Box MLP (`SNet`)
   - **M2:** Gradient Boosted Trees (`HistGradientBoostingRegressor`)
   - **M3:** Non-linear Matérn Gaussian Process (with calibrated $\pm 2\sigma$ uncertainty)
   - **M4 (Flagship):** **Non-Dimensional Physics-Informed Neural Network (PINN)** predicting $1 + k(\Pi)$ with `torch.autograd.grad` physical derivative constraints.
3. Document failure modes (especially the $L/d < 7$ separation plume) and log results in `results/replication.md`.

### Phase 2: Run New Multi-Condition CFD Simulations $\rightarrow$ Condition-Aware & Multi-Fidelity AI Models
- Expand beyond Vardhan's single frozen point ($U = 2\text{ m/s}, \alpha = 0^\circ$) to practical ocean conditions (see `knowledge/03-flow-conditions.md`):
  - **Axisymmetric $L_1$ sweeps (fast, ~2–5 s/run):** Velocity $U \in [0.5, 3.0]\text{ m/s}$, water depth/temperature ($\nu, \rho$), laminar–turbulent transition (`kOmegaSSTLM`), inflow turbulence, and biofouling roughness (`nutkRoughWallFunction`).
  - **Targeted 3D $L_2$ runs:** Angle of attack / sideslip ($\alpha \in [0^\circ, 15^\circ]$), near-surface waves / submergence depth ($h/d, \text{Fr}$), and control flaps / stern fins ($\delta_e, \delta_r$).
- Train **Multi-Fidelity Surrogates / PINNs ($S_1, S_2$)** combining $L_0$ physics + $L_1$ axisymmetric + $L_2$ 3D CFD to predict $(C_D, C_L, C_M)$ across conditions.

### Phase 3: Integration into 6-DOF AUV Vehicle Simulator
- Couple the trained Phase 1/2 PINN & GP hydrodynamic models into **Fossen's `PythonVehicleSimulator`** (referenced in `knowledge/06-related.md`, inspired by Lin et al. 2025 *JMSE 13:310*).
- Compare baseline vs. PINN-optimized hulls executing realistic underwater missions (depth changes, wave disturbances, flap/fin maneuvering, and battery energy consumption).

---

## 6. Prerequisite Guided Lab Before Phase 1/2 (`~/Projects/hpc-pinn-lab`)

On **2026-11-20**, the owner decided to first do a **guided, hands-on Linux / HPC / OpenFOAM / PINN lab** in a separate repo (`/Users/nallasaikirankumar/Projects/hpc-pinn-lab`) so they are fully comfortable with Linux VMs, SSH, `rsync`, SLURM, OpenFOAM 1D $\rightarrow$ 2D, and CLI-based Kaggle/Colab GPU training—specifically implementing **Hubert Baty (2024), arXiv:2403.00599v1** (*"A hands-on introduction to Physics-Informed Neural Networks for solving partial differential equations with benchmark tests taken from astrophysics and plasma physics"*) **including running all classical numerical simulation baselines ourselves** so the entire dataset is simulated and logged.

### Current Status of `~/Projects/hpc-pinn-lab` & Local Environment (as of 2026-11-20)
- `~/Projects/hpc-pinn-lab` was created and `git init` completed.
- **Mac environment:** macOS 15.7.5 (`arm64`), `ssh`, `rsync`, `gh`, `gcloud` installed; `~/.kaggle/credentials.json` exists.
- **Last step reached:** Installing **Multipass** via Homebrew hit a permissions error because `/opt/homebrew` was owned by an older macOS account `sainalla` (current user is `nallasaikirankumar`). Fix given:
  ```zsh
  sudo chown -R $(whoami):admin /opt/homebrew
  brew update
  brew install --cask multipass
  multipass launch 24.04 --name hpc-vm --cpus 4 --memory 6G --disk 25G
  ```
- **5-Module Guided Lab Plan (`hpc-pinn-lab`):**
  1. **Module 1:** Ubuntu 24.04 VM + SSH keys + `~/.ssh/config` + `rsync` + `LOG.md`.
  2. **Module 2:** Local single-node **SLURM** (`slurm-wlm` + `munge`) + `sbatch`, `squeue`, `sacct`, job arrays.
  3. **Module 3:** **OpenFOAM 1D $\rightarrow$ 2D** simulation campaigns submitted via SLURM.
  4. **Module 4:** `arXiv:2403.00599v1` Part 1 — 1D classical numerical solvers (dataset generation) + PyTorch PINNs (soft vs. hard BCs) via SLURM.
  5. **Module 5:** `arXiv:2403.00599v1` Part 2 — 2D numerical PDE solver sweeps (Poisson / Grad–Shafranov) + 2D Forward & Inverse PINN trained on GPU via **Kaggle CLI** (`kaggle kernels push`).

---

## 7. Current State of Files in `auv-hull-surrogate`

- `.venv` $\rightarrow$ symlinked to `/Users/nallasaikirankumar/Projects/rbc-shear-surrogate/.venv` (PyTorch 2.15, scikit-learn 1.9, scipy 1.18, matplotlib 3.11).
- `results/dataset_overview.png` $\rightarrow$ generated (4-panel exploratory physics visualization of all 3,021 hulls).
- `knowledge/papers/pdf/` $\rightarrow$ empty (owner has arXiv links `2304.12420` & `2211.10360` to read the base paper first).
- `git status` $\rightarrow$ still on initial branch `main` with no commits yet.
- `models/`, `eval/`, `design/`, `cfd/` $\rightarrow$ empty, ready for Phase 1 once the owner finishes reading the base paper and/or completes `hpc-pinn-lab`.
