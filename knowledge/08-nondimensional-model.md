# 08 · Non-dimensional mathematical model

The whole pipeline (geometry, CFD set-up, surrogate inputs and outputs) is written in dimensionless groups.
Dimensional numbers appear only when a case is written for OpenFOAM, which solves in SI units.

## 1. Scales
| Symbol | Meaning | Paper case (verified from their files) |
|---|---|---|
| L | body length (nose to stern; the bill is included for swordfish and sailfish) | varies per design |
| U∞ | free-stream speed | 2.0 m/s |
| ρ | density | 1027 kg/m³ |
| ν | kinematic viscosity | 1.736124635 × 10⁻⁶ m²/s |
| p∞ | reference pressure | 0 (gauge) |

Dimensionless variables:
- x* = x/L
- u* = u/U∞
- p* = (p − p∞)/(ρU∞²)
- k* = k/U∞²
- ω* = ωL/U∞
- ν_t* = ν_t/(U∞L) = ν_t/(ν·Re)

## 2. Governing equations (steady incompressible RANS, k-ω SST)
∇*·u* = 0

(u*·∇*)u* = −∇*p* + ∇*·[(1/Re + ν_t*)(∇*u* + ∇*u*ᵀ)]

Re = U∞L/ν is the only flow parameter. With the paper's U∞ and ν, Re = 1.152 × 10⁶ · (L / 1 m).
The k* and ω* transport equations of SST (Menter 1994; OpenFOAM `kOmegaSST`) carry over unchanged, with every
length scaled by L and every velocity by U∞.

**Gravity, hydrostatic pressure and depth drop out.** For a fully submerged body in incompressible flow, a uniform
pressure offset adds no net force (it is cancelled by the constant hydrostatic field, which only gives the
buoyancy ρgV). So depth enters only through ρ and ν (temperature and salinity), and through the cavitation number
σ = (p∞ − p_v)/(½ρU∞²), as a check.

## 3. Inflow turbulence (paper values made dimensionless)
- Paper inlet: k = 0.01 m²/s² and ω = 57 s⁻¹.
- Turbulence intensity Tu = √(2k/3)/U∞ = **4.1 %**: high for open ocean, typical of a tow tank or wind tunnel.
- Eddy-viscosity ratio ν_t/ν = k/(ων) ≈ **101**.
- We keep both as the paper condition; `inflow.Tu` in the registry varies Tu later.

## 4. Geometry: every length divided by L
- Myring: a/L, c/L, d/L (= 1/fineness), n, tan θ.
- Fins: span/D, root and tip chord over D, t/c, sweep, x_le/L, deflection.
- Fish: thickness t/L, x_max, bill length/L, section width/height ratio, superellipse exponent.

The registry stores dimensional reference values plus these ratios, and surrogates take the ratios plus Re as inputs.

## 5. Outputs (coefficients)
| Coefficient | Definition | Why |
|---|---|---|
| C_D,S = D / (½ρU∞² S_wet) | drag on wetted area | compares directly with ITTC friction C_F; the swordfish/sailfish literature uses it (0.009 / 0.0075) |
| C_D,V = D / (½ρU∞² V^(2/3)) | drag on volume^(2/3) | the AUV design figure of merit (drag per payload volume) |
| C_D,A = D / (½ρU∞² A_frontal) | drag on frontal area | bluff-body comparisons |
| C_L, C_Y, C_m, C_n | lift, side force, pitching and yawing moments (moments use reference length L about the centre of volume) | for Phase 3 control |
| C_p, C_f | surface pressure and skin-friction fields | for field surrogates |
| 1 + k = C_D,S / C_F,ITTC(Re) | form factor | the Phase 1 physics feature |

The paper's `forceCoeffs` used Aref = body volume (2.14 × 10⁻³ for swordfish1), which is not an area. Their
dataset stores drag in newtons, so that doesn't affect it; we recompute all coefficients from the logged forces.

## 6. Similarity and what "same conditions as the paper" means
- **Same dimensional conditions** (U∞ = 2 m/s, the same ρ and ν, the same inlet k and ω): each design then gets its own
  Re (0.7–5 × 10⁶ across the 20 references). This is what the first sample run uses.
- **Same Re:** scale U∞ (or ν) so that Re matches. This isolates shape effects and is a later run.
- **Mesh in units of L:**
  - base cell 0.0723 L;
  - domain from 1 L ahead to 3 L behind the body centre, and ±8 × the largest half-width sideways;
  - surface refinement levels 5–7, a level-2 refinement box, 2 prism layers with wall functions.

  These match the paper's swordfish1 case (55 × 5 × 5 base cells, 0.08 m for L = 1.107 m).
