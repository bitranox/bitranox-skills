# skill-writer checklist - process-review-verification-before-completion (2026-08-27, read back from the same layer)

Change: one row in the Common Failures table plus one short section. Reading a value back proves
nothing unless the read is served by the SAME layer the write targeted. Ships with plugin 5.258.0.

Source: a contribution queued by an earlier dream at `rnprivat/machines/proxmox/kpx01`, delivered
now as part of the softdev tree dream's batch.

## PLAN

- [x] Skill type: discipline (an iron law plus tables of claim -> what actually proves it). The
      change adds a claim shape the tables did not carry: "the write landed".
- [x] Home chosen by trigger: the skill already owns "is my claim true, and what evidence settles
      it". This is that question applied to the INSTRUMENT rather than the claim, so it belongs in
      the same skill rather than in a shell or git skill - the pairs span git, config, systemd and
      device settings, and no one of those owns it.
- [x] Scope: one table row and one short section with its own small table. No new file.

## RED

- [x] Coverage checked against the CURRENT shipped content first: a grep for `same layer`,
      `backing store`, `stored .* runtime` and `read it back` over the skill returned 0 hits. The
      existing table covers tests, linters, builds, bugs, agents and requirements - every row is
      about the CLAIM, none about the read being served by the wrong layer.
- [x] NO behavioural baseline was dispatched this session. Stated plainly rather than implied: this
      shipped on the maintainer's instruction to drain the queue. The queue entry records that the
      defect produced a wrong verification step in shipped documentation and sent readers to the
      wrong escalation.
- [x] The failure is asymmetric in a way worth stating, and the text says so: before a reload a
      successful write reads as failed; after one, a write that never persisted reads as applied.

## GREEN

- [x] The section names the pairs concretely (git index vs working tree, config file vs running
      process, unit file vs loaded unit, a device's stored vs running settings) so a reader can
      recognise the shape rather than only agree with the principle.
- [x] It gives the resolution, not just the warning: name BOTH layers, say which one you just read,
      and where the stored layer has no read path of its own, force the transition and verify after
      it.
- [x] Private specifics from the queue entry were SCRUBBED - the originating instance named a
      specific device and its vendor commands. The shipped text carries only generic pairs.
- [x] ASCII only, no em-dashes or typographic tells.

## REFACTOR

- [x] Frontmatter/description unchanged.
- [x] No session narrative, no machine paths, no hostnames.
- [x] Full hook suite green after the change: 2015 passed, 1 skipped.
