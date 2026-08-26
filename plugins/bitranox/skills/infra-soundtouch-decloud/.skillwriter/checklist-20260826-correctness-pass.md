# skill-writer checklist - infra-soundtouch-decloud (correctness pass)

A correctness pass over a shipped skill, not a new one. Every domain claim is checked against the
AfterTouch source at commit `719cc446e632852bb9df9a884e3ee1571d6f9bdb`, and the preset behaviour is
re-measured on hardware. The USB route is removed; the diagnostic port and SSH cover everything.
Scripts and their tests grow to match.

## PLAN

- [x] Change type: factual correction plus one new subcommand. The failure mode under test is a
      FALSE STATEMENT, so the primary instrument is verification against ground truth, with
      application scenarios for the one piece of new behaviour.
- [x] Scope unchanged: SKILL.md as an index, five reference files, `scripts/` and `tests/`.
- [x] Two ground-truth sources chosen up front: the upstream repository at a pinned commit, and the
      live installation, because upstream text and local measurement can each be right where the
      other is not.

## RED

The behavioural RED for the new `enable-ssh` precondition DID NOT RUN CLEANLY, and that is recorded
rather than worked around.

- [x] The inert probe bounds tools, not context, and it retains the `Skill` tool. The previous
      version of this skill is installed on the machine, so the baseline arm invoked it and answered
      from the OLD text instead of from no text. That is contamination, and the arm is void as a
      baseline.
- [x] What the void arm still proves, because it quoted the installed text verbatim: the removed
      stereo-pair claim was actively steering agents. It reported "rooting is explicitly flagged as
      one of the two things that need confirmation before touching the device because it can brick
      it" and "phase 1 requires asking 'is this speaker part of a stereo pair' before any change".
      Upstream restores stereo pairing and reports no bricking, so that guidance was wrong AND
      reaching readers.
- [x] Route taken instead, per the rule for an inherited lesson: the evidence for every corrected
      claim is a check against ground truth, which no inherited context can fake.
- [x] Each removed or corrected claim has a named contradicting source. Alexa is on the shutdown's
      dead list, not the surviving one. `26.x` appears zero times upstream against 13 for `27.x`,
      and `remote_services on` was removed in 7.x. Upstream's own compose has `network_mode: host`
      commented out and marked Linux only. The USB route requires a power cycle. The account id is
      validated as a path-safe identifier, not as seven digits. The failure threshold upstream is 90
      seconds, above the 80 the skill used to give.
- [x] A search control accompanies each absence claim: `brick` returns 4 unrelated files where
      `preset` returns 72, so the corpus search itself works.

## RED, the mechanical arm, which did run

- [x] The CLI contract tests fail against the pre-change text: breaking one documented flag in a
      reference file turns the reference-invocation test red, and restoring it turns it green.
- [x] The table-rendering check answers both ways before it is believed. Its control pair renders a
      clean row clean and a pipe-inside-a-code-span row broken. Two earlier versions of that check
      were discarded because their controls could not distinguish the two cases.

## GREEN

- [x] Application scenario, the factory-reset speaker, run against the revised text. The agent
      identified the unpaired state as the special case, read `margeAccountUUID` first, paired an
      account, re-checked it, and only then opened SSH, then ran the migration and the persistence
      step. That is the behaviour the new precondition exists to produce.
- [x] Every dispatch asked for a `Skill gaps` section, and both replies produced one.
- [x] Live verification, which no scenario can substitute for: two wired speakers rebooted with the
      restore timer stopped, sampled at 10s and at 2s. Presets returned at six and stayed; no sample
      showed zero; the service's account document stayed byte-identical at 55985 bytes across both
      runs. Measured on service 0.129.0.

## REFACTOR

Six gaps reported. Four closed, two declined.

- [x] CLOSED: `<deviceId>` appeared in three URLs with no stated source. Now says it is the Ethernet
      MAC in upper case and gives two commands that read it.
- [x] CLOSED: how pairing reaches a speaker that is not yet pointed at the service was never stated,
      and the reply flagged it as the first thing to question if pairing appears to do nothing. The
      service resolves the device id to an address and talks to the speaker directly, HTTP first
      then telnet, so the speaker must be known and reachable but need not be migrated yet.
- [x] CLOSED: `migrate --confirm` was named but never shown as a command, so its flag shape had to
      be inferred from a neighbouring example. Now shown in full.
- [x] CLOSED: `--full-config` likewise appeared only as a bare flag name. Now shown in full.
- [x] DECLINED: no SSH login credentials in the persistence section. The file has a "Logging in"
      section giving the host-key options and stating root with no password; the gap is an artifact
      of the excerpt the scenario was given, not of the file.
- [x] DECLINED: no absolute path for the scripts. `scripts/<name>.py` relative to the skill is the
      convention across this marketplace, and hard-coding an install path would be wrong on any
      machine that installs it elsewhere.
- [x] GREEN diffed against RED in both directions. Nothing the void baseline produced is missing
      from GREEN; the baseline produced no commands at all, having no file access.
- [x] A gap the fix itself opened, found by re-running: the new example carries a trailing shell
      comment, which the invocation matcher fed to the parser as arguments. Fixed in the matcher
      rather than the prose, since a trailing comment is legitimate, and the matcher is re-proved to
      still reject a genuinely bad flag.

## Quality checks

- [x] No session narrative, operator instruction or scratch path in the skill or this artifact.
- [x] Every address is a reserved documentation range, and the example device id is now 12 hex
      digits so it can be the MAC the text says it is. No real MAC, account, hostname or path.
      Verified: `grep -rnE '([0-9]{1,3}\.){3}[0-9]{1,3}|/home/|/Users/' .`
- [x] Frontmatter measured, not eyeballed: description is 411 characters, under the cap.
- [x] Tables render correctly under the renderer GitHub uses, controls passing both ways.
- [x] Scripts ship tests and they pass: 95, up from 69. The new file tests the CLI surface by
      calling `main()` and by parsing every documented invocation with the real parser, which is
      what made the broken documented commands visible at all.
- [x] Repo gate green.
