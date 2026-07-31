# skill-writer checklist - meta-skill-writer (2026-08-01, diff GREEN against RED both directions)

Change: REFACTOR gains the rule that a GREEN run is diffed against the baseline in BOTH directions,
because a new step competes for the agent's attention rather than adding to it. A lost result is a
REFACTOR requirement ranked by value not count, confirmed to reproduce before any restructuring,
and a judgement that keeps being skipped after a mechanical step becomes a required OUTPUT of that
step. One checklist box added. Ships with plugin 5.122.0.

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: technique. Application scenario, per this skill's own testing table.
- [x] Tested under the rule shipped in 5.121.0: every arm was asked for a `Skill gaps` section, and
      GREEN's list was worked as REFACTOR input rather than treated as a pass.
- [x] RED attempt 1 gave the answer away and is reported rather than counted. The two arms were
      presented as tidy lists of 2 and 4 items, where the missing finding is visible at a glance.
      Real GREEN output is long prose in which an absence is invisible without a deliberate diff,
      so the format did the work the skill is supposed to do.
- [x] RED attempt 2 was realistic - two full six- and eight-finding review reports as separate
      files, differently ordered and reworded, the lost item buried mid-list, GREEN strictly richer
      at a glance - and it still passed. Investigating why produced the finding below.
- [x] ENVIRONMENTAL CONTAMINATION FOUND, and it invalidates a whole class of baselines on this
      machine. The attempt-2 reply quoted "A new step competes with the existing ones for the
      reviewer's attention rather than adding to it" and attributed it to the procedure file. That
      sentence is in no file the agent was given and nowhere in the plugin; it is verbatim from the
      curated memory fact's BODY. Route: the plugin's UserPromptSubmit recall hook runs in EVERY
      directory, and with `cross_tree_search` on (the default) it scans `discovery_roots()`, which
      is the configured list UNION `$HOME`. A temp dir with no CLAUDE.md on its ancestor chain is
      therefore still fed the answer. No directory on a machine with the store is a valid baseline
      environment for a rule the store already holds. `--bare` and `CLAUDE_CONFIG_DIR` both isolate
      it but take auth with them, so neither is usable.
- [x] Also worth stating: the agent FABRICATED the citation, presenting recalled text as a quote
      from the file it was told was its only source. This is why quote-back is verified against the
      file rather than trusted from the reply.
- [x] RED attempt 3, with recall walled to the current tree so the clean room reached no store,
      FAILED as predicted. The reply is entirely procedural and checks only what GREEN GAINED - "If
      RED did NOT flag duplicated helpers, identical signatures, or anonymous return shapes
      (expected)". The vanished SEVERE finding is never mentioned in any form.
- [x] Weak, literal model (haiku) throughout. Scenario withheld the trap: it never says a finding
      is missing, and states that the new section "produced exactly the kind of finding it was
      written to produce" so the gained side looks like success.
- [x] GREEN, same model, same prompt, same walled environment, reversed the verdict: "It is
      completely absent. F1 and F3-F6 all reappear in GREEN as G2, G4-G8, but F2 is gone", quoted
      the new text back, and rejected the trade - "The edit ships as 'more findings' (8 vs 6) but
      is actually a worse review for production risk".
- [x] GREEN's gaps list produced one real hole in the new text, and it is CLOSED: it could not
      distinguish a genuine attention loss from run-to-run variance ("The cause could be: the skill
      misdirected focus ... or the repository differs between runs. No way to know without
      re-running under controlled conditions"). REFACTOR now requires confirming the loss
      reproduces, naming the three rival explanations, because one run per condition shows a
      mechanism is plausible and never that it is stable. Its other four items are scenario
      artifacts (absent model tier, absent test prompts), not skill gaps, and are declined here.
- [x] Verified by quote-back: four contested questions, each answered with a direct quote of the
      governing sentence, no NONE - the diff direction, whether a loss is a trade, what precedes
      restructuring, and the fix for a skipped post-mechanical judgement.
- [x] The config knob flipped for the probes was restored and VERIFIED at the value it started on
      (`cross_tree_search: true`), with the full config printed back.
- [x] Token budget: hub skill, body remains an index; the addition sits in the REFACTOR phase it
      governs.
- [x] No session narrative or private provenance in the skill text; verbatim agent output appears
      in this artifact only where it IS the evidence.
- [x] No addresses, MACs, hostnames or machine paths added.
