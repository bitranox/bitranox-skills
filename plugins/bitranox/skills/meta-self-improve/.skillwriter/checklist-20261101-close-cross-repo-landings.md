# skill-writer checklist - meta-self-improve (2026-11-01, close entries that land in another repo)

Step 3b gains one bullet continuation after "Close an entry only once it actually shipped...": a
contribution delivered in ANOTHER repo (a private repo, the local toolbox, a user command) is
closed in the same pass that verifies the landing, against the queue it was FILED in, one `ship`
per entry with the queue as the last argument, lengthening `--match` on an ambiguous match, and a
`list <queue>` afterwards. Nothing else in SKILL.md changed.

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: technique; the test is application - closing 22 entries delivered elsewhere.
- [x] RED (opus + haiku, pre-edit step 3b text): both answered NONE for "when and against which
      queue do you close entries delivered in another repo".
- [x] GREEN (opus + haiku, edited text): both quoted "close it in the same pass that verifies the
      landing" and "Close it against the queue it was FILED in, not the repo it landed in".
- [x] Gaps from both GREEN probes FIXED: where the queue goes on `ship` (last positional, as on
      `add`; checked against the argparse definition in contrib_queue.py), what happens on an
      ambiguous `--match` (it refuses, per the module docstring), how to confirm (`list <queue>`),
      and the note format (`"<repo> <commit>"`). Gaps DECLINED: the `queues` output format (the
      command is self-describing and documented in references/memory-backend.md); a batch close
      verb (out of scope for a text change).
- [x] Re-probe on the final text (haiku): gave `ship --match "nap-owed key" --note "<repo>
      <commit>" <queue>` against the FILING queue, lengthen-on-ambiguous, and `list <queue>`
      to confirm. Remaining gaps (zero-match case, key format) DECLINED: the tool refuses a
      zero match loudly and `queues` prints the key.
- [x] Tiers: opus + haiku (RED, GREEN), haiku (final). Self-improve is the highest-risk skill, so
      both tiers ran at RED and GREEN.
- [x] Description unchanged - no routing keyword moved.
- [x] Added lines within width; ASCII only; no address, hostname or machine path; no history
      phrasing.
