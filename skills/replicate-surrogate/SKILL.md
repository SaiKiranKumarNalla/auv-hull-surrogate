---
name: replicate-surrogate
description: Replicate the paper's DNN drag surrogate on their data (train_2400 / test_data) and add GP and gradient-boosting baselines. Use on Day 1–2.
---
# Replicate the surrogate
1. Read `reference/.../trained_NN_surrogate_and_optim_in_loop/` (read-only); identify inputs, scaling, architecture, loss.
2. Write our own loader and model in `models/` (do not copy GPL code unless the repo becomes GPL — see AGENTS.md).
3. Train; report MAPE on their test set vs their 1.85 %. Add Gaussian process and gradient boosting baselines.
Done when: a results table (paper value | ours | notes) is in `results/replication.md` and in REVIEW_QUEUE.
