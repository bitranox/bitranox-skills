# skill-writer checklist - git-worktrees (2026-11-09, queued contributions)

- [x] Entries covered: D20, D21, D22, D23, D24, D25, D26.
- [x] Mechanism: Commands executed in a throwaway repo: a pruned worktree re-registered with `git worktree add --no-checkout`, copied `.git` and rewritten admin `gitdir`, then `git reset`, leaving the modified and untracked files intact, `git worktree list` listing it; the throwaway-index tree plus `diff --raw --no-abbrev` listed only the changed blobs and `ls-files -o -i --exclude-standard` the ignored file; `git worktree add` on the existing dir refused and `repair` failed; `landed.py` on an orphan exits 2; `n=$(git cherry bad topic | grep -c '^+')` printed 0 with cherry exit 128; `git check-ignore -q` with a directory-only pattern: no slash rc 1, trailing slash rc 0, plain pattern both rc 0, unlisted rc 1; `uv sync --extra dev` rc 0 with the extra, rc 2 without (fall-through to `uv sync`, rc 0).
- [x] RED text check (fragment counts, pre-edit HEAD vs edited file): `red baseline can be the dependency` 0->1; `FOLDER NAME` 0->1; `uv sync --extra dev` 0->1; `Removing many finished` 0->1; `registration was pruned` 0->1; `check-ignore -q "$LOCATION/"` 0->1.
- [x] GREEN text check: every fragment is present in the edited file at the place a reader of that situation meets it.
- [x] Behavioural probes: none dispatched in this batch, so RED and GREEN are TEXT checks of the skill file, not a behavioural pass; no "X does not happen" verdict is claimed.
- [x] Width and fence check over the added lines printed nothing; the paragraph after each insertion was read.
- [x] ASCII only, present tense (history-phrase finder over the added lines: no hit), no private host or repo name.
- [x] Skill decisions read first (`skill_decisions.py show`); no rejected or removed decision reversed.
- [x] Decisions: none - additive guidance from queued contributions, no recorded decision is reversed.
