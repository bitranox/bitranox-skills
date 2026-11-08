# Review checklist: meta-skill-writer, restoring a voided entry (2026-11-06)

Change covered: one sentence in the `void` bullet of "Record every decision the edit makes". It
said "to restore a voided entry, add it again as a new entry"; an unchanged re-add with the same
date is refused as identical, so the text now says to add it again with its `why` saying it
restores that entry, which gives it a new id. No rule is added, removed or reversed; none of the
five anchored sentences is touched.

Decisions: none - wording corrected to match the shipped code; no rule changed

## Evidence

- [x] Step 0b of the procedure ran: `show meta-skill-writer` lists five live `rule` entries and one
      `rejected` entry; this change touches none of their anchors.
- [x] The claim checked against the code: `skill_decisions.py` `entry_id` is
      `d-<date>-<first 8 hex of sha256 over the entry without its id>`, and `_entry_problems`
      refuses an entry whose id is already known with "id: an identical entry is already in the
      ledger or earlier in this batch". A changed `why` changes the hash, so the id is new, and no
      void supersedes that new id, so the entry is live.
- [x] Executed against the shipped code in a scratch skill dir: `add` of a `rule` entry wrote
      `d-20261106-e98f5af2`, rc 0; a `void` naming it wrote `d-20261106-3d62adc2`, rc 0; the same
      `rule` entry again was refused, rc 1, with the "identical entry" line above; the same entry
      with `why` changed to say it restores the voided id wrote `d-20261106-f248a62f`, rc 0; `show`
      then listed `d-20261106-f248a62f` as the one live entry.
- [x] The refusal is pinned by `test_an_identical_entry_is_refused_in_the_batch_and_against_the_
      ledger` in `hooks/tests/test_skill_decisions.py`.
- [x] `python3 plugins/bitranox/hooks/skill_decisions.py check meta-skill-writer`: 0 findings,
      rc 0.
- [x] No behavioural RED/GREEN probe: the change states what the code does and adds no rule, so
      the evidence is the code reading and the executed commands above, not an agent's choice.
- [x] Width and fence check over the added lines printed nothing; the paragraph after the edited
      bullet ("Each entry also has `topic` ...") holds no back-reference that re-binds.
- [x] No private host, path or session detail added to the skill.
