# checklist-20260904-record-lessons-do-not-capture

Change under test: procedure step 1 no longer captures learnings through `bitranox:meta-self-improve`.
The handover RECORDS each lesson as one trigger-first line under `## Lessons for the next nap`, and
`meta-dream-nap` / `meta-dream-tree` capture from that heading. A tooling lesson is the same one
line, prefixed `tooling:`, and is not a reason to open the tool.

The measurement behind it: over 21 days of transcripts, the handover watcher's block began 131
instrumentation episodes in sessions outside the marketplace repo, 461 minutes, 19% of it
memory-store work and 18% skills-repo edits; `meta-self-improve` was invoked 31 times inside those
episodes, `memory_engine.py add` followed, then fixes to the engine. The handover's own share of
work-project minutes went from 1% to 9-10% in the three weeks after the skill shipped.

## PLAN

- [x] Skill type: discipline. The failure is a procedure step followed as written (capture first),
      so the test is the same scenario against the old and the new text.
- [x] Scope: `SKILL.md` here, plus one sentence each in `meta-dream-nap` and `meta-dream-tree` so
      the heading has a reader. No hook change; `context-watcher.py`'s offer text is unchanged.

## RED

- [x] Scenario: a data-pipeline session at the handover threshold, the user agreed, two durable
      lessons in hand (a CSV reader dropping a row, a bucket needing a region flag), nothing
      uncommitted. List the first five actions.
- [x] Inherited-coverage checked with `redcheck.py --corpus-cascade` on a work project: verdict
      INHERITED COVERAGE, adjudicated a false positive - shared terms are `action`, `commands`,
      `following`, `staging`, and neither named fact body mentions a handover or a nap. The
      record-do-not-capture rule is taught nowhere on this machine.
- [x] RED on sonnet FAILS as predicted: action 1 is "Invoke `bitranox:meta-self-improve` to
      capture the two learnings", quoting the table row "Durable learnings go to the memory store
      via `bitranox:meta-self-improve`" as its authority, and the handover it drafts deliberately
      excludes the two lessons "(they went to memory in step 1)".

## GREEN

- [x] Re-run on haiku, the least inferential tier, against the rewritten text, same scenario: no
      skill invocation and no engine call in the five actions; both lessons appear under
      `## Lessons for the next nap` as one trigger-first line each ("When processing CSV rows where
      the final column is empty, the reader silently drops the entire row ...").
- [x] Both arms asked for a `Skill gaps` section; both lists recorded and worked below.

## REFACTOR - every gap closed or declined

- [x] GAP (RED sonnet): the table row sends lessons to the store now. CLOSED - the row is rewritten
      to name the heading and the measurement, and step 1 states the prohibition and the reader
      (`meta-dream-nap` / `meta-dream-tree`) explicitly.
- [x] GAP (GREEN haiku): writes `handover.md` before reconciling `OPEN-WORK.md`. DECLINED as a text
      gap - step 2 already says "BEFORE you overwrite it" in capitals; the ordering slip is the
      tier's, and the same arm on sonnet keeps the order.
- [x] GAP (both arms): the expiry wording, the section order, the `OPEN-WORK.md` line format and
      the commit message. DECLINED - all four are stated in sections of the full skill that the
      probe excerpt omitted (the expiry blockquote, the line format under "Two files", the
      `/clear` nudge wording); nothing in this change touches them.
- [x] GREEN diffed against RED in both directions: GREEN lost the capture step, which is the
      intended change, and kept reading both files, the reconcile, the overwrite and the commit.
      The two lessons, which RED kept OUT of the file, are now IN it.
- [x] Quote-back: "which line forbids running the engine here?" answered on haiku with the step 1
      sentence verbatim.
- [x] The heading now has a reader on both sides: `meta-dream-tree` step 1 and `meta-dream-nap`
      step 1 name `## Lessons for the next nap` as capture input (text check, both files).

## Quality

- [x] Description unchanged; measured `len()` 509, under the 1024 cap.
- [x] No narrative, no scratch paths, no addresses added; the measurement is stated as a result.
- [x] Cross-references by skill name; the engine script named only to forbid it here.

## Deployment

- [x] Hook suite green with CI's dependency set; `repo-gate.py --ci` before the push.
- [x] Version bumped in `plugin.json` and `pyproject.toml`; CHANGELOG entry carries the numbers.
