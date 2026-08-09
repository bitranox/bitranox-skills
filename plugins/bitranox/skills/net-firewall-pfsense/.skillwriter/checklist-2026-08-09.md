# skill-writer checklist - net-firewall-pfsense - 2026-08-09

Skill type: **technique + reference** (a diagnostic path plus a bundled jig). Tested with
application scenarios and a retrieval scenario, per "Testing All Skill Types".

## PLAN

- [x] Skill type identified: technique/reference, so application and retrieval scenarios rather
      than pressure scenarios.
- [x] Three scenarios drafted before any text was written: a silent cross-subnet outage, adding a
      DNS host override from a script, and SSH output polluted by client diagnostics.
- [x] Scope decided: self-contained SKILL.md plus `scripts/` and `tests/`. No supporting reference
      files, so no routing table is required.

## RED - baseline, no skill present

Three isolated agents with no filesystem access, so nothing could be read out of the repo.

- [x] **Silent cross-subnet outage: FAILED.** Asked why five of six DHCP-reserved devices reach
      the LAN but nothing beyond it with no log line, the baseline answered "a firewall or
      floating rule ... built around an alias" and proposed `pfctl -vvsr`, then gateway status,
      then per-reservation BOOTP options. It never reached ARP. This is the gap the skill exists
      to close.
- [x] **DNS host override: PASSED.** The baseline reached `$config['unbound']['hosts']` and
      `write_config()` unaided. It did guess at the `require_once` chain, mutated the `$config`
      global directly rather than through `config_get_path`/`config_set_path`, and flagged that it
      could not tell unbound from dnsmasq.
- [x] **Merged SSH streams: PASSED.** The baseline identified the banner as client stderr and
      wrote "What I would not do: grep the warning lines back out of the combined output ... That
      papers over the actual bug."
- [x] Two passing baselines investigated rather than accepted: neither is contamination (the
      probes have no filesystem access and quoted nothing from the repo), so both traps are
      genuinely weaker than assumed. The skill keeps them as short trap entries and does not build
      the body around them; the value there is the jig applying them automatically, not the advice.

## GREEN - same scenarios with the skill

- [x] **Silent cross-subnet outage: now correct.** The agent opened with "A DHCP reservation with
      the 'Static ARP Entry' box ticked", explained the layer-2 mechanism, and reached for
      `doctor`, then `dhcp list` and `arp --permanent` to confirm, and `dhcp rm-static-arp` to fix.
- [x] **Retrieval from the skill index: correct.** Given ten skill descriptions including three
      plausible neighbours (`files-edit-xml`, which names pfSense config.xml; `compuse-ssh`;
      `process-debug-systematic`) and with NONE stated as acceptable, the agent selected
      `net-firewall-pfsense` and declined to stack the generic debugging skill on top.
- [x] Every dispatch asked for a `Skill gaps` section and each reply's list is recorded below.

## REFACTOR - gaps reported by GREEN

- [x] **Closed:** the mechanism was documented only for multi-interface devices, so applying it to
      a replaced NIC or a firmware-changed MAC was an inference beyond the text. The section now
      states the general rule (one MAC pinned permanently, broken whenever that is not the MAC
      currently using the address) and lists the triggers as examples.
- [x] **Closed:** the failure is now stated as occurring at layer 2 before rule evaluation, which
      is why nothing logs.
- [x] **Declined:** "no walkthrough for diagnosing several affected devices at once". `doctor`
      reads the whole configuration in one pass and reports every reservation; a batch procedure
      would describe what the verb already does.
- [x] **Declined:** "no `--fw` alias, host or key given, so the invocation stays a placeholder".
      Correct and intended - the skill ships with no host names and no default target.
- [x] Quote-back verified: re-asked what to check first, the answer quotes the diagnose table's
      first row rather than paraphrasing it.
- [x] GREEN diffed against RED in both directions. Nothing the baseline produced is missing: the
      baseline's rule/alias/gateway path was wrong for this symptom, and `rules --counters` still
      exposes `pfctl -vvsr` for the cases where it is right.

## Quality

- [x] Name follows the registry: `net` is a taxonomy category whose description reads
      "Networking: DNS, routing, proxies, firewall, VPN" and seeds a `firewall` sub.
- [x] Frontmatter carries only `name` and `description`; description is trigger-first and yields
      well over three distinctive keywords (pfSense, "ARP Table Static Entry", snort2c, pfctl,
      unbound, config.xml, DHCP reservations).
- [x] Description states triggering conditions only and does not summarise the workflow.
- [x] Flags are not frozen into the body; it directs the reader to `pfsense.py --help` and
      `pfsense.py <verb> --help`.
- [x] No narrative, no operator instructions, no scratch paths, no before-and-after commentary.
- [x] Every address, MAC and path is a reserved documentation value.
      `grep -nE '([0-9]{1,3}\.){3}[0-9]{1,3}|([0-9a-f]{2}:){5}[0-9a-f]{2}|/home/|/Users/|/tmp/'`
      returns only `192.0.2.x` and `/path/to/key`.
- [x] No external doc reference that an install cannot reach; the body is self-sufficient.

## Scripts and tests

- [x] `scripts/pfsense.py` is stdlib-only and imports no sibling script, so it works from an
      install with nothing provisioned.
- [x] `tests/test_pfsense.py` covers every main function: 62 tests, all passing.
- [x] Mutation-tested rather than merely green. Six single-line mutations were applied to the
      source in a scratch copy and each turned its guarding test red: merging stderr into stdout,
      ignoring `--apply`, downgrading a shared address to a warning, dropping the PHP escaping,
      taking the first of an ambiguous match, and skipping the pre-change snapshot.
- [x] Verified against live hardware, not only fixtures: every read-only verb was run against a
      real pfSense 2.8.1 box and compared with what the box reports directly, and one host
      override was added and removed end to end, confirmed by resolving it before and after.
- [x] `doctor` proven able to both pass and fail, against two real saved configurations: one with
      no armed static-ARP entry exits 0, one with two exits 1 and names both.

## Security

- [x] Generated PHP escapes every interpolated value as a single-quoted literal; a round-trip test
      decodes it the way PHP does, and a control asserts the unescaped form really does break out.
- [x] XML parsing refuses a `DOCTYPE` or `ENTITY` declaration before parsing, which closes entity
      expansion without a non-stdlib dependency.
- [x] Mutations are dry runs until `--apply`, snapshot first, and abort if the snapshot fails.
- [x] There is no default target, so a mutating command names the firewall it acts on.
- [x] `BatchMode=yes` is forced when the caller omits it, so a rejected key fails instead of
      prompting for a password.
- [x] Diff reviewed for secrets, private hostnames, internal addresses and paths: none present.
