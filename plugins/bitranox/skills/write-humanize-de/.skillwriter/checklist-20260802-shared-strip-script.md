# skill-writer checklist - write-humanize-de (2026-08-02, one shared strip script)

Change: this skill no longer ships its own `scripts/strip_typographic_tells.py` or its tests. Both
now live once at `<plugin>/hooks/`, and the skill's five invocations point there. Ships with 5.135.0.

- [x] Receipt held (`skill_receipt.py start meta-skill-writer`, re-issued this session).
- [x] ROOT CAUSE of a defect that had already bitten: the script shipped TWICE, byte-identical,
      under one module name. In a whole-plugin pytest run the DE copy loaded first, so the EN tests
      were exercising the DE script - which is why the EN code-span fix looked absent while passing
      in isolation. One copy makes that impossible rather than merely unlikely.
- [x] Verified the DE tests carried nothing language-specific before deleting them: a diff against
      the EN file showed 0 DE-only lines - it was a strict subset. The suite total drops by ~54
      because those tests were running the same code twice, not because coverage was lost.
- [x] New home is `hooks/`, matching where this plugin already keeps shared code a skill invokes
      (`memory_engine.py`, `tell_chars.py`), and where the `tell_chars` module it depends on already
      sits - so the import is now a sibling lookup rather than a three-level walk.
- [x] All five invocations in this SKILL.md repointed to
      `bash <plugin>/hooks/run-python.sh <plugin>/hooks/strip_typographic_tells.py`, per the rule
      that a cross-skill script reference states its home and its launch shim. Verified: 0 stale
      `scripts/strip_typographic_tells` references remain anywhere in the catalogue.
- [x] Verified three ways, because the collision was invisible to one of them: plain pytest (1394),
      the CI dependency set (1388), and `repo-gate --ci`. The gate had caught it only because it
      passes `--import-mode=importlib` for exactly this reason.
- [x] Also corrected `repo-gate`'s comment, which cited these two files as its example of colliding
      basenames - true when written, false now. It names `test_git_state.py` instead, which still
      collides.
- [x] No session narrative or private provenance added; no machine paths added.
