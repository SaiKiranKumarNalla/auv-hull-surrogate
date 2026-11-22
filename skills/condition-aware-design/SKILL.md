---
name: condition-aware-design
description: Use the surrogates to find the best hull for different practical missions (cold slow survey, warm fast transit, rough long deployment) and verify the optima with CFD. Use for the final demonstration.
---
# Condition-aware design
1. Objective: minimum drag (or drag per volume) under constraints (fixed volume / payload length).
2. Optimise per mission condition (Bayesian optimisation or CMA-ES on the surrogate).
3. Verify the top 3 hulls per mission with L1 (and L2 if angle matters).
4. Show how the optimal hull shifts with condition.
Done when: figure + verification table + plain-language summary in the README.
