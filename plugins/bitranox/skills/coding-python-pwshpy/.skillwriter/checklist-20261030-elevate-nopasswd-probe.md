# skill-writer checklist - coding-python-pwshpy (elevate() no-password probe, [280])

- [x] Rule: on POSIX, `elevate()` first runs the relaunch's own interpreter as `<python> -c pass`
      under `sudo -n`; if that passes it relaunches under `sudo -n` with no prompt, and only
      otherwise asks once with `sudo -v` (no terminal: that raises `ElevationDeclinedError`),
      relaunching under `sudo -n` once the credential is cached.
      Where: SKILL.md, the `ElevationDeclinedError` parenthesis in the error-model bullet
      (replaces "asks once with `sudo -v` ... and then runs the command under `sudo -n`").
      Backed by: src/pwshpy/adapters/native/elevation.py (`_PROBE_ARGS = ("-c", "pass")`, the
      probe before `_ask_sudo_for_root`).
- [x] Receipt held (skill_receipt.py start meta-skill-writer before the first edit).
- [x] RED on opus against the pre-edit text: it concluded `sudo -v` runs first, so a no-terminal
      call with a NOPASSWD rule fails and raises - the behaviour [280] removed.
- [x] GREEN round 1, opus and haiku, 3 questions: both quoted the new text. Haiku found the
      sentence "fails and raises this error ..., and then runs the command" self-contradictory;
      opus found the probe's target unclear (does it run the relaunch itself?). Both fixed.
- [x] GREEN round 2, opus and haiku, 4 questions (one added for `timestamp_timeout=0`): every
      answer correct and quoted, no NONE on a question the text settles. The probe argument was
      still unnamed in both gap lists; the text now names `<python> -c pass` (a literal from the
      code, no behaviour claim added, so no third round).
- [x] Tiers haiku and opus, one cell per question per tier per round.
- [x] Skill gaps triaged: 3 closed in the text (sequence of raise vs relaunch, probe target,
      probe argument). Declined: the definition of "no terminal" (sudo decides that, not pwshpy);
      sudoers argument-specific rules (out of scope, sudo semantics); telling "password refused"
      from "no cached credential" apart (one error class by design, the message differs);
      UAC path and exit 77 (documented elsewhere in the skill: the elevation and exit-code
      sections); probe failure for a user not in sudoers (falls through to `sudo -v`, which
      reports it - the existing behaviour).
- [x] Rule 2 (adjacent rot found while verifying rule 1): the runner exit-code list now gives 127
      for a failed uv install or none possible without curl/wget, and, run elevated, for an
      untrusted temporary directory, git configuration file or git (not only an old git).
      Where: SKILL.md, the exit-code paragraph (127 clause). Backed by: pack_runner.sh (1034,
      1043, 1051, 967, 632/637, 1397) and pack_runner.ps1 (839, 1032, 1041, 1091, 2148, 2226-2236).
- [x] RED for rule 2, opus on the old text, 5 cases: NONE on all five (it also read 70 as a rival
      for the install failures). GREEN, haiku on the new text: 127 on all five, each quoted.
      Gaps declined: the meaning of "untrusted" (defined by the runner's own stderr reason, and
      in docs/power-tools.md); the old-git threshold (2.32, stated in CLAUDE.md and power-tools.md).
- [x] Description measured: unchanged (frontmatter not edited).
- [x] ASCII only, present tense, added prose wrapped like the surrounding text, no code span
      split across lines.
- [x] Security scan: prose only; no secrets, hostnames, private paths or PII.
