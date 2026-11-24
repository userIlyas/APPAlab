# Publication Git plan — approval required

Destination only: https://github.com/userIlyas/APPAlab.git (public). Read-only GitHub API checks confirmed authenticated user userIlyas (id 60938770), admin/push rights, no branches. No writes made to GitHub during preparation.

Local repository: /home/leany/memory-tracing/APPAlab. It is independent of the original upstream clones; no nested .git, submodules, copied object databases or original history.

1. Local main bootstrap commit: root `.gitignore` only. This supplies a minimal default branch in the empty remote.
2. Local `publication/initial-agentic-banking-openappa` branch: complete reviewed source snapshot, integration/archive, documentation and provenance, in a source-import commit. Git executable modes preserved from upstream index; no WSL accidental all-executable tree.
3. Inspect local diff/name list/modes, run source/hash/Compose/static checks, local secret scan, every reachable history blob scan, confirm no gitlinks or forbidden credentials/artifacts. Git author uses GitHub noreply identity, not an inferred private email.
4. Present final structure, exhaustive file list (`PUBLICATION-FILES.txt`), checksum manifest, security results, test limitations and local commit ids to owner. **STOP for explicit approval before any push/PR.**
5. After approval, re-read destination branches/permissions. If remote changed from empty, stop and reconcile with owner rather than overwrite anything.
6. `git push -u origin main` — create minimal base. Verify remote default branch; if GitHub did not choose main, set main as default (only after the same approval).
7. `git push -u origin publication/initial-agentic-banking-openappa`.
8. `gh pr create --repo userIlyas/APPAlab --base main --head publication/initial-agentic-banking-openappa --title "Initial publication: Agentic Banking Lab + OpenAPPA taint integration" --body-file docs/PULL_REQUEST.md`.
9. Verify PR base/head/files; return URL and coverage/limitations. Do not merge PR, write upstream repos, enable deployment, or start refactoring.

No reset --hard, clean -fd, force push, auto merge or upstream push. Push approval is not authorization to run banking/LLM E2E. Active tests would require their own exact instance/sink scope.
