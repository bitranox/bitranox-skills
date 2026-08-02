# Behavioral passes (the full catalog)

Each pass has its OWN trigger; read a no-op off THAT trigger, never off an unrelated signal. Two
kinds: **counter-gated** passes (filler queue, model review, backup reminder, promotion dwell)
carry out-of-store counters, so a no-change dream stays a no-op; **chain-gated** passes (CLAUDE.md
reconciliation, dedup, placement) are triggered by the ancestor CLAUDE.md CHAIN plus the entries
this dream just wrote, so they run EVERY dream - a just-seeded store is exactly when new overlap
appears. An empty or unchanged store makes only the counter-gated passes no-op.

## Removal = obsolete-pruning + manual (NO usage/age/size decay)

There is no automatic forgetting: usage cannot be measured (a note sits in context; reasoning is
silent, so absence of a signal does NOT mean unused), and age and detail/size are not valid forget
metrics. Detail belongs in the pulled body - near-free, never a delete reason. The ONLY removals,
all content-based and propose-first (the backup makes them safe): (1) dedup/merge duplicates;
(2) obsolete/superseded pruning - archive a note ONLY if its CONTENT is dead (references a deleted
file/flag, a resolved issue, superseded by a newer entry, leaked task-state), via
`reconcile_memory_index.py --archive <slug> <level>` (home:
`<plugin>/skills/meta-self-improve/`, launch through `hooks/run-python.sh`; it archives the body only
when NO level still points at the slug). Launch it as a real script file, never a heredoc piped into
`run-python.sh` (a `-` stdin arg fails with `gate script not found: -`). (3) a manual "forget this".
Never archive a still-valid but quiet note.
(See `forgetting-is-usage-based-only`.)

## Contradiction / override

When memory contradicts a hand-written `CLAUDE.md` rule, GROUND TRUTH decides - not the channel.
A CLAUDE.md can be outdated just like a memory can be wrong. Verify against the actual state (the
code, files, system, measurements, git history): if the evidence shows MEMORY is wrong, correct
the memory (engine); if it shows the CLAUDE.md is OUTDATED, propose the CLAUDE.md fix
(backed up and reported, as every CLAUDE.md edit); if ground truth cannot be established, ASK the user -
never silently prefer either side. Memory-vs-memory: a narrower rule that CONTRADICTS a higher one
becomes a self-contained OVERRIDE (more-specific wins at load), NOT a `[[reference]]`; flag a
persistent contradiction for the user.

## CLAUDE.md reconciliation (tiers ARE altitudes; reconcile to save context)

Every `CLAUDE.md` in this project's ancestor chain cascades into its context, so the chain + the
store form ONE altitude lattice; apply the same reference+delta normalization, with "reduce total
always-loaded context" as the decision rule. Back up a `CLAUDE.md` only BEFORE an actual edit.
Reconcile in BOTH directions and RULE-BY-RULE: (1) each just-written entry against the chain, AND
(2) - the direction that is easy to skip - EACH rule/section of EVERY CLAUDE.md in the chain
against the WHOLE store (tree-top store + same-scope memory + any enforcing hook or covering
skill), which finds PRE-EXISTING CLAUDE.md<->store duplication independent of what this dream
wrote. Do NOT approximate the pass by grepping only the newly-written entries' keywords - that
checks direction (1) only and misses every overlap that predates the dream (the exact shortcut
that has slipped this pass more than once). Report a PER-RULE verdict (covered -> declutter /
belongs-higher / only-here / contradiction), never a blanket "nothing to apply"; "nothing" is
valid ONLY as a VERIFIED result (chain walked, N files, every rule cross-checked), never assumed
from emptiness or a new-entry-only grep. For a rule found in the chain:

