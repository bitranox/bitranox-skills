# skill-writer checklist - meta-claude-hooks (no dependency provisioning, and a crash reads as an allow)

Change: one new section, "Your handler runs with no dependency provisioning", plus two traps - a
crashed hook is indistinguishable from an allowing one, and widening a retrospective hook's window
cannot fix periodicity. Two adjacent corrections came out of the same testing: the `exit 2` vs
`WorktreeCreate` sentence pair read as a contradiction, and it is fixed here and in `SKILL.md`.

## PLAN

- [x] Skill type: reference/hub for hook authoring. Test approach: text check of the artifact, plus
      application scenarios against the new text.
- [x] Scope: one reference section and three trap bullets. No frontmatter change - the description
      already triggers on writing, debugging and reviewing a hook.
- [x] Checked against EVERY shipped skill before writing, not the one the change was filed against.
      `meta-skill-writer` owns the authoring prescription ("A hook must never wedge a turn. Every
      failure path exits 0") and the bare-environment IMPORT rule for the contribution gate. Neither
      states the runtime consequence, which is the gap: a hook is never launched through a runner,
      so a guarded import's fallback is not a fallback, it is the only path.
      Verified with `claim_check.py --pattern 'uv run --script|no venv|bare interpreter|without a
      venv|dependency provisioning' --control 'hook'` over both skills: ABSENT, control matched 233
      times across 6 files, so the files were read.
- [x] The retrospective-hook claim was ALREADY shipped ("A retrospective hook cannot prevent
      anything", since 5.208.0). Only the counter to widening the window is new, so this change
      extends that trap rather than adding a second one.

## RED

- [x] A behavioural RED is not available on this machine: `redcheck.py --corpus-cascade` assembled
      827 documents and reported STRONG inherited coverage, naming the document that already teaches
      the lesson. Route taken, per this skill's own rule: TEXT CHECK of the artifact, recorded above.
- [x] The RED against the FILE failed before this change and failed in the direction that costs real
      work: an author following the skill completely still had no reason to expect the interpreter to
      lack their parser, and no reason to test a guard's error paths.

## GREEN

- [x] Application scenario (ship a `PreToolUse` YAML guard cross-platform): the agent produced a
      lazy guarded import returning a SKIP sentinel, a last-resort handler that exits 0, and test
      cases for malformed JSON, empty stdin, an unmodelled payload shape and an environment without
      the parser.
- [x] Quote-back, missing library: "Combined with fail-open, a missing library does not announce
      itself: the import raises, the hook exits 0, and the gate is off." and "Import it lazily,
      guarded, and degrade to SKIPPED - never to a pass."
- [x] Quote-back, a guard with a bug: "So a bug in a guard presents as approval rather than as a
      failure, and the guard reads as working right up until you check."
- [x] Quote-back, the `uv run --script` escape hatch: quoted in full, including the cost, and
      correctly judged as usually the wrong trade rather than forbidden.
- [x] Pressure scenario for the periodicity trap (two senior approvals, a ship date, last reviewer,
      rejection costs a sprint): the agent requested changes, and rejected the "widen it further"
      option specifically, quoting "periodicity is the defect and window size is not a dial on it."

## REFACTOR

- [x] Every gap both runs reported is closed or declined:
  - CLOSED: the text called a periodic supervisor nothing in particular, so a reader could not map
    it to an event. It now names `Stop` and `PostToolUse` and says there is no "every N turns" event.
  - CLOSED: "Policy hooks use `exit 2`. `WorktreeCreate` is the only event where any non-zero exit
    blocks." reads as self-contradictory. Corrected against `io-contract.md`, which states the
    precise rule, in both this reference and `SKILL.md`.
  - DECLINED: no stdin schema, no timeout value, no matcher syntax. All three live in
    `references/io-contract.md` and `references/configuration.md`; the scenario supplied one excerpt,
    and the routing table already sends a reader to those files.
  - DECLINED: cross-platform parse timeouts, subprocess encoding and CRLF. Out of scope for a hooks
    reference; `bitranox:meta-skill-writer` owns cross-platform script packaging.
  - DECLINED: whether a retrospective supervisor should be kept as an audit aid once a `PreToolUse`
    guard ships. A judgement the skill should leave open.
- [x] GREEN diffed against the pre-change text in BOTH directions. Nothing the old traps delivered is
      missing: every pre-existing bullet survives unedited except the `exit 2` one, which gained
      precision, and the never-fires bullet, which gained the crash case rather than losing the
      misconfiguration case.
- [x] The worked example is the real degrade ladder (preferred parser, hardened fallback, then a
      skip sentinel), not a sketch, and the prose states why the sentinel outweighs the import.

## Quality

- [x] ASCII only, present tense, no session narrative, no machine paths.
- [x] `SKILL.md` stays a lean hub: the new detail is one clause on an existing bullet plus a routing
      table entry, and the section itself lives in the reference file.
- [x] `hookdoc_stamp.py coverage` still reports complete (31 events, 65 required names).

## Deliverables

- [x] One new section and three amended traps in `references/authoring.md`; two amended bullets and
      one routing-table row in `SKILL.md`. No script change, so no `tests/` change here.
