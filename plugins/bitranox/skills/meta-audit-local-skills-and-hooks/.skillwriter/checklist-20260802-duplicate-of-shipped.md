# skill-writer checklist - meta-audit-local-skills-and-hooks (2026-08-02, duplicate-of-shipped)

Change: a new deterministic check reports every local hook or skill script the marketplace also
ships. It reports the PAIR and a status, never a verdict, because the local side can be the better
one. The deep dream already runs this audit, so the dedup pass lands with no new dream step.

- [x] Receipt held (`skill_receipt.py start meta-skill-writer`, issued this session).
- [x] RED is a MEASUREMENT, not a fixture: the audit reported "0 findings" on this machine while
      eight local toolbox tools duplicated shipped ones and had already drifted. The old duplicate
      check compares skill DESCRIPTIONS at directory level, so `toolbox` vs `compuse-toolbox` never
      matched and file-level duplication was structurally invisible to it.
- [x] Verified against the real pre-retirement state, not only synthetic fixtures: the local toolbox
      was reconstructed from the commit before the retirement into an isolated home, and the check
      reported 7 of the 8 (the 8th was never committed, so it is absent from the archive).
- [x] The load-bearing NEGATIVE verified on real data too: the four retired hook tombstones in
      `~/.claude/hooks` all have a shipped twin by basename and none was flagged. Flagging a
      tombstone would push a reader to delete the thing that makes a stale caller fail loudly.
- [x] The check does NOT tell you to delete. A local copy can be drifted because it is AHEAD (a fix,
      a wider scope), and deduping that by deletion destroys the improvement rather than sharing it.
      IDENTICAL -> retire; DIFFERS -> read the diff, contribute the local delta if it is the better
      one, retire only once it lands. Both verdicts are pinned by their own test.
- [x] WHY a recurring pass rather than retiring at contribute time: with commit rights the local
      copy goes in the same push, but via a PR the twin appears in a later session with nobody
      standing at the contribution. Only a pass that re-asks can close that window.
- [x] Silence that means "could not look" is called out in the body: without `--shipped` the
      duplicate checks have nothing to compare against, and a run that cannot look must not read
      like a run that looked and found nothing.
- [x] No session narrative or private provenance added; no machine paths added to the SKILL.md.