- **Already covered by a broader always-present home** (memory at the same scope, the tree's top,
  or a broader ancestor `CLAUDE.md` that already cascades here) -> propose DELETING the lower
  duplicate. Flag-only is the fallback ONLY when no broader covering home exists.
  - **ENHANCE-BEFORE-DELETE (unconditional precondition).** "Covered" is usually PARTIAL - the
    `CLAUDE.md` rule often carries an example, a why, or a nuance the memory hook lacks. Never
    delete on topic-overlap alone: READ both, FOLD every unique detail from the `CLAUDE.md` rule
    INTO the surviving memory entry (via the engine), VERIFY the survivor fully subsumes it, only
    THEN propose the deletion.
  - **Git tracking is NOT a condition here.** Whether the source or the covering home is tracked,
    gitignored, or outside a repo has no bearing on the trim: gitignore is irrelevant to LOADING
    (verified - a gitignored file is still read in a trusted workspace), and the store's own
    durability is the Durability pass's job, not a gate on this one. Judge only by the
    reachability invariant below.
  - **Coverage can also be a HOOK or a SKILL.** A hook enforces automatically but is
    BOUNDARY-LIMITED (fires only at its trigger, only where the plugin is installed); judge
    "covered" against the UNION of {hook enforcement + skill + always-loaded memory} and keep the
    prose layer for what the hook/skill cannot reach. Fold unique detail into the surviving tier
    before deleting.
- **Belongs higher** (recurs across the subtree) -> lift the general to the broadest covering
  tier, leave only the DELTA below (`[[general]]` + delta), or remove it if there is no delta.
- **Genuinely only-here** -> leave it (it IS the delta). **Contradiction** -> verify against
  ground truth (see Contradiction / override above): evidence decides which side is outdated;
  unresolvable -> ask the user.
- Guards: never LIFT a narrow rule into a tier that loads where it is irrelevant (net context
  loss); never demote a must-always directive into a lazy body; never remove a rule whose covering
  home fails the reachability invariant below. Back up first (every CLAUDE.md edit is reversible),
  then apply, and REPORT every file touched.

### The reachability invariant (the ONLY test for removing a rule)

> Remove a rule from a `CLAUDE.md` only when a covering rule lives at an ANCESTOR DIRECTORY of that
> file and is delivered as ALWAYS-LOADED TEXT. Otherwise rewrite in place (deduplicate, shorten,
> merge) and KEEP the rule where it is.

Ancestor `CLAUDE.md` and `CLAUDE.local.md` text loads into every session started at or below that
directory, via the native cascade. Three ways a trim still loses a rule:

- **A SIBLING or CHILD is not a covering home.** It never loads where the trimmed file loaded,
  however adjacent it looks. Test it as path arithmetic: the covering home's directory must be an
  ancestor-or-self of the trimmed file's directory. Two projects sharing a rule means it belongs at
  their COMMON ANCESTOR, not in whichever of the two you kept.
- **A `mem:` pointer covers only as far as its HOOK.** Folding a rule into a memory fact is
  legitimate, but only the trigger-first hook line in the ancestor's pointer block is always in
  context; the body is read on demand. If the rule must fire unprompted, the hook has to carry the
  trigger - which ENHANCE-BEFORE-DELETE above already requires.
- **An ancestor's `@import` whose target sits ABOVE the workspace root is silently skipped** (only
  the raw `@...` line travels as text). Prefer the ancestor's own TEXT as the covering home.

Git plays no part in this decision: not tracked-vs-ignored, not the remote, not who could clone it.
Those affect whether an edit needs a commit, never whether a rule reaches context.

## Point a rule at its skill or HOOK; do not restate it

Check each rule fact for a bitranox SKILL or HOOK that already covers/ENFORCES its topic
(sanitization -> `coding-input-sanitization`, resilience -> `coding-resilience`, tells ->
`write-humanize-en`/`-de` + the `tell-sweep` hook, shell traps -> `compuse-bash`, remote
PowerShell -> `compuse-ssh`, pgrep self-match -> the `block-pgrep-self-match` hook). A hook is the
strongest coverage but boundary-limited. When covered, keep the always-loaded index hook as the
trigger and make the BODY a concise pointer (`Detail: bitranox:<skill>` / `enforced by the <hook>
hook`) instead of restating content. The dream does not delete such a rule - the always-on trigger
is its value.

## Filler-word classification (keeps recall precise) - PER PROJECT

