# skill-writer checklist - meta-skill-writer (table re-pad exception; closing the receipt)

Change: (1) the Iron Law gains a second mechanical carve-out, WHITESPACE-ONLY TABLE RE-PADDING
proven cell by cell, with four conditions, the rule for when a commit gate's proof stands in for
the review artifact, and what is NOT the exception (a word fix, inner spacing, a fenced table, a
still-non-canonical result; split such a change). (2) The procedure gains a closing step,
`skill_receipt.py end meta-skill-writer`, beside Step 0 and as the last Deployment box, with the
receipt's 8-hour expiry and `check`.

## PLAN

- [x] Skill type: discipline (the Iron Law) for (1); technique (a procedure step) for (2).
- [x] Scenarios drafted before editing: A, a pure re-pad with the four facts stated; A-neg, the
      same re-pad plus a one-word fix in a cell (the direction where the exception must NOT
      apply); B, the procedure is finished and the session moves to unrelated work.
- [x] Scope: two passages of an existing hub skill; no front-matter change, no supporting file.

## RED

- [x] Inherited-context check: `redcheck --corpus-cascade` named a memory fact for A that teaches
      committing the formatter's output with a mechanical artifact, so a behavioural RED for A
      could answer from inherited context. Route taken: a text check of the artifact (the
      pre-change file names no re-pad or padding exception and no `end` step: grep, zero hits)
      plus quote-back probes that must quote the supplied text or answer NONE. For B the hits
      were shared vocabulary only; no document teaches `skill_receipt.py end` for this skill.
- [x] RED A (pre-change Iron Law text): chose B, run RED/GREEN, quoting "Fail any one of the three
      and the Iron Law applies unchanged."; gap reported verbatim: "The text never directly
      addresses a pure body-formatting change (table whitespace re-pad) ... gives no parallel
      carve-out for semantically-inert body formatting".
- [x] RED B (pre-change Step 0 + Deployment): closing quote NONE; gap reported verbatim: "nothing
      in the given text states a parallel closing action (e.g., an "end" receipt ...)".

## GREEN

- [x] GREEN A, sonnet: chose A, walked all four conditions, quoted the gate sentence and took the
      "anywhere else" branch, listing the four facts the artifact must state.
- [x] GREEN A, haiku: chose A. Its quote merged a sentence of the first exception into the second
      (not verbatim); the decision and the four listed facts were right.
- [x] GREEN A-neg, sonnet and haiku: both chose B, quoting "A re-pad that also fixes one word ...
      is not this exception". The exception does not fire where it must not.
- [x] GREEN B, sonnet: named `skill_receipt.py end meta-skill-writer` as the remaining step, quoted
      the "Last step" passage, and in a follow-up scenario re-issued `start` before a later edit.
- [x] Every dispatch asked for a "Skill gaps" section; the lists are worked below.
- [x] GREEN diffed against RED in both directions: RED A's reading that a table row is a body line
      (so the front-matter exception never covers it) survives as the reason the second exception
      is separate; nothing RED produced is missing from GREEN.

## REFACTOR

- [x] Gap (A-neg, sonnet) "no guidance on mechanics of splitting the commit" - CLOSED: the text
      now says the Iron Law applies to the whole change and to commit the re-pad on its own.
- [x] Gap (B) "no text defines what a fresh receipt means in terms of time/TTL" - CLOSED: the
      passage now states the receipt expires 8 hours after `start`.
- [x] Gap (A, sonnet) "partial gate proof" - CLOSED. First judged covered by "proves all four
      itself", but the quote-back answered NONE for a gate that checks only some conditions, so
      the text now says "a gate that proves only some of them is not" a record.
- [x] Gap (A, sonnet) "location/format of the review artifact" - DECLINED: Step 0 names
      `.skillwriter/checklist-<date>.md`; outside the probe's excerpt only.
- [x] Gap (A-neg, sonnet) "how much testing a one-word fix needs" - DECLINED: governed by the Iron
      Law as written; out of scope of this change.
- [x] Gap (B) "are the other Deployment boxes prerequisites of closing" - DECLINED: the closing
      step names its own precondition (the change and its review artifact committed).
- [x] Each closed gap verified by quote-back (direct quote or NONE) on the final text.

## Quality

- [x] ASCII only across the file; no address, hostname or machine path added.
- [x] Present tense, no session narrative.
- [x] Front matter untouched; `build_skill_triggers.py --check` in sync.
- [x] Tables in the file canonical per `reformat_tables.py --check`.

## Deliverables

- [x] SKILL.md Iron Law section and the closing-receipt step, applied.
- [x] The sanctioned exception is enforced mechanically, not left to prose: `repo-gate.py`
      `table_repad_problem` proves the four conditions against origin/master and waives the
      checklist only then; tests in `hooks/tests/test_repo_gate.py`, each condition mutated out
      and its test watched to fail.
