# skill-writer checklist - infra-windows-servicing (2026-08-27, audit bucket G)

A false absolute repeated at three sites.

## PLAN
- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference/technique. Every defect here is a FACTUAL claim, so the test is a
      ground-truth check against the real file, the installed package or live tool output, not a
      pressure scenario.
- [x] Scope: correction only. No new capability, no procedure reshaped.

## RED
- [x] Behavioural RED deliberately NOT used: these skills are INSTALLED on this machine, so a probe
      answers from the shipped wording rather than the draft and cannot fail honestly. The route
      taken instead is the one the skill names - a ground-truth check whose result is immune to
      inherited context.
- [x] Once `wmic.exe` is absent there IS an error and a non-zero status: cmd.exe prints `'wmic' is
      not recognized...` and sets ERRORLEVEL 9009; PowerShell raises `CommandNotFoundException`.
      So "returns EMPTY, not an error" is wrong as stated.
- [x] UNVERIFIABLE by execution on this host, and recorded as such rather than guessed: this is
      Linux, no Windows 11 25H2 is in reach, and the one Windows box available is not 25H2 so a
      result from it would prove nothing either way.
- [x] The observation behind the claim is real but mis-attributed: the error goes to STDERR, and
      this skill's whole operating context is driving a Windows guest with output captured to a
      file, so `wmic ... > out.txt` without `2>&1` leaves a genuinely empty file.

## GREEN
- [x] All three sites now say a stdout-only capture sees empty, name the exit code, and tell the
      reader to capture `2>&1` and check the status before parsing. The skill's existing remedy
      (`fsutil fsinfo drives`, `Get-Volume`) was already correct and is kept.

## Quality
- [x] Present tense; no session narrative, no operator instructions, no scratch paths.
- [x] No address, MAC, hostname or machine path added. Verified:
      `grep -nE '([0-9]{1,3}\.){3}[0-9]{1,3}|/home/|/Users/|/tmp/' SKILL.md`

## Follow-up (decision review, same day)
- [x] The replacement claim is itself UNVERIFIABLE on this host, so the passage now says so in
      line and names the single run that would settle it. Chosen over dropping the exit code
      (which makes 'check the exit code' untestable) and over reverting to the original, which
      is plainly false. The marker is deliberate: this file carries many measured facts, and an
      unmarked inherited one would read as measured.
