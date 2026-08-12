# skill-writer checklist - meta-dream-crosstree (corroboration counts distinct projects)

Change: step 4's corroboration paragraph. The counter it describes now measures >= 2 DISTINCT
PROJECTS instead of one sighting per dream run, so the paragraph's statement that "two projects
corroborating inside a SINGLE crosstree run still count as one" is replaced, and the fan-out is told
to name the project each fact came FROM rather than its own cwd.

## Scope
- [x] Prose only in this skill; the mechanism and its tests live with `meta-dream-tree`, which owns
      `dream_state.py`, and are reviewed under that skill's checklist for the same change.
- [x] The paragraph keeps deferring the gate's definition to the tree dream and adds only what a
      cross-tree reader needs: which argument to pass, and that a single run can now satisfy the
      gate.

## RED
- [x] The paragraph described the counter accurately for the old mechanism and so became false with
      it: it told the reader a sighting is recorded per DREAM, that two projects inside one run
      count as one, and that the distinct-projects test is judgement the tool does not perform.
- [x] A subagent given the pre-change paragraph, asked what `should-promote` prints after two
      sightings recorded from the SAME project, answered `promote` and reported the backstop
      satisfied. Its own gaps list named the unresolved conflict: the text "is silent on what the
      correct AGENT action is when the mechanical backstop says promote but the judgment-based
      distinct-projects test fails".

## GREEN - verified from behaviour, not from the text
- [x] The same question against the new paragraph answers `hold`, backstop NOT satisfied, quoting
      "know what the counter measures: >= 2 DISTINCT PROJECTS, one entry per project however often
      it is recorded".
- [x] The reader now reaches the opposite conclusion about a re-run over unchanged bodies, matching
      what the CLI does.
- [x] No baseline result is lost: every gap the pre-change arm reported was a confusion the stale
      text created (whether the tool dedups, what to do when tool and judgement disagree), and the
      mechanism now answers each.

## REFACTOR
- [x] Gap reported by both arms: the numeric threshold was not stated in this paragraph, so the
      reader inferred 2 from an example. CLOSED: the paragraph now says ">= 2".
- [x] Undecided gap list is empty.

## Quality
- [x] The argument the fan-out must pass is stated with the consequence of omitting it, not as a
      bare parameter.
- [x] No narrative, no provenance, no machine paths.
- [x] ASCII only.
- [x] Frontmatter untouched, so the CSO description is unchanged and needs no re-review.
