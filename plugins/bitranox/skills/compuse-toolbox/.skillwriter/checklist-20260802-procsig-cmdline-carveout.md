# skill-writer checklist - compuse-toolbox (2026-08-02, procsig --cmdline carve-out)

Change: the shipped `procsig.py` stops searching a command string a shell was handed, and SKILL.md
states that second guarantee beside the existing self-match one. Ships with plugin 5.138.0.

- [x] Receipt held (`skill_receipt.py start meta-skill-writer`, issued for this change).
- [x] RED first, from the real incident rather than an invented one: a SIBLING shell whose argv
      quotes the needle, and the `timeout 30 ssh host '<cmd>'` forking-wrapper shape. Both failed
      against the shipped code (matched pids 401 and 501), and a third test asserting a plain argv
      still matches passed throughout - so the gap was the carve-out, not the matching itself.
- [x] The classification block was lifted VERBATIM, not reimplemented smaller. Its own comments
      record defects that earlier hand-written attempts shipped: cutting an arbitrary trailing word
      reduced `ssh-agent` to `ssh` and made the whole OpenSSH toolchain unfindable, and testing only
      argv[0] against a shell table let the standard fleet-probe form through to `--kill`. A
      condensed variant would have re-opened them, and my own review of my own matching heuristics
      has a measured record of missing exactly this class.
- [x] Verified faithful by AST rather than by eye or line count: all 22 shared definitions match the
      hardened original; only `main` differs, which is the deliberate generic-subset CLI surface.
      The queue item said not to forward-port the 561-line tool wholesale, and the CLI surface is
      what that meant - the safety logic cannot ship in halves.
- [x] An existing test was CHANGED, and the reason is recorded rather than glossed:
      `test_resolve_targets_excludes_self_and_ancestors` planted `bash -c "pkill openvmm"` as its
      matching ancestor, which the carve-out now skips before `resolve_targets` is consulted. Left
      alone it would have stayed green while exercising nothing. It now uses a plain argv, and the
      shell case became its own test asserting the incident shape never matches at all.
- [x] Documentation follows the code in the same change: the module docstring's behaviour section
      and the `--cmdline` help text were ported too, since both still promised a plain substring
      match. SKILL.md gains the second guarantee plus the one-way bias and the `--exe`/`--comm`
      fallback, so a reader who loses an expected match knows what to do.
- [x] The absence claim is stated honestly. SKILL.md says what is NOT covered (an unclassifiable
      argv is skipped and can never match) rather than implying total coverage, matching the tool's
      own docstring.
- [x] Suites green: 37 in compuse-toolbox, 1390 across hooks plus skills with the CI dependency set,
      `repo-gate.py --ci` clean.
- [x] No session narrative, no private provenance, no machine paths added to the shipped files.
