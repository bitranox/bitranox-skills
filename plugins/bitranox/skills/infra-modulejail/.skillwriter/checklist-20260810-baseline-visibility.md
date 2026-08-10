# skill-writer checklist - infra-modulejail (2026-08-10, patch: KEEP-input durability)

A second, narrow edit on the same day. Scope is deliberately smaller than what was proposed,
because the RED run did not support the larger change.

## The proposed edit was DROPPED - RED passed

Proposed: teach that a module kept only because it was loaded at generation time is covered by
accident. A sealed subagent (sonnet) got the shipped skill and a scenario in which four docker
netfilter modules are unwhitelisted, unblocked and loaded.

It answered all four questions correctly: named the `(currently loaded)` clause as the cause,
ruled the node unsafe against a future regeneration, prescribed adding the four to the whitelist
plus a cold regeneration and re-exercise, and rejected "docker works so coverage is fine",
citing the skill's own zram/zstd section as the mirror image.

So the shipped text already carries this: step 1 states `KEEP = (currently loaded) UNION
(baseline profile) UNION (whitelist)` and the runtime-modules section already refuses
"it works" as evidence.

Baseline contamination was checked before accepting the pass, and one form is present and worth
recording: the SCENARIO supplied the finding. It handed over all three facts (not whitelisted,
not blocked, currently loaded) whose conjunction IS the conclusion, leaving only the mechanism to
name. So the pass shows the skill suffices for a reader ALREADY holding that fact pattern; it
does not show a reader would assemble it unprompted. That is a weaker result than a clean pass,
and it is why the mistakes table gains one row pointing at the audit habit, while the body is not
rewritten around a trap the text already implies.

## What WAS shipped, and the gap that justified it

From the same run's gaps list, unresolvable from the text:

    "'Baseline profile' is named as one of the three KEEP inputs but its contents are never
     described ... I assumed the baseline profile does not already durably cover these four
     modules ... If the baseline profile does cover them, part of my 'not safe' verdict would be
     wrong. Real information gap, not resolvable from the excerpt."

That is a genuine defect: the skill makes coverage depend on the baseline and gives no way to
read it, so a reader cannot separate durable coverage from accidental and cannot check their own
verdict.

Measured on a real node, which also confirms the agent's assumption was correct:

    BASELINE_MINIMAL='ext4 xfs btrfs vfat ... overlay ...'
    BASELINE_CONSERVATIVE="$BASELINE_MINIMAL virtio ... nvme ahci ..."
    ip_tables, iptable_nat, iptable_filter, xt_conntrack : 0 occurrences
    overlay: whitelist AND baseline    xt_addrtype, zfs: whitelist only

Added: a durability table over the three KEEP inputs, the one-line command to read the baseline,
and the measured contrast. Plus one mistakes row.

## Checks

- [x] Iron Law honoured: the change that had no failing test was NOT shipped
- [x] The change that WAS shipped traces to a gap the run could not resolve, verified on a host
- [x] Baseline contamination assessed and recorded rather than glossed
- [x] Every command in the addition executed on a real node, not reviewed
- [x] Frontmatter unchanged, so the trigger map needs no rebuild for this patch
- [x] No addresses, MACs, hostnames or private paths; module and variable names only
- [x] No session narrative or operator provenance
- [x] Security: documentation only, no scripts, no credentials in the diff
- [x] Version bumped PATCH (doc fix inside an existing skill, no new capability)
