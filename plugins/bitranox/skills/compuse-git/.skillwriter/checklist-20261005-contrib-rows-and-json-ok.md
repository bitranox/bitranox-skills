# skill-writer checklist - compuse-git (2026-10-05, contrib rows C3/C82 + git_state --json ok)

Two new quick-reference rows (asserting a clean tree with `&& echo CLEAN`; `git reset --keep`
untracking another session's staged file) and one sentence added to the `git_state.py` tools
paragraph documenting `--json` `ok` semantics.

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. Test approach: retrieval - two questions, each answered with a
      direct quote of the governing row or NONE.
- [x] RED (pre-change text, pasted): "Does `git status --porcelain && echo CLEAN` prove the tree
      is clean?" - NONE (no row addresses the idiom; an agent without the row would reason from
      first principles and could go either way). "What happens to a file another session staged
      after `git reset --keep HEAD~1`?" - NONE.
- [x] Reproduced both claims against real git before writing the row (not reasoned from
      prose): a scratch repo showed `git status --porcelain && echo CLEAN` prints CLEAN whether
      the tree is dirty or clean (the `&&` only reflects `status`'s own exit code, not
      dirtiness); a second scratch repo showed a session-staged file (`A other.txt`) becomes
      untracked (`?? other.txt`) after `git reset --keep HEAD~1` while its content survives on
      disk, and `git fsck --unreachable` lists the staged blob as dangling, confirming the
      `update-index --cacheinfo` recovery path.
- [x] GREEN (new rows pasted): same two questions now answer with a direct quote of the new row
      text ("asserts NOTHING", "becomes UNTRACKED... while its on-disk CONTENT survives").
- [x] `git_state.py --json` `ok` semantics checked against the script source
      (`skills/compuse-toolbox/scripts/git_state.py`): `ok = rc != 2` in both `_main_files` and
      `_main_repos`, so `ok` is true on exit 1 too - the added sentence matches the code.
- [x] GREEN diffed against RED in both directions: nothing removed, two gaps closed.
- [x] Description unchanged - no routing keyword moved.
- [x] No address, MAC, hostname or machine path added.
- [x] Present tense, no session narrative, no private provenance.
