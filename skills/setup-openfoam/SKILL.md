---
name: setup-openfoam
description: Tutor the owner through setting up a GitHub Codespace with OpenFOAM, Python and the repo, and running the tutorial case. Use first.
---
# Setup OpenFOAM (tutor mode: the owner runs every command)
1. Mac: `brew install git gh python@3.12`; `gh auth login`; private GitHub repo for this folder (see git-workflow).
2. Open the repo in a **GitHub Codespace** (4-core if available).
3. Install OpenFOAM (openfoam.org or openfoam.com packages via `apt`; record which and the version in DECISIONS.md).
4. Run the official `simpleFoam` pitzDaily tutorial; explain the case structure (`0/`, `constant/`, `system/`).
5. Python venv: numpy, pandas, scikit-learn, torch, matplotlib, pyyaml.
Done when: the tutorial runs and the owner can explain the case folders. Stop the Codespace when idle.
