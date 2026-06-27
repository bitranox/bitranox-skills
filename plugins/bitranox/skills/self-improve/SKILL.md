---
name: self-improve
description: Use at the end of a turn that produced a learning, such as a correction from the user, a rule or preference stated ("remember this", "from now on", "always/never"), a process or tooling mistake (wrong command, a quirk of the shell/SSH/environment, a misread of stale output, over-waiting, a tool or file you missed and re-derived), a wasted build or test cycle, or any reusable discovery (a procedure, a timing, a gotcha, a flag combination, a path). Captures the learning into project memory and CLAUDE.md so the harness compounds. A gated Stop hook nudges this automatically; also run on "self-improve", "/self-improve", "improve the harness", or "capture what we learned".
---

# self-improve

Turn what this session taught into a durable improvement, so the same lesson is not re-learned next
time. The unit of value is one small, reusable fact or rule recorded in the right place: a project
**memory** entry (the `MEMORY.md` index plus its topic files) or a **CLAUDE.md** guardrail.

**Core constraint: memory is finite. Default to updating an existing entry and to short index lines,
never to appending blindly.** A self-improver that bloats memory makes the harness worse, not better.

If a project ships its own extension of this skill (a more specific `*-self-improve` for its repo,
exact memory paths, ledgers, or push gates), read it and honor its extra rules on top of this one.

## Memory backend
This skill writes durable learnings to Claude Code's **Auto memory**: the native per-project store
at `~/.claude/projects/<project>/memory/`, whose `MEMORY.md` index is loaded into context each
session. Auto memory is on by default in recent Claude Code (v2.1.59+), so before relying on it,
confirm it is actually active; otherwise learnings get written but never loaded.

- **Detect:** the `~/.claude/projects/<project>/memory/` directory exists, and settings do not set
  `"autoMemoryEnabled": false` (and the env var `CLAUDE_CODE_DISABLE_AUTO_MEMORY` is unset).
