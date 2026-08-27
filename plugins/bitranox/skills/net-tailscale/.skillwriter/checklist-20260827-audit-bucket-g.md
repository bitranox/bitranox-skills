# skill-writer checklist - net-tailscale (2026-08-27, audit bucket G)

Three defects: a flag that does not exist, a diagnostic that cannot diagnose, and a miscited issue.

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
- [x] `tailscale up --help` on the installed 1.98.3 lists 28 flags and none is `--tun`. Userspace
      networking is a `tailscaled` DAEMON flag and the value is `userspace-networking`, not
      `userspace`, per `tailscaled --help` and the vendor's own documentation. Both halves wrong.
- [x] `tailscale status` emits the `Tailscale DNS` line zero times; `tailscale dns status` emits
      it. But renaming the subcommand alone makes the passage WORSE: upstream drives that line
      solely from the `accept-dns` pref, with no platform term in the conditional. Measured on
      this Linux host: the line reads `disabled` AND quad-100 resolves in 11 ms. It cannot
      distinguish the platforms, and this skill tells the reader to run pfSense with
      `accept-dns=false` anyway.
- [x] Issue 12021 is a control long-poll failure that never reconnects, not a boot race. Its body
      and all 13 comments contain no mention of boot ordering; the 25 apparent `boot` hits are all
      `bootstrapDNS` log tokens.

## GREEN
- [x] The userspace passage now names the daemon flag and the correct value. The DNS passage drops
      the false tell, tells the reader to test quad-100 directly, and explains why the status line
      is not the tell. The issue citation moved to the watchdog paragraph it actually supports.
- [x] The FreeBSD/pfSense premise itself is UNVERIFIED and the text no longer asserts it flatly -
      it says to verify on the node. The two live pfSense nodes in this tailnet were deliberately
      not touched.

## Quality
- [x] Present tense; no session narrative, no operator instructions, no scratch paths.
- [x] No address, MAC, hostname or machine path added. Verified:
      `grep -nE '([0-9]{1,3}\.){3}[0-9]{1,3}|/home/|/Users/|/tmp/' SKILL.md`
