# Skill-writer checklist: recording a declined owed nap (backlog 890)

Scope: one new bullet under "When to run" telling the reader how to record that the USER declined
the owed post-compaction nap (`dream_state.py nap-decline --by user`), what that does to the Stop
gate, and that it is only for the user's own word. The mechanism ships in the same change:
`self_improve_signals.decline_nap_owed` / `nap_owed_declined` / `nap_owed_blocks`, the gate's
`_nap_owed_hint`, the context watcher's yield, and the `nap-decline` verb in `dream_state.py`.

## RED

- [x] The skill did not say the rule: `grep -niE "declin|nap-decline|said not to|do not run"
      skills/meta-dream-nap/SKILL.md` on the pre-edit text returned nothing (exit 1), and the same
      grep over `skills/meta-dream-tree/SKILL.md` and its `references/*.md` returned nothing.
      Text check of the artifact, not a behavioural arm: the verb did not exist before this
      change, so no reader could have produced it.

## GREEN

- [x] Quote-back of the new text (SKILL.md, When to run): "The user declines the owed nap (says
      not to run it, or not to read that old session): record it with `python3
      <plugin>/skills/meta-dream-tree/dream_state.py nap-decline [cwd] --by user`, then stop."
      and "Run it only on the user's own word in this conversation: the gate's block is not a
      reason to decline, and neither is a transcript that looks uninteresting."
- [x] Every mechanism claim in the bullet checked against the code:
      - "Without that record the gate blocks again on the next message": the gate's dedup key is
        the sha1 of the last user message (`self-improve-gate.py`, `sig = hashlib.sha1(...)`), and
        `test_a_nap_the_user_declined_no_longer_blocks` goes RED with the decline check removed.
      - "stops blocking until the next compaction owes a new nap": `mark_nap_owed` rewrites the
        marker without the decline; `test_a_later_compaction_owes_a_new_nap_the_decline_does_not_cover`.
      - "the flag stays set": `decline_nap_owed` keeps the marker; asserted by
        `test_declining_an_owed_nap_records_who_and_when` (`is_nap_owed` stays True).
      - "a later dream still offers that transcript": `dream_state._review_target` reads the owed
        transcript first while it has unread bytes, and the decline does not touch the watermark.
- [x] The Stop gate's own block text names the verb and the same restriction ("on the user's own
      word only, never because this block is in the way"), pinned by
      `test_owed_nap_reason_directs_to_the_nap_and_says_read_from_disk`.

## Not run

- [x] No subagent RED/GREEN arm: this change was made under a no-dispatch constraint, so the
      evidence is the text check above plus the hook and CLI tests. Recorded as unverified on a
      live reader.

## Quality

- [x] Frontmatter unchanged (description untouched, so no derived artifact moves).
- [x] ASCII only; no address, hostname or machine path added (the path shown is `<plugin>/...`).
- [x] Present tense, no history narrative; the latest-release finder pattern has no hit in the
      new bullet.
- [x] Not a mirrored skill: `repo-gate.py --mirrors` lists no twin for meta-dream-nap.
