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
file/flag, a resolved issue, superseded by a newer entry, leaked task-state, or a version-bound
lesson a newer release made history - a fixed bug, a finished migration, a test result on that
version - found by `versionrot.py` and confirmed by a re-check against the current release, while
a version-bound claim the re-check finds still true is REWORDED, not archived), via
`reconcile_memory_index.py --archive <slug> <level>` (home:
`<plugin>/skills/meta-self-improve/`, launch through `hooks/run-python.sh`; it archives the body only
when NO level still points at the slug). Launch it as a real script file, never a heredoc piped into
`run-python.sh` (a `-` stdin arg fails with `run-python.sh: script not found: -` and exit 2). (3) a manual "forget this".
Never archive a still-valid but quiet note. Size pressure is met by representation, never by
deletion: a fact's always-present cost is one short index line, kept lean by dedup, and its body
costs nothing until read. The same policy binds outside a dream: a "prune memory" request removes
only by the three routes above, and a change to the memory engine adds no decay, idle counter or
usage metric.

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

Prove "already covered" with a quote from SHIPPED skill text only - a `SKILL.md`, a reference
file, a script's help. Exclude `*/.skillwriter/*`: those review checklists repeat rule text while
testing it, so a quote from one makes a rule look shipped that no skill states
(`meta-skill-audit`'s `audit_skills.py` excludes them the same way). Search with
`grep -rn --exclude-dir=.skillwriter`.

**When a fold MOVES a fact's content into a skill** (a fold campaign, often run outside any dream,
that writes the content into SKILL.md or a reference file and then cuts the fact's hook or archives
the fact - distinct from this pass's keep-the-trigger default), treat every behaviour claim, flag or
API name and number in the body as unverified: far more sessions trust the skill than the fact.

- Diff each body against the version the classification read: bodies change between planning and
  folding. Measured: about one body in four held a claim that was false by fold time when the batch
  had been classified days earlier. Hand the fold editor the adversarial reviewer's amended text
  plus a re-verify step, never the first classifier's hint.
- Re-check each claim against the current source or by running it (`--help`, a probe, the live
  config), and give verifiers MEASURE items, not only quote-back. Re-check the names a rule cites,
  not only the rule: a rule can still hold while the flags it names have moved. Read the target
  skill's own measurements before carrying a duration or size, and never carry a value that varies
  per machine or config: name the axis and how to read the live value.
- Search the local `~/.claude/commands` and `~/.claude/skills` for related detail (a local command
  file can hold what the fact got wrong), and list the shipped compuse-toolbox scripts before calling
  any tool machine-local.
- After the fold, quote-check each quoted sentence as a substring of the INSTALLED plugin text, read
  after the user has run `/plugin marketplace update` and `/reload-plugins`; a verify record from an
  earlier round is not evidence for the final text.
- If the pointer is kept, correct in the same pass any claim the fold refuted in its body, and in
  its hook if the hook states it.
- Before archiving a fact, run `ref_map.py --root <anchor> <slug>` (home:
  `<plugin>/skills/meta-self-improve/`, launch via `hooks/run-python.sh`) for inbound `[[refs]]`
  and plain-prose mentions inside the store. `--archive` of the LAST pointer refuses on its own
  (exit 1, nothing written) while a fact links or names the slug or a level's `CLAUDE.md` names it,
  and lists them; `--force` archives anyway. Neither looks outside the store and the level
  `CLAUDE.md` files, so still grep every other doc and skill file for the bare slug and for any
  heading the rule sat under before the fold.
  Re-point each hit to the skill. For many slugs, sweep in ONE `grep -F -f <patterns-file>` pass
  that excludes vendored trees (`.venv`, build `target/`, large source checkouts). Measured: a
  per-slug walk of a large tree ran past 5 minutes.

## Filler-word classification (keeps recall precise) - PER PROJECT

The per-prompt recall hook is model-free: it queues any not-yet-classified keyword for THIS
project (`load_pending_keywords(proj)`). If the queue is non-empty, hand it to an `opus` subagent
to classify each word as **filler** (no topical signal: "again", "previous") or **topical** (a
real term: "bindsnap"). Apply per-project: `add_filler_words(filler, proj)`,
`add_topical_words(topical, proj)`, `clear_pending_keywords(proj)`, in that order: the two adds
raise `StateWriteError` when a list cannot be read or written, and clearing the queue after a
failed add would lose the classification, so stop and report instead. The learned filler list, the
topical list and the pending queue are all PER-PROJECT, keyed by `proj_key(proj)`, because a word
can be noise in one project and the subject of another: `compression` classed as filler in a docs
project would otherwise drop out of every prompt in a codec project. Only universal generic-English
filler belongs in the shipped, global baseline (`hooks/filler_words.json`), via PR, and a change to
where these lists are stored keeps that split. Be conservative: unsure -> topical. Empty queue ->
no-op.

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
SKILL (Skill tool); the skill name is not a command. Its own `audit_local.py` (home:
`<plugin>/skills/meta-audit-local-skills-and-hooks/scripts/`, launch via `hooks/run-python.sh`)
takes a SUBCOMMAND first: `audit_local.py check --root <anchor> --no-personal` (the tree's top
dir) runs the checks
(`targets` with the same flags only lists the dirs); `--root` without one is refused by argparse
with exit 2. Follow that
skill for the procedure, above all its refusal to edit a dir some plugin owns; do not restate the
rule here and do not re-derive the target list with a `find`, which is how a tool repo's mirrored
twin gets edited. Findings follow this project's dream mode. No `.claude/skills` in the tree -> no-op.

## Durability: keep each store locally git-tracked (auto, machine-local)

Every dream, ensure the anchor's `.claude-memory/` is version-controlled by a LOCAL git repo
(store-own-repo: `git init` inside `.claude-memory/`; ephemeral `state/` + `*.lock` gitignored),
then commit the dream's changes. Local first: the dream never creates a remote and never pushes on
its own. A PRIVATE off-site backup remote the user created may be configured on the store repo;
pushing to it stays a deliberate act, and the one push this file describes (the force-push in step
4 of "Bound history growth") runs only inside a squash the user approved. A private project with
`track_private` on tracks the store in the project's own repo instead. Public project / non-git:
the store-own-repo keeps private memory out of any public push. Safe machine-local move ->
auto-apply even in `propose` mode.

When a store lives directly under `~/.claude`, track it with ONE repo AT `~/.claude` behind a
WHITELIST `.gitignore`: `/*`, then `!/.gitignore`, `!/CLAUDE.md`, `!/<store-dir>/`, plus
`<store-dir>/state/` and `<store-dir>/*.lock`. Never blanket-track `~/.claude` (session
transcripts, `file-history/`, backups and nested plugin git repos under `plugins/cache/`), and
before the first commit run `git add -A -n` and require that nothing outside those paths appears.

A NEW remote is propose-first even when one already exists: the store holds no single sensitive
fact, but the assembled set (subnets, host addresses, credential file paths) is an infrastructure
map. Scan for literal credentials (assigned password/token/key values, PEM blocks, long base64
blobs) against a positive control, and verify the remote's privacy from the hosting API after
creation, not from the creation dialog.

## Bound history growth (squash, count-gated)

When a store repo exceeds ~50 commits (`git rev-list --count HEAD`), squash to a single fresh
snapshot commit. Memory values current state, not history. Safe for these LOCAL repos and a
personal private backup remote; NEVER squash/force-push a shared or published repo (marketplace
append-only rule). The count gate is not authority on its own: squash only in a quiet window (no
peer session writing the store, no store file written for about 15 minutes, no `.git/index.lock`,
HEAD already on the remote), and propose it first.

Squash by compare-and-swap, never an orphan branch (`checkout --orphan; add -A; commit;
branch -m` is not atomic against a peer's commit, and its `add -A` sweeps a peer's UNCOMMITTED
edits into your snapshot):

1. `git bundle create <backup-outside-the-repo> --all`, then prove it by cloning it back: the
   bundled branch's commit count and tree must match the repo's.
2. `new=$(git commit-tree <old>^{tree} -F <msgfile>)` builds the single root from HEAD's tree
   without touching the index or working tree.
3. `git update-ref refs/heads/<branch> "$new" <old>` swaps it in only if the branch still points
   at `<old>`, so a racing peer commit is refused rather than lost.
4. A backup remote needs `git push --force-with-lease=<branch>:<old>`, run only on the user's go for
   this squash (or left for the user to run); if it refuses,
   `git update-ref refs/heads/<branch> <old> "$new"` puts the branch back. The bundle and the
   reflog are the revert paths. Confirm `git status --porcelain` is unchanged before and after.

## Off-machine backup reminder (time-gated)

When `backup_reminder_due()` is true (> ~30 days), REMIND the user to push the store repo(s) to a
PRIVATE remote against disk failure. Propose-first: the user creates/approves the remote and
pushes; never auto-create or push. Then `mark_backup_reminded()`. Not due -> no-op.
