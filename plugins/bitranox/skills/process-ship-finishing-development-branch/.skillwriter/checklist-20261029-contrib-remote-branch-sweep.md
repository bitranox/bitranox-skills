# skill-writer checklist - process-ship-finishing-development-branch (Step 7 remote sweep)

- [x] Change: new Step 7 "Sweep Stale Branches on the Remote" (list from the remote, map to PRs,
      content-check landing with landed.py, propose and delete only on confirmation, offer
      delete_branch_on_merge), core-principle line, one Never and one Always item.
- [x] Mechanism claim measured with a local bare remote: after another clone deleted `feature`,
      `git branch -r` still listed `origin/feature`, `git ls-remote --heads origin` did not,
      `git push origin --delete feature` failed `remote ref does not exist` (exit 1), and
      `git fetch --prune` removed the ghost. The gh calls are GitHub API usage, not run here.
- [x] Cross-skill script named with its home path (`<plugin>/skills/git-worktrees/scripts/landed.py`).
- [x] RED text check (origin/master): `ls-remote` 0, `delete_branch_on_merge` 0.
- [x] GREEN quote-back: "**List what the remote really has, not your remote-tracking refs.**";
      "PROPOSE the list and delete only what the user confirms".
- [x] Description: one trigger added (stale merged or closed branches on the remote); measured
      292 chars. Routing unverified.
- [x] Receipt held (skill_receipt.py start meta-skill-writer) before the first SKILL.md edit.
- [x] Behavioural probes: none dispatched (this batch ran under a no-subagent rule), so RED and
      GREEN are TEXT checks of the skill file: each rule's key fragment counted in
      `git show origin/master:<file>` (0) and in the edited file (>=1). Recorded as a text check,
      not a behavioural pass; no "X does not happen" verdict is claimed.
- [x] ASCII only (no byte above 0x7F in the diff), present tense (history-phrase finder: 0 hits in
      added lines), no private host, VMID, cluster or repo name in the added text.
