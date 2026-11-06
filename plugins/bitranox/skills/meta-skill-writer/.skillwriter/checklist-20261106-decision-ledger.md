# Review checklist: meta-skill-writer, the decision ledger (2026-11-06)

Change covered: Step 0b (read a skill's rejected and removed decisions before the first edit, and
reverse one only with an answer to its `reopen_if`), "Record every decision the edit makes"
(kinds, fields, evidence tiers, anchor choice, baseline pass, the checklist `Decisions:` line),
the "A decision is not a story" carve-out after "Keep out of both", one sentence after "Where the
loop stops", and a PLAN and a REFACTOR checklist box. The skill's own ledger is created with this
change.

Decisions: d-20261106-c0264155, d-20261106-4fc131dc, d-20261106-c667b338, d-20261106-02d4c22c, d-20261106-e9ea1801, d-20261106-9d417d2a

## Evidence

- [x] Step 0b of the procedure ran: the skill had no ledger, so `show meta-skill-writer` printed
      nothing; no recorded decision is reversed.
- [x] RED as a text check on the pre-edit file: `decisions\.jsonl|skill_decisions|prior
      decision|declined decision` 0 hits.
- [x] RED behavioural, opus and haiku `bitranox:baseline-probe` arms loading the installed
      pre-edit skill, scenario "re-add a rule removed from devops-bmk last month": both answered
      NONE to "look up earlier decisions before editing", "where are they recorded" and "record
      the decision afterwards". Both also read "Keep out of both: what the operator ... changed
      their mind about" as forbidding any record of a reversed decision.
- [x] `redcheck --corpus-cascade`: verdict inherited on the shared terms come, condition,
      decisions, re-add in the tree-top memory index; adjudicated a false positive, since none of
      those index lines says to look up a skill's earlier decisions. The behavioural RED stands.
- [x] Every command the change adds was executed before the GREEN probe, in a scratch git repo
      holding a copy of the skill: `add --from-file` (rc 0, id printed), `show <skill>` and
      `show <skill> --kind rejected,removed --full` (rc 0; nothing printed before any entry
      existed), `check <skill>` (0 findings), and `show <skill> --skill-dir <dir> --full` run
      from a directory outside any repository (rc 0, the entry printed).
- [x] Claims checked against the code: `add` refuses an anchor found other than exactly once
      (`skill_decisions.py`, `_anchor_count_problems`, `hits != 1`); `add` assigns `v`, `id` and
      `date`; required fields and the four tiers match `validate_entry`; `repo-gate.py --ci`
      sweeps every ledger (`check_all_skill_decisions` in `run_checks`).
- [x] GREEN, opus and haiku arms with the edited sections pasted: both run both `show` commands
      before the edit, keep the removal when the `reopen_if` is not met ("without that answer,
      keep the decision"), write a superseding `rule` entry with `supersedes` naming the old id,
      put the reason in the ledger and not the checklist, and give the `Decisions:` line, each
      with a direct quote.
- [x] GREEN gaps closed in the text: the `kind` field named; the `reopen_if` answer goes in the
      new entry's `why`; the four evidence tiers defined; edit first, then the entry (an anchor
      quotes the text as written), replacing "first records"; `topic` reused from the superseded
      entry; `refs` defined; Step 0b runs after the receipt; mirrored pairs found with
      `repo-gate.py --mirrors`; an edit that deletes an anchored sentence records a superseding
      entry; `add` refuses an anchor found zero times as well as twice; non-rule kinds take
      `"anchors": []`.
- [x] Delta re-probe on the touched questions, opus and haiku, quote-back required: both quoted
      the governing line for kind, the `why` field, the `inherited` tier, edit-then-entry, topic
      and refs, and the superseding entry for a deleted anchor. The haiku arm put an anchor on a
      `removed` entry; after the `"anchors": []` line, a haiku quote-back quoted it and answered
      `[]`. No new undecided gap after that run.
- [x] Gaps declined: whether one entry or two should record a re-add that also deletes a rule
      (judgement the skill leaves open: both pass the gate); whether an `inherited` changelog is
      enough to answer a `reopen_if` (judgement; the tier records how strong the answer is); "two
      Step 0s" (the receipt is labelled FIRST and Step 0b says "after the receipt"); what a
      failing RED looks like for a re-add (owned by the testing guidance, out of scope here);
      gaps from the one-bullet quote-back about `supersedes` and a required `why` (covered
      elsewhere: "names the old one in `supersedes`" and "Each entry also has ... `why`" in the
      same block).
- [x] Diffed GREEN against RED both ways: the receipt, plan, owning-repo and RED steps the RED
      arms listed are all still in the GREEN answers; nothing lost.
- [x] Width and fence check over the added lines printed nothing; ASCII only; the paragraph after
      each insertion point read (the "The trap is" paragraph still follows the Keep-out text, and
      "Last step" still follows the new blocks).
- [x] No private paths, hosts or names in the skill text, the ledger entries or this checklist.
- [x] Tiers and cells: RED 2 (opus, haiku), GREEN 2, delta 2, quote-back 1 (haiku).
