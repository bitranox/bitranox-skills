# skill-writer checklist - compuse-toolbox (add the `fleet_ssh` jig)

Change: ship an ssh/scp wrapper that keeps the login user and the resolved key the same identity,
after that pairing broke in a hand-rolled wrapper. Reference-skill edit plus a new tested script.

## PLAN
- [x] Skill type: reference (tool index with a per-tool rationale). Test approach: retrieval - can
      an agent holding the skill pick the right jig and use it correctly?
- [x] Trigger is measured, not hypothetical: a wrapper whose `--user` flag reached key resolution
      but never the scp path resolved one user's key and connected as another. On a host that
      accepts root and refuses the local account, that is `Permission denied (publickey)` from a
      command line where the flag looks honoured.
- [x] Checked it is not already shipped: the skill names 11 tools, none of them an ssh/scp wrapper.
      `transfer push` is adjacent but answers "copy this big file at a capped rate", not "reach this
      host as this user without prompting".
- [x] Scope: one script plus tests, one table row, one rationale bullet, one description clause.

## RED
- [x] 27 tests written against the traps, each pinning one behaviour: `--user` reaches an scp
      destination and a remote source; a user named in the path wins over the flag; a local-to-local
      copy gains no user and has no host to heal; the key and the login are the same identity;
      `BatchMode=yes` in both modes; `IdentitiesOnly` only when a key is used; an existing but
      unreadable key is skipped; no readable key means no `-i`; strict host-key checking is the
      default; the trusting mode is opt-in and uses a separate known-hosts file; `/dev/null`
      known-hosts is refused; the retry heals once, never on an ordinary failure, never on a zero
      exit whose stderr merely mentions the phrase, and never without the opt-in.
- [x] Three mutants, each failing only the tests that describe it: no scp-user write-back (3 fail),
      trust on by default (1), heal without the opt-in (1). The scp-user test goes through the
      wiring rather than the helpers, because both helpers were correct alone and only their join
      was wrong - a pure-function test passes on the bug.
- [x] Retrieval baseline, agent given the pre-change table and an unattended deploy needing a copy
      plus a remote run: it hand-writes a five-option `ssh`/`scp` block twice, and its gaps list
      names the judgement it could not resolve from the skill - "whether `host.example` is on the
      user's own/trusted subnet ... or an arbitrary/untrusted host was not stated". That is the
      per-call retyping and the unanswered host-key policy this jig exists to settle.
- [x] Baseline contamination noted rather than claimed as a pass: the scenario names which account
      the host accepts, so the destination-user trap cannot fail there. That trap is held by the
      mutant above, which is the stronger evidence anyway.

## GREEN
- [x] 27 pass. Whole-repo gate green with the CI dependency set.
- [x] Retrieval run with the new table: the agent names `fleet_ssh` as "the purpose-built tool for
      exactly this shape of task (root-only key, refuses local account, scp identity must match ssh
      identity)", and its fallback keeps `root@` on both legs, citing the reason - "so the key and
      the login identity can never drift apart". The identity rule transfers even into a hand-rolled
      answer, which is what the bullet is for.
- [x] Live-checked against a real host, not only in tests: an ssh command returns as root, and the
      scp form that fails without the write-back lands the file owned by root with a matching
      checksum.
- [x] Description clause names the SYMPTOM (retyping an option block per call, an scp login user
      that has to go inside the path), not the implementation.
- [x] Nothing site-specific is baked in: key templates come from `FLEET_SSH_KEY_CANDIDATES`
      (os.pathsep-separated, taking `{user}` and `{home}`) and the default user is whoever runs it.
- [x] Table row and rationale bullet follow the established shape; table realigned by the hook.

## REFACTOR
- [x] Both dispatches asked for a `Skill gaps` section and both lists are recorded here.
- [x] GREEN gap, declined with a reason: the agent identifies the right jig and then cannot run it,
      because the `Invoke` column is a relative `uv run scripts/...` path and its context carries no
      toolbox directory. Declined because it is a property of all twelve rows, not of this one -
      the body already says "Run from the skill directory, or give the full path", and a skill
      invoked through the skill system is announced with its base directory. Changing one row's
      convention would leave eleven inconsistent with it; if the convention is wrong it is wrong
      skill-wide and belongs in its own change.
- [x] GREEN gap, closed by the text already: both arms ask whether the host is a churn-prone
      reimaged fleet or an unknown host. The GREEN arm answers it from the bullet, naming the
      separate known-hosts file as the fleet form; the flag is `--trust-changing-host-keys`.
- [x] GREEN diffed against RED in both directions. Nothing the baseline produced is missing from
      GREEN: both give a working copy-then-run pair, both flag the 255 ambiguity, and GREEN adds the
      tool identification and the identity rationale.
- [x] Quote-back on the contested rule: the governing sentence is "scp carries the login user INSIDE
      the path and has no `--user` flag, so a wrapper that reads `--user` only to pick the key hands
      scp a destination naming nobody".

## Quality
- [x] Present tense, no session narrative, in the skill and in this artifact.
- [x] Every host, user and path added here is a reserved documentation value: `host.example`,
      `devuser`, `/tmp/deploy.sh`. Verified with the address/path grep over the skill.
- [x] Script is import-safe (work behind `__main__`), stdlib only, no third-party import to guard.
- [x] CLI contract: `--dry-run` prints the argv and `--json` makes it machine-readable, diagnostics
      to stderr, a usage error exits 2 without connecting, and otherwise the exit status is ssh's
      own so the caller keeps the remote command's code.

## Deliverables
- [x] `scripts/fleet_ssh.py`, `tests/test_fleet_ssh.py` (27 tests), SKILL.md row + bullet +
      description clause.
- [x] `plugin.json` bumped to 5.175.0; `docs/skills.md` regenerated; `skill_triggers.json`
      regenerated and unchanged.
