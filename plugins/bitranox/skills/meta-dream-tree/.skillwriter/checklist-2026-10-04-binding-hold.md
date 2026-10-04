# Skill-writer checklist: a `hold` from should-promote binds a promotion (2026-10-04)

Scope: step 5's corroboration-gate sentence. Before, it said the tree-top promotion "passes the
corroboration gate" and "HOLD keeps the fact at the project level", with no word on a part-way
move, on what to do when routing and the verdict disagree, and no misplacement distinction (that
lives only in references/dream-core.md). After: classify each tree-top-bound fact as MISPLACEMENT
or PROMOTION first, and write the class down before reading its verdict. A misplacement is
re-homed whatever the verdict says. For a promotion the verdict is obeyed: `promote` moves it to
the tree top and runs `promoted`, while `hold` keeps it at its project level, with no part-way
move as a compromise. A `promote` never picks the level. Two rationalization rows added. Technique
edit inside a process skill; no name, description or trigger changed, so derived docs and
triggers do not move.

## PLAN

- [x] Skill type: technique step in a process skill. Test approach: application scenario on the
      least inferential tier (haiku), inert probe type `bitranox:baseline-probe`, the step text
      given inline as an unshipped draft under a neutral name, with the dream-core routing prompt
      verbatim.
- [x] The claim re-checked against its own evidence first. The earlier probe's placement arm
      moved two facts to the tree top on `hold`, writing "No promotion gate applied". Both facts
      were general hooks at levels whose PLACE-HERE excluded them, which dream-core.md classes as
      misplacements to re-home. So the observed outcome was right by the core and the reasoning
      ignored the gate. That fixture had no genuine promotion candidate, which is the case
      this edit is about.
- [x] One fixture, four levels (`.`, `projects`, `projects/webshop`, `projects/reportgen`), six
      model-inferred facts: A, a promotion candidate (hook names the webshop, its PLACE-HERE
      covers it, the body reads universal, verdict `hold`); B, a misfiled general ssh hook at
      reportgen (verdict `hold`, correct answer: re-home to `.`); C, the control (hook names
      both projects, git habit, verdict `promote`, correct answer: `.` plus `promoted`); three
      distractors that stay.

## RED (current text)

