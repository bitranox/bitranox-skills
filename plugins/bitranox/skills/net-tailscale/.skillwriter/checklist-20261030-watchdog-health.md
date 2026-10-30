# skill-writer checklist - net-tailscale (watchdog keyed on the daemon's Health report)

- [x] Change: SKILL.md "Boot ordering and staying up" - the watchdog paragraph now names the
      signal (a `Health` entry containing the coordination-server text, or a timed-out status
      call), states that no LocalAPI endpoint reports the last control contact, reads
      `BackendState` before `Health` and leaves anything but `Running` alone, and keeps a probe
      failure (missing CLI, non-zero exit, unparseable output, missing `jq`) from ever
      restarting the daemon.
- [x] Verified against a working implementation: the rule set matches the decision function of a
      tested watchdog (timeout -> restart; non-zero exit or parse failure -> probe failure;
      BackendState other than Running -> left alone; Health matched by substring, missing key
      as empty). The Health wording is the text tailscaled 1.98 and 1.104 print.
- [x] Receipt held (skill_receipt.py start meta-skill-writer); the edit was made by the agent
      that loaded the skill.
- [x] redcheck --corpus-cascade: hits were ordinary-word overlaps (dead, restart, timer); no named
      document states the lesson. RED run as a text check anyway.
- [x] RED (opus quote-back on the pre-edit file): restart signal PARTIAL ("a recent
      control-plane contact", no field), LocalAPI NONE, probe failure PARTIAL ("restart the unit
      on a stale/failed result", which reads as restarting on a probe failure), Stopped or
      NeedsLogin NONE, timeout meaning PARTIAL.
- [x] GREEN round 1 (opus and haiku, 2 cells): all five questions quoted. Gaps reported: timeout
      vs probe failure read as a conflict (both tiers), precedence of BackendState over Health,
      Health shape. Closed: a timeout is a daemon failure with no JSON to read, a non-zero exit
      is a probe failure, BackendState is read first, Health is an array of strings.
- [x] Round 2 (haiku): all quoted. Gaps closed: refused socket named as a probe failure, match
      stated as substring, missing Health key counts as empty, the fallback rule stated as a
      rule rather than only as the measured case.
- [x] Round 3 (haiku): all five quoted. Gaps closed: the LocalAPI sentence moved to its own
      bullet (it read as an insertion inside the Health bullet); a status output without
      `BackendState` named as a probe failure.
- [x] Round 4 (haiku) on the final text: both touched questions quoted ("its output does not
      parse or has no `BackendState` ... report that and do not restart"; "Do not look for a
      "last control contact" time: no LocalAPI endpoint reports it"). No new undecided gap: the
      probe noted only that it chose the probe-failure bullet for a missing BackendState, which
      that bullet names explicitly.
- [x] Declined: restart rate, backoff figures and interval - owned by bitranox:coding-resilience,
      which the paragraph points at; other BackendStates beyond the two named - covered by
      "anything but Running"; Health wording for other versions - only the measured versions
      are stated, by design.
- [x] Width and fence check over the added lines printed nothing; the paragraph after the edit
      (the coding-resilience pointer) still binds to the watchdog.
- [x] Description measured: unchanged (frontmatter not edited).
- [x] ASCII only, present tense; the latest-release finder found no history line.
- [x] Security scan: prose only; no secrets, hostnames, private paths or PII.
