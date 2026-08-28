# skill-writer checklist - infra-proxmox (2026-08-28, audit bucket A)

Twenty-two verified findings, nearly all of them damage done by the original extraction of the
upstream Proxmox guide rather than by anything an author wrote.

## PLAN
- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. Every finding is a FACTUAL claim about Proxmox or about this skill's
      own structure, so the test is a ground-truth check against the upstream guide, not a
      pressure scenario.
- [x] Ground truth fetched ONCE and reused: the full upstream admin guide, rendered to text, with
      controls confirming it actually contains the terms searched for. Its version is 9.2.4 while
      this skill states 9.1.2; every fact used here was read from that copy and none of them is
      version-sensitive in that range.
- [x] All 22 confirmed to still reproduce before any edit (`claim_check.py`, rc 0 on each).

## RED
- [x] Behavioural RED deliberately NOT used: the skill is INSTALLED on this machine, so a probe
      answers from the shipped wording. The route taken is a ground-truth check against upstream,
      immune to inherited context.
- [x] The headline finding is not a wrong number. `(default = cgroup v1: 1024, cgroup v2: 100)`
      had been shuffled by the extraction into `cgroup v1:` / `100)` / `1024, cgroup v2:` on
      separate lines, which reads as the two values REVERSED. Eight occurrences across seven files.
- [x] Same class, three more sites: `target_size_rati`, `man cpu-models.c` and
      `PVEAPIToken=USER@` each lost the tail of a token at a line wrap, and
      `/etc/pve/local/pveproxy-ssl.key,` was swallowed into the word `pveproxywhich`.
- [x] Two findings are UPSTREAM defects faithfully copied, not extraction damage: the
      `<<INSERT VERSION>>` placeholder appears verbatim in the upstream guide, and so does the
      `--mailto root --mailto admin` example.
- [x] Section 11.3 Container Images was MISSING from the skill entirely. The chapter index mapped
      it to `container-images.md`, which actually held the start of 11.4.

## GREEN
- [x] All eight cpuunits declarations reassembled to the upstream line, per-command ranges
      preserved (1-262144 for qm, 0-500000 for pct). Verified by listing every remaining
      `default = cgroup` line.
- [x] Wrap-truncations repaired against the upstream sentence in each case.
- [x] SKILL.md's troubleshooting row no longer calls 1024 "the default": upstream says the weight
      "defaults to 100 (or 1024 if the host uses legacy cgroup v1)", so the row now names both and
      scales its example, since the weight only means anything relative to the other guests.
- [x] The Docker-in-an-unprivileged-CT contradiction resolved by finding that the two fixes address
      DIFFERENT failure modes - AppArmor probing in SKILL.md, nesting plus nat-chain networking in
      `security-and-os-config.md`. Neither was wrong; each was incomplete. Both now name the other
      half, so either entry point yields the whole fix.
- [x] Section 11.3 restored from upstream into `container-images.md`, and the 11.4 material it had
      been holding moved into `container-settings.md`, which previously began mid-11.4.2. The
      prose, commands and section structure are upstream's; the one abridgement is the
      `pveam available --section system` sample output, kept to three rows because the listing is
      illustrative and its contents change with every template refresh. The file says so at that
      point, so the trim is visible to a reader and to the next audit.
- [x] `locks.md` truncated at the chapter boundary. Verified non-destructive first: all 24 bled
      lines of chapter 12 text are already present in `ch12-sdn/overview-and-installation.md`, so
      nothing is lost; a See also now points there.
- [x] The two orphaned CLI files given back their commands: `pveceph fs destroy <name> [OPTIONS]`
      with its upstream description, and the `qm wait` options moved out of `qmrestore.md` into
      `qm-set-wait.md`, where that command is declared. A duplicated `## See also` heading there
      was removed on the way.
- [x] The truncated HA error-recovery step restored from upstream, including
      `ha-manager set vm:100 --state disabled`, and the HA chapter index no longer claims the
      identical section range for two different files.
- [x] The change-detection table rebuilt as a real table that names the VALUES
      (`legacy`, `data`, `metadata`) beside the labels, because "Default" is a label and not a
      settable value, and the `vzdump` example's argument moved back inside its code fence.
- [x] The `<<INSERT VERSION>>` note now tells the reader to test the STATE rather than the
      version, since upstream never filled the placeholder: if `ls -l /etc/ssh/ssh_known_hosts`
      still shows the symlink, run the unmerge.

## Beyond the filed findings
- [x] The audit reported the corrupted circumflex twice. A sweep of the whole skill found it
      **63 times across 10 files**, every one inside a regex or an escape default where an ASCII
      caret is required. Upstream contains ZERO of that character and 70 ASCII carets, so all of
      them are extraction damage. Fixed skill-wide and verified to zero.
- [x] The same strings carried a second corruption: `[^\x00-\x08\x10-\x1F\x7F]` where upstream has
      `\x0a-\x1F`. That is not cosmetic - it changes which control characters the pattern accepts.
      Twelve occurrences, fixed and verified; upstream has none of the `\x10-` form.
- [x] A truncated `<userid>` regex in `pveum.md` that had swallowed its own description was
      restored from upstream.
- [x] The known-broken appendix G table is repaired. Each of its rows had been split across three
      lines, and a previous bulk repair had removed the `<-` wrap markers that showed where. It is
      now a valid six-column table with upstream's alignment markers, and the header regained the
      "Too" it had lost.

## Deliberately not changed
- [x] The `--mailto root --mailto admin` example was changed to the comma form `--mailto root,admin`
      even though upstream writes it with the flag twice. The finding is an INTERNAL contradiction:
      the same file documents `mailto` as a "Comma-separated list", and the comma form is
      unambiguously valid. The claim that a repeated flag silently drops the first address was NOT
      verified here (it needs a live PVE host), so the fix relies only on the documented type.
- [x] Upstream's own typo "change detecation" is left as it stands; it misleads nobody and matches
      the source.

## Quality
- [x] Present tense; no session narrative, no operator instructions, no scratch paths.
- [x] No address, MAC, hostname or machine path added; the restored upstream examples use
      upstream's own values.
- [x] Frontmatter untouched, so no routing keyword moved and the description cap is unaffected.
- [x] Every table touched re-checked for uniform cell counts, and the formatter re-run to a no-op.
