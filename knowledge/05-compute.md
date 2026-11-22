# 05 · Compute
| Where | Use |
|---|---|
| Mac | Code, git, plotting, L0 |
| GitHub Codespaces (free ~60 h/month, 2–4 cores) | OpenFOAM install (`apt` / official image), axisymmetric cases, scripting |
| Kaggle CPU notebooks (4 cores, background runs) | L1 sweeps overnight |
| Kaggle / Colab GPU | Surrogate training (small tabular data → CPU is often enough) |
Their 3D cases used 8 cores; on 4 free cores expect ~1–3 h per 3D case → keep L2 to ~50–100 cases with a coarse mesh
(mesh-sensitivity study on 3 meshes first). Delete CFD fields after extracting forces (their README warns about disk).
