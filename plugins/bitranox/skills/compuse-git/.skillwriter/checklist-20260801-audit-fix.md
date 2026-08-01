# skill-writer checklist - compuse-git (2026-08-01, isolated-audit fix)

Source: the first clean-room sweep run by `bitranox:meta-skill-audit`. Ships with plugin 5.127.0.

- [x] WRONG: the quick-reference gave git's error for `rev-parse --short` with 2+ revs as
      `fatal: needed a single commit`. Git actually says `fatal: Needed a single revision`. My own
      first check returned German (`Benoetigte einen einzelnen Commit`), which is the more useful
      half of the finding: the message is LOCALIZED, so the skill now says to detect this by exit
      code 128 and never by grepping the text.
- [x] Fixed the same wrong string in the shipped `hooks/git-footgun-guard.py` docstring and user
      message, and in its test's assertion - one bug, three copies, per fix-it-in-every-sibling.
      Guard tests re-run: 20 passed.
- [x] Receipt held (`skill_receipt.py start meta-skill-writer`, this session).
- [x] Every QUOTE checked against the real file; every executable claim re-run rather than trusted.
- [x] No session narrative or private provenance added; no machine paths, addresses or hostnames.
