# skill-writer checklist - compuse-toolbox (add the `claim_check` jig)

Change: contribute the local toolbox tool `claim_check.py` upstream into this skill, per the
crosstree-deep dream's toolbox CONTRIBUTE pass. Reference-skill edit (a tool index), not a
technique rewrite, so the bar is: the new row must be discoverable from the description, the tool
must ship with its tests, and the "why a jig" section must state the trap it encodes.

## PLAN
- [x] Skill type identified: reference (a tool index with a per-tool rationale section).
- [x] Scope decided: one table row, one rationale bullet, one description clause, the script and
      its tests. No change to any existing tool's row or behaviour.
- [x] Checked it is not already shipped BEFORE proposing: `compuse-toolbox/SKILL.md` named
      procsig, git_state, conflict_scan, ci_triage, jsonl_grep, transcript_tail (6 of the 12 local
      tools); `gate.py` was already named in a shipped SKILL.md; `claim_check` was in none.
      This is the `check-a-queued-contribution-against-every-skill` rule, which found 4 of 9
      already-shipped entries in an earlier queue drain.

## GREEN
- [x] Description stays trigger-first and third person; the new clause names the SYMPTOM ("deciding
      from a grep whether some text is already present in a set of files"), not the tool's design.
- [x] Description does not summarise a workflow.
- [x] Table row follows the established shape: what you would otherwise hand-roll, plus the exact
      `uv run scripts/<tool>.py` invocation.
- [x] Markdown table realigned (the reformat-md-tables hook did it on save).
- [x] Rationale bullet states the TRAP, matching how every other bullet in that section reads: the
      dangerous result of a content check is the NEGATIVE, so a control pattern that must match
      turns a silent false all-clear into a loud BROKEN verdict.
- [x] Exit codes documented in the bullet (0 present / 1 absent / 2 broken), format-independent,
      per the machine-readable-CLI rule.
- [x] Script shipped at `scripts/claim_check.py` alongside its siblings, PEP 723 header intact.
- [x] Usage lines inside the script repointed from `tools/` to `scripts/` for its new home.
- [x] Tests shipped at `tests/test_claim_check.py`; the copied harness pointed at `parents[1] /
      "tools"`, which is the personal toolbox layout, and was repointed to `scripts/`. Caught by
      running them, not by reading them: 3 of 48 failed on a JSONDecodeError from an empty stdout.
- [x] Full skill suite green: 48 passed under CI's dependency set.

## REFACTOR
- [x] No duplication introduced: the tool is now shipped here AND still present in the personal
      `~/.claude/skills/toolbox`. That is the intended end state for a contributed tool (the local
      toolbox is the workshop), and the local copy is the one the local nudge hook resolves.
- [x] No existing row, bullet or behaviour changed.

## Deliverables
- [x] `scripts/claim_check.py`, `tests/test_claim_check.py`, SKILL.md row + bullet + description.
- [x] `plugin.json` version bumped so installs see the change.
- [x] `skill_triggers.json` and `docs/skills.md` regenerated (the description changed).
