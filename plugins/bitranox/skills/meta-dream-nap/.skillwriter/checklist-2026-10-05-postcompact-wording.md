# Skill-writer checklist: PostCompact wording correction (2026-10-05)

Scope: the frontmatter `description` and the "When to run" bullet both said "the PostCompact
nudge points here". Verified against `plugins/bitranox/hooks/post-compact-nudge.py`: it only
calls `mark_nap_owed(...)` and prints nothing (its own docstring: "PostCompact is a side-effect-
only event ... A reminder printed here therefore reached nobody"). The pointer-and-block comes
from `self-improve-gate.py`'s Stop gate (`_nap_owed_hint`), which reads the obligation and names
this skill. This is a FACTUAL correction to an existing claim, not a new rule, workflow step, or
trigger - no discipline is being taught or changed, so there is no agent behaviour to RED/GREEN
against. Both occurrences reworded to name the Stop gate as the thing that blocks and points here,
keeping PostCompact's role (recording the obligation) correct too.

## Verification

- [x] Claim re-checked against the current code, not assumed: read `post-compact-nudge.py` in
      full and traced `self-improve-gate.py`'s `_nap_owed_hint` / `_routing_hint` call chain.
- [x] No new trigger, rule, or workflow step added - only an existing mechanism description
      corrected, so the RED/GREEN pressure-test cycle does not apply (there is no agent decision
      to test; the description still starts "Use for a QUICK, cheap..." with every prior trigger
      phrase intact).
- [x] Frontmatter still parses (`name`/`description` only) and `description` is 433 characters,
      well under the 1024 cap.
- [x] `docs/skills.md` and `skill_triggers.json` regenerated from the updated description;
      `build_skill_docs.py --check` and `build_skill_triggers.py --check` both report in sync.

## Security and hygiene

- [x] Diff reviewed: prose only, no secret, address, hostname, or real machine path added.
- [x] Added text is ASCII only (no em/en dashes or curly quotes).
