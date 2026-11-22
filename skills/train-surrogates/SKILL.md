---
name: train-surrogates
description: Train and evaluate S1 (hull+condition→C_D) and S2 (hull+angle→C_D,C_L,C_M) surrogates, including physics features, GP uncertainty and a multi-fidelity model (L0 + learned correction). Use after data exists.
---
# Train surrogates
1. Features: raw params + physics features (Re, fineness ratio, wetted area, L0 drag).
2. Models: MLP, GP, gradient boosting, multi-fidelity (predict CFD/L0 ratio).
3. Splits: random test + **unseen conditions** (e.g. hold out the coldest water / highest roughness).
4. Metrics: MAPE, R², calibration of GP intervals; error vs data size.
Done when: results table + one documented failure mode.
