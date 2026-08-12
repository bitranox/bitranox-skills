# skill-writer checklist - compuse-toolbox (2026-08-12, redcheck row leads with the startup-context question)

Change: the `redcheck` routing-table row and its narrative bullet are rewritten around the question
a user actually arrives with - "does the agent already know this, so my baseline prompt cannot
really fail?" - and now name the new `--corpus-cascade` mode, which assembles that startup context
instead of leaving the reader to enumerate it. The usage column carries a runnable invocation and
the two exit codes that matter (1 = already covered, 3 = empty corpus).

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: hub / routing table. The edit is one row plus its narrative bullet.
- [x] NO BEHAVIOURAL RED WAS STAGED on the underlying lesson, for the reason the tool exists: it is
      already in this machine's always-loaded index, so an arm testing it cannot fail honestly.
      Declared route for this file: a RETRIEVAL test on the row's own wording, which is novel text
      and therefore not something inherited context can supply.
- [x] RETRIEVAL TEST FAILED FIRST, and was fixed rather than rationalised. One
      `bitranox:baseline-probe` (sonnet, foreground, unnamed, whole table visible, NONE explicitly
      allowed, one question, zero tool calls) was asked in a user's own words: about to hand a
      fresh subagent a prompt to prove new guidance is needed, warned the answer may already sit in
      the notes and rule files the machine feeds every agent at startup, does not want to read them
      by hand. Verdict: NONE. The old row led with the jargon "RED" and with "CLAUDE.md chain and
      memory bodies", none of which the user's phrasing contains.
- [x] THE FAILING PROBE ALSO DEMONSTRATED THE CONTAMINATION THE TOOL IS ABOUT, which is why the
      NONE is trustworthy rather than noise: it volunteered that a tool named `redcheck` answers
      the question and then asserted that tool was "outside the table you gave me" when the row was
      in fact row 15. It knew the tool from its inherited context and still could not find the row,
      so the miss is a property of the ROW, not of the probe's ignorance.
- [x] ROW REWRITTEN to lead with the chore ("reading by hand every notes/rules file a machine feeds
      an agent at startup"), then the user's question in quotes, then what the tool does about it.
      The jargon term is kept only as "baseline/RED prompt", after the plain wording.
- [x] RETRIEVAL RE-TESTED after the rewrite with the identical question and a fresh probe: picked
      `redcheck`, gave the correct reason (it assembles the startup context and names the file that
      already teaches the scenario), quoted the runnable invocation, zero tool calls.
- [x] The usage column carries real runnable value, not a placeholder: the full relative path to
      the script, the flag pair a reader would actually type, and the two exit codes that change
      what they do next.
- [x] Accuracy check (table to file): every claim in the row and the bullet is true of the shipped
      tool - the mode name, the files it reads, gitignored files being included, naming the file
      that teaches the scenario, the answer-leak check, exit 1 and exit 3, and the strong-versus-
      weak asymmetry. Verified against the tool's own `--help` and a real run, not from memory.
- [x] Cross-skill pointer kept accurate: the row and bullet still say the tool ships in
      `process-test-driven-development` and is only indexed here, so the table stays the one place
      that answers "is there already a tool for this?".
- [x] Table formatting: the row keeps the three-column shape and the file was left as the
      table-formatting hook rewrote it.
- [x] Token budget: one row and one bullet, no new section.
- [x] Frontmatter description unchanged.
- [x] No session narrative, no machine paths, no memory-fact slugs in the skill text.
- [x] No addresses, MACs, hostnames or machine paths added.
