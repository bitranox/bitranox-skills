# skill-writer checklist - infra-modulejail (2026-08-27, audit bucket G)

Four defects, one of which silently ends the skill's own mandatory discovery loop.

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
- [x] The suffix regex `\.ko(\.[gxz]+)?$` cannot match `.ko.zst`; a character class of g, x and z
      consumes neither s nor t. Confirmed on a realistic file list.
- [x] Neither side normalised hyphens: module FILE names are hyphenated, `lsmod` names are
      underscored, so `comm` mismatched every hyphen-named module and put LOADED modules into the
      block list - exactly what the skill's first invariant exists to prevent.
- [x] `keep.closure` was consumed by `comm` and produced by nothing; `keep.raw` was produced and
      consumed by nothing. The step between them existed only as one prose sentence.
- [x] Step 3 emitted bare `install X /bin/true`. Coreutils `true` cannot write to syslog, so
      `journalctl -t modulejail` is empty forever - and "the list is empty" is the STOP CONDITION
      of the runtime-discovery loop, which therefore terminates on its first pass reporting the
      jail finished.
- [x] The filed headline for that last one was a false positive: the doc never claims "no trace".
      The two passages describe different channels. The real defect is larger and is what is fixed.

## GREEN
- [x] `all.mods` now strips the four real suffixes explicitly, drops anything else `*.ko*` caught,
      and normalises to the underscore form. Verified against a list containing `.ko.zst`,
      `.ko.xz`, `.ko.gz`, `.ko`, a hyphenated name and a `.ko.xz.sig`: the old `sed` left two
      suffixes on, left the hyphens, and passed the `.sig` through as a module name; the new
      pipeline handles all six correctly.
- [x] `resolve` normalises too, and the fixed-point loop that WRITES `keep.closure` is now in the
      skill, with the collation and name-form requirements stated.
- [x] Step 3 emits the logger form; the generated directive was run and exits 0, so the block
      stays silent to the caller while producing the journal line the discovery step reads. The
      discovery step now says how to verify before trusting an empty result.

## Quality
- [x] Present tense; no session narrative, no operator instructions, no scratch paths.
- [x] No address, MAC, hostname or machine path added. Verified:
      `grep -nE '([0-9]{1,3}\.){3}[0-9]{1,3}|/home/|/Users/|/tmp/' SKILL.md`
- [x] The tool references (`modulejail --dry-run`, `modulejail.sh`) named a program the skill never
      said how to obtain, and whose only real implementation lives at private paths that must not
      appear in a marketplace skill. Replaced with the hand-built pipeline as the gate, keeping the
      both-streams caveat for anyone driving it with a generator of their own.
