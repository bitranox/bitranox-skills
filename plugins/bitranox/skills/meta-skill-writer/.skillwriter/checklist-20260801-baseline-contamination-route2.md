# skill-writer checklist - meta-skill-writer (2026-08-01, injected-context baseline contamination)

Change: the "Watch for baseline contamination" section in testing-skills-with-subagents.md now
covers TWO routes. Route 1 is the existing one, the agent explores its way to the answer, and its
scratch-dir fix is marked as closing that route only. Route 2 is injected context - a memory or
recall hook, a RAG layer, an auto-loaded rules file - which a scratch dir does not close, with the
unfindable-citation tell, the fabrication-versus-injection split, and ranked isolation. The RED
section of SKILL.md gains a pointer naming all three ways a baseline falsely passes. Ships with
plugin 5.123.0.

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: technique. Application scenario.
- [x] Not a new section. The existing text prescribed the fix that FAILS for route 2 - "run it with
      neutral framing ... or from a scratch dir outside the tool's repo" - so an author following
      it got a false all-clear from the skill's own contamination check.
- [x] Isolation used for BOTH arms, per the rule being shipped: clean room outside the tree, recall
      walled with `cross_tree_search: false`, restored and VERIFIED at its original value with the
      full config printed back. Without it the arms would have measured the memory fact written
      earlier the same session, which is the exact failure under test.
- [x] RED failed decisively. Scenario: an author whose baseline PASSED, having pinned a weak model,
      withheld the trap, and run from a scratch dir - with the baseline reply quoting a rule
      attributed to the procedure file. Verdict: "There is NO gap to fill. ... Do not edit the
      skill." It then ran the skill's own contamination check and cleared it - "You ran from
      scratch directory (check), so this check passes" - pronounced the baseline trustworthy,
      "Yes", and never noticed the unfindable quote sitting in the reply it was shown.
- [x] Weak, literal model (haiku). The scenario withheld the trap: it never mentions memory,
      recall, injection or quoting, and it states the two documented mitigations were already
      applied so the obvious answers are pre-empted.
- [x] GREEN, same model, same prompt, same isolated environment, reversed it: "the baseline PASSED
      for the wrong reason ... That exact sentence is not in your scenario. This is Route 2
      contamination (environmental injection)", and it prescribed grepping the quote to confirm.
- [x] GREEN's gaps list worked as REFACTOR input. Three reported, three CLOSED:
      - it could not tell whether a hallucinated rule counts as contamination or legitimate
        baseline signal, noting "a hallucinated rule that matches your intuition does not prove
        your gap exists". That distinction was missing and is now stated: an unfindable quote has
        two explanations, grep the corpus to tell them apart, and BOTH void the baseline.
      - the route-1 scratch-dir sentence read as sufficient isolation on its own, so it now says
        "which closes THIS route ONLY, never route 2".
      - it could not name the injector in a reader's own environment, which a shipped skill cannot
        do; answered instead with the environment-agnostic action, grep the quote across the rules
        and memory corpus to find the source.
- [x] Verified by quote-back: five contested questions, each answered with a direct quote, no NONE -
      the three false-pass routes, what a scratch dir closes, the unfindable-quote explanations and
      response, whether fabrication is usable evidence, and what to record when isolation fails.
- [x] Written for readers who do not run this plugin: routes and tells are stated generically
      (memory hook, RAG layer, auto-loaded rules file), with the CLI-specific blanket switches named
      only as the option that costs auth.
- [x] Token budget: the detail lands in the reference file that owns baseline mechanics; SKILL.md
      gains a short pointer in the RED phase rather than the full treatment.
- [x] No session narrative or private provenance in the skill text; verbatim agent output appears in
      this artifact only where it IS the evidence.
- [x] No addresses, MACs, hostnames or machine paths added.
