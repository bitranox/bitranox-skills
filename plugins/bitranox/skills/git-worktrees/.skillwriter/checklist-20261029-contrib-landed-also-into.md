# skill-writer checklist - git-worktrees (landed.py --also-into, four rules)

- [x] Change: `landed.py --also-into REF` (repeatable; the commits count as landed when the tip is
      an ancestor of REF; never covers uncommitted files; output field `also_into`), Step 4
      fallbacks for a branch a later branch rewrote and the `branch -d` stale-master refusal,
      Step 3 paragraphs on gitignored gate inputs and a worktree under $HOME, a quick-reference
      row on `git worktree move` across filesystems.
- [x] Code TDD: 6 new tests in tests/test_landed.py; RED 5 failed (argparse rejected
      `--also-into`) and the premise test passed (x1 reads NOT LANDED); GREEN 25 passed; reverting
      only the `or any(c["contains"] ...)` line failed 2 (`assert 1 == 0`), restored green.
- [x] Mechanism claims measured in throwaway repos: after `git push origin topic:master` with a
      lagging local master, `git branch -d topic` exited 1 ("not fully merged") while
      `merge-base --is-ancestor topic origin/master` exited 0; a gitignored file in the main
      checkout was absent from a new worktree; strace showed `git worktree move` calling
      `rename(2)`, which rename(2) documents as EXDEV across mounts.
- [x] RED text check (origin/master SKILL.md): `--also-into` 0, `not fully merged` 0,
      `cross-device` 0, `outside `$HOME`` 0; the Step 3 text had no gitignored-input rule.
- [x] GREEN quote-back: "**A new worktree does not have the main checkout's GITIGNORED files.**";
      "prefer a base outside `$HOME`"; "Pass that ref with `--also-into <ref>`"; "`-d` judges
      "fully merged" against the branch's upstream, or against HEAD"; "`git worktree move`
      renames the directory (`rename(2)`)".
- [x] Description: unchanged (572 chars).
- [x] Receipt held (skill_receipt.py start meta-skill-writer) before the first SKILL.md edit.
- [x] Behavioural probes: none dispatched (this batch ran under a no-subagent rule), so RED and
      GREEN are TEXT checks of the skill file: each rule's key fragment counted in
      `git show origin/master:<file>` (0) and in the edited file (>=1). Recorded as a text check,
      not a behavioural pass; no "X does not happen" verdict is claimed.
- [x] ASCII only (no byte above 0x7F in the diff), present tense (history-phrase finder: 0 hits in
      added lines), no private host, VMID, cluster or repo name in the added text.
