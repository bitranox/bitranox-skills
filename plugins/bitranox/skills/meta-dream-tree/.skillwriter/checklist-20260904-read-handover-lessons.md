# checklist-20260904-read-handover-lessons

Change under test: step 1 (capture first) names `## Lessons for the next nap` in a repo's
`handover.md` as capture input. A work session that hands over RECORDS its lessons there and does
not capture them itself (see `meta-context-watcher`'s checklist of the same date), so without a
reader on this side the lines would never reach the store.

## PLAN

- [x] Skill type: technique (a procedure step gains one input). Test approach: retrieval - can an
      agent holding the text name where a handed-over lesson enters the store?
- [x] Scope: one sentence in step 1; no new file, no script.

## RED

- [x] Text check against the pre-change file: `grep -c 'Lessons for the next nap' SKILL.md` is 0,
      so an agent following step 1 as written enumerates "this session's" learnings only and a
      lesson recorded by an earlier session's handover has no reader. The behavioural arm is the
      handover skill's own RED (sonnet), where the lessons were kept OUT of the file because the
      writing session captured them; once that capture is gone, this step is the only entry point.

## GREEN

- [x] Text check against the changed file: the heading is named in step 1 with the reason a
      dream that skips it drops the lessons, and the git history of `handover.md` is named as the
      way to reach a handover already overwritten since the last dream.
- [x] The paired handover GREEN (haiku) writes both lessons under exactly that heading, so the
      producer and this consumer agree on the heading string byte for byte.

## REFACTOR - every gap closed or declined

- [x] GAP: which handovers - the cwd's only, or every repo under the anchor? CLOSED in the text:
      every repo root under the anchor, plus the history of each `handover.md` since the last
      dream, because the file is overwritten wholesale each session.
- [x] No other gap surfaced; the change is one input to an existing step.

## Quality

- [x] Description unchanged; measured `len()` 480, under the cap.
- [x] No narrative, no scratch paths, no addresses added.

## Deployment

- [x] Hook suite green with CI's dependency set; `repo-gate.py --ci` before the push.
- [x] Version bumped in `plugin.json` and `pyproject.toml`; CHANGELOG entry names the change.
