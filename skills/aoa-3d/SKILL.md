---
name: aoa-3d
description: Run the small 3D angle-of-attack set (C6) with the paper's snappyHexMesh-style template on a coarse, mesh-checked grid, extracting drag, lift and pitching moment. Use after the L1 sweep is running.
---
# 3D angle of attack
1. Study the reference template (`aoa_0` case) read-only; write our own template with `aoa` and our mesh settings.
2. Mesh study at one hull and 8°: 3 meshes.
3. Run ~50–100 cases: ~10 hulls × angles {0, 2, 4, 8, 12}° × 2 speeds.
Done when: C_D, C_L, C_M table with converged runs; 0° results agree with L1.
