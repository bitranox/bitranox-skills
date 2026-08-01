# skill-writer checklist - git-worktrees (2026-08-01, isolated-audit fix)

Source: the first clean-room sweep run by `bitranox:meta-skill-audit`. Ships with plugin 5.127.0.

- [x] WRONG: the Step 0 "submodule guard" claimed `GIT_DIR != GIT_COMMON` is "also true inside git
      submodules". Measured with the skill's OWN commands across three states: plain submodule
      SAME, linked worktree DIFFER, normal checkout SAME. A plain submodule never trips the test,
      so the guard existed for a condition that does not occur.
- [x] Rewritten to state what git actually does and to keep the `--show-superproject-working-tree`
      probe for the case that CAN differ - a submodule with its own worktree attached. The
      downstream handling ("treat a submodule as a normal checkout") was already correct and is
      unchanged.
- [x] Receipt held (`skill_receipt.py start meta-skill-writer`, this session).
- [x] Every QUOTE checked against the real file; every executable claim re-run rather than trusted.
- [x] No session narrative or private provenance added; no machine paths, addresses or hostnames.
