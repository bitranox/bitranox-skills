# skill-writer checklist - net-tailscale (new skill, 2026-08-10)

New guidance/reference skill: running Tailscale on Linux and in unprivileged LXC, and the
clone-identity, device-access, and boot-ordering gotchas that bite.

## PLAN
- [x] Skill type: technique/reference - test is an application scenario.
- [x] Scenario drafted before writing: bring a CLONED unprivileged LXC (that inherited a
      Tailscale identity) onto the tailnet as its own node without disturbing the original.
- [x] Scope: self-contained SKILL.md, no bundled script - matches every existing infra/net
      skill; the watchdog is described and delegated to coding-resilience, not shipped here.

## RED - baseline WITHOUT the skill
- [x] Baseline dispatched with the skill NOT supplied, on two tiers (a capable model and a
      weak literal model).
- [x] VERDICT: the weak-literal baseline FAILED - it wiped the Tailscale state but MISSED
      machine-id regeneration and MAC regeneration (the real clone-collision vectors) and the
      "never bake Tailscale into a clone base" root cause; AppArmor handling was thin.
- [x] The capable-model baseline was strong but quoted injected environment context, so it is
      recorded as a contaminated baseline, not a clean pass.

## GREEN
- [x] Text addresses each failure: wipe tailscaled.state before first start; regenerate
      machine-id and MAC in the same pass; the upstream fix (do not bake Tailscale into a
      cloned template); the /dev/net/tun grant and AppArmor unconfined for unprivileged LXC;
      the network-online ordering (issue 12021); a dead-poll watchdog; auth key from a file.
- [x] Re-tested WITH the full skill on the weak-literal tier that failed baseline: it now
      resets machine-id and MAC, handles the device and AppArmor, orders after the network,
      and explains the hijack. Every baseline failure flipped.
- [x] Frontmatter trigger-first; description states triggers, does not summarize workflow.
- [x] No @ links; cross-references name skills.
- [x] ASCII only, no em-dashes or typographic tells.

## REFACTOR
- [x] GREEN gaps triaged. Genuine gap closed: the GREEN agent downgraded the MAC reset to
      "optional" for containers, so the text now states it is REQUIRED when the clone and
      source share a bridge / L2 (the usual case) and only skippable on separate networks.
- [x] Second fix: the AppArmor step now says to add the `unconfined` line to the clone's
      `.conf` when the source has it, not only to diff.
- [x] Gap declined with reason: the machine-id command was reported "unnamed" but the shipped
      code block names `systemd-machine-id-setup` and `dbus-uuidgen --ensure`; the watchdog's
      exact JSON field is deliberately delegated to `tailscale ... --help` + coding-resilience
      rather than frozen here.
- [x] GREEN diffed against RED both directions; no valuable baseline result lost (the
      userspace-tun fallback is retained).
- [x] Fixes verified by quote-back against the shipped text.

## Quality
- [x] Present tense; no session narrative or private provenance.
- [x] Every value is reserved-documentation or generic - RFC 7042 MAC range, node-example
      hostname, /path/to placeholders. No real host/IP/MAC/tailnet identity. Verified.
- [x] Common-mistakes table.
- [x] Token budget: reference skill; body kept a lean procedure.
- [x] External references are install-reachable: `tailscale up --help` for flags, the Tailscale
      issue number as context, no bare package-local doc path.

## Deployment
- [x] Security review of the diff: no secrets, credentials, private hostnames, IPs, internal
      paths, or PII - no real tailnet identity, no auth key.
- [x] Category prefix `net-` is a registry key; name is descriptive.
- [x] Derived artifacts regenerated (skill_triggers.json, docs/skills.md) and README count
      bumped.
- [x] Plugin version bumped (MINOR) in the same change.
- [x] repo-gate.py --ci green with CI's dependency set.
- [x] Additive commit to master; history append-only, no force-push.
