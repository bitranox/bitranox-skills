# meta-dream-tree: correct the pre-enforcement pinned-entry claim, state the real gate

Scope: step 5 PLACEMENT's closing sentence, the step-11 report line, two Deliverables bullets, one
Rationalizations row, and one Common-mistakes bullet in `SKILL.md`; the paired "Boundaries" bullet
and the routing-prompt paragraph in the shared `references/dream-core.md`. A companion change in
`meta-self-improve/references/memory-backend.md` (command table + store-format pin description) and
`CHANGELOG.md` corrects the same claim outside this skill's files; the engine itself
(`hooks/memory_engine.py`) is unchanged - this is documentation catching up to already-shipped,
already-reviewed code (commit `2dbe15c`).

## The finding this fixes

`SKILL.md` and `dream-core.md` both said a pinned entry is "EXEMPT from move/reword/archive unless
the user approves that specific change" - true only as prose before `2dbe15c`, and now wrong in a
specific way: `add_or_update_entry` REFUSES an ordinary `add` on a pinned slug (`PinnedEntry`,
`hooks/memory_engine.py` line 254), but `move`/`relocate`/`rename` were deliberately left
unchanged - they carry `pin` through untouched and never refuse on it (`memory_engine.py` lines
112-113, 615-620, 949, 1035), so re-leveling a pinned fact is not gated at all. The old text told
the dream to treat PLACEMENT itself as needing the user's approval for a pinned fact, which is a
real behavioral instruction, not just wording - a dream literally following it skips a legitimate
move. Five sites carried variants of the same claim: step 5's heading and closing sentence, a
Common-mistakes bullet ("Moving a pinned entry" listed as a mistake), a Rationalizations row, two
Deliverables/report lines, and both the Boundaries bullet and the routing-prompt paragraph in
`dream-core.md` (the second one is the actual routing prompt meta-dream-nap and meta-dream-crosstree
also route through). All five plus both `dream-core.md` sites were corrected in this change.

## What the tests showed