The per-prompt recall hook is model-free: it queues any not-yet-classified keyword for THIS
project (`load_pending_keywords(proj)`). If the queue is non-empty, hand it to a `sonnet` subagent
to classify each word as **filler** (no topical signal: "again", "previous") or **topical** (a
real term: "bindsnap"). Apply per-project: `add_filler_words(filler, proj)`,
`add_topical_words(topical, proj)`, `clear_pending_keywords(proj)`. Learned lists are PER-PROJECT
(a word can be noise here, a topic there; see `recall-filler-per-project`); only universal
generic-English filler belongs in the shipped baseline, via PR. Be conservative: unsure ->
topical. Empty queue -> no-op.

## Model-hierarchy review (time-gated)

When `model_review_due()` is true (> ~30 days), ask the `claude-code-guide` agent for the current
model lineup and compare to "Concrete tiers" in
`bitranox:process-agents-subagent-driven-development`. On a shift, PROPOSE a re-tier of that one
mapping via the upstream loop. Then `mark_model_reviewed()`. Not due -> no-op.

## Skill-gap review (propose-first, fuzzy)

Look for a bug/correction/rework that landed WHILE a bitranox skill plausibly governed that area.
Treat it as a candidate coverage gap: propose a skill update (pattern, checklist item, or test)
via the upstream loop - never only local memory, never auto-edit. This is the deliberate home for
`flag-a-skill-when-a-real-bug-slips-past-it` (the deterministic hooks cannot judge "did the skill
have a gap?"). Nothing correlating -> no-op.

## Gate-coverage audit (model-driven complement to the regex audit)

The SessionEnd audit is a hook and shares the regex gate's blind spots. On dreaming you HAVE the
model: semantically re-read the transcript tail for real corrections/discoveries that did not fire
the gate. Handle BOTH halves: first capture the missed LEARNING (the content is the point), then,
for a recurring phrasing gap, propose broadening the family patterns in `self_improve_signals.py`
(role-split strict sets + BROAD audit nets, with a regression test; never concatenate the
role-split sets) via the upstream loop. Nothing slipped -> no-op.

## Local skill/hook audit - the PROJECT half (per tree)

A tree's own `.claude/skills` is shipped by no plugin, so not one marketplace gate reaches it: a
description the router cannot derive a trigger from, a script with no test, a `tests/` dir that
exists but does not collect, all survive indefinitely. Run
`bitranox:meta-audit-local-skills-and-hooks` over THIS tree with `--no-personal` - the personal
`~/.claude` half is machine-global and belongs to the deep crosstree dream, not here. Invoke the
SKILL (Skill tool); the skill name is not a command, and its own `audit_local.py` is what takes
`--root <tree> --no-personal`. Follow that
skill for the procedure, above all its refusal to edit a dir some plugin owns; do not restate the
rule here and do not re-derive the target list with a `find`, which is how a tool repo's mirrored
twin gets edited. Findings follow this project's dream mode. No `.claude/skills` in the tree -> no-op.

## Durability: keep each store locally git-tracked (auto, machine-local)

Every dream, ensure the anchor's `.claude-memory/` is version-controlled by a LOCAL git repo
(store-own-repo: `git init` inside `.claude-memory/`; ephemeral `state/` + `*.lock` gitignored),
then commit the dream's changes. LOCAL-ONLY, never a remote. A private project with
`track_private` on tracks the store in the project's own repo instead. Public project / non-git:
the store-own-repo keeps private memory out of any public push. Safe machine-local move ->
auto-apply even in `propose` mode.

## Bound history growth (squash, count-gated)

When a store repo exceeds ~50 commits (`git rev-list --count HEAD`), squash to a single fresh
snapshot commit (orphan branch, re-add, replace). Memory values current state, not history. Safe
for these LOCAL repos; NEVER squash/force-push a shared or published repo (marketplace append-only
rule).

## Off-machine backup reminder (time-gated)

When `backup_reminder_due()` is true (> ~30 days), REMIND the user to push the store repo(s) to a
PRIVATE remote against disk failure. Propose-first: the user creates/approves the remote and
pushes; never auto-create or push. Then `mark_backup_reminded()`. Not due -> no-op.
