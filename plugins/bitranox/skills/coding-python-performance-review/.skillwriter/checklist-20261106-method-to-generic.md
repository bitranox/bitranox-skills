# skill-writer checklist - coding-python-performance-review (2026-11-06, method to generic)

The measurement method and the language-neutral checklist now live in
`bitranox:coding-performance-review`. Three passages here point there instead of restating them:

- "Always Flag: Unbounded Memory and Unsafe Input" keeps its heading and now says the
  language-neutral checklist and the method live in the generic skill ("load it alongside this
  skill"), with Step 4f named as this skill's Python scanner for the unbounded-memory item.
- The BEFORE-figure paragraph under "Validating a claim or comparing before/after" now reads
  "Before trusting an AFTER figure, follow the method in `bitranox:coding-performance-review`:
  reproduce the recorded BEFORE figure with the same probe, interleave the arms and pin the core."
- Key Behaviors: the two "ALWAYS flag unbounded memory" / "ALWAYS flag unsafe input" lines are one
  line, "ALWAYS walk the generic checklist - unbounded memory and unsafe input first".

Step 4f, `find_unbounded_memory.py` and the description are unchanged.

Decisions: d-20261106-4e9b9bbf

- [x] Receipt fresh (`skill_receipt.py check meta-skill-writer`).
- [x] Step 0b: `skill_decisions.py show coding-python-performance-review --kind rejected,removed
      --full` and `show coding-python-performance-review` both printed nothing (no ledger yet), so
      no recorded decision is contradicted.
- [x] Not mirrored: this skill ships only from this marketplace.
- [x] All three replaced passages were found verbatim before the edit.
- [x] RED (opus, no tools, pre-edit SKILL.md from `git show HEAD:` plus the generic SKILL.md pasted
      in full; scenario: a Python ETL step reading a 4 GB CSV with `f.read().splitlines()` and
      calling `requests.get` once per row). Expected to pass, since the old text carried the
      "Always flag" list itself. It did: finding 1 SEVERE unbounded memory, citing A "Always Flag"
      ("**Unbounded memory growth.** Code that reads big files ...") plus A "4f" and B "What to flag
      in code (any language)"; finding 2 SEVERE N+1, citing B "N+1 calls. A query, HTTP request,
      subprocess or RPC per item where one batched call would do."; finding 3 unsafe/untrusted
      input from both skills; a CSV-parsing correctness note.
- [x] GREEN (opus, same setup, edited SKILL.md). Pass: finding 1 SEVERE unbounded memory, citing
      B "What to flag in code (any language)" ("**Unbounded memory (usually SEVERE).** Reading a
      big file ...") and A "Always Flag" quoted as "sends the checklist to B: 'load it alongside
      this skill.'"; finding 2 SEVERE N+1 from B "N+1 calls"; finding 3 MEDIUM per-item I/O
      (connection per request) from B "Per-item I/O"; finding 4 unsafe and untrusted structured
      input from B. The quote of the new pointer line is the quote-back for the edit.
- [x] GREEN diffed against RED both ways: every RED finding is present in GREEN (memory, N+1,
      unsafe/untrusted input, the `splitlines()` CSV correctness point now inside finding 1); the
      sources moved from A's old list to B's checklist, as intended. Nothing lost in the probe.
      Text check of the removed passages against the generic skill: everything is carried there
      except two pieces of advice: when the reproduced BEFORE figure is far too fast, count calls
      into the hot function to find the guard that returns early and leave a comment in the test
      saying why its input has that shape; and the Python remedies list for unbounded memory
      (generators, `iter` chunks, server-side cursors). Open for the generic skill's Method item 2;
      not added here, since this change only points at the generic text.
- [x] Haiku arm of GREEN run beside opus (2 tiers, 3 cells: RED opus, GREEN opus, GREEN haiku).
      Pass: finding 1 SEVERE "Unbounded Memory" citing B "What to flag in code (any language)"
      and A "4f", with "A's `## Always Flag: Unbounded Memory and Unsafe Input` sends the reader
      to B for the checklist"; finding 2 SEVERE N+1 citing B "**N+1 calls.** A query, HTTP
      request, subprocess or RPC per item where one batched call would do."
- [x] Width and fence check over the added lines: one hit, the new Key Behaviors line at 120
      columns. Kept: it is the specified text, and the list already holds a 221-column line (the
      RESPECT prior decisions line). No fence problem. ASCII only.
- [x] Paragraph after each insertion point read: "## Purpose" follows the Always Flag pointer;
      "Report findings with measured numbers ..." follows the BEFORE-figure line and still reads on;
      the Key Behaviors line ends the list.
- [x] `build_skill_triggers.py --check` and `build_skill_docs.py --check` report in sync (no
      description changed).
- [x] Tests: this skill's suite plus the generic skill's pass with CI's dependency set (204 passed).

## Skill gaps reported by the probes, and what was decided

Both RED and GREEN reported the same gaps, so none is caused by this edit; each is declined here
as out of this change's scope (it replaces three passages and changes no rule):

- No N+1 / per-item I/O `Type` in Step 6 and no class for it in Step 5 (both arms). Declined, out
  of scope: classification here follows the generic checklist's severity definition, which both
  arms applied; extending Step 5/6 is a separate change.
- Profiling the real test suite hides network cost when tests mock HTTP (both arms). Declined, out
  of scope: a Python-pipeline question, unchanged by this edit.
- No peak-memory measurement guidance; no fallback when an API has no batch endpoint; no request
  timeout guidance. Declined, owned by `coding-performance-review` (its Method and checklist).
- Cache hit-rate threshold stated as ">=20%" and ">20%"; "accepted" versus "declined" for prior
  decisions. Declined, out of scope: pre-existing wording in sections this edit does not touch.
- Whether `find_unbounded_memory.py` matches a chained `f.read().splitlines()`. Declined,
  answerable only by running the scanner, which the text-only probe could not.
- One-at-a-time presentation versus the probe's request for a list. Declined: the probe's prompt
  asked for a list, not a gap in the skill.

Two gaps only the GREEN haiku arm reported (the first comes from this edit):

- The "Always Flag: Unbounded Memory and Unsafe Input" heading names two items while its body now
  lists six checklist items held in the generic skill. Declined: the heading is kept so the section
  name stays stable for readers who look it up, and the body states that the list lives in
  `bitranox:coding-performance-review`; both haiku and opus followed the pointer to B's checklist.
- 4f says SEVERE outright where B says "usually SEVERE" (haiku). Declined, out of scope: 4f is
  unchanged, and it adds the condition "confirm the source can actually grow unbounded" first.

## Follow-up: the Python remedies stay here

The text check above found the Python remedies list for unbounded memory carried by neither
skill. The pointer paragraph now ends "the Python remedies are generators, `iter` chunks,
server-side cursors, line-by-line or `io` streaming, and pagination" (the language-neutral early
return advice went to the generic skill's Method item 2, with its own checklist there).

- [x] RED (text check): `grep -i "server-side cursor"` over both skills' SKILL.md found nothing;
      the pre-edit text (`git show HEAD:`) had it at line 36.
- [x] GREEN quote-back, opus (effort medium) and haiku, 2 cells: asked which remedy the text names
      for a 30-million-row `fetchall()`, both quoted "server-side cursors" from the list above.
- [x] Gap both arms reported: the list ties no remedy to a case. Declined: choosing among them is
      the reviewer's judgement, and the Step 4f section is where a finding is written up.
- [x] The dropped clause "unless the project has deliberately accepted skipping it" is covered by
      the Key Behaviors line "RESPECT prior decisions by default, but RE-ASSESS them".
- [x] Added lines: none over 100 columns, no fence. ASCII only.

No ledger entry for this follow-up: it restores a list the pre-edit text carried, and the
decision recorded above still governs.
