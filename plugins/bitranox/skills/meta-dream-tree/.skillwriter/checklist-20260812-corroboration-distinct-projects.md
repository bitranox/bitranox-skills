# skill-writer checklist - meta-dream-tree (corroboration counts distinct projects)

Change: step 5's tree-top promotion gate, and the matching paragraph in `references/dream-core.md`,
now state that a model-inferred fact needs >= 2 DISTINCT PROJECTS rather than >= 2 dream sightings,
and instruct the dream to name the project a fact came FROM. `dream_state.py`'s usage block and the
dwell store behind it change with them.

## Scope
- [x] The prose and the mechanism are one change. The gate's stated contract was already ">= 2
      distinct projects"; the counter behind it counted runs, so the text was not describing what
      shipped. Both sides move together rather than the text being softened to match the code.
- [x] Single source confirmed: the gate is stated once per skill and the shared detail lives in
      `references/dream-core.md`. Neither call site restates the store's internals.

## RED
- [x] A dream re-reads UNCHANGED fact bodies on every run, so a per-run sighting counter is
      satisfiable by one act of judgement re-derived: a second run over an unchanged store
      mechanically re-derives the same candidate list and flips the gate to `promote`. One measured
      pass recorded 84 sightings.
- [x] Driving the shipped CLI showed it: two `saw-promotable` calls naming the same project printed
      dwell `2`, and `should-promote` printed `promote`.
- [x] A subagent given the pre-change text and asked what `should-promote` prints after two
      sightings from ONE project answered `promote`, citing "the dwell counter is the mechanical
      backstop that also requires a second run".

## GREEN - verified from behaviour, not from the text
- [x] The same subagent question against the new text answers `hold`, and quotes the governing
      clause (">= 2 DISTINCT PROJECTS, one entry per project however often it is recorded").
- [x] The CLI now prints dwell `1` for 84 sightings from one project and `hold`; a sighting from a
      second project prints `2` and `promote`, readable from either project.
- [x] `promoted` clears every project's sighting, so a single later sighting prints `1` and `hold`
      rather than re-tripping the gate.
- [x] Tests assert both directions (N=2 and N=84 from one project hold; two projects promote), and
      fail when the fix is mutated back to counting repeats - so they are not vacuous.

## REFACTOR
- [x] Gap reported by both test arms: the threshold number was not stated where the counter is
      described, so the reader inferred it. CLOSED: the crosstree paragraph now names ">= 2".
- [x] Two tests that could no longer fail under the new mechanism are rewritten to read from a
      SECOND project, where a wrongly-recording read flips the verdict. They previously asserted
      nothing.
- [x] Undecided gap list is empty.

## Quality
- [x] The instruction is actionable at the point of use: the command shows the project argument and
      says it defaults to the cwd, which is the wrong value for a fan-out.
- [x] No narrative, no provenance, no machine paths.
- [x] ASCII only.
- [x] Frontmatter untouched, so the CSO description is unchanged and needs no re-review.
