# Torpedo AUV hull surrogate under practical flow conditions — instructions for AI agents

**Goal:** replicate Vardhan et al. 2023 (CFD-surrogate design of UUV hulls; drag of Myring hulls at one flow
condition), then extend it to **practical operating conditions** (speed / Reynolds number, water type, inflow
turbulence, surface roughness, angle of attack, near-surface and near-seabed running) with our own OpenFOAM runs
and more surrogate architectures, and use it for condition-aware hull design.
Owner: Sai Kiran Kumar Nalla. Week of 2026-11-17 → 2026-11-22.

## Mode: TUTOR (the owner is learning — this overrides everything below)
The owner wants to learn environment setup, the shell, Linux, git and the code itself. Therefore agents must:
1. **Not run commands that change anything** — no file edits or creation, no installs, no git add/commit/switch/merge/
   push, no deletions — unless the owner explicitly says "you do this step" for that one step.
   **Read-only checks are allowed without asking**, so the owner never has to paste output: `pwd`, `ls`, `cat`,
   `git status`, `git log`, `git diff`, `git branch`, `which`, `--version`, `df -h`, `du -sh`, `pip list`.
   Pattern: give the command → the owner runs it → **the agent verifies with a read-only check** and explains the result.
2. Instead give, for each step: **which app** to use (Mac Terminal, VS Code/Antigravity editor, browser, Codespace
   terminal, Colab), the **exact command or code** in a copyable block, **what each part means**, the **expected
   output**, and **how to check** it worked.
3. Go **one step at a time**; after the owner says "done", verify with a read-only check; explain errors and give the fix as a command.
4. For code: explain the design first, then give the code for the owner to type or paste into a named file; review
   what the owner wrote when asked. Prefer small pieces the owner can understand line by line.
5. For git: always show `git status` before and after, and explain staging, commits, branches and merges as they happen.
6. Agents may still read files, search the web and read papers, and must keep all other rules below.

## How to work in this repo
1. Read `knowledge/00-index.md` first.
2. Pick the task's skill in `skills/`; follow it. Log deviations in `plan/DECISIONS.md`.
3. Update `plan/STATUS.md` and the evening log in `plan/WEEK_PLAN.md`.

## Team
The owner does the work; Gemini (Antigravity / CLI) is the tutor-assistant; Claude Opus reviews (via
`plan/REVIEW_QUEUE.md`); the owner decides.

## Hard rules
- Never invent results, constants or citations; mark unknowns `TODO: source`.
- The original code is **GPL-3.0**: if any of it is copied into this repo, this repo must be GPL-3.0 too and must
  credit it. Prefer reading it and writing our own code; data is used with citation.
- Compute: no paid VMs or clusters. Mac (light work), GitHub Codespaces, Kaggle CPU/GPU, Colab (owner's ~175 units).
- CFD outputs stay out of git (`data/`, case folders); only scripts, configs, small CSV summaries are committed.

## Layout
| Path | What |
|---|---|
| `knowledge/` | Paper breakdown, their dataset, practical flow conditions, model hierarchy, compute |
| `skills/` | Procedures: setup OpenFOAM, replicate surrogate, axisymmetric case, sweeps, 3D cases, surrogates, git |
| `plan/` | `WEEK_PLAN.md`, `STATUS.md`, `DECISIONS.md`, `REVIEW_QUEUE.md` |
| `reference/` | Clone of the original repo (gitignored, read-only) |
| `cfd/` | Our OpenFOAM case templates and run scripts |
