# checklist - self-review item 14, refusals that must fire

Self-Review gains item 14: code that must refuse over input it could not read reads first and
classifies the error, never gating the read on `Path.exists()`/`is_file()`, with a mode-000 RED
test; and each prescribed refusal test must fail in the scratch copy before its task's code is
applied.

Decisions: d-20261115-70fc73b0, d-20261115-f2900b7b

## RED

- [x] Skill decisions read first: one rejected entry (no fixed numbers in item 7); untouched.
- [x] Mechanism measured before writing it down: as a non-root user, a file inside a mode-000
      directory makes `Path.exists()` and `is_file()` raise PermissionError on 3.12.15 and
      3.13.16 and return False on 3.14.8; `read_text()` raises PermissionError on all three.
- [x] The `is_file` lesson is already in this machine's memory index, so a behavioural RED cannot
      fail honestly; the evidence is a coverage check against the skill file.
- [x] Coverage check on the pre-edit Self-Review, inert text-only probe, opus and haiku. Q1
      (existence probe before a read that must refuse): NONE on both tiers. Q2 (a refusal test
      already answered by an earlier generic guard): NONE on both tiers; both named items 9 and 12
      as the same principle scoped to substring assertions and argparse exit 2 only.

## GREEN

- [x] Same questions on the edited text, opus and haiku, plus a control (an optional config read
      with `if path.is_file()`, absence normal). Both tiers quoted item 14 for Q1 and Q2, rewrote
      the loop to read-then-classify, prescribed the mode-000 test, and described the
      before-code run. Control: both left the optional read alone (item 14's trigger is a task
      that must refuse).
- [x] Quote-back: each quote is verbatim from the edited text.
- [x] GREEN diffed against RED: no baseline result lost.

## REFACTOR

- [x] Every dispatch asked for a `Skill gaps` section; all lists recorded and decided.
- [x] Declined: "what a missing body should do" - set by the task's own STOP condition, not by a
      generic item.
- [x] Declined: "mode 000 does not stop reads on Windows" - item 10 (Platforms) already requires
      each prescribed test to pass on every CI OS or skip with a stated reason.
- [x] Declined: "an earlier guard that refuses every input to the verb" - then the new refusal is
      unreachable, which is a plan finding in its own right; judgement left to the author.
- [x] Declined: "an unreadable optional file" - outside the item's trigger.
- [x] Width and fence check over the added lines printed nothing; the paragraph after the item
      ("If you find issues, fix them inline") read, still correct; the Self-Review intro states no
      item count.
- [x] Both decisions recorded with `skill_decisions.py add` (rule entries with anchors).
