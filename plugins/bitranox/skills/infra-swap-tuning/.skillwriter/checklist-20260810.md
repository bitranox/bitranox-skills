# skill-writer checklist - infra-swap-tuning (2026-08-10, new skill)

New skill under the existing `infra` top-level category (hypervisors, virtualization, storage;
`infra` is in skill-taxonomy.json, and bare `infra-<name>` matches the existing members).

## RED - unaided baseline

A sealed subagent (sonnet) got a hypervisor scenario with no skill: 62 GB host, ZFS root, ARC
capped 8 GB, swap on a 16 GB zvol at 0 bytes used, swappiness 10, several 16 GB Windows guests,
and a 55-minute freeze in which ping and cluster membership survived while sshd never completed a
banner and every container userland was stuck.

It got the MECHANISM right unaided - zvol-swap reclaim reentrancy, zram at priority 100, keep the
zvol as a backstop, PSI as the instrument. So a skill that only restated the mechanism would earn
nothing. What it could not do was choose the numbers:

- Set `swappiness = 30` from argument alone, and justified it with "once zram is in place,
  swapping is cheap (RAM-to-RAM, compressed, no disk I/O)" - the general-server assumption this
  skill exists to disprove for hypervisors.
- Sized zram at 8 GB by reasoning. Its own gaps section: "The zram-size (8 GB) and
  min_free_kbytes (640 MB) numbers are reasoned defaults ... not values validated against this
  specific host's actual page churn".
- Asked directly HOW it would measure whether its swappiness choice was right, it proposed PSI,
  `vmstat si/so` and `sar -W` - never compressibility, the input that decides it.

It also wrote "VM guest RAM being swapped is genuinely bad for guest latency" and raised
swappiness anyway, having no number to weigh it against.

Two baseline ideas were folded into the skill: check network-shipped logs first because journald
stalls with everything else, and read PSI cumulative totals separately from the instantaneous
averages.

## Ground truth (measured, and the shipped code block was executed)

The compressibility snippet was extracted verbatim from the shipped SKILL.md and run on a real
hypervisor against a live guest process:

    24 MB  ratio 1.66x  zero pages 29.4%

matching an independent earlier sample (1.67x / 30.4%), so the ~1.16x net figure the skill quotes
is reproducible rather than a single draw. Also measured: several nodes swapping 2-3 GB at
swappiness 10, PSI instantaneous 0.00 with non-zero cumulative totals, and a 32 GB zram device
resizing to 16 GB only once the automation compared configured size instead of liveness.

## GREEN - same scenario, with the skill

The subagent measured before deciding and refused to set a number without it: "Run the script
before finalizing - don't ship a swappiness change on the assumption alone." It added zram on the
zvol rule rather than on the ratio, kept the zvol as capacity, and named both automation traps.
That is the exact behaviour RED failed at.

## GREEN gaps - closed or declined

- [x] CLOSED. "No concrete swappiness number for the keep-it-low case, only LOW" - the decision
      table now gives values (leave at 10; 60-100 only above 2x) and a floor (do not go below 10).
- [x] CLOSED. "No formula for the 1.2x-2.0x middle ground" - that band is now an explicit row.
- [x] CLOSED. Self-contradiction: pressure-driven reclaim "ignores swappiness" while swappiness is
      chosen from the ratio. New subsection separates the two: pressure-driven reclaim ignores it
      (so zram works at any value), swappiness governs ROUTINE proactive swapping (so the ratio
      decides how much of that you want).
- [x] DECLINED. ZFS zvol properties for the swap device (sync, primarycache, volblocksize) - real,
      but a ZFS-tuning topic; this skill decides swap shape, not dataset properties.
- [x] DECLINED. Alerting before zram fills - monitoring design, out of scope. The skill names the
      condition worth watching (`full avg10` above 0) and leaves the alerting stack to the reader.
- [x] DECLINED. Sizing by guest-RAM density rather than a flat percentage - the skill already
      states the cap-not-reservation model and the near-1:1 cost when full, which is the input a
      reader needs; a density formula would be invented, not measured.
- [x] DECLINED. "Script wasn't included in what I received" - it is in the shipped SKILL.md; the
      test prompt carried a summary.

## Both directions

Nothing the baseline produced is missing from GREEN. The baseline's strongest unaided items
(mechanism, priority-100 zram, keep the zvol, PSI) all reappear; the numbers move from reasoned
to measured, which is the whole delta.

## Checks

- [x] Name `infra-swap-tuning`, valid characters, category prefix in skill-taxonomy.json
- [x] Frontmatter: name + description only; trigger-first, under 1024 chars, no workflow summary
- [x] Description yields distinctive keywords (zram, swappiness, ZFS zvol, freeze with kernel
      alive, sshd no banner)
- [x] The one code block was EXECUTED verbatim on a real host, not reviewed
- [x] Self-contained SKILL.md; no supporting files, so no routing table and no shipped scripts
      (hence no `tests/` requirement)
- [x] Token budget: 1323 words, OVER the 500-word technique target, and kept deliberately. The
      body is procedure plus reference (a measurement script, a decision table, a config block, a
      verification set), which is the reference-skill shape the budget rule exempts. Trimming was
      considered and rejected: the parts a reader could skip are the measured numbers, and those
      are the only thing separating this skill from advice the baseline already produces unaided.
      Revisit if it grows further; the split point would be moving the sampling script to its own
      file, which then requires `tests/`.
- [x] Cross-reference to `bitranox:infra-modulejail` by skill name, no `@` link
- [x] No addresses, MACs, hostnames or private paths; device names are generic (`/dev/zram0`)
- [x] No session narrative or operator provenance
- [x] Security: no secrets or credentials; the sampling snippet reads `/proc/<pid>/mem`
      read-only as root on the local host and writes nothing
