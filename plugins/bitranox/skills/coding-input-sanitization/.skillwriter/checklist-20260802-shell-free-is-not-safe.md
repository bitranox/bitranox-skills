# skill-writer checklist - coding-input-sanitization (2026-08-02, shell-free is not validated)

Change: a Common Mistakes entry for "it takes an argv, so there is no shell to inject into", using
the `chpasswd` line-oriented stdin injection. Ships with plugin 5.139.0.

- [x] Receipt held (`skill_receipt.py start meta-skill-writer`, issued for this batch).
- [x] Attacks the RATIONALIZATION, not just the API. The wrong belief is "no shell means no
      injection"; the entry names that belief in the reader's own words and then breaks it, which is
      what makes it fire at the moment it is needed.
- [x] Concrete and checkable: `chpasswd` reads `user:password` one entry PER LINE, so a newline in a
      password smuggles a SECOND entry and, run as root, sets root's password - with no shell
      anywhere. Plus the neighbouring case, a name starting with `-` parsed as an option by
      `useradd`/`gpasswd`.
- [x] Ends by mapping back to this skill's own model rather than standing apart: the sink here is a
      line-oriented parser, so it gets escaped/validated like any other sink. That keeps the file's
      single organising idea intact instead of adding an exception to it.
- [x] Placed in `## Common mistakes` beside the other belief-shaped entries ("I validated the input,
      so output is safe"), matching their voice and length.
- [x] Verified ABSENT before writing and PRESENT after with control-gated `claim_check`.
- [x] No exploit recipe beyond what the fix requires, no session narrative, no private paths.
- [x] Suites green and `repo-gate.py --ci` clean with the CI dependency set.
