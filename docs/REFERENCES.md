# Key references

Ten core references for this project, grouped by what each one supports. [Back to the project page](../README.md)

Status column: **read** = read in full or in large part for this project; **abstract** = read from the abstract and
summaries only, full text still to read; **standard** = widely cited method reference, details from memory, to verify. Where the author list is not given, take it from the arXiv page.

## Foundations

| # | Reference | Supports | Status |
|---|---|---|---|
| 1 | Vardhan, H. et al. (2023). *Sample-Efficient and Surrogate-Based Design Optimization of Underwater Vehicle Hulls.* [arXiv:2304.12420](https://arxiv.org/abs/2304.12420) | Pilot A: the Myring-hull CFD setup and dataset we replicate | read |
| 2 | Celik, I. B., Ghia, U., Roache, P. J., Freitas, C. J., Coleman, H., Raad, P. E. (2008). *Procedure for Estimation and Reporting of Uncertainty Due to Discretization in CFD Applications.* J. Fluids Eng. 130(7): 078001. [doi:10.1115/1.2960953](https://doi.org/10.1115/1.2960953) | Grid convergence index (GCI) used in our mesh study | standard |
| 3 | Li, Y., Zhang, D.-y., Bao, C.-m., Liu, Q., Hu, J.-m., Liu, Z.-w. (2026). *High-fidelity surrogate-based multidisciplinary multi-objective sequential optimization for AUV design.* Applied Ocean Research 175: 105219. [doi:10.1016/j.apor.2026.105219](https://doi.org/10.1016/j.apor.2026.105219) | Closest marine pipeline: parametric AUV hull → CFD → surrogate with adaptive sampling | read |
| 4 | Karniadakis, G. E., Kevrekidis, I. G., Lu, L., Perdikaris, P., Wang, S., Yang, L. (2021). *Physics-informed machine learning.* Nature Reviews Physics 3: 422–440. [doi:10.1038/s42254-021-00314-5](https://doi.org/10.1038/s42254-021-00314-5) | Framing of the architecture study: PINNs, neural operators, hybrids | standard |
| 5 | *CarBench: A Comprehensive Benchmark for Neural Surrogates on High-Fidelity 3D Car Aerodynamics* (2025). [arXiv:2512.07847](https://arxiv.org/abs/2512.07847) | Closest benchmark design to Study 2: 3D RANS, many shape families, cross-family generalisation | abstract |

## Recent work (2025–2026)

| # | Reference | Supports | Status |
|---|---|---|---|
| 6 | Roche, S., Van Mooy, M., McGuire, N., Cai, L., How, J. P., Girdhar, Y. (2026). *CORL-AUV: CFD Oriented Reinforcement Learning for Autonomous Underwater Vehicles.* [arXiv:2607.09557](https://arxiv.org/abs/2607.09557) (v3) | CFD-trained surrogate drag models for AUV control; later motion work | read |
| 7 | Cooper-Baldock, Z., Santos, P. E., Brinkworth, R. S. A., Sammut, K. (2026). *3D Underwater Path Planning via Generative Flow Field Surrogates.* [arXiv:2606.06077](https://arxiv.org/abs/2606.06077) | Generative surrogates of full 3D flow fields around submarines | read |
| 8 | Kwon, Y., Kim, D.-H., Seo, J., Chung, H. (2025). *A CFD-Based Surrogate for Pump–Jet AUV Maneuvering.* J. Mar. Sci. Eng. 13(10): 2014. [doi:10.3390/jmse13102014](https://doi.org/10.3390/jmse13102014) | CFD-derived manoeuvring surrogate; its stated limit (new geometry needs new CFD) motivates a shape-varying corpus | read (in part) |
| 9 | *WAKESET: A Large-Scale, High-Reynolds Number Flow Dataset for Machine Learning of Turbulent Wake Dynamics* (2026). [arXiv:2602.01379](https://arxiv.org/abs/2602.01379) | Precedent for releasing an underwater-vehicle CFD dataset for ML | abstract |
| 10 | *3D Neural Operator-Based Flow Surrogates around 3D Geometries: Signed Distance Functions and Derivative Constraints* (2025). [arXiv:2503.17289](https://arxiv.org/abs/2503.17289) | Geometry encoding (signed distance fields) and physics constraints for Study 2 | abstract |

## Further reading

| Reference | Use |
|---|---|
| Raissi, M., Perdikaris, P., Karniadakis, G. E. (2019). *Physics-informed neural networks.* J. Comput. Phys. 378: 686–707 | Original PINN method (Study 1b) |
| Krishnapriyan, A. et al. (2021). *Characterizing possible failure modes in physics-informed neural networks.* NeurIPS | Why data-free PINNs fail (Study 1b) |
| Li, Z. et al. (2021). *Fourier Neural Operator for Parametric PDEs.* ICLR | FNO (Study 2) |
| Pfaff, T. et al. (2021). *Learning Mesh-Based Simulation with Graph Networks.* ICLR | MeshGraphNet (Study 2) |
| Wu, H. et al. (2024). *Transolver.* ICML | Transolver (Study 2) |
| Groves, N. C., Huang, T. T., Chang, M. S. (1989). DARPA SUBOFF geometry, DTRC/SHD-1298-01 | Validation geometry |
| *TurtLES* (2026), [arXiv:2611.09567](https://arxiv.org/abs/2611.09567) | Turbulent 3D wake benchmark |
| *ShipNet* (2026), [arXiv:2606.15356](https://arxiv.org/abs/2606.15356) | Geometric deep learning for ship hulls |
| *FG-ConvNO* (2026), [arXiv:2610.33456](https://arxiv.org/abs/2610.33456) | Geometry-aware neural operator for propellers |
