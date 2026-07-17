# skill-writer checklist - compuse-git (2026-07-18, gate-&&-commit sequencing)

Change: added a Quick-reference row - chain a quality gate before commit/push with && so a RED
gate blocks the commit; a newline- or ;-separated sequence runs the commit regardless of the
gate's exit status and pushes a red state. Notes it is distinct from the compound-job rc-misread.

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED: without the row an agent writes `pytest ; git commit` (or newline-separated) and the
      commit lands even when tests are red - a real, recurring miss (fact
      feedback-chain-gate-commit-so-a-red-gate-blocks-the-commit).
- [x] GREEN: row states the trigger, the && fix, and why ; / newline discards the gate exit; explicitly
      differentiates from the existing gated-rc-from-log lesson so the two do not read as duplicates.
- [x] Scope: universal shell/git mechanics; not project-specific.
- [x] Security scan: prose only, no secrets/hosts/paths.
- [x] CSO description: unchanged (body edit; "commit" / "a git command fails confusingly" cover retrieval).
- [x] Token budget: one table row; skill stays compact.
