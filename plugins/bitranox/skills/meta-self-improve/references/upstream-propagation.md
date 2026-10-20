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
Queue first, then do the steps below now or later. `contrib_queue.py list` shows what is pending
(numbered); `contrib_queue.py drain` clears it and records each entry as shipped, so a drained
intent is not queued again - ONLY after the change actually shipped.

**Close every entry by its OUTCOME, and close it individually.** `ship --match <text> --note <where
it landed>` for one that DELIVERED; `drop --match <text> --reason "<why>"` for one that turns out
FALSE (you verified the claim and it is wrong) or SUPERSEDED (a later release already covers it).
Either way it has to leave the queue, or every future dream re-reads and re-evaluates it forever.
Select with `--match`, not `--index`: an index comes from a listing and SHIFTS under the previous
close, so two closes from one listing hit the wrong second entry. Every verb acts on the queue of
ONE project, keyed by a hash of the cwd (or the path passed) at
`~/.claude/self-improve-audit/<hash>.contrib.jsonl`, so a `list`/`ship`/`drop` run from a different
directory than the `add` sees another or an empty queue and refuses with `no queued contribution
matches`. Run `contrib_queue.py queues` first: it lists every queue with its key, open count and
project path; then close the entry from that project's dir or address it as `queue_key:<hash>`,
which every verb accepts. `drain` closes the WHOLE queue at
once and fits only a sweep where every entry shipped. `contrib_queue.py shipped` and
`contrib_queue.py rejected` show what left and why. The drop writes a TOMBSTONE, which is
the part that makes it stick: `add` dedups only against the LIVE queue, so without the tombstone the
next dream that re-notices the same gap silently re-queues it. A re-add of a dropped intent is
refused and says so. An out-of-range index is refused rather than deleting the wrong entry.

Dropping is a JUDGEMENT, so record the evidence in `--reason`: "verified false, <the check you ran>"
or "shipped in <version>". A queue entry you merely doubt is not a drop - test it and find out.

**Before writing a queued documentation contribution, check it is not already shipped elsewhere.**
The entry's `--target` is a guess made when the learning was captured, and the rule often already
lives in a sibling skill that owns the TRIGGER rather than the topic (one measured queue drain: 4
of 9 documentation entries were already shipped, 3 of them in a sibling). So search EVERY shipped
skill (each `SKILL.md` and its `references/`), not only the one the entry names, plus the local
layer (`~/.claude/skills/`, `~/.claude/commands/`), which can hold detail no shipped skill has.
Read the matching lines instead of trusting a hit count or a miss, and try each spelling: a
hyphenated pattern misses the spaced form (`defense-in-depth` does not find "defense in depth"),
and a literal command such as `cp -a` misses the same rule worded as prose. When a sibling already
carries the rule and its trigger fires where the reader needs it, drop the entry with
`--reason "already in <skill>/<file>"` rather than adding a second copy, which will drift. When it
carries the rule but is not loaded where the reader needs it, add a one-line pointer to it in the
skill that IS loaded there, never a second copy of the rule. Re-check
the file even for a rule queued earlier in this session: context can hold text the repo has since
changed.

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
