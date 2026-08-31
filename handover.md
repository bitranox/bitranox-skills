# STALE - read 2026-08-31, work continued. The standing items it carried now live in OPEN-WORK.md, which is the file to read.

## State

`HEAD == origin/master == d4b5068`, plugin `5.296.1`, released to PyPI and GitHub, CI green.

**The working tree is NOT clean, and the modified files are not mine.** A CONCURRENT session is
working in this same checkout:

```
 M plugins/bitranox/skills/coding-python-textual/SKILL.md
 M plugins/bitranox/skills/coding-python-textual/widgets/progress_bar.md
```

Leave them. That session also shipped `5.295.3` and `5.296.0` mid-flight here. Commit with an
explicit pathspec, never `git add -A`, and assert the expected version before any bump - that
assert is what stopped this session overwriting their `5.296.0` with a stale `5.295.3`.

## Shipped from this session

| version | what                                                    |
|---------|---------------------------------------------------------|
| 5.294.2 | `check_version_sync` reports the states it used to pass |
| 5.294.3 | dropped 5.294.2's hand-rolled TOML fallback             |
| 5.295.0 | new jig `anchor_edit`                                   |
| 5.295.1 | its backup keyed on recoverability, not tracking        |
| 5.295.2 | first-write-wins backup (superseded)                    |
| 5.296.1 | numbered backups per run                                |

## Decided, with the reason - do not reopen

- **`check_version_sync` states an invariant.** Every way of failing to learn a version is
  reported, because an empty failure list is what it returns when the versions AGREE. The only
  skip is a checkout with no `pyproject.toml`, decided by whether the FILE EXISTS - a different
  question from whether a version could be read out of it, and collapsing the two into one `None`
  is what hid three of the four quiet paths.
- **No fallback TOML parser below 3.11; it reports instead.** One shipped in 5.294.2 and was
  removed: a hand-rolled reader answers wrongly in silence, only below 3.11 where nothing
  exercises it, and it left a malformed pyproject passing there while firing on 3.11+. A 3.10
  contributor is now blocked by the gate. That is accepted - loud beats silent.
- **`anchor_edit` is scoped to the SCRIPTED and bulk path.** The baseline arm showed an agent
  handles a single interactive edit well without it, because the Edit tool already refuses a
  non-unique `old_string`. The table row says so rather than claiming the whole ground.
- **Its backup asks whether git could RESTORE the file (tracked AND clean), not whether git tracks
  it.** Both questions are asked separately: `git status --porcelain` is empty for a gitignored
  file exactly as for a clean one.
- **Backups are numbered and unbounded** - `.bak`, `.bak.1`, `.bak.2`, higher newer. A safety copy
  that deletes itself after N runs is not one.

## Owed

- **One memory-store update, deliberately not written.** The tree-top fact
  `feedback-restore-an-experiment-from-a-copy-not-from-git-while-the-work-is-uncommitted` should
  gain the AUTOMATED form of its own rule: a tool deciding whether to save a file aside must key on
  recoverability (tracked AND clean), not on tracking, and must number its copies rather than reuse
  the name. Skipped because a dream is consolidating the store in another session and an upsert
  supplies the whole body, so a stale read would clobber their edit. Do it once the dream is done.

## Deliberately not done

- **The scripts-path question, and it is skill-wide.** Two of three test arms stalled on how a
  COMMITTED script names a jig's path; the installed plugin path is version-stamped, so hard-coding
  it breaks on the next update and a glob plus `tail -1` sorts lexicographically. It affects all
  the `compuse-toolbox` jigs equally, so it belongs in the table preamble or a documented vendoring
  step, with its own RED/GREEN. Recorded in
  `plugins/bitranox/skills/compuse-toolbox/.skillwriter/checklist-20260831-anchor-edit.md`.
- Carried over, untouched: the 153 older changelog entries (a declared boundary at the top of
  `CHANGELOG.md`, not a backlog), the store-repo squash (needs a go, the store has a private
  remote), the 4 remaining audit slices (prior work in `/tmp/scriptwave-2026-08-28/`), and
  consolidating `transcript_index` against the shipped `jsonl_grep` + `transcript_tail`.

## Files that matter

- `plugins/bitranox/skills/compuse-toolbox/scripts/anchor_edit.py` + `tests/test_anchor_edit.py`
- `plugins/bitranox/hooks/repo-gate.py` - `pyproject_version`, `check_version_sync`
- `plugins/bitranox/skills/compuse-toolbox/.skillwriter/checklist-20260831-anchor-edit.md`

## The exact next action

**Zero-pad the numbered backup: `.bak.001`, not `.bak.1`. The user asked for this after the work
above was released, so it is requested, not optional.** Non-padded numbering sorts `.bak.10` before
`.bak.2` in `ls`, which is the lexicographic trap `newest` exists to prevent, and a manual restore
reads that listing.

Change `next_backup_path()` in
`plugins/bitranox/skills/compuse-toolbox/scripts/anchor_edit.py` - it currently builds
`f"{path.name}.bak.{index}"`. Note the padding does NOT fix ordering past 999 (`.bak.1000` sorts
before `.bak.999`), so decide whether to widen there or accept it, and say which in the changelog.

Tests to update in `tests/test_anchor_edit.py`: `test_every_run_keeps_its_own_backup` and
`test_backups_number_upward_without_a_gap` both assert the literal `.bak.1` / `.bak.2` names.
RED-verify against the current behaviour before changing the code. Then bump, changelog, gate,
commit with a pathspec, push, watch CI.

The owed memory update above is the other outstanding item.

**Then: reap a backup once git can restore the file.** Requested straight after the padding, in
these words: "once its commitet, delete those baks". Read as a feature for `anchor_edit`, not a
cleanup chore - the repo currently holds NO `.bak` files (checked), and the ones from this
session's probes are in the session scratchpad, which is discarded anyway.

It is coherent with the tool's own rule: a backup exists precisely because git could NOT restore
the file, so once git can, the copy is litter. `is_recoverable_from_git()` already answers exactly
that question and is the seam to build on.

CONFIRM THE SHAPE WITH THE USER BEFORE BUILDING - two readings, and they differ:

- a separate verb (`anchor_edit reap FILE`) run after committing, which never deletes as a side
  effect of an edit; or
- automatic reaping at the START of the next edit to that file - if the file is now tracked AND
  clean, its earlier `.bak*` are redundant, so remove them before writing the new one.

The second is tidier and the more likely intent, but it deletes files as a side effect of an
unrelated edit, which is the kind of thing a safety tool should not do quietly. Whichever is
chosen: never reap a `.bak` this tool did not write, the reap must be refusable (`--no-reap` or
dry-run), and it must report every path it removed.

## How to verify the state still stands

```bash
cd /media/srv-main-softdev/projects/public/KI/bitranox-skills
env -u VIRTUAL_ENV uv run --with pytest --with PyYAML --with lxml --with defusedxml \
  --with ruamel.yaml --with httpx2 python plugins/bitranox/hooks/repo-gate.py --pre-push
```

Expect `repo-gate: all checks passed`. The count moves as the concurrent session lands work; it was
**4114 passed / 13 skipped / 1 xfailed** at `d4b5068`. The xfail is the documented write-then-run
gap and is STRICT.

---

Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not delete
it - if this session ends badly it is the only record of where things stood.
