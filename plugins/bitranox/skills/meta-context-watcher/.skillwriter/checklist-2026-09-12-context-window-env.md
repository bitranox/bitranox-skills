# Skill-writer checklist: meta-context-watcher declared-window leg (2026-09-12)

Scope: "When it fires on its own" section only, mirroring the context-watcher.py hook fix shipped
in the same change (unknown model family reads `CLAUDE_CODE_MAX_CONTEXT_TOKENS`). Reference-type
edit tested by retrieval scenarios; no workflow, frontmatter, name or triggers changed.

## RED (baseline, pre-change text)

- [x] Dispatched a sonnet baseline-probe with the pre-change text verbatim, three retrieval
      questions. Results: Q1 quoted "so nothing needs configuring" as covering glm-5.3 - a false
      claim the text asserted unconditionally. Q2 (what window for a non-family model) answered
      NONE. Q3 (does the watcher use CLAUDE_CODE_MAX_CONTEXT_TOKENS) answered NONE. Gaps also
      flagged: the text never says which model's record governs, and never reconciles "nothing
      needs configuring" with the escape hatch that exists because it sometimes fails.
- [x] Inherited-coverage check: the scenario is about THIS hook's window resolution; no ancestor
      CLAUDE.md or memory fact on this machine documents the declared-window leg (it was
      discovered this session from the CLI binary). Not inherited.

## GREEN (post-change text)

- [x] Same three questions plus a fourth (which model's record decides) against the new text.
      All four answered with direct quotes: declared window for glm-5.3 (no configuring needed),
      200k for neither-known-nor-declared, most recent assistant record governs.
- [x] GREEN diffed against RED in both directions. Gained: the declared-window rule, the
      precedence rule, the 200k fallback, the governing-record answer. Lost: nothing - every RED
      gap is either closed in the text or declined below.

## REFACTOR (from GREEN's gaps list)

- [x] Precedence order now stated as one rule (family, then declaration, then 200k), including
      why a known family ignores the env var.
- [x] The severed "Declining" paragraph (a stray paragraph break my first edit left) re-joined.
- [x] The malformed backtick pair in the min() formula fixed to a single clean code span.
- [x] DECLINED: distinguishing "launcher declared it but the hook cannot see it" from "nothing
      declared" - both fall back to the 200k window, which errs small (asks early, costs a
      decline, never silently inert); the misconfigured report catches an over-large window, and
      a too-small one cannot be caught by construction. No reader action differs, so no rule.
- [x] DECLINED: how a family is recognized from a record (prefix table) - implementation detail
      of the hook, not guidance the skill's reader needs; the hook source documents it.

## Quality checks

- [x] No frontmatter, name, description or trigger changed (verified by diff: body section only).
- [x] No narrative provenance, no session log, no machine-specific values in the new text.
- [x] Addresses reserved as documentation values: none added (glm-5.3 is the model id under
      discussion, not an address).
- [x] Word budget: the section stays a reference doc; no bloat added.
- [x] Tests for the hook itself: test_context_watcher.py extended (7 new tests), 63 pass,
      RED-verified by mutation (the env-leg mutation killed exactly the two env-leg tests,
      controls stayed green).
