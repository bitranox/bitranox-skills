# skill-writer checklist - compuse-bash (2026-07-18, two shell-arg / enumeration gotchas)

Change: added two Quick-reference rows - (1) never put backticks or $(...) in self-authored
double-quoted args (git -m, memory --hook/--title): bash command-substitutes them and runs the
word as a command; (2) never head/tail-cap an enumeration grep (silent cap = false "all N sites
updated"); count first with grep -rc, then list uncapped.

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED: without the rows an agent authoring a commit/hook message with a backtick has bash run
      the backticked word (a real `shutdown` was executed this way once), and an agent enumerating
      change-sites with `grep ... | head` reports a false "all sites updated". Both are recurring,
      documented misses (facts no-backticks-in-shell-args, feedback-never-head-cap-an-enumeration-grep).
- [x] GREEN: both rows state the trigger, the failure mechanism, and the safe form (single quotes /
      -F file; grep -rc then uncapped) - directly in the always-scanned Quick-reference table.
- [x] Scope: universal shell mechanics, matches compuse-bash's charter ("read that result truthfully");
      not project-specific.
- [x] Security scan: prose only, no secrets/hosts/paths; the `shutdown` reference is a generic example.
- [x] CSO description: unchanged (body edit only; no new triggers needed - "pipelines" / "output
      looks ambiguous" already cover retrieval).
- [x] Token budget: two table rows; skill stays a compact reference card.