- **If absent or disabled, recommend to the user (do not silently skip):** run `/memory` and toggle
  Auto memory on, or set `"autoMemoryEnabled": true` in `~/.claude/settings.json`, and upgrade to
  Claude Code v2.1.59+ if older. Until it is on, fall back to recording durable rules as a CLAUDE.md
  guardrail so nothing is lost. (See https://code.claude.com/docs/en/memory.)

The store's **backend is a choice, not fixed to flat files.** By default it is Auto memory's
`MEMORY.md` + topic files (the push tier, loaded every session). Where a memory MCP server is
installed - `basic-memory` over those same files, or `server-memory` (see "Scaling memory as it
grows") - it is the pull-tier backend for the large episodic tail. The split is the rule: the **most
important standing rules** stay in `MEMORY.md` / CLAUDE.md (push, always in context) and never only
in a search-only MCP store, while the episodic tail can live in the MCP store.

Keep the memory systems in their lanes, and do not duplicate across them:
- **Auto memory / `MEMORY.md` (this skill):** durable, curated, deduplicated rules and facts, loaded
  every session. This is where learnings go.
- **The `remember` plugin / `.remember/`:** session task-continuity only (a time-decaying handoff
  journal: `now.md` -> `today-*.md` -> `recent.md` -> `archive.md`). Never put durable learnings there,
  and never copy handoff/task state into Auto memory.

### Scaling memory as it grows

Self-improve adds entries over time, so the store grows. Manage the growth by escalation; do not let
it bloat:

1. **Keep it lean (default, holds for a long time).** One fact per topic file, a one-line `MEMORY.md`
   index entry (under ~200 chars), and EDIT an existing entry rather than appending a new one (the
   core anti-bloat rule). The index lines are what keep the loaded-every-session cost small.
2. **When the `MEMORY.md` index itself gets too big to scan**, add semantic search over the topic
   files with the `basic-memory` MCP (markdown-file-backed, local `fastembed` embeddings - no cloud). It
   keeps its own DB/config in `~/.basic-memory` (it does not litter the memory dir) and can point
   straight at the existing `~/.claude/projects/<project>/memory/` directory, so it augments the
   native store with search without replacing it and without a migration. Best fit.
   - **Before pointing it at the files, stop it from rewriting them.** basic-memory's sync can write
     its OWN frontmatter (permalink, etc.) into the source markdown, which clashes with the
     self-improve schema (`name`/`description`/`metadata`). In `~/.basic-memory/config.json` set
     `ensure_frontmatter_on_sync: false`, `disable_permalinks: true`, `format_on_save: false` (edit it
     with the `edit-json` skill), then back up the memory dir and diff after its first index run to confirm
     nothing was modified.
   - Alternative: `@modelcontextprotocol/server-memory` is a knowledge-graph store
     (entities/relations) - a different model and a separate parallel store, not a search layer over
     the existing files. Use it only if you actually want the graph model.

Add an MCP server through the `update-config` skill (it edits the MCP/settings config); never wire one
in silently.

**Push vs pull - keep both in their lanes.** `MEMORY.md` is PUSH: loaded into context every session,
always present, zero query - the reliable home for critical, always-apply rules. `basic-memory` is
PULL: semantic search on demand (a tool call), so a memory only surfaces if you actually search for
it. Keep must-hold rules as short `MEMORY.md` index lines or CLAUDE.md guardrails (push, reliable),
and use `basic-memory` for the large tail of episodic/topic memories (pull, scalable). Never move a
must-hold rule into the search-only store: a critical rule has to be in context every time, not only
when queried.

## When to run

Any turn that contains a learning signal. Signals come in **families** - the gated Stop hook fires
on all of them: a user **correction**, an explicit **"remember"**, a user **endorsement** of an
idea you proposed ("good idea", "good call" - a confirmed approach worth recording), an assistant
**self-admitted miss** ("you're right", "my mistake"), or a **realization** - a turn where you
finally work out how something really fits together ("now I understand the real topology...", "I
figured out that X actually runs on Y", "now it's clear"). A realization about your own
infrastructure or a project's architecture, topology, or data-flow is a durable discovery: capture
the fact, do not let it evaporate when the turn ends. You can also invoke this skill manually. If you
reflect and find nothing durable, say so in one line and stop. Do not manufacture a "learning".

When you notice the gate missed a signal, fix the **whole family**, not just the one phrase you were
handed - propose the related variants yourself rather than waiting to be fed each one.

## Procedure

Create one todo per step.

### 1. Gather candidate learnings
Reflect on the just-finished work (the transcript tail, and any session buffer the project keeps).
List the concrete, reusable things this session surfaced, one plain sentence each. Discard anything
that is task state, already recorded in the repo or git history, or only mattered to this conversation.

### 2. Classify each candidate
| Kind                                                                                                                                                          | Home                                                                                                                                                                                                                                                                     |
|---------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| A correction or working-style directive from the user ("from now on...", "always/never...", "don't do X")                                                     | a `feedback`-type memory **and**, if it should bind future sessions, a guardrail line in CLAUDE.md                                                                                                                                                                       |
| A recurring process / tooling / environment mistake (wrong command pattern, a shell/SSH/OS quirk, reading stale output, over-waiting, a forgotten discipline) | the project's recurring-error record if it has one (bump count + date), else a `feedback` memory phrased as the check that avoids it next time                                                                                                                           |
| A discovery or a miss (a tool/path you re-derived, a measured timing, a gotcha, a flag combo, a working procedure)                                            | the most relevant existing `project`/`reference` memory, or a new one                                                                                                                                                                                                    |
| A realization about your own infrastructure or a project's architecture / topology / data-flow ("now I understand the real ...", "X actually runs on Y")      | record the FACT at the right altitude (step 3b): own infra spanning projects -> the top-level/parent CLAUDE.md; one project's scope -> that project's CLAUDE.md or its memory; **unsure which -> ask the user where it belongs**. See the memory-vs-CLAUDE.md note below |
| A skill was wrong, missing, or mis-triggered                                                                                                                  | **propose**; gated-scaffold a new one only with permission (see step 5); never rewrite an existing skill inline (the one self-edit exception is this skill itself, see the meta-loop)                                                                                    |
| Nothing durable                                                                                                                                               | drop it                                                                                                                                                                                                                                                                  |

### 3. Dedup BEFORE writing (mandatory)
For each surviving candidate, search first (`grep -ril "<keyword>"` over the memory dir and the
CLAUDE.md files). If a related entry exists, **edit it** (sharpen it, add the new example, bump the
count) instead of creating a new file. New file only when nothing covers it. Keep a new `MEMORY.md`
index line to one line under ~200 chars; put the detail in the topic file, not the index.

### 3b. Choose the layer(s) - by scope and abstraction
CLAUDE.md and MEMORY.md exist at several layers: global user config, a parent directory spanning
many unrelated projects, an org or subtree root, a subsystem, a single repo. Record at the
**narrowest layer that still covers everywhere the lesson applies**: a tool/shell/OS quirk true
everywhere -> the global user layer; something spanning several unrelated projects -> the shared
parent; a host/infra/deploy fact -> the org-or-subtree root; one subsystem's repos -> that
subsystem's file; a single repo -> that repo's file. The same scope test picks which MEMORY.md.

A single lesson may deserve **two entries at different abstraction levels**: the **general
principle** at the broad layer and the **concrete instance** (the actual file, flag, error,
immediately actionable) at the narrow layer. When you split, the broad entry states the reusable
rule and the narrow one gives the specific case; **cross-link** them and never duplicate the same
text. Default to a single layer; split only when the generalized form is genuinely reusable beyond
this project (the core anti-bloat constraint still applies).

A CLAUDE.md under version control is a shared artifact: **propose** the edit with a diff rather
than auto-committing (see step 4). Private MEMORY.md entries stay auto-apply.

**Memory vs CLAUDE.md (and when both).** A must-hold structural fact - your own infrastructure
topology, a project's architecture or data-flow that has to be in context every time - goes in the
right-altitude **CLAUDE.md** (own infra spanning projects -> the top-level/parent CLAUDE.md; one
project -> that project's CLAUDE.md), matching where infra already lives. A smaller episodic or
looked-up detail goes in the **memory** store: a `MEMORY.md` topic file (with its one-line index
entry), or - where a memory MCP server is installed (`basic-memory`, or `server-memory`; see
"Scaling memory as it grows") - that MCP store, which is the pull-tier home for the episodic tail.
Keep must-hold facts in the push tier (CLAUDE.md / `MEMORY.md` index), never move them into a
search-only MCP store. Use **both** push and a topic entry only as the general-principle (CLAUDE.md)
plus concrete-instance (memory) split above - cross-linked, never duplicated. When the altitude is
genuinely unclear, **ask the user where it belongs** rather than guessing.

### 4. Risk-classify and apply
- **Auto-apply (low risk, additive):** a new memory topic file plus one short index line; appending a
  guardrail line to a CLAUDE.md that is not under version control; bumping a recurring-error count and
  date. Do these directly.
- **Propose, then wait (higher risk):** rewriting or deleting an existing entry, restructuring a
  CLAUDE.md section, editing a version-controlled CLAUDE.md at any layer, pruning the index, or any
  change you are unsure how to classify. Show the diff
  and the reason; apply only after the user agrees. When this needs a decision from the user, follow
  **Asking for a decision** below.
- **Never auto-edit shared or published artifacts:** anything in a public/shared repo, published
  docs, or release text, and respect any project push/publish gate. This skill touches private
  notes (memory, CLAUDE.md, session buffers) only.

### 5. New-skill gaps: propose first, scaffold only when gated
If a missing (or broken) skill is the real fix, write a one-paragraph proposal: what it triggers on,
what it does, and whether it is **shared** (belongs in a skills repo/plugin) or **project-specific**
(lives in this repo's `.claude/skills/`).

- **Default: stop at the proposal.** Authoring a skill is a deliberate act; do not silently spin one
  up inside an auto-improvement turn.
- **Gated auto-scaffold (explicit permission only):** ask one short question - scaffold this skill
  now? On a yes, build it with the `skill-writer` skill rather than hand-rolling the SKILL.md: create
  the directory and frontmatter, then **baseline-test it with subagents before relying on it**. Place
  it at the right scope - a **shared** skill in the source skills repo, then propagate via the upstream
  PR loop (see **Propagating skill improvements upstream**); a **project-specific** skill in this
  repo's `.claude/skills/`, which stays local with no PR. Scan the new content for secrets, PII, and
  infrastructure references before any push.

The single skill you may edit without this gate is this self-improve skill and its gate: see
**Improving this skill (meta-loop)** below.

### 6. Escalate repeats: count, then enforce
A rule the model keeps missing is not a documentation gap. Soft rules (memory, CLAUDE.md prose) are
advisory - the model can and will skip them - so track recurrences and climb a ladder; do not just
write the note louder.

- **Count the miss.** When a recurrence matches an existing rule, bump that rule's recurrence count
  and date (a `recurrence: N (last YYYY-MM-DD)` line in its memory entry, or the project's
  recurring-error ledger). This is how "repeatedly" gets measured instead of guessed.
- **No rule yet (first miss):** write the rule - a `feedback` memory and/or a CLAUDE.md guardrail.
- **Recurs once, a rule already exists:** strengthen it (move it earlier, mark it MUST, add the
  failing example) and bump the count.
- **Recurs again (count reaches 2):** STOP re-wording. Prose has failed twice and more prose will not
  help. Escalate to a **deterministic guard** that blocks the bad action regardless of the model's
  attention - the way the tell-sweep hook blocks em dashes on every write. Propose one of: a hook
  (via the `update-config` skill), a script or CI check, or a real code/tooling fix. Put the decision
  to the user; never auto-create hooks. When the guard is a hook or script, make it portable: write
  the logic in Python (not bash or `jq`), invoke it through an interpreter-resolving launcher, pin
  the launcher and scripts to LF in `.gitattributes` (`*.sh text eol=lf`, and `*.py`/`*.json`) so a
  Windows clone with `core.autocrlf=true` cannot CRLF-break the shell shim (a committed
  `.gitattributes` overrides each clone's `core.autocrlf`, so this needs no per-clone git config),
  mark it executable in git with `git update-index --chmod=+x` (this writes the mode straight into
  the tree, so it is correct regardless of `core.fileMode`; a working-tree `chmod` does not persist
  when `core.fileMode` is false, leaving the installed copy non-executable), and exit 0 on every
  failure path so a broken guard never wedges a turn. Hooks run only on local Claude Code surfaces
  (the CLI and the Desktop Code tab), not the cloud or consumer-chat surfaces. Note in the rule that
  it has graduated to a guard so it is not re-littered with notes.
- **Place the guard by scope, and propagate a global one (do not leave it local-only).** Apply the
  step-3b scope test to the guard itself. A guard for a GLOBALLY-USEFUL quirk - a general shell, OS,
  or tooling mistake true in any repo, like the pgrep/pkill bracket self-match - belongs in the
  SHARED marketplace plugin's `hooks/` (a Python script run through the interpreter-resolving
  launcher, registered in the plugin's `hooks.json`) and MUST be propagated to the source repo via
  **Propagating skill improvements upstream** below, exactly like a shared skill. Adding it only to
  the local `~/.claude/hooks` + `settings.json` is a bug: a reinstall loses it and every other
  install never gets it. A PROJECT-SPECIFIC guard (one that only makes sense in one repo) stays local
  to that project and is never propagated. This propagate-on-global rule covers hooks and scripts,
  not just skills.

The point: memory and CLAUDE.md change what the model is *told*; a guard changes what the model can
*do*. A rule that must always hold belongs in a guard, not only in prose.

### 7. Report
End with a short summary: what was auto-applied (file plus one line each) and what is proposed and
awaiting your go. No filler.

## Improving this skill (meta-loop)
The one exception to "suggest, do not author" (step 5) is **this skill and its gate**
(`self-improve-gate.py`): keeping the improver itself effective is the whole point, so you may edit
them. Treat it as the highest-risk change: **propose-first always**, and after a substantive change to
the procedure or the gate, re-verify with a baseline subagent test before relying on it. A change to
this skill or any shared skill must reach the source repo, not just the installed copy a plugin update
overwrites - see **Propagating skill improvements upstream** below.

Enter the meta-loop when any of these show the improver itself is failing:
- **Bad result:** the user rejects or corrects what a self-improve run produced (wrong entry, wrong
  lane, memory bloat).
- **Gate false positives / negatives:** it keeps firing on non-learnings, or it missed a real
  correction.
- **Going in circles:** the same learning is recorded again and again across sessions, or a recorded
  rule keeps being violated.
- **Insufficient:** a process error recurs even though it is already in the ledger and a rule already
  exists and was already strengthened.

Diagnose which stage failed, then fix that stage:
| Symptom                                    | Stage                                                           | Fix                                                                                                                                                                                          |
|--------------------------------------------|-----------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Recorded the wrong thing / wrong lane      | classify, dedup (steps 2-3)                                     | sharpen the classification or dedup wording                                                                                                                                                  |
| Memory bloat, duplicate entries            | dedup / autonomy (steps 3-4)                                    | tighten "edit existing over new", or downgrade an auto-apply to propose-first                                                                                                                |
| Gate fires on noise, or misses corrections | the gate script                                                 | adjust its regex signal patterns                                                                                                                                                             |
| Rule recorded but STILL violated           | the step-6 enforce ladder was skipped, or the guard is too weak | do not add more notes. Run step 6 to its end (count the misses, escalate to a deterministic guard or a real fix). If a guard already exists and still fails, harden the guard, not the prose |

**Circle-breaker (mandatory):** if two self-improve passes on the same issue have not resolved it,
stop recording more notes about it. Writing the same lesson a third time *is* the circle. Switch
tactic (enforcement or a real fix) or hand the decision to the user. Do not keep adding memory.

## Propagating skill (or hook) improvements upstream
Most self-improve output is personal (memory and project CLAUDE.md) and stays local on the user's
machine - it is not shared. A SHARED, DISTRIBUTED artifact is different: a skill OR a hook/guard
installed from a plugin or marketplace (for example a skill or a `hooks/` script in the bitranox
plugin), or this self-improve skill and its gate. When you change or ADD one, the edit lands in the
installed copy, which a plugin update OVERWRITES on the next sync. The change is lost (and every
other install never gets it) unless it reaches the artifact's SOURCE repo. The repo is the single
source of truth; the installed copy is ephemeral. Creating a globally-useful hook only in the local
`~/.claude/hooks` + `settings.json`, instead of in the marketplace plugin, is the exact mistake this
section prevents.

**Scope guard (decide first):** only propagate SHARED artifacts. A project-specific skill or hook
(one that lives in a project's own `.claude/`, specific to that repo) is never propagated: it stays
in that project. Never symlink it and never open a PR for it.

When you add or change a shared skill or hook, run this loop:
1. **Confirm scope.** The skill is shared/distributed, not project-specific. If unsure or
   project-specific, stop and keep the change local.
2. **Scan the diff.** Grep for secrets, credentials, private hostnames/IPs, internal paths, and
   personal or project codenames. Never let any of these leave the machine (the same scan you run
   before any push to a public or shared repo).
3. **Route by who and how - the gate decides the path:**
   - **Maintainer, interactive (a human is approving changes live):** the live approval IS the gate.
     Commit directly to the repo's default branch and push - no PR ceremony.
   - **Maintainer, unattended/async (a scheduled or background self-improve, no human approving
     live):** do NOT commit straight to the default branch. Open a structured self-PR so an
     auto-review agent (or the maintainer later) merges or rejects it.
   - **Outside contributor (no write access):** fork, then open a structured PR.
4. **Bump the distributed version (REQUIRED for version-gated installs).** Before committing, read
   the repo's `CONTRIBUTING`/release docs so you follow its rule rather than guess. If the artifact
   is distributed by version - a plugin or package whose installed copies only re-fetch when the
   version changes (a Claude Code plugin's `plugin.json`, an npm/PyPI package, ...) - bump that
   version per the repo's semver convention IN THE SAME COMMIT and note the bump in the subject.
   Propagation is NOT done until the version is bumped: without it every install stays on the old
   copy and the change ships to nobody. A docs-only change that does not touch the distributed
   artifact may be exempt (check the repo's rule).
5. **Confirm, then apply.** Ask one short permission prompt, then carry out the routed path:
   - **Direct commit:** edit in the repo clone, commit (with the version bump from step 4), push to
     the default branch.
   - **PR (self-PR or fork):** edit on a new branch, push, `gh pr create` with a structured title and
     body so a downstream agent can auto-merge or auto-reject without guessing:
     - **Title:** `skill(<name>): <one-line change>` (or `hook(<name>):` / `gate:` / `docs:`); append
       `; bump to X.Y.Z` if the repo's history does.
     - **Body:** **Motivation** (the learning or failure that prompted it), **What changed** (file by
       file), **Scope** (shared, not project-specific; applies beyond this one setup), **Safety**
       (diff scanned, no secrets, PII, or infrastructure references).
   Keep the diff minimal and focused on one skill or hook.

**Maintainer local setup:** symlink the installed shared-skill directories into your repo clone so
in-place edits land in git instead of the ephemeral install. Symlink ONLY shared skills, never
project-specific ones. The pre-flight scan in step 2 is mandatory before any push or PR.

## Asking for a decision
When you need the user to choose, **ask one question at a time, never a batch.** For each question:
state plainly what is being decided, give the realistic implications and trade-offs of each option,
and end with a recommendation and the one-line reason for it. Wait for the answer before asking the
next question. A wall of simultaneous questions, or options with no recommendation, pushes the
decision work back onto the user. One clear question with a steer is easier to answer.

## Writing style
These notes are read by a future agent and may live in CLAUDE.md. Keep them plain and short: state
the fact and the why, skip promotional adjectives, and avoid em-dashes and other typographic or
invisible AI tells (en-dash and other dashes, curly quotes, guillemets, ellipsis, and invisible
blanks like the zero-width space, non-breaking space, and BOM). Sweep generated files for these with
a `grep -nP` over the tell code points before you call the work done.

## Common mistakes
- Appending a new memory file when an existing one should have been edited (bloats the index).
- Mixing the two lanes: a one-off task finding logged as a recurring-process rule, or vice versa.
- Auto-applying a rewrite or delete. Additive is auto; destructive is propose-first.
- Authoring a skill on the fly instead of suggesting it.
- Recording session state ("the build is running") as if it were a durable learning.
