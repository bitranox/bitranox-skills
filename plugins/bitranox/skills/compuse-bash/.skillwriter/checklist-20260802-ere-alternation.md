# skill-writer checklist - compuse-bash (2026-08-02, alternation under grep -E)

Change: one Quick-reference row for BRE/ERE alternation being inverted, so a backslash-escaped pipe
under `grep -E` searches for a literal pipe and silently matches nothing. Ships with plugin 5.143.0.

- [x] Receipt held (`skill_receipt.py start meta-skill-writer`, issued for this batch).
- [x] From a measured miss, not theory: `grep -iE "a\|b"` was used in this session to check whether
      two facts existed, returned nothing, and the "(no file)" verdict was believed. Both files did
      exist. That is the worst shape for this defect - a search deciding whether something EXISTS.
- [x] Checked the WHOLE catalogue before writing, per the rule captured earlier today, not just the
      nominated target. All 67 SKILL.md scanned: four hits, and READING them showed every one is a
      skill USING `-E` alternation correctly (`'etag|last-modified'`, `'api[_-]?key|secret'`) rather
      than documenting the trap. Control: 26 skills mention grep, so the scan really read files.
- [x] Home chosen by trigger, not topic. `compuse-ssh` owns the BSD-grep trap because that one bites
      over SSH; this one bites locally and its symptom is a wrong RESULT from a shell command, which
      is compuse-bash's stated domain. Placed beside the two existing grep rows (the silent `head`
      cap and the `grep -c` exit-1 idiom), which fail the same way: a confident wrong answer.
- [x] States the INVERSION rather than one half of it, so the reader is not left thinking one form
      is universally right - and names why nothing warns you: the shell keeps the backslash inside
      double quotes, and the exit status is an ordinary "no match".
- [x] The row's own escaping was VERIFIED BY RENDERING, not by eye - a table row about escaped pipes
      that renders its own examples wrong would teach the opposite. Confirmed the source produces
      `a\|b` for BRE, bare `a|b` for ERE, and `grep -iE "a\|b"` for the mistake, after the
      reformat-md-tables hook rewrote the file.
- [x] No session narrative, no private paths, no machine-specific detail in the shipped text.
- [x] Suites green and `repo-gate.py --ci` clean with the CI dependency set.
