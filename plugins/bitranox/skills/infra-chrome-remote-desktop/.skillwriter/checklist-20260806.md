# skill-writer checklist - infra-chrome-remote-desktop (2026-08-06, new skill)

Skill type: reference/technique (a diagnose-and-repair procedure with two discipline rules -
read the journal before spending an OAuth code, and verify PAM as the unprivileged user).

## PLAN

- [x] Type identified; test approach = application scenarios, one per branch of the decision table.
- [x] Three scenarios drafted before any text was written.
- [x] Scope decided: self-contained SKILL.md, no supporting files, no bundled scripts.
- [x] Naming: `infra-*` per `skill-taxonomy.json`. `compuse-*` is command-running mechanics and
      `compuse-vnc` is a client that drives a target; this skill administers a host service, which
      the `meta-using-bitranox-skills` domains list groups under infrastructure.

## RED (baseline, no skill)

- [x] Scenario A ("PIN is not valid", host online): the agent never read
      `journalctl -u chrome-remote-desktop@<user>`. It planned to delete the device entry and spend
      a fresh single-use OAuth code, and declined to check the stored hash at all - "I did not
      hand-verify the exact byte-level construction of `host_secret_hash`". Exactly the wrong turn
      the skill's Step 1 forbids.
- [x] Scenario B (NNP sudo refusal): the agent reached "run as the user" but its leading hypothesis
      was sshd hardening, and its remediation was `sed -i` deleting `NoNewPrivileges` from an
      ssh.service drop-in plus `systemctl restart ssh` over the live SSH session, with an LXC reboot
      as the alternative. Destructive, and aimed at a cause that is not the one in play. It also
      never mentioned clearing the half-written config, and its verification commands
      (`systemctl --user`, `usermod -aG chrome-remote-desktop`) do not match how CRD is supervised.
- [x] Scenario C (stored PIN): baseline PASSED, so it was re-run to rule out environment
      contamination. With network the agent fetched Chromium's `pin_hash.cc` and got the formula
      and argument order right. Air-gapped, the same scenario FAILED - it asserted
      `SHA256(host_id + pin)` as its primary hypothesis and stated the value is "not a real HMAC
      despite the `hmac:` label". The pass was supplied by the environment, not by the model.

## GREEN (with the skill)

- [x] All three scenarios re-run against the worktree file by path, not an installed copy.
- [x] A: read the journal first, matched the table row, fixed the group ownership, ran the
      pamtester pair including the negative control, and did not spend a code.
- [x] B: identified the root run as the cause, cleared the config, ran the registration pattern
      with the `trap`-cleaned grant, and verified the grant was gone afterwards.
- [x] C: reproduced the formula with the correct argument order and built a synthetic positive
      control; no network needed.
- [x] Every dispatch, RED and GREEN, was required to return a `Skill gaps` section reporting
      concrete evidence rather than a verdict.

## REFACTOR (gaps closed)

- [x] **Self-contradiction, found by GREEN B.** The table's disproof clause for the NNP row read
      "the value is `0` in the shell that failed - look elsewhere", but a root run sets the flag on
      the spawned binary, so the invoking shell legitimately reads `0`. The row pointed a reader
      away from the true cause. Row rescoped, and prose added stating that a root run needs no probe.
- [x] **Cross-section dependency, GREEN B.** That the code is already spent appeared only in a
      later section, so a reader fixing the invocation would retry on a dead code. Stated at the
      point of failure and added to the mistakes table and red flags.
- [x] **Silence, GREEN A.** Whether the PAM fix needs a service restart was unstated and the agent
      acted on an assumption. Answered explicitly (no restart; the check runs per connection).
- [x] **Missing case, GREEN C.** The two-run protocol assumed a known-good PIN, which the usual
      case does not have. Added the synthetic-config positive control.
- [x] **Silence, GREEN A.** No fallback when `pamtester` cannot be installed. Added the journal as
      the slower fallback effect check.
- [x] **Lost from RED, scenario A.** The baseline preserved stale configs by moving them aside;
      the first draft said `rm -f`. Adopted the baseline's better behaviour - the failed run's
      config is the only record of what it wrote.
- [x] **Silence, GREEN B.** `~<user>` is not expanded inside quotes or in a variable. All paths
      now resolve the home with `getent`.

## Gaps declined, with reasons

- [x] How to reach an LXC container (`pct exec` vs ssh) - owned by `infra-proxmox`, not a CRD fact.
- [x] Whether `--pin` is mandatory at registration - not measured; asserting either way would ship
      an unverified claim.
- [x] How to discover which desktop-session binary is installed - the operator's choice of desktop
      environment, not a CRD behaviour. The snippet notes the value is per-box.
- [x] The code and redirect URL appearing in `ps` and shell history - real, but the code is
      single-use and expires, and `start-host` exposes no alternative interface.
- [x] Chromium's published `pin_hash_unittest.cc` vector as a fixed control - not verified
      first-hand here, and the agent that produced it also reported corrupting a character of it on
      its first pass. The synthetic self-test gives the same guarantee with no constant to get wrong.
- [x] Coordinating "have the user connect" with a live journal tail - ordinary operational detail.

## Verification

- [x] Quote-back on all four changed points returned a direct quote of the governing text; no NONE.
- [x] Both Python blocks EXECUTED, not reviewed: the shipped snippet run as a script against a
      synthetic config prints `True` for the stored PIN and `False` for another, and the control
      block's asserts pass.
- [x] The swapped-argument claim executed: the correct PIN reports `False` under the swapped form,
      confirming that form cannot report a match for any input.
- [x] All 10 bash blocks pass `bash -n` with placeholders substituted.
- [x] `unix_chkpwd` verified first-hand as `-rwxr-sr-x root shadow` (setgid shadow, not setuid
      root), the healthy `/etc/shadow` mode verified as `root:shadow 640`, and
      `/etc/pam.d/chrome-remote-desktop` confirmed to be a real PAM service name.

## Quality and security

- [x] Frontmatter is trigger-first ("Use when installing, registering, or repairing...") and yields
      well over 3 distinctive keywords; `build_skill_triggers.py` regenerated.
- [x] File is pure ASCII - no em/en dash, curly quote, ellipsis, NBSP or verdict emoji.
- [x] Present tense throughout; no session narrative, no operator instructions, no scratch paths.
- [x] No secrets, no OAuth codes, no PINs, no private hostnames, IPs or MACs. Placeholders only
      (`<user>`, `<code>`, `<pin>`, `<host-name>`). Verified by grep for address, MAC and home-path
      patterns.
- [x] No bundled scripts, so no `tests/` dir is required.
- [x] Registry sync: `build_skill_docs.py` and `build_skill_triggers.py` regenerated, README skill
      count raised in both places, `plugin.json` bumped 5.156.0 -> 5.157.0 (MINOR, a new skill).
