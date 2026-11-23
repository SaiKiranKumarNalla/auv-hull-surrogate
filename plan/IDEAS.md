# Ideas parked until after 2026-12-24

- hpc-pinn-lab (Baty 2024 PINN lab) — paused; Linux/HPC learned inside AUV Phase 2.

## Blood-flow case plugin for the harness (added 2026-11-23)
Not a separate project: once the AUV project is done and the agent/model harness is ready, test the harness on
arterial blood flow as a second CFD case.
- Geometry: patient shapes from the Vascular Model Repository (SimVascular) or the AVT aortic dataset; run our own CFD.
- Related: Image2Flow (arXiv 2402.18236), synthetic aorta surrogates with active learning (arXiv 2610.27130),
  Du et al. aorta CFD (arXiv 2503.12515).
- Check first: dataset licences, whether VMR models include simulation results, and pulsatile-flow cost.