- [x] Behavioral pressure-test run (this correction changes the dream's PLACEMENT behavior, not just
      wording, so the discipline-skill Iron Law applies - it is not "content the code already
      enforces the same way regardless of what the doc says"). Two `bitranox:baseline-probe`
      dispatches (no Bash/Read/Write - decisions must come from the pasted excerpt alone), same
      two-situation scenario, pre-edit vs. corrected excerpt of step 5 + the Common-mistakes bullet
      pasted directly into the prompt (not read from disk, so the RED run cannot see the corrected
      file).
  - RED (pre-edit excerpt): Situation A (pinned fact at the anchor, content belongs at a project
    level, several unpinned siblings already correctly moved down) - agent declined to move it,
    quoting the excerpt's own "EXEMPT from move/reword/archive" line and the Common-mistakes entry
    naming "Moving a pinned entry" as a mistake; proposed reporting it for approval instead.
    Situation B (a different pinned fact's hook is stale/wrong) - agent correctly declined to
    rewrite it and proposed reporting it. Confirms the pre-edit text produces the wrong PLACEMENT
    behavior (declines a move the engine would have allowed) while already getting the content
    question right.
  - GREEN (corrected excerpt): Situation A - agent ran `move --from-level <anchor> --to-level
    <lower> --slug <slug>`, quoting "`move` carries the pin through unchanged and never refuses on
    it, so re-leveling a pinned fact is ordinary placement work like any other entry - no exception,
    no separate approval step"; treated it identically to the unpinned siblings, batched into the
    same propose-diff. Situation B - still declined to touch content, named `PinnedEntry` and
    `amend-pinned`'s human-only scope from the excerpt, proposed reporting instead. The flip is
    exactly the targeted one (A only); B's already-correct behavior did not regress.
  - Skill gaps reported by both runs were about mechanics the generic scenario never supplied
    (literal slug/level tokens, the reporting channel's exact shape) - not textual ambiguity in the
    excerpt itself. Not counted as a gap to close.
- [x] Mechanical PRESENT/ABSENT verification with `compuse-toolbox/scripts/claim_check.py` against
      the actual working-tree files (control phrase confirms the file was read, not assumed): old
      "re-level every unpinned entry" -> ABSENT; old "EXEMPT from move/reword/archive" -> ABSENT (in
      both `SKILL.md` and `dream-core.md`, checked separately against the Boundaries bullet and the
      routing-prompt section); old "Moving a pinned entry, or moving DOWN" -> ABSENT; new
      "re-leveling a pinned fact is ordinary placement work" -> PRESENT (1 hit); new "engine
      REFUSES" -> PRESENT (4 hits: PLACEMENT, the Rationalizations row, and both Common-mistakes
      bullets); `dream-core.md` new `PinnedEntry` -> PRESENT (2 hits: Boundaries bullet, routing
      prompt).
- [x] Corpus-contamination check: the loaded CLAUDE.md/memory cascade for this session (the softdev
      tree-top + `projects/` + `public/` + `KI/` + `RESEARCH` levels) contains no fact about
      `PinnedEntry`, `amend-pinned`, or a `bx:pin` write-gate - inspected directly rather than run
      through a corpus-cascade tool, since the full injected text was already in hand. Low risk of
      an inherited hit explaining the RED->GREEN flip.

## Placement / phrasing choice

- [x] Kept "content vs. placement" as the one distinction threaded through every corrected site,
      matching the code exactly: `add`/`amend-pinned` gate CONTENT (`PinnedEntry`, refuses/deliberate
      escape hatch); `move`/`relocate`/`rename` are placement and are never gated. Did not invent a
      third category.
- [x] Did not claim archive is engine-gated. `reconcile_memory_index.py`'s `archive_entry` does not
      check `pin` at all (read directly - no call to `add_or_update_entry`, no pin check anywhere in
      the function), so the corrected `dream-core.md` Boundaries bullet says archiving is NOT gated
      by the engine and states the dream's own no-archive policy separately, rather than folding it
      into the same "the engine refuses" sentence as `add`. `SKILL.md`'s own corrected text and this
      skill's memory-backend.md row make no claim about archive either way, matching the task's
      explicit two-way scope (state exactly which path refuses, which merely preserves) rather than
      extending it to a third verb nobody asked about.
- [x] Extended the fix past the two literal call-out sites (step 5's closing sentence, the
      Common-mistakes bullet) to the Rationalizations row, the two Deliverables/report lines, and
      both `dream-core.md` sites, because leaving them as found would have shipped a file that
      contradicts itself in the same read - one paragraph saying re-leveling needs no exception,
      three lines later a checklist item asking to verify "pinned entries untouched". Left
      `dream-core.md`'s `## Acceptance harness` sentence ("pinned entry untouched") alone: it
      describes `tests/fixture_asserter.py`'s actual HARD assertion (level, pin flag, and hook all
      checked unchanged), read directly - the fixture's planted pinned fact is already at its
      correct level, so the assertion holds regardless of this fix and is not the same claim as the
      corrected PLACEMENT prose.

## Scope declined

- [x] Did not edit `hooks/memory_engine.py`'s module docstring line ("`pin` marks it as one of the
      iron rules the dream must not silently archive/move/reword AND gates ordinary `add`"). Read
      literally it is defensible - "silently" qualifies all three verbs, and an ordinary reported
      `move` is not silent - but it is outside this task's two-file-plus-changelog scope and outside
      a hooks file this task was told not to touch; flagging it in the task report rather than
      editing source code under a documentation task.
- [x] Did not edit `meta-dream-crosstree/SKILL.md` or `meta-dream-crosstree-deep/SKILL.md`. Both
      only point at `dream-core.md`'s Boundaries ("live in references/dream-core.md ... read them
      there, they are not restated") with no local restatement (checked directly - no "exempt"/
      "EXEMPT"/"untouched" text in either file), so fixing the shared `dream-core.md` corrects what
      all three skills read without opening two more skill-writer flows outside this task's scope.
- [x] Did not touch `tests/fixture_builder.py` or `tests/fixture_asserter.py`. The fixture's planted
      pinned fact never needs a PLACEMENT move in the current test (it is already at the correct
      anchor level), so the fix does not require a fixture change to stay green; adding a fixture
      case that actually re-levels a pinned fact would be new test coverage, not a doc correction.

## Checks

- [x] Description frontmatter untouched, so the CSO lint and skill-router trigger map are
      unaffected.
- [x] No cross-skill or script references added; no renumbering of the existing 11 (+10b) procedure
      steps.
- [x] No session narrative or private provenance in the skill text or this artifact.
- [x] No hostname, IP, credential, or machine-specific path introduced.
- [x] LF endings; ASCII only (no em/en dash, no curly quotes in the changed text).
- [x] No `plugin.json` version bump in this change (5.203.0 already accounts for the capability this
      documents; this is a same-version doc correction, not a new capability).
- [x] `repo-gate.py --ci` passes on the full change set (recorded in this task's own report).
