# skill-writer checklist - process-review-enhance-code-quality (gate holds only on wrong behaviour)

Change: the Step 7 gate holds the loop open only for a SEVERE or MEDIUM that gives a realistic
caller wrong behaviour. Test gaps over correct behaviour (surviving mutant, obeyed-but-unpinned
invariant, a test asserting less than it could), doc wording that misleads no caller, and clarity
of correct code keep their severity but never hold the loop; they are settled by cheap-or-accept,
and restructuring correct code is never cheap. A sweep that FOUND a gate-holding finding is not
the last one even after the fix. A standing "fix all" applies cheap-or-accept to non-gating
findings, with the rest presented once as `accept:` proposals. A review parked in a handover or
backlog line points at the skill and never restates the exit rule. Updated: the Workflow diagram,
the outer-loop paragraph, Step 3's invariant note, Step 7, the severity table header, Common
Mistakes. Shipped in plugin 8.18.0.

## PLAN

- [x] Skill type: discipline (a loop with an exit rule). Test approach: decision scenario at the
      exit point, two variants so the gate is shown to bite both ways, two model tiers.
- [x] Motivation, from session transcripts: one library ran sweeps 13-19 after the severity gate
      shipped. Every sweep reported MEDIUM test gaps (up to 9 surviving mutants, 16 mutation gaps in
      one sweep) and doc wording, each counted as reachable, and a standing "fix all" fixed every
      MINOR too; each fix seeded the next sweep. A backlog line written before the gate stated the
      old "finds nothing and changes nothing" rule, and a later session resumed from that line,
      quoting it. The loop ended only when the user deferred the next sweep.
- [x] User decision (recorded in the decision log): keep the loop, tighten the gate; no sweep cap.

## RED

- [x] Contamination: arms run from a directory whose cascade assembles 0 documents
      (`redcheck --corpus-cascade` exit 2, nothing inherited), no tools, slash commands off,
      setting sources limited to project; the skill text is pasted into the prompt.
- [x] Scenario: sweep 9 of a fictional CSV-cleaning library, MEDIUM flat at 6-7, user's standing
      "fix all", project rule "accept no technical debt". Variant A: five MEDIUM, all non-behavioural
      or exotic (surviving mutant, unpinned obeyed invariant, unclear README word, a 58-line
      function, a 40-microsecond rename/fsync window plus power loss). Variant B adds one real
      wrong exit code on a documented CI recipe.
- [x] RED, old text: haiku B started sweep 10 counting the mutant, the invariant and the README
      word as reachable ("any reader of the README"). Sonnet B ended the loop on the sweep that found
      the exit-code bug, reading "its fixes get ... not another full sweep" as licence. All four arms
      fixed every non-behavioural finding, the refactor included, and all 8 MINOR under "fix all".
      Both A arms ended the loop but reported "reach for non-behavioural findings is undefined".

## GREEN

- [x] Sonnet and haiku A: END LOOP, quoting "Only wrong behaviour holds the loop open"; F1-F3
      fixed as cheap, the refactor and the race proposed as `accept:`, MINOR batched and the
      "fix all" scope asked once.
- [x] Sonnet and haiku B: START SWEEP 10, quoting "sweep again whenever the sweep just finished
      FOUND a gate-holding finding" and "Fixing a gate-holding finding does not make its sweep the
      last one"; only F6 holds the loop.
- [x] Diffed against RED both ways: the RED arms' exit-code family sweep for F6 and the F5
      reach-as-reason records reappear; the refactor of correct code is gone by design.

## REFACTOR

- [x] Gap closed: Step 7's "found none" read two ways -> "found no gate-holding finding".
- [x] Declined, with reasons: "cheap" for a test harness over several readers (pre-existing
      definition, judgement left to the reviewer); which exit code a bad-data file earns (a
      machine-drivable convention question, not this gate); whether a project rule overrides an
      `accept:` (the text already says a recorded acceptance is a decision, and the user is asked).
- [x] Quote-back, haiku, final text: Q1 sweep-after-fix, Q2 surviving mutant, Q3 "fix all" on a
      refactor, Q4 restating the rule in a backlog line - each answered with a verbatim sentence,
      none NONE.

## Quality

- [x] Grep for "realistic caller can reach", "finds none" and "MINOR included" leaves no stale
      statement of the old gate.
- [x] Tables canonical (the formatter hook re-padded every edited table). ASCII only, present
      tense, no session narrative, no private hosts or paths, no real project names.
- [x] Frontmatter and description unchanged, so `skill_triggers.json` needs no rebuild.
- [x] Security scan: prose and tables only.

## Deliverables

- [x] `SKILL.md` edits as listed; no script, so no `tests/` change. Version 8.18.0 (MINOR: changed
      loop exit), `pyproject.toml` matched, CHANGELOG entry.
