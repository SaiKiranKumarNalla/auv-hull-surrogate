---
name: git-workflow
description: Teach the owner git step by step (status, branch, add, commit, log, diff, merge, GitHub push, Codespaces) in tutor mode. Use whenever the owner saves work, starts a task branch or asks about git.
---
# Git workflow (tutor mode: give commands, explain, the owner runs them)
**App:** Mac Terminal (or the Codespace terminal), inside `~/Projects/auv-hull-surrogate`.

| Step | Command | Teach |
|---|---|---|
| Where am I? | `git status` | branch, staged vs unstaged vs untracked |
| History | `git log --oneline --graph --all` | commits, branches, HEAD |
| New task branch | `git switch -c day1-axisym-case` | why branches: safe experiments |
| See changes | `git diff` / `git diff --staged` | reading a diff |
| Stage | `git add <file>` (avoid `git add .` until `.gitignore` is understood) | the staging area |
| Commit | `git commit -m "cfd: add axisymmetric wedge case"` | small commits, message style `area: what` |
| Back to main and merge | `git switch main` → `git merge day1-axisym-case` | fast-forward vs merge commit |
| Undo safely | `git restore <file>`, `git restore --staged <file>`, `git revert <hash>` | never `reset --hard` without understanding it |
| GitHub (private repo) | `gh auth login` → `gh repo create auv-hull-surrogate --private --source . --push` | remotes, `origin`, push |
| Daily | `git push` at the end of each day | backup + Codespace sync |

Exercises: Day 0 commit the first paper note on a branch and merge it; Day 1 make a mistake on purpose and undo it
with `git restore`; Day 3 resolve a deliberate merge conflict.
## Done when
The owner can explain status / stage / commit / branch / merge and has pushed the repo privately to GitHub.
