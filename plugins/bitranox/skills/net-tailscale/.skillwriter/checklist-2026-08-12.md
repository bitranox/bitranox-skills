# skill-writer checklist - net-tailscale - 2026-08-12

Skill type: **technique + reference** (a diagnostic mechanism plus a resolver-config trap).
Tested with one application scenario per "Testing All Skill Types", proportionate to a single
new section added to an existing skill.

## PLAN

- [x] Skill type identified: technique/reference addition to an existing skill; one application
      scenario is proportionate (not a pressure-scenario battery).
- [x] Absence confirmed before writing: `claim_check.py --pattern 'MagicDNS|100\.100\.100\.100'
      --control 'tailscale'` against the pre-change file returned ABSENT (control matched 33
      times, so the file was read).
- [x] Scope decided: one new section ("DNS: MagicDNS on quad-100 is platform-asymmetric"), a
      frontmatter description addition, a "When to use / not" bullet, and two Common-mistakes
      rows. No new supporting files.

## RED - baseline, pre-change text

One isolated agent, given the full pre-change SKILL.md text (no DNS section) plus a diagnostic
scenario: an identical unbound forward-zone pointing at `100.100.100.100` works on Linux nodes
and returns SERVFAIL on a pfSense node in the same tailnet, with `tailscale ping` still working.

- [x] **FAILED.** The baseline reasoned from general pfSense knowledge instead of a stated
      mechanism (the document had none): it proposed a `pf` bogon-block theory (`100.100.100.100`
      sitting in the CGNAT range pfSense's default "Block bogon networks" is plausible to catch)
      as the root cause. This is a plausible-sounding, wrong diagnosis - the real mechanism is
      that `tailscaled` never serves quad-100 on FreeBSD at all, not that pfSense's firewall is
      blocking it.
      It did correctly avoid recommending `accept-dns=true`, but for the wrong reason ("it
      wouldn't fix a firewall-level drop") - it had no way to know the real trap (`pkg` breakage).
- [x] Its own "Skill gaps" section named the gap directly: "the doc never mentions FreeBSD,
      pfSense, `pf`, or bogon filtering... nothing warns that porting an 'identical' resolver
      config to a non-Linux node can hit a completely different failure mode."
- [x] Result investigated rather than accepted as a clean pass/fail: the RED agent had no
      filesystem access (isolated probe), so its wrong answer is a genuine capability gap in the
      pre-change text, not contamination from elsewhere.

## GREEN - same scenario, new text

- [x] **Correct.** Given the new section, the agent named the platform asymmetry directly:
      `tailscaled` on FreeBSD "does not serve quad-100 at all," confirmed via `tailscale status`
      reporting "Tailscale DNS: disabled" and a direct query to quad-100 timing out with no
      listening socket - matching the document's own confirmation steps.
- [x] Quote-back verified: the agent's SERVFAIL/NXDOMAIN reasoning is a direct quote of the
      governing text ("SERVFAIL means the zone is configured but its target is dead ... NXDOMAIN
      means the name genuinely does not exist"), not a paraphrase.
- [x] Correctly declined `accept-dns=true` for the RIGHT reason this time, quoting the `pkg`/
      `resolv.conf` consequence verbatim rather than reasoning around it.
- [x] `Skill gaps` requested and reported: the agent noted the document hands off the pfSense-side
      *fix* to `bitranox:net-firewall-pfsense` without restating it, and declined to guess at
      remediation beyond "not `accept-dns=true`" - this is the intended scope boundary, not a gap
      in this skill (see REFACTOR).

## REFACTOR - gaps reported by GREEN

- [x] **Declined:** "no restatement of the pfSense-side fix (what `doctor` does about a rewritten
      `resolv.conf`)." Intentional - that fix belongs to `bitranox:net-firewall-pfsense`, which
      already documents it (`pkg` fails to resolve -> `doctor`); restating it here would drift out
      of sync with that skill's own text. The cross-reference is deliberate, not a gap.
- [x] **Declined:** "no FreeBSD-side alternative to forwarding at quad-100." Out of scope for this
      incident's facts (mechanism plus diagnostic tell); a prescribed alternative was not part of
      what was verified and would be unverified advice.
- [x] GREEN diffed against RED in both directions: GREEN gained the correct root cause and lost
      nothing RED produced - RED's defensive pf-bogon advice was built on the wrong premise, so
      dropping it is not a loss.

## Quality

- [x] Frontmatter still carries only `name` and `description`; description extended with the new
      trigger clause (MagicDNS/quad-100 SERVFAIL/timeout on FreeBSD/pfSense) and stays
      third-person, triggers-only, no workflow summary.
- [x] New section placed where a reader debugging name resolution meets it - after the daemon/boot
      sections, before Common mistakes.
- [x] No narrative, no operator instructions, no scratch paths, no before/after commentary in the
      section text.
- [x] Every address is a reserved documentation value: `100.100.100.100` is Tailscale's own fixed
      service address (not a private/internal IP); `internal.example` sits under the RFC 2606
      reserved `.example` TLD. `grep -nE '([0-9]{1,3}\.){3}[0-9]{1,3}|([0-9a-f]{2}:){5}[0-9a-f]{2}|
      /home/|/Users/|/tmp/' SKILL.md` returns only `100.100.100.100` occurrences.
- [x] Cross-reference to `bitranox:net-firewall-pfsense` added in both the "When to use / not"
      preamble and the DNS section itself, matching the skill's existing cross-reference pattern.
- [x] ASCII only; passed the tell-sweep hook on edit with no findings.

## Security

- [x] Diff reviewed for secrets, private hostnames, internal addresses and paths: none present -
      every value is either Tailscale's own documented quad-100 address or an RFC-reserved
      placeholder.
