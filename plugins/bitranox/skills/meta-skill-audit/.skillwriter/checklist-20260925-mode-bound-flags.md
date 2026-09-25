# skill-writer checklist - meta-skill-audit (2026-09-25, room inside the source, mode-bound flags)

Change: the exit-code line of Procedure step 2 adds two exit-2 refusals - a room inside the source,
and a flag the mode would ignore - and states which flags those are: `--kind`, `--skip-existing`
and `--include-vendored` belong to the `--scripts` sweep and are refused without it;
`--hooks-dir` is refused without `--skills-dir`. (The shim sentence above it changed in the same
release under `checklist-20260925-shim-loud-default.md`.)

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: technique, tool-bearing. Test approach: the shared retrieval arm (quote or NONE,
      haiku, inert `bitranox:baseline-probe`, text pasted). Questions here: Q6 (`--kind hook`
      without `--scripts`), Q7 (a room inside the source), control Q9 (a source inside the room).
- [x] Scope: one list item in step 2; frontmatter, `name:` and description untouched.

## RED

- [x] Inherited coverage: the same `redcheck --corpus-cascade` run as the compuse-toolbox checklist
      of this date (STRONG on function words only); route taken: the quote-back text check.
- [x] RED, pre-change text: Q6 and Q7 answered NONE. Control Q9 answered exit 2 with the quote.

## GREEN

- [x] Q7 exit 2 and Q9 exit 2, each with a direct quote. Q6 exit 2 with a quote, but GREEN reported
      a gap: `--kind` reads as a valid flag elsewhere, so "a flag the mode would ignore (`--kind`,
      ... without `--scripts`)" read two ways.
- [x] REFACTOR: the sentence now says the three flags belong to the `--scripts` sweep and are each
      refused without it. Re-tested Q6 alone by quote-back (haiku): exit 2, quoting "`--kind`,
      `--skip-existing` and `--include-vendored` belong to the `--scripts` sweep, so each is
      refused without `--scripts`". Its remaining gap (the exact error text) is declined: the
      refusal message names the flag and `--help` lists the modes.
- [x] Diffed against RED in both directions: Q9 still right with the same quote; nothing lost.

## Quality

- [x] Every claim executed against the real script with a control: `--list --kind hook` without
      `--scripts` exits 2 ("--kind is honoured only with --scripts"), the same with `--scripts`
      exits 0; a `--room` inside the `--plugin` source exits 2 and creates nothing there.
- [x] No address, hostname or machine path added; no bare package-local doc reference.
- [x] Script tests cover each stated case (test_audit_cli, test_audit_reports).
- [x] Security: prose only.
