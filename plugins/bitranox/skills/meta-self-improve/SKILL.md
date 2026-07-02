---
name: meta-self-improve
description: Use at the end of a turn that produced a learning, such as a correction from the user, a rule or preference stated ("remember this", "from now on", "always/never"), a process or tooling mistake (wrong command, a quirk of the shell/SSH/environment, a misread of stale output, over-waiting, a tool or file you missed and re-derived), a wasted build or test cycle, or any reusable discovery (a procedure, a timing, a gotcha, a flag combination, a path). Captures the learning into project memory and CLAUDE.md so the harness compounds. A gated Stop hook nudges this automatically; also run on "self-improve", "/self-improve", "improve the harness", or "capture what we learned".
---

# self-improve

Turn what this session taught into a durable improvement, so the same lesson is not re-learned next
time. The unit of value is one small, reusable fact or rule recorded in the right place at the right
altitude: a project **memory** entry (in the curated store `.claude-bx-selflearning/`: the `index.md`
index plus `facts/` bodies), a **global cross-project rule** in the curated `~/.claude` store
(`~/.claude/.claude-bx-selflearning/`), or a
**CLAUDE.md** guardrail (see step 3b).

**Core constraint: memory is finite. Default to updating an existing entry and to short index lines,
never to appending blindly.** A self-improver that bloats memory makes the harness worse, not better.

This skill is the per-turn CAPTURE. The periodic BATCH consolidation - dedup/merge/generalize/re-wire/
prune the whole store, like sleep - is `bitranox:meta-dream-project` (this project; run it when memory
has grown or a consolidation is nudged as due) and, for the occasional cross-project pass,
`bitranox:meta-dream-global`. Capture here; consolidate there.

If a project ships its own extension of this skill (a more specific `*-self-improve` for its repo,
exact memory paths, ledgers, or push gates), read it and honor its extra rules on top of this one.

