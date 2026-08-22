# skill-writer checklist - git-worktrees (the tell for a shared build cache)

Change: extend the existing "Sharing a build cache dir" Quick Reference row with the recognition
signal - phantom errors naming real symbols, and the grep that identifies them.

## PLAN

- [x] Skill type: procedure with a Quick Reference table. Test approach: text check of the
      artifact.
- [x] Checked what the skill ALREADY says before writing, and it is partially covered: the row
      already prescribes a per-worktree `CARGO_TARGET_DIR` and already mentions phantom errors.
      What is missing is the DIAGNOSTIC - how a reader recognises they are in this situation while
      staring at a compiler error that names real symbols.
- [x] Scope: extend the existing row. A new section would separate the symptom from the rule that
      prevents it.

## RED

- [x] Behavioural RED is NOT available on this machine: `redcheck.py --corpus-cascade .` reports
      INHERITED COVERAGE naming `.claude-memory/facts/no-build-topic-worktree-in-ovm-target.md`.
      Route taken: TEXT CHECK of the artifact.
- [x] The RED against the FILE failed before this change in the specific direction that costs time:
      the row told a reader what to DO, and a reader who had not done it had no way to recognise
      the resulting error as this problem. The error reads as a defect in the code in front of you.

## GREEN

- [x] Text check: the row now states what the compiler actually does (links the other worktree's
      crate), why that misleads (the symbols are real), and the test that settles it.
- [x] Quote-back for the diagnostic: "THE TELL: grep your own worktree for the name the compiler
      SUGGESTS; zero hits means you are reading a sibling's build."

## REFACTOR

- [x] The measured evidence is kept as a SHAPE, not as borrowed symbols: the error is given as
      `no method named X found, help: there is a method X_ns with a similar name`, so the pattern
      (the suggestion differs by a suffix) transfers to any language, and no private project's
      identifiers ship in the marketplace.
- [x] Kept the existing remedy sentence (sccache for cross-tree reuse) so the row still answers
      "then how do I share anything".

## Quality

- [x] ASCII only, present tense, no session narrative, no machine paths, no private symbols.

## Deliverables

- [x] One extended Quick Reference row in `SKILL.md`. `scripts/wtclean.py` and its tests are
      unchanged.
