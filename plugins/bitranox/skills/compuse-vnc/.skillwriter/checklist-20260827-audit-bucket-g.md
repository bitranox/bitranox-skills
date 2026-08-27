# skill-writer checklist - compuse-vnc (2026-08-27, audit bucket G)

The frontmatter description called noVNC a VNC server and put the server on the wrong host.

## PLAN
- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference/technique. Every defect here is a FACTUAL claim, so the test is a
      ground-truth check against the real file, the installed package or live tool output, not a
      pressure scenario.
- [x] Scope: correction only. No new capability, no procedure reshaped.

## RED
- [x] Behavioural RED deliberately NOT used: these skills are INSTALLED on this machine, so a probe
      answers from the shipped wording rather than the draft and cannot fail honestly. The route
      taken instead is the one the skill names - a ground-truth check whose result is immune to
      inherited context.
- [x] noVNC is the browser-based VNC CLIENT the Proxmox web UI serves; it exposes no bare RFB
      socket for `vnc-remote-control` to dial. The skill's own body already attributes the server
      role correctly and says the Proxmox VM console server is ON THE HOST, not on the target.
- [x] A second error sat in the same sentence and was not filed: "nothing is installed on the
      target except its VNC server" mis-locates the server for the very case the parenthetical
      names.

## GREEN
- [x] Sentence rewritten to fix both. Description measured with `len()`: 595 characters, well
      under the 1024 cap.
- [x] The first rewrite introduced a `: ` inside a plain YAML scalar and the commit gate REJECTED
      it as unparseable front matter. Reworded with ` - `; `yaml.safe_load` now parses it.
- [x] `docs/skills.md` regenerated, since it mirrors this description.

## Quality
- [x] Present tense; no session narrative, no operator instructions, no scratch paths.
- [x] No address, MAC, hostname or machine path added. Verified:
      `grep -nE '([0-9]{1,3}\.){3}[0-9]{1,3}|/home/|/Users/|/tmp/' SKILL.md`
- [x] Mirrored skill: the twin under `apps/utils/vnc_remote_control` carries the identical change
      and its own `plugin.json` is bumped.
