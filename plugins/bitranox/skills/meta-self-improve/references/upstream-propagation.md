# Propagating skill (or hook) improvements upstream

Most self-improve output is personal (memory, project CLAUDE.md) and stays local. A SHARED,
DISTRIBUTED artifact is different: a skill or a `hooks/` script installed from a plugin or
marketplace, or the self-improve skill and its gate themselves. An edit to the INSTALLED copy is
overwritten by the next plugin update and reaches nobody else - the SOURCE repo is the single
source of truth; the installed copy is ephemeral. Creating a globally-useful hook only in the local
`~/.claude/hooks` + `settings.json` is the exact mistake this loop prevents.

**Scope guard (decide first):** only propagate SHARED artifacts. A project-specific skill or hook
(one living in a project's own `.claude/`) stays in that project - never symlinked, never PR'd.

**QUEUE THE INTENT THE MOMENT YOU JUDGE IT SHIPPABLE - before you do the work.** The classic loss is
not a bad PR, it is a good intent that never became one: the session ends, the private fact survives
in the store, and "this should become a skill change" evaporates with the context. Nothing used to
record it. So the instant a learning looks skill/hook-worthy:

    bash <plugin>/hooks/run-python.sh <plugin>/skills/meta-self-improve/contrib_queue.py add \
      --what "<the change>" --target "skill:<name>|hook:<name>" --why "<the evidence>" "<cwd>"

That queue is DURABLE and per-project: SessionStart surfaces it every session and does NOT consume it
(unlike the miss-audit), so the intent outlives the session and gets picked up when the work suits.
Queue first, then do the steps below now or later. `contrib_queue.py list` shows what is pending;
`contrib_queue.py drain` clears it - ONLY after the change actually shipped.

When you add or change a shared skill or hook:

1. **Confirm scope.** Shared/distributed, not project-specific. If unsure, stop and keep it local.
2. **Scan the diff.** Grep for secrets, credentials, private hostnames/IPs, internal paths, and
   personal or project codenames. Nothing sensitive leaves the machine. Sensitivity is something to
   STRIP, not a disqualifier: if the rule still teaches once the private specifics are replaced
   with generic placeholders, scrub and contribute the cleaned version; only a rule USELESS without
   its specifics stays private.
3. **Route by who and how - the gate decides the path:**
   - Maintainer, interactive (a human approving live): the live approval IS the gate - commit to
     the default branch and push, no PR ceremony.
   - Maintainer, unattended/async (scheduled or background run): open a structured self-PR for an
     auto-review agent or the maintainer to merge.
   - Outside contributor: fork, then a structured PR.
4. **Bump the distributed version (REQUIRED for version-gated installs).** Read the repo's
   CONTRIBUTING/release docs first. If the artifact ships by version (a plugin's `plugin.json`, an
   npm/PyPI package), bump it per the repo's semver convention IN THE SAME COMMIT and note it in
   the subject - without the bump, every install stays on the old copy and the change ships to
   nobody. Docs-only changes may be exempt (check the repo's rule).
5. **Confirm, then apply.** One short permission prompt, then the routed path. For a PR, structure
   it so a downstream agent can merge or reject without guessing:
   - Title: `skill(<name>): <one-line change>` (or `hook(<name>):` / `gate:` / `docs:`); append
     `; bump to X.Y.Z` if the repo's history does.
   - Body: **Motivation** (the learning that prompted it), **What changed** (file by file),
     **Scope** (shared, applies beyond this setup), **Safety** (diff scanned, no secrets/PII/infra).
   Keep the diff minimal and focused on one skill or hook.

**Maintainer local setup:** symlink the installed shared-skill directories into the repo clone so
in-place edits land in git instead of the ephemeral install. Symlink ONLY shared skills. The step-2
scan is mandatory before any push or PR.