- [x] Inherited coverage: `redcheck.py --corpus-cascade` over the worktree read 1338 documents and
      flagged STRONG coverage, the misplacement-vs-promotion memory fact among the hits (its
      pointer hook is in the always-loaded index of this repo's level). That fact teaches B's
      answer, not A's. The behavioural arms were kept, because contamination pushes an arm
      toward the correct answer: a RED that still fails is a real failure. The text check was
      also run: the pre-change step 5 has no rule for a part-way move, no rule for routing
      against the verdict, and no misplacement distinction.
- [x] RED, three arms on the current text. A: kept by routing ("the hook fires only for
      webshop's Celery charge task retries"), moved to `projects` with no reference to the
      hold, and kept as UNSURE with the gap "The procedure does not specify what to do when
      routing logic directs to `.` (tree-top) but the dwell-store gate returns `hold`". B: `.`,
      `projects`, stayed. C: `.` plus `promoted` in all three.
- [x] Old-text arms interleaved with the first GREEN batch (old, new, old, new, old, new), three
      more on the old text. A: kept ("HOLD keeps the fact at the project level"), moved to
      `projects` ("I assumed `hold` prevents tree-top promotion but allows movement within the
      projects hierarchy"), and kept as UNSURE. B: stayed on the hold, `projects` twice. C: `.`
      plus `promoted` in all three.
- [x] RED outcome over six old-text arms: the held promotion candidate left its project level in
      2 of 6. Only 1 of 6 cited the hold as the reason it stayed. The misfiled fact reached `.`
      in 1 of 6.

## GREEN

- [x] Round 1, three arms (first draft). A held in 3 of 3, quoting the new `hold` sentence. B
      re-homed to `.` in 2 of 3; the third held it, with the gap "whether hold can override a
      misplacement diagnosis". C went to `projects` in 3 of 3, each still running `promoted`.
- [x] REFACTOR from round 1. LOST, C: the old text sent C to `.` 6 of 6. The draft's
      "`promote`: move it" lost the old sentence's "tree-top" anchor, so arms moved C to the
      narrowest common parent and still cleared its sightings. Now: "`promote`: move it to the
      tree top". B held on a printed verdict: the misplacement bullet gains "(a `hold` answers
      the promotion question, not this one)".
- [x] Round 2, three arms. A held 3 of 3. B: `.` 2 of 3; the third held it, with the gap "Facts 1
      and 2 both have `should-promote` results (`hold`), suggesting their routing sent them
      toward tree-top for a promotion gate decision". C: `.` plus `promoted` 2 of 3; the third
      routed it to `projects` and ran no `promoted`, which is internally consistent.
- [x] REFACTOR from round 2. A printed verdict was read as evidence of class, so the class is now
      a required output, written per fact BEFORE reading the verdict, because "a verdict on
      record says nothing about which class a fact is".
- [x] Round 3, three arms. A held 3 of 3. B: `.` 3 of 3, quoting the misplacement bullet. C: `.`
      plus `promoted` 2 of 3; the third routed C to `projects` (no `promoted`). One arm's gap
      named the cause: "my routing yields `projects`, but should-promote says 'promote' ... the
      procedure does not explicitly prioritize one over the other".
- [x] REFACTOR from round 3: "A `promote` never picks the level, routing does: it only lets a
      fact go to the tree top when routing sent it there; if routing picked a lower level, that
      is where it goes, and no `promoted` runs." A first wording ("a fact routing sends below the
      tree top is an ordinary move ... whatever `should-promote` printed") was caught before
      testing as contradicting the hold's no-part-way rule and was scoped to `promote` only.
- [x] Placing C at `projects` is a ROUTING error (`projects` PLACE-HERE names uv, pytest, CI and
      PyPI; `.` names git). It is not a gate error, and the old text shows the same failure on
      B: 3 of 6 old-text arms routed the ssh fact to `projects` as the narrowest common parent.
      The routing prompt lives in references/dream-core.md and is out of this edit's scope.
      DECLINED here.

## Totals (A = held promotion candidate, the item's defect)

| text         | arms | A stays at its project level | A moved off its level | B re-homed to `.` | C to `.` + `promoted` |
|--------------|------|------------------------------|-----------------------|-------------------|-----------------------|
| old          | 6    | 1                            | 2                     | 1                 | 6                     |
| new, round 1 | 3    | 3                            | 0                     | 2                 | 0                     |
| new, round 2 | 3    | 3                            | 0                     | 2                 | 2                     |
| new, round 3 | 3    | 3                            | 0                     | 3                 | 2                     |

## Quote-back on the final text

- [x] Three haiku arms, the final gate paragraph alone, four questions each, every answer a direct
      quote or NONE. Held promotion with a tempting middle level: `projects/webshop`, quoting "no
      move to the tree top and no move part-way up as a compromise" (3 of 3). Misfiled ssh fact
      with a `hold` on record: `.`, quoting "(a `hold` answers the promotion question, not this
      one)" (3 of 3). `promote` with routing at `.`: `.` plus `promoted` (3 of 3). `promote` with
      routing at `projects`: `projects`, no `promoted`, quoting "A `promote` never picks the
      level, routing does" (3 of 3). No NONE.
- [x] Remaining gaps DECLINED: which engine command re-homes a fact and in what order the
      sighting is recorded (the `move` instruction earlier in the step, and the engine table in
      meta-self-improve's references/memory-backend.md); whether a held fact needs a closing
      command (none exists; "report it as held" is the whole action); routing confidence and
      batching (unchanged step text, owned by the routing prompt in dream-core.md).

## Sibling skills

- [x] meta-dream-crosstree step 4 carries the same gate. Three haiku RED arms on its current text,
      same A and C candidates: A stayed and C went to `.` plus `promoted` in 3 of 3, each quoting
      the corroboration bar ("a model-inferred generalization promotes once seen in >= 2 DISTINCT
      PROJECTS"). Its gate is the step's whole subject, not one clause in a routing step. The
      defect does not reproduce there. Not edited.
- [x] meta-dream-nap step 4 is chain-internal placement through the core's routing prompt and
      carries no promotion-gate text of its own. Not edited.

## Security and hygiene

- [x] Diff reviewed: prose only, no secret, address, hostname or real user path.
- [x] Added lines ASCII only; the step lines within 100 columns.
- [x] meta-dream-tree tests run with CI's dependency set.
