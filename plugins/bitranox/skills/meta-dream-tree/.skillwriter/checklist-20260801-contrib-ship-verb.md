# skill-writer checklist - meta-dream-tree (2026-08-01, close a contribution by outcome)

Change: step 10's delivery instruction said "`contrib_queue.py drain` ONLY for the ones that
actually shipped; leave one queued" - an operation the tool cannot perform, since `drain` clears
the entire queue. It now closes each delivered entry with `ship --match`, each disproven one with
`drop`, and reserves `drain` for a sweep where every entry shipped. Ships with plugin 5.124.0.

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] RED and GREEN ran hermetically in two separate temp dirs, each seeded with the SAME four
      contributions, each arm's agent RUNNING its chosen commands, and both judged on the resulting
      STATE rather than on the reply. An earlier attempt let RED's run mutate state that GREEN then
      read, and GREEN duly reported "no new commands needed" off the leftovers.
- [x] Weak, literal model (haiku) for both arms. Recall was walled for the runs and the setting
      restored and verified afterwards.
- [x] RED, on the old prose plus the old interface, LOST DATA. It filed the delivered contribution
      as `drop --index 1 --reason "shipped: included in 5.122.0 release"` - the same mislabel that
      motivated this change - and then, because the index had shifted under that close, dropped
      "needs user input one" as well, stamping it with the other entry's reason. Ground truth: 1 of
      2 must-stay contributions destroyed, 3 records in the rejected tombstone, none shipped.
- [x] GREEN, same seed and model on the new prose plus `ship`/`--match`: pending held exactly the
      two must-stay entries, `shipped` held the delivered one with its release note, `rejected` held
      the disproven one. Nothing lost, nothing mislabelled.
- [x] GREEN's gaps list worked as REFACTOR input. The first GREEN reported inferring the safe close
      ORDER ("didn't clarify that dropping index 1 would cause a reindex ... I inferred the correct
      order"), which is the hazard RED had just triggered - so `--match` was added as an
      order-proof selector, refusing on no match or an ambiguous one, and the prose now names it
      instead of `--index`. The final GREEN reported only scenario artifacts.
- [x] Tool changes ship with sibling tests: 12 new cases in
      `skills/meta-self-improve/tests/test_contrib_queue.py` covering the outcome split, the
      re-queue block reading the closed set, back-compat for records with no outcome, the `--match`
      selector, its ambiguity and no-match refusals, and the exactly-one-selector rule. Each was
      verified RED before the code existed. Full suite 889 pass.
- [x] No session narrative or private provenance in the skill text; verbatim agent output appears in
      this artifact only where it IS the evidence.
- [x] No addresses, MACs, hostnames or machine paths added.
