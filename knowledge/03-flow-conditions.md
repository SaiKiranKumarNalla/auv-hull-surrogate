# 03 · Practical flow conditions for torpedo AUVs

Reference vehicle class: REMUS-100-like, diameter ≈ 0.19 m, length ≈ 1.6 m (`TODO: verify from a public spec`).
Kinematic viscosity ν: fresh water 20 °C ≈ 1.0e-6 m²/s; seawater 4 °C ≈ 1.6–1.7e-6 m²/s (`TODO: verify, ITTC tables`).
Reynolds number on length Re_L = U·L/ν ≈ 0.5e6 – 5e6 across the conditions below.

| # | Condition | Why it matters in practice | Parameter range | How to simulate | Cost |
|---|---|---|---|---|---|
| C1 | **Speed / Reynolds number** | Slow surveys vs fast transits; drag ∝ U² but C_D changes with Re | 0.5 – 3 m/s | 2D axisymmetric RANS (wedge), vary U | cheap |
| C2 | **Water type** (cold seawater, warm seawater, fresh river/lake) | ν and ρ change Re and drag; Nordic fjords vs tropics vs rivers | ν, ρ from temperature & salinity | same as C1, change ν, ρ | cheap |
| C3 | **Laminar–turbulent transition** | At low Re a laminar nose region lowers drag; fully turbulent RANS over-predicts it | Re_L < ~3e6 | compare k-ω SST vs a transition model (`kOmegaSSTLM` in OpenFOAM) | cheap |
| C4 | **Inflow turbulence** | Rivers and tidal channels are turbulent; open ocean is calm | turbulence intensity 0.1 % – 10 % | inlet k, ω | cheap |
| C5 | **Surface roughness / biofouling** | Long deployments roughen the hull | equivalent sand roughness 0 – 1 mm | rough-wall functions (`nutkRoughWallFunction`) | cheap |
| C6 | **Angle of attack / sideslip** (manoeuvres, depth changes, cross-currents) | Lift, side force and pitching/yaw moment for control and stability | 0° – 15° | **3D** RANS (their template already has `aoa`) | medium |
| C7 | **Near the seabed** (bottom-following surveys) | Ground effect changes lift and moment | gap / D = 0.5 – 5 | 3D (or 2D planar approximation) with a wall | medium |
| C8 | **Near the free surface** (shallow running, launch/recovery) | Wave-making resistance, suction toward the surface | depth / D = 1 – 5; Froude number | 3D two-phase `interFoam` | expensive (stretch) |
| C9 | **Waves** (orbital velocities near the surface) | Unsteady forces, added mass | linear waves, H, T | unsteady inflow or two-phase | expensive (stretch) |
| C10 | **Sheared current** (near-bed / river velocity profile) | Non-uniform inflow → moments | power-law inlet profile | 3D with profiled inlet | medium (stretch) |

Uniform steady currents are equivalent to a change in relative speed (C1) — not a separate case.
Priority for this week: **C1–C5 (axisymmetric, cheap, many runs)** + **C6 (3D, a small set)**. C7–C10 are stretch/future.

## Phase 2 additions requested 2026-11-23

### Environment (extends C2)
| # | Condition | Physics | How to simulate | Cost |
|---|---|---|---|---|
| C11 | **Depth / hydrostatic pressure** | Water is incompressible here, so a uniform pressure offset does **not** change drag. Depth matters only through (a) temperature and salinity at that depth → ρ, ν (use C2), (b) cavitation margin (irrelevant at < 3 m/s below a few metres), (c) hull compression (structural, not CFD) | depth → T, S profile → ρ, ν; check cavitation number σ = (p∞ − p_v)/(½ρU²) | cheap |
| C12 | **Salinity / density** | ρ from 998 (fresh) to ~1028 kg/m³; ν changes ~5 % with salinity, ~70 % with temperature | ρ, ν from TEOS-10 / ITTC 7.5-02-01-03 tables (`TODO: verify`) | cheap |
| C13 | **"Pollution" effects** | Dissolved pollutants and microplastics barely change bulk ρ, ν. The real effects are **biofouling / oil film → roughness** (C5) and **suspended sediment → effective density and viscosity** (turbid rivers, ~1–5 %) | roughness via C5; sediment via a modified ρ, ν (mixture model only if needed) | cheap |

### Design features (new: break axisymmetry → 3D)
| # | Feature | Why | How to simulate | Cost |
|---|---|---|---|---|
| D1 | **Tail fins / control surfaces** (cruciform, X-tail) | 10–30 % extra drag; stability and manoeuvring | 3D RANS; parametrise span, chord, sweep, NACA section, position | medium–high |
| D2 | **Flap / rudder deflection** (incl. a tall flap) | Control forces and moments vs drag penalty | D1 + deflection angle δ; 3D | high |
| D3 | **Angle of attack with fins** | Lift, side force, pitching moment for Phase 3 (Fossen model coefficients) | combine C6 + D1 | high |
| D4 | **Thruster** (later) | Thrust deduction and wake fraction change net drag | cheapest: actuator disk (momentum source); full: rotating propeller (MRF or AMI) | medium → very high |

### Compute reality (free tier only)
- Axisymmetric 2D (C1–C5, C11–C13): ~1–2 min per run → thousands of runs possible.
- 3D hull ± fins (C6, D1–D3): ~0.5–3 h per run on 2–4 cores → tens to a few hundred runs. Use symmetry planes,
  coarse meshes plus a grid-convergence subset, and multi-fidelity surrogates (many 2D + few 3D).
- Resolved propeller (D4 full): only a handful of runs; prefer the actuator disk.
