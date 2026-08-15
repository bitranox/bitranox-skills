# meta-dream-nap: correct the sixth pinned-entry overclaim site

Scope: one clause, the closing sentence of step 4 "Chain-internal placement only" in `SKILL.md`.
No other file in this skill mentions pinning. The engine itself (`hooks/memory_engine.py`) is
unchanged - this is documentation catching up to already-shipped, already-reviewed code
(commit `2dbe15c`), and it corrects a site commit `d21efe9` missed when it fixed the same claim in
five other places (`meta-self-improve/references/memory-backend.md`,
`meta-dream-tree/SKILL.md`, `meta-dream-tree/references/dream-core.md`).

## The finding this fixes

Step 4 ended "Low/UNSURE and anything involving a sibling stays put. Pinned entries untouched." -
a flat, unqualified carve-out read naturally as "the nap must never move OR rewrite a pinned
entry." That is the same pre-enforcement claim `d21efe9` corrected everywhere else: the engine
REFUSES an ordinary `add` on a pinned slug (`PinnedEntry`, `hooks/memory_engine.py` line 254), but
`move`/`relocate`/`rename` carry `pin` through untouched and never refuse on it (lines 112-113,
614-620, 949, 1035), so re-leveling a pinned fact is ordinary placement work, not an exception. The
sentence also directly contradicted the routing prompt this same file defers to
(`references/dream-core.md`, corrected by `d21efe9`: "A pinned fact is placed by this SAME routing
prompt, up or down, like any other entry") - a reader following step 4 to the letter and then
opening the core it cites would meet two different rules for the identical decision.

## What the tests showed

- [x] Behavioral pressure-test run (this is a real behavioral correction - the old text told the
      nap to decline a legitimate placement move, not a pure wording change - so the Iron Law
      applies in full). Two `bitranox:baseline-probe` dispatches (model: sonnet; no Bash/Read/Write,
      so the decision can only come from the pasted excerpt), identical two-situation scenario, the
      nap's own `## Procedure` section pasted verbatim (steps 1-6) with only step 4 differing
      between arms - pre-edit vs. corrected wording, not read from disk.
  - RED (pre-edit step 4, "Pinned entries untouched."): Situation A (a pinned fact at the anchor
    whose routing evidence unambiguously says it belongs at proj-1, content accurate) - agent left
    it at the anchor, quoting the excerpt's own "Pinned entries untouched" as a categorical
    override of the evidence-routing clause, and put it on the deferred-list instead of moving it.
    Situation B (a different pinned fact, level already correct, body stale) - agent also declined
    to rewrite it, citing the same "untouched" clause plus the absence of any defined
    content-correction step. Confirms the pre-edit text produces the wrong PLACEMENT behavior on A
    (declines a move the engine would allow) while B's content question was already handled right
    for unrelated reasons (no step in the procedure authorizes a content rewrite regardless of pin).
  - GREEN (corrected step 4, "A pinned fact re-levels like any other entry, pin intact; only its
    CONTENT is out of reach"): Situation A - agent re-levels it "down from anchor to proj-1, right
    now, pin intact," quoting "A pinned fact re-levels like any other entry, pin intact" as direct
    authorization. Situation B - still declines to touch content, quoting "only its CONTENT is out
    of reach (per the core's Boundaries)" as explicit and unqualified. The flip lands exactly on
    the targeted behavior (A only); B's already-correct behavior did not regress.
  - Skill gaps reported by both runs are about mechanics the generic scenario never supplied (which
    bucket "report it" belongs in, whether the full dream has more authority over pinned content
    than the nap, what "dead-content" means for step 5) - pre-existing ambiguity in the nap's
    overall procedure, not introduced by or specific to the corrected pin clause. Nothing there
    requires a further change to this clause.
- [x] Mechanical PRESENT/ABSENT verification with `compuse-toolbox/scripts/claim_check.py` against
      the actual working-tree file (control phrase confirms the file was read, not assumed): old
      "Pinned entries untouched" -> ABSENT; new "A pinned fact re-levels" -> PRESENT (1 hit, line
      44); new "only its CONTENT is out of reach" -> PRESENT (1 hit, line 45; the sentence wraps
      across these two lines in the source, so the two checks together cover the whole new clause).
- [x] Corpus-contamination check: ran `process-test-driven-development/scripts/redcheck.py
      --corpus-cascade` against this task's actual working directory. It flagged the tree-top
      `CLAUDE.local.md` as a term-overlap hit (5 shared terms: chain-only, clearly, finds, pinned,
      placement; 23%) - traced to a DIFFERENT fact
      (`reference-engine-move-is-chain-only-and-guards-only-inbound-refs...`, about sideways moves
      refusing and dangling OUTBOUND refs, nothing about pinned-entry placement). Direct grep of
      every ancestor `CLAUDE.local.md` and every `.claude-memory/facts/` body on the chain for the
      actual mechanism (`PinnedEntry`, `amend-pinned`, `re-level`, `carr(y|ies) pin`) returned zero
      hits - the specific lesson under test is not present anywhere in the ambient cascade, so the
      redcheck flag is bag-of-words overlap on common vocabulary in a large multi-topic file, not
      inherited coverage of this lesson. The RED run's own behavior corroborates this: it failed
      honestly (declined the move) rather than reasoning around the pre-edit text.

## Placement / phrasing choice

- [x] Matched `dream-core.md`'s corrected Boundaries wording rather than inventing new phrasing:
      "re-levels like any other entry" / "pin intact" / "only its CONTENT is out of reach" all
      echo the core's "like any other entry" / "carries the pin through unchanged" / "Only a
      pinned fact's CONTENT is out of reach" so the two texts agree instead of merely both being
      non-false.
- [x] Did not restate the whole gate (which verb refuses, which verb preserves, what `amend-pinned`
      is) inline - per the task's instruction to keep this file's SCOPE DELTA minimal and defer
      mechanics to `dream-core.md` via "(per the core's Boundaries)", matching how the rest of this
      file already defers ("all semantics per dream-core.md").
- [x] Did not restructure the bullet or renumber the procedure; the edit is the closing clause of
      step 4 only.

## Sweep for remaining sites (whole skills tree, not just this file)

Searched broadly for the SHAPE of the old claim (pinned + untouched/skipped/excluded/exempt/left
alone, in a dream/placement context), not one exact string: `grep -rniE "pinned"` over every `.md`
under the plugin, then `grep -rniE "pin"` over every `.py` under `skills/` and `hooks/` filtered to
lines also containing untouch/skip/exclud/exempt/leave/alone/never touch/never move/stays put/do
not move/do not touch.

- [x] `meta-dream-nap/SKILL.md:44` (this file) - FIXED, the finding this checklist covers.
- [x] `meta-self-improve/references/memory-backend.md`, `meta-dream-tree/SKILL.md`,
      `meta-dream-tree/references/dream-core.md` (Boundaries bullet + routing prompt) - already
      corrected by `d21efe9`; re-read directly, all state the content-vs-placement distinction
      correctly, no leftover "exempt"/"EXEMPT"/old-wording hits.
- [x] `meta-dream-tree/references/dream-core.md:173` ("Report counts (merges, placements with
      direction, prunes, pinned untouched)") - a report-category label (how many pinned facts had
      their CONTENT left untouched this run), not a placement-exemption claim; consistent with the
      corrected text three lines above it in the same section. Left alone.
- [x] `meta-dream-tree/SKILL.md:228` ("pinned entry untouched" inside the Acceptance-harness
      paragraph) - describes `tests/fixture_asserter.py`'s actual HARD assertion (level, pin flag,
      hook all checked unchanged) for the fixture's specific planted pinned fact, which never needs
      a PLACEMENT move because it is already planted at its correct level (`tests/fixture_builder.py`
      plants it at the anchor with an org-wide-scoped hook). The assertion is TRUE regardless of
      this fix; not the same claim as the corrected PLACEMENT prose. Confirmed by reading
      `fixture_asserter.py` line ~70 (checks `pin_hits[0][0] == m["tree1"]`, i.e. the fixture's
      known-correct anchor level, plus `.pin` and unchanged `.hook`) and `fixture_builder.py`'s PIN
      case comment ("an obsolete-LOOKING but PINNED fact at the anchor -> untouched
      (propose-only)"), which is about the ARCHIVE gate (obsolete-looking but must not be silently
      archived), not placement. Left alone - this matches the disposition the prior checklist
      (`meta-dream-tree/.skillwriter/checklist-20260815-pin-gate-doc-fix.md`) already recorded for
      the same paragraph.
- [x] `meta-dream-tree/tests/README-acceptance.md:19` ("PIN (pinned entry untouched)") - same
      fixture-assertion description as above, one level up in the doc chain. Left alone for the
      same reason.
- [x] `meta-dream-crosstree/SKILL.md:171` and `meta-dream-crosstree-deep/SKILL.md:131` - both read
      "The family Boundaries (memory, CLAUDE.md, skills/hooks, pinned entries, structural moves)
      live in `references/dream-core.md` ... read them there, they are not restated" - a pointer,
      no local restatement of any claim. Left alone.
- [x] `hooks/memory_engine.py` (module docstring line 19, `PinnedEntry` class docstring line 113,
      `amend_pinned_entry` docstring lines 284/286) and `hooks/tests/test_memory_pin_gate.py` (file
      docstring line 4) - all already state the POST-`2dbe15c` behavior correctly ("the movers ...
      carry pin through untouched and never refuse on it"); "untouched" here means the `pin` FLAG
      itself is carried unchanged by a move, not that the entry never moves. Not the false claim.
      Left alone.
- [x] `docs/setup.md`, `docs/usage.md`, `docs/architecture.md`, and every other "pinned" hit outside
      the dream-skill family (subagent-model / index-pin / dependency-pin / UI-pin usages in
      unrelated skills) - checked directly, none describe the memory engine's pin gate or a
      dream/placement exemption. Not the same claim; out of scope.

No seventh site carrying the false claim was found. Every other "pinned...untouched"-shaped hit in
the tree is either already corrected (four sites from `d21efe9`) or describes something true and
unrelated (a report-category label, a fixture assertion about a fact already at its correct level,
a pointer to the core, or the pin FLAG surviving a move - which is the correct claim, not the false
one).

## Scope declined

- [x] Did not touch `tests/fixture_builder.py` / `tests/fixture_asserter.py` in `meta-dream-tree`.
      The fixture's planted pinned fact never needs a PLACEMENT move in the current test (it is
      already at the correct anchor level), so this fix does not require a fixture change to stay
      green; adding a fixture case that actually re-levels a pinned fact would be new test
      coverage, outside this task's fix-the-doc-claim scope.
- [x] Did not open a `meta-skill-writer` flow for `meta-dream-crosstree`/`meta-dream-crosstree-deep`
      - both only point at `dream-core.md`'s Boundaries with no local restatement, so nothing there
      needs fixing.

## Checks

- [x] Description frontmatter untouched, so the CSO lint and skill-router trigger map are
      unaffected.
- [x] No cross-skill or script references added; no renumbering of the existing 6-step procedure.
- [x] No session narrative or private provenance in the skill text or this artifact.
- [x] No hostname, IP, credential, or machine-specific path introduced.
- [x] LF endings; ASCII only (no em/en dash, no curly quotes in the changed text).
- [x] No `plugin.json` version bump in this change (5.203.0 already accounts for the capability
      this documents; this is a same-version doc correction, not a new capability).
- [x] `repo-gate.py --ci` passes on the full change set (recorded in this task's own report).
