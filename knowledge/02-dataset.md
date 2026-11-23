# 02 · Their dataset (verified 2026-11-23 against the cloned repo)

| File | Rows |
|---|---|
| `cad_cfd_pipeline_surrogate_data_generation/surrogate_data/train_2400.txt` | 2,400 |
| `uuv_optim/data/surrogate/test_data.txt` | 621 |
| `feasible_data_myring.csv` / `data_myring_infeasible.csv` | geometrically valid / invalid hulls |

Columns (space-separated, no header): **a, b, c, d, n, θ, D**
| Col | Meaning | Unit | Range |
|---|---|---|---|
| a | nose length | mm | 50–600 |
| b | cylindrical body length | mm | ~1–1850 (total L = a+b+c ∈ 1000–2000 mm) |
| c | tail length | mm | 50–600 |
| d | diameter | mm | 50–200 |
| n | Myring nose exponent | – | 1–5 as stored. **Confirmed:** the CAD script samples 10–50 and divides by 10 (`run_script.py`: `n = dp[4]/10`) before building and saving the hull, so the stored value is the real exponent |
| θ | tail semi-angle | degrees | 1–50 |
| D | total drag | N | — |

## Fixed flow condition (all 3,021 hulls)
- U = 2.0 m/s, angle of attack 0° (`0.orig/U`)
- ρ = 1027 kg/m³ (`system/forceCoeffs`), ν = 1.736124635e-6 m²/s (`constant/transportProperties`; two older values are commented out)
- OpenFOAM v2112, `simpleFoam` (steady RANS, k-ω SST)
- Example case (swordfish1): total drag 1.50 N ≈ 6 % pressure + 94 % friction (from `force.dat`; `TODO: re-check`). The tables keep only total D.

## Known issues in their code (verified)
1. Dead dropout: `nn.Dropout(p=0.2)` is created inside `forward()` and never applied (`student_model.py`).
2. Test leakage: `nn_train.py` uses `test_data.txt` as its evaluation set during training and picks the best of 5 restarts → optimistic test error.
3. Their GP baseline used a linear kernel (`DotProduct + WhiteKernel`) — `TODO: re-check in othe_regressors.ipynb`.

## Myring profile (as implemented in their `cad_sim/src_code/run_script.py`, lengths in mm)
- Nose, 0 ≤ x ≤ a: r(x) = (d/2) · [1 − ((x − a)/a)²]^(1/n)
- Body, a ≤ x ≤ a + b: r = d/2
- Tail, a + b ≤ x ≤ L, with s = x − a − b: r = d/2 − (3d/(2c²) − tanθ/c)·s² + (d/c³ − tanθ/c²)·s³
