# Skill-writer checklist: line-break-codepoint trap described as closed (2026-10-05)

Scope: the passage about keeping tell examples in backticks claimed a line-break codepoint
(U+2028, U+2029, U+0085) "is invisible to the detector and still rewritten by the script, because
`str.splitlines()` breaks on exactly those". Verified against `plugins/bitranox/hooks/tell_chars.py`:
both `find_tell_lines` (line 251) and `transform_outside_code` (line 134) now call the module's own
`split_lines()`, whose docstring explicitly names the OLD bug this replaced (the two functions used
to split differently and could disagree about where a line ended) and states it splits "on REAL
line breaks only - never on U+2028, U+2029 or U+0085". The claim was stale: the trap it describes
is closed, not open. Rewrote the passage to describe the current, closed state and why it matters
(both walks now agree), instead of the old open trap.

## Verification

- [x] Claim re-checked against the current code: read `tell_chars.split_lines`'s full docstring
      and both call sites (`find_tell_lines` line 251, `transform_outside_code` line 134).
- [x] This is a factual correction to a claim about tool behaviour, not a new rule or workflow
      step - the surrounding instruction (keep examples in backticks) is unchanged and still
      correct for its own reason (protecting the examples from either walk), so no RED/GREEN
      pressure test applies; there is no new agent decision being taught.
- [x] Frontmatter unaffected (not touched); `description` unchanged.
- [x] Reread the full paragraph after editing to confirm it reads coherently and does not
      contradict the adjacent sentences about backtick protection.

## Security and hygiene

- [x] Diff reviewed: prose only, no secret, address, hostname, or real machine path added.
- [x] Added text is ASCII only (no em/en dashes or curly quotes) - verified by grep for the tell
      character ranges over the diff.
