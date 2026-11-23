# Parametric design (Tier 1 + appendages)

Requires `pip install manifold3d` (boolean union of hull and fins).

| File | What |
|---|---|
| `hull_families.py` | Tier-1 hull profiles r(x): Myring, NACA body, Haack (Von Kármán / LV), elliptic+parabolic, flat stern, fish-like |
| `appendages.py` | Fins: trapezoid planform, NACA 00tt section, sweep, taper, all-moving deflection, trailing-edge flap, any roll angles; `build(design)` fuses everything into one watertight solid |
| `quality.py` | Geometry gate: `repair` (clamps needle tips, thin or over-long fins) and `check` (watertight, one solid, genus 0, tip thickness, collar detector); `python design/quality.py` writes `quality/report.csv` |
| `render_closeups.py` | Close-ups of bill, fin-root and fin-tip regions (`quality/closeups_*.png`) |
| `sampler.py` | Parameter ranges (`RANGES`) and `sample(rng)` for the corpus; `python design/sampler.py` builds 200 random designs as a check |
| `specs/*.json` | Hand-made example designs (cruciform, X-tail with flaps, tall rudder, bow planes, flat stern, fish with dorsal/pectoral/anal/caudal fins) |
| `samples/`, `samples_full/` | Binary STL exports (bare hulls; hulls with appendages) |

Each design is a JSON dict, so every corpus run stores the exact geometry recipe next to its CFD results.
Bills are blended into the body (one surface), fin roots are filleted and fin tips rounded (see `../plan/HARNESS.md`).
Not yet modelled: hinge gaps, fin dihedral, non-symmetric sections, propeller/thruster.
