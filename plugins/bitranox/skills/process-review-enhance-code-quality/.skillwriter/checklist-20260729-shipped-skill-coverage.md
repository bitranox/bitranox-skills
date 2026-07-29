# skill-writer checklist - process-review-enhance-code-quality (2026-07-29, shipped-skill coverage)

Change: a fourth always-on check - if the repo ships a Claude Code skill, verify by script that it
names every CLI subcommand (from the tool's own `--help`) and every public export (from `__all__`).
Scored under Documentation. Shipped in plugin 5.100.4.

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED, from a real miss rather than a hypothetical: three consecutive review passes over
      ipscout scored Documentation 9/10 while the skill that repo SHIPS named twelve of eighteen
      subcommands and twenty-five of thirty callables. The review looked at README, docs and
      docstrings and never at the artifact the repo publishes for agents to consult. It was caught
      by the user asking, one step before the release.
- [x] The failure is worse than an omission. A usage skill is what an agent consults to decide
      what a tool can do, so what it omits does not get used - and a past-tense claim ("no X
      surface yet") steers an agent away from a feature that now exists. Both have shipped here:
      a skill naming 8 of 30 callables, and one asserting a subsystem did not exist two releases
      after it did. The check names both failure modes so a reviewer recognises them.
- [x] GREEN: the check is mechanical and cannot be satisfied by reading - it compares against
      `--help` output and `__all__`, which is how the real miss was found. A snippet is included so
      a reviewer can run it rather than eyeball it.
- [x] Severity guidance given: MEDIUM for an omission, SEVERE where the skill states something the
      code contradicts, since that actively misleads.
- [x] Scoped so it does not fire on projects that ship no skill, and it does not demand per-flag
      detail - that stays with `--help`, which cannot go stale. Wrong advice here would push
      reviewers toward duplicating flag lists into prose that rots.
- [x] Heading updated from "Three always-on robustness checks" to "Four always-on checks", and the
      scoring note widened to name Documentation alongside Resource Safety and Security.
- [x] Scope: shared/general - applies to any repo shipping a skill, in any language.
- [x] Security scan: prose plus a short snippet, ASCII, no secrets/hosts/paths/PII.
- [x] CSO description: unchanged (body addition, frontmatter untouched).
- [x] Token budget: one bullet plus a snippet added to a process skill that is already a checklist.
