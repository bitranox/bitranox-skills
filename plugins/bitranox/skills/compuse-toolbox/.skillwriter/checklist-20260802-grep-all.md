# skill-writer checklist - compuse-toolbox (add the `grep_all` jig)

Change: ship a search that cannot silently skip gitignored files, after the defect bit twice in one
session. Reference-skill edit plus a new tested script.

## PLAN
- [x] Skill type: reference (tool index with a per-tool rationale).
- [x] Trigger is measured, not hypothetical: in one session the session `grep` reported 17 of 43
      memory levels, and 1 of 4 files carrying a dead doc reference. Both under-counts were acted on
      as complete, and the second one nearly shipped a "fixed everywhere" claim that was false.
- [x] Checked it is not already shipped: `compuse-toolbox` names 7 tools, none of them a
      completeness-preserving search; `claim_check` is the adjacent one but answers "is this present
      in THESE files", not "find every file that has it".

## RED
- [x] 11 tests written first, failing on a missing module. Each pins one behaviour: matches inside a
      gitignored file are reported; the stderr summary quantifies how many a normal grep would miss;
      matches go to stdout and the summary to stderr so the stream stays parseable; exit 0/1 split;
      the JSON envelope carries a per-match `gitignored` flag; JSON still emitted on the no-match
      path; `--glob` filtering; a bad regex exits 2 rather than looking like zero matches; a missing
      path exits 2; it works outside a git repo; `.git` internals are never searched.
- [x] The bad-regex test exists because "nothing matched" and "the pattern never compiled" would
      otherwise print identically - the same vacuous-answer shape this store already records twice.

## GREEN
- [x] 11 pass.
- [x] Validated against the REAL case, not only the fixture: on this tree it reports 73 pointer
      blocks with 55 gitignored, matching `find`'s ground truth of 73, where the session grep returns
      17. The stderr line names the 55 explicitly, so the gap is stated rather than left to be
      noticed.
- [x] Skip list kept deliberately small (`.git`, vendored and cache dirs). A broad skip list would
      reintroduce the silent under-reporting the tool exists to prevent - noted in the source.
- [x] CLI contract per `every-cli-needs-a-machine-readable-mode`: `--json` envelope, JSON on the
      failure path, warnings and the summary on stderr, format-independent exit codes.
- [x] Description clause added names the SYMPTOM ("sweeping a repo for every occurrence without
      silently skipping gitignored files"), not the implementation.
- [x] Table row and rationale bullet follow the established shape; table realigned by the hook.

## REFACTOR
- [x] `gitignored()` batches by repo root and runs `git check-ignore --stdin` once per root rather
      than once per file; `check-ignore` exiting 1 for "nothing ignored" is handled as normal, not
      as an error.
- [x] Binary files sniffed and skipped rather than decoded and matched as mojibake.

## Deliverables
- [x] `scripts/grep_all.py`, `tests/test_grep_all.py` (11 tests), SKILL.md row + bullet + description.
- [x] `plugin.json` bumped; `skill_triggers.json` and `docs/skills.md` regenerated (description changed).
