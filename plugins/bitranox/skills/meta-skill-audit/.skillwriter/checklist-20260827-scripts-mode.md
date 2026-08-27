# skill-writer checklist - meta-skill-audit (2026-08-27, document the script sweep)

Edit: the skill documents `--scripts`, the mode that reviews a plugin's shipped Python and
JavaScript rather than its skills, and the pre-pass that feeds it. The mode shipped in plugin
5.257.0 with no mention in the SKILL.md, so a reader following the Procedure could reach only the
skill sweep.

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. Test approach is a retrieval scenario - can a reader find the mode and
      the judgement calls it needs?
- [x] RED is a coverage check against the skill FILE, not a subagent. The lesson under test is
      "this tool has a second mode", which no cascade or memory entry teaches, but the skill is
      INSTALLED on this machine, so a probe would answer from the shipped text rather than from the
      draft. A text check of the artifact is immune to that.
- [x] RED ran and FAILED: comparing `audit_skills.py --help` against the SKILL.md, 12 real flags
      appeared in `--help` and nowhere in the skill - `--scripts`, `--kind`, `--include-vendored`,
      `--skip-existing`, `--list`, `--reuse-room`, `--model`, `--timeout`, `--only`, `--prefix`,
      `--skills-dir`, `--hooks-dir`.
- [x] The RED is non-vacuous. Run as a set difference it could report the opposite, and the control
      arm - flags the SKILL.md DOES name - returned `--jobs`, `--plugin`, `--room`, proving it read
      the file rather than failing to parse it.
- [x] First instrument was WRONG and is recorded as such: `script_prepass.argparse_flags_vs_docs`
      answers docs -> `--help` (a documented flag the parser rejects) and returned 0 hits. The
      question here is `--help` -> docs. A well-formed check answering the other direction reads as
      a pass.
- [x] GREEN: after the edit the mode-bearing flags resolve - `--scripts`, `--kind`,
      `--include-vendored`, `--skip-existing`, `--list`, `--reuse-room` - and `script_prepass.py`
      is named with its home and launch shim.
- [x] Six flags remain undocumented ON PURPOSE (`--model`, `--timeout`, `--only`, `--prefix`,
      `--skills-dir`, `--hooks-dir`) and "every flag named" is explicitly NOT the success criterion.
      skill-writer's rule is to point a reader at `--help` and keep the body to the judgement
      `--help` cannot give; enumerating a flag list freezes it and it goes stale. The three
      documented choices are the ones with a consequence a reader cannot read off help text.
- [x] Scripts ship with tests and they pass: 127 cases across
      `skills/meta-skill-audit/tests/`, run with CI's dependency set.
- [x] Every code block executed as written, not reviewed.
- [x] Cross-references use skill names with REQUIRED markers; the one script reference states its
      home (`skills/meta-skill-audit/scripts/`) and the `hooks/run-python.sh` launch.
- [x] Description unchanged, so no routing keyword moved and the 1024-char cap is not in play.
- [x] No address, MAC, hostname or machine path added. Verified:
      `grep -nE '([0-9]{1,3}\.){3}[0-9]{1,3}|([0-9a-f]{2}:){5}[0-9a-f]{2}|/home/|/Users/|/tmp/'`
      returns nothing.
- [x] Present tense throughout, no session narrative and no private provenance in the skill or this
      artifact.
- [x] Body stays an index: the new section states the three judgement calls and the facts/leads
      split, and sends the flag list to `--help`.