## Memory backend
Durable learnings live in the project-local **curated store** `<project>/.claude-bx-selflearning/`:
- **`index.md`** - the index pulled into context with ONE `@import` line (a scope-descriptor block on
  top + one markdown-link line per fact, with tiny bodies inlined). Because it is `@import`ed, every
  line is always in context. The import line lives in the UNTRACKED **`CLAUDE.local.md`** by default
  (symmetric with the gitignored store - nothing memory-related touches tracked git, a fresh clone has
  neither the wiring nor the store), or the TRACKED **`CLAUDE.md`** when `track_private` is on (so a
  teammate's clone loads it too).
- **`facts/<slug>.md`** - heavy bodies, kept OUT of the always-loaded index and Read on demand.

**The write path is the engine, never a hand-write.** Capture ONE fact by invoking
`hooks/memory_engine.py` (via the plugin's `hooks/run-python.sh` launcher, cross-platform):

    add --proj "<cwd>" --type feedback|project|reference|user --title "..." --hook "one line"
        --body-file <tmpfile> [--source <native-slug>] [--pin] [--scope "what this level is for"]

The engine upserts by slug (merging provenance + pin), decides inline-vs-`facts/` by size and by
whether the body contains an import-like `@token` (such a body goes to `facts/`, never inlined),
ensures the `@import` block (in `CLAUDE.local.md` by default, `CLAUDE.md` if `track_private`) + the `index.md` scope block, takes a lock, and is
mtime-neutral. **Do NOT Write/Edit `index.md`/`facts/` yourself** - the PostToolUse hooks would
then churn the file every turn; the engine writes directly and bypasses them.

**Two tiers (native raw + curated).** Claude Code's native Auto memory (`~/.claude/projects/<proj>/
memory/MEMORY.md`) stays ON as the raw/uncurated tier; it also loads at session start. Capture goes
to the CURATED tier (the engine above). Both load; their union is your memory. The dream de-doubles
(a fact lives in exactly one tier) and promotes worthwhile raw entries into the curated store; it
leaves some-value raw entries in native. You do not need Auto memory on for capture to work, but
keeping it on preserves the raw tier - do not disable it.

**Version gate.** `@import` needs a new-enough Claude Code. If `self_improve_signals.import_supported()`
is false, the store will not load; recommend the user upgrade rather than hand-writing bodies into
CLAUDE.md (never do that).

Keep the memory systems in their lanes:
- **The curated store + native raw tier (this skill):** durable, curated, deduplicated learnings.
- **The `remember` plugin / `.remember/`:** session task-continuity only (a time-decaying handoff
  journal). Never put durable learnings there, and never copy handoff/task state into memory.

### A memory MCP is an optional SEARCH index, never the store

A memory MCP (`basic-memory`) is **not** the home and **not** a write path - routing learnings
through it skips the index and they become unindexed + unsearched (a real regression). Its ONLY
sanctioned role is an optional, full-text + knowledge-graph SEARCH index OVER the local
`.claude-bx-selflearning/` files, to sharpen CROSS-project recall. When present it must be read-only
over those files (`ensure_frontmatter_on_sync: false`, `disable_permalinks: true`,
`format_on_save: false` so it never rewrites them); when absent, recall falls back to the built-in
keyword scan (never a hard dependency - self-healing). Add or remove it through the `update-config`
skill; never wire one in or out silently.

### Scaling: keep it lean

One fact per entry, a one-line hook (under ~200 chars), and EDIT an existing entry (re-run the engine
with the same title -> it upserts) rather than appending a near-duplicate. `index.md` is capped
(`reconcile_memory_index.over_cap`); when it grows, the dream moves inline bodies out to `facts/` and
prunes. If the index ever drifts from `facts/`, `reconcile_memory_index.py <curated-dir>` backfills
missing lines - additive, idempotent.

## When to run

Any turn that contains a learning signal. Signals come in **families** - the gated Stop hook fires
on all of them: a user **correction**, an explicit **"remember"**, an **endorsement of a good idea
from either side** ("good idea", "good call") - when YOU judge the user's suggestion good, the user
found the better path, so adopt and record it (kin to a self-admitted miss); when the user endorses
your proposal, it is a confirmed approach - an assistant **self-admitted miss** ("you're right", "my
mistake", "I should have ...", "I missed ...", "in hindsight ..."), an assistant **committing to a rule
going forward** ("from now on I'll ...", "going forward I'll ...") - especially after being reminded of a
rule you overlooked - or a **realization or discovery** - a turn where you finally work out how something
really fits together OR locate the thing you were hunting ("now I understand the real topology...", "I
figured out that X actually runs on Y", "now it's clear", "found it - the bug was ...", "found the root
cause"). (A bare acknowledgement like "understood" is NOT itself the signal - the lesson is the rule or
directive it acknowledges; trigger on that. Citing a rule you'd missed - "per the X rule" - is an audit
candidate, reviewed next session, not a live nudge.)
A realization about your own
infrastructure or a project's architecture, topology, or data-flow is a durable discovery: capture
the fact, do not let it evaporate when the turn ends. You can also invoke this skill manually. If you
reflect and find nothing durable, say so in one line and stop. Do not manufacture a "learning".

When you notice the gate missed a signal, fix the **whole family**, not just the one phrase you were
handed - propose the related variants yourself rather than waiting to be fed each one.

### End-of-session miss audit (self-tuning loop)

Because the per-turn Stop gate is precision-tuned, it misses some signals. A two-stage loop catches
those without making the live gate noisy:

- **SessionEnd** (`self-improve-audit.py`) scans the whole transcript and, using the broader recall
  patterns in `self_improve_signals.py`, records **candidate misses** (a broad match the strict gate
  did not catch) to a per-project audit file. It cannot call the model, so it only records.
- **SessionStart** (`session-start.py`) surfaces that audit once next session, so you **review the
  candidates**: confirm the genuine misses, capture their learnings here, and for a real gap extend
  the gate's family patterns in `self_improve_signals.py` (the meta-loop). Patterns live in that one
  shared module so the gate and the audit never drift.
- **Premature signals belong in the audit, NOT the live gate.** A mid-course pause ("let me stop and
  inspect", "let me double-check", "wait, ...") only HINTS at a lesson - the lesson is not formed yet;
  it resolves later into a discovery ("found it") or a self-admission ("I should have"), which the live
  gate already catches. So those precursors are deliberately BROAD-audit-only (a next-session review
  candidate, where a human decides if there was a lesson or an anti-pattern), never a per-turn nudge.

## Procedure

Create one todo per step.

### 1. Gather candidate learnings
Reflect on the just-finished work (the transcript tail, and any session buffer the project keeps).
List the concrete, reusable things this session surfaced, one plain sentence each. Discard anything
that is task state, already recorded in the repo or git history, or only mattered to this conversation.

### 2. Classify each candidate
| Kind                                                                                                                                                          | Home                                                                                                                                                                                                                                                                                               |
|---------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| A correction or working-style directive from the user ("from now on...", "always/never...", "don't do X")                                                     | a `feedback`-type memory **and**, if it should bind future sessions, a guardrail line in CLAUDE.md                                                                                                                                                                                                 |
| A recurring process / tooling / environment mistake (wrong command pattern, a shell/SSH/OS quirk, reading stale output, over-waiting, a forgotten discipline) | the project's recurring-error record if it has one (bump count + date), else a `feedback` memory phrased as the check that avoids it next time                                                                                                                                                     |
| A discovery or a miss (a tool/path you re-derived, a measured timing, a gotcha, a flag combo, a working procedure)                                            | the most relevant existing `project`/`reference` memory, or a new one                                                                                                                                                                                                                              |
| A realization about your own infrastructure or a project's architecture / topology / data-flow ("now I understand the real ...", "X actually runs on Y")      | record the FACT at the right altitude (step 3b): useful across projects -> the curated `~/.claude/.claude-bx-selflearning/` store (kept concrete); one project's scope -> that project's memory; a must-hold intermediate-subtree rule -> that level's CLAUDE.md; **unsure which -> ask the user** |
| A skill was wrong, missing, or mis-triggered                                                                                                                  | **propose**; gated-scaffold a new one only with permission (see step 5); never rewrite an existing skill inline (the one self-edit exception is this skill itself, see the meta-loop)                                                                                                              |
| Nothing durable                                                                                                                                               | drop it                                                                                                                                                                                                                                                                                            |

### 3. Dedup BEFORE writing (mandatory)
For each surviving candidate, search first (`grep -ril "<keyword>"` over `.claude-bx-selflearning/`
(`index.md` + `facts/`), the native memory dir, and the CLAUDE.md files). If a related entry exists,
**update it**: re-run the engine `add` with the SAME `--title` - it upserts (merges provenance, keeps
the pin), so sharpening a fact is the same command, not a new entry. New entry only when nothing
covers it. Keep the `--hook` to one line under ~200 chars; put the detail in `--body`/`--body-file`
(the engine inlines a tiny body, sends a heavy one to `facts/`).

### 3b. Choose the altitude(s) - by SCOPE, placed concretely
Knowledge lives at always-present homes, narrowest to broadest:
- **per-project** -> the project's curated store (`.claude-bx-selflearning/index.md` + `facts/`),
  written with the engine. **Per-turn capture writes at the PROJECT level only** (`--proj "<cwd>"`);
  it does NOT reach up to edit an ancestor's CLAUDE.md. Raising a fact to a higher altitude is the
  DREAM's job (promotion), not per-turn capture - so a routine capture never touches a parent tree.
- **global / cross-project** -> the curated store at the `~/.claude` user-scope altitude
  (`~/.claude/.claude-bx-selflearning/`, `global_rules_dir()`), whose `index.md` is @imported by
  `~/.claude/CLAUDE.md` so it loads in every session. It is a normal curated store (index hook +
  lazy `facts/` body), written with the engine like any altitude, and it is NOT `CLAUDE.md`, so it
  never disturbs the user's hand-written rules. This is the home for a rule useful across projects.
  (The old loose `~/.claude/rules/bitranox/` layer was converted into this store; do not recreate it.)
- **intermediate / a parent subtree** -> only `CLAUDE.md` cascades there, so an intermediate must-hold
  rule goes in that level's `CLAUDE.md` (a bounded, propose-first touch; see CLAUDE.md policy in
  `bitranox:meta-dream-project`).

Decide by **scope of applicability, NOT abstractness.** Record at the narrowest home that still covers
everywhere the lesson applies. Concrete, specific knowledge that is useful everywhere (e.g. "log into
the fleet with key X, accept host-key changes in our subnet") goes to the GLOBAL layer KEPT CONCRETE -
abstracting it would destroy its usefulness. Generalize/abstract ONLY when the specifics are so
project-bound they fit nowhere else; then lift the reusable principle up and keep the concrete instance
local. The per-level scope descriptors (the `<!-- bitranox:self-learning -->` block in each level's
`CLAUDE.md`) say what each altitude is about; when the altitude is genuinely unclear, **ask the user**.

**A universal rule can also belong in a SHIPPED skill (the shared brain) - do not stop silently at your
private layer.** The `~/.claude` curated store is machine-local: it teaches only YOU. When a captured rule
is clearly universal AND it EITHER matches a shipped skill's domain (a shell gotcha ->
`bitranox:compuse-bash`, a git gotcha -> `bitranox:compuse-git`, etc.) OR is substantial enough to
warrant a NEW skill domain of its own, ALSO surface it as a public-contribution candidate so other users
get it: enrich the existing skill, or propose a NEW skill (built with `bitranox:meta-skill-writer`, named
per the taxonomy in `skill-taxonomy.json` / `CONTRIBUTING.md`; creating a new skill is the gated path -
propose first, scaffold only on explicit permission, see step 5). **Sensitivity is NOT a disqualifier - it is
something to STRIP:** if the rule still teaches its lesson once the private specifics (paths, hosts,
secrets, org/setup details) are removed or replaced with generic placeholders, scrub them and contribute
the cleaned version; only a rule that is USELESS without those specifics stays private. Route it through
the upstream self-PR loop (see **Propagating skill improvements upstream**) as a self-contained,
provenance-free, scrubbed addition. This is OPT-IN and propose-first: publishing exposes content and is a deliberate
act, so never auto-publish - but do not let a clearly-shippable universal rule reach ONLY your private
layer without raising the option. (The dream's skill-fit pass, `bitranox:meta-dream-project` step 9, is
the batch backstop; raise it here at capture time when it is obvious.)

**Fill descriptor gaps up to the highest existing `CLAUDE.md`.** The altitude tree should be contiguous:
find the HIGHEST existing `CLAUDE.md` in the ancestor chain (search up to `/`, but never create above
it), then at EVERY level between the project and that highest one that LACKS a `CLAUDE.md`, CREATE one
holding just the marked scope-descriptor block ("what this level is about") so the classifier has a
descriptor at every altitude - do not skip a gap. `altitude_chain(proj)` returns exactly this contiguous
set (gap levels included). Creating/editing a version-controlled `CLAUDE.md` is propose-first (auto in
`auto` mode); a brand-new descriptor-only `CLAUDE.md` outside version control may be created directly.
This gap-fill stays CONSERVATIVE - it never creates a `CLAUDE.md` ABOVE the highest existing one. The
sole exception is `bitranox:meta-dream-global-deep`'s org-chart audit, which (with the cross-tree view)
may PROPOSE a brand-new top-level headquarters above the current highest rung when a truly-universal rule
has no top home - always user-gated, never automatic here.

**Normalization (reference + delta), not duplication.** When a general rule and a specific case
overlap, store the general ONCE at its altitude and have the lower entry `references [[general]]` plus
only its delta - they compose at load (the general is always-present above), never duplicated.
**References point UPWARD only**: a project entry may reference a global rule; a higher entry must NEVER
reference a lower one (deleting a project would dangle it). Verify with
`reconcile_memory_index.py --check <altitude-chain>` (upward-only, no orphans, no over-cap); the chain
comes from `self_improve_signals.altitude_chain(proj)`. The `CLAUDE.md` tiers in the ancestor chain are
altitudes in this same model (each cascades into a project's context), so a rule duplicated across them
normalizes the same way - general at the broadest covering tier, delta below; the dream skills carry the
full reconciliation cases (`bitranox:meta-dream-project` "CLAUDE.md reconciliation").

**Promotion to the global layer is gated** (it loads into EVERY session, so a wrong entry is high-blast).
A USER-stated concrete rule promotes eagerly; a model-INFERRED generalization needs corroboration (seen
across >= 2 dreams) first - `should_promote()` / `note_promotion_candidate()` in `self_improve_signals.py`,
controlled by the `promotion` config knob. Per-turn capture usually writes PER-PROJECT and lets
`bitranox:meta-dream-project` lift broadly-useful items up; do not eagerly globalize an inferred rule here.

A `CLAUDE.md` under version control is a shared artifact: **propose** the edit with a diff (see step 4).
Private memory and the machine-local `~/.claude/.claude-bx-selflearning/` store stay auto-apply. Read user
preferences (dream mode, promotion eagerness, nudges) via `self_improve_signals.load_config()` - one
machine-local config, never re-asking a decision the user already made.

### 4. Risk-classify and apply
- **Auto-apply (low risk, additive):** capturing a curated fact via the engine `add` at the project
  level (it upserts, so this covers both new and sharpened entries); appending a guardrail line to a
  CLAUDE.md that is not under version control; bumping a recurring-error count and date. Do these
  directly. The engine writes the private, gitignored curated store - additive and safe.
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

## Pathfinder discipline (leave it better)

Capturing learnings is one half of stewardship; the other is the code and files you pass through. Be a
good pathfinder:

- **Leave every file/area better than you found it.** Fix the adjacent rot you touch and can verify (a
  stale doc line, a latent bug, an AI-writing tell), not just the line you came for.
- **No technical debt.** When you spot a mistake, point it out CLEARLY; never pass it silently or wave
  it off as "works anyway" - a deferred "harmless" issue is how debt accumulates and it masks the next
  real failure.
- **Out-of-scope fixes go in their own worktree.** A fix unrelated to the current change belongs in a
  separate worktree (`bitranox:git-worktrees`), so the current change stays focused and reviewable.
  Surface, do not silently rewrite, another session's deliberate logic.
- **Clean up after yourself.** Remove temporary tooling, mounts, scratch files, and one-off scaffolding
  once the goal is met; keep only what is durable and worth reusing (and say what you kept).

## Common mistakes
- Appending a new memory file when an existing one should have been edited (bloats the index).
- Mixing the two lanes: a one-off task finding logged as a recurring-process rule, or vice versa.
- Auto-applying a rewrite or delete. Additive is auto; destructive is propose-first.
- Authoring a skill on the fly instead of suggesting it.
- Recording session state ("the build is running") as if it were a durable learning.
