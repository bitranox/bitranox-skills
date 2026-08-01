# skill-writer checklist - web-frontend-responsive-ux (2026-08-01, isolated-audit fix)

Source: the clean-room sweep run by `bitranox:meta-skill-audit`. These five skills reported after
four batches had already shipped, so their findings were triaged last. Ships with plugin 5.131.0.

- [x] WRONG: `references/touch-and-gestures.md` called `setPointerCapture` on `pointerdown` - the
      exact thing SKILL.md forbids two files away ("Do NOT `setPointerCapture` on pointerdown - it
      redirects the subsequent `click` to the rail and silently kills the thumbnail link's
      navigation"). The example is what a reader copies, so it shipped the defect the rule exists
      to prevent. Capture now happens once movement passes the threshold, which is what the rule
      prescribes.
- [x] WRONG: the scope table handed Core Web Vitals and the Lighthouse workflow to
      `web-frontend-pagespeed`, which states in its own opening that those topics are NOT YET
      WRITTEN. The row now names it as the right owner without promising coverage it disclaims.
- [x] UNEXECUTABLE: a command's comment promised "point axe at an offline mirror" while the command
      passed no such flag. The script does have `--axe-url` (its help even says "point to a local
      mirror for offline"), so the example now uses it.
- [x] DANGLING x6: six scope-table handoffs name skills that do not ship. Marked "(PLANNED, not yet
      shipped)" rather than deleted - the rows carry roadmap intent, and two of the six
      (`sec-privacy-web-gdpr`, `web-frontend-a11y-audit`) are explicitly reserved names under the
      standing 2026-07-05 decision. Marking keeps the roadmap while stopping a reader hunting for
      an uninstallable skill. NOTE the inconsistency this creates: the identical rows in
      `sec-appsec-web-baseline` were left untouched earlier under that same decision, so the two
      skills now treat reserved names differently. Surfaced for a decision rather than resolved
      unilaterally.
- [x] Receipt held (`skill_receipt.py start meta-skill-writer`, re-issued this session).
- [x] Every claim re-measured against the real tool or file rather than taken from the report.
- [x] No session narrative or private provenance added; no machine paths added.
