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
