# Top index cost side and topic placement - design

Date: 2026-11-09. Status: design approved section by section; no implementation yet.

## Problem

The tree top's pointer block is read by every session in the knowledge tree, because Claude Code
loads the whole ancestor chain of `CLAUDE.local.md` files. On the maintainer's tree it grew about
8.5x in fifteen weeks, and most of that growth was relocation, not new knowledge: in the latest
day of growth, 159 of 163 pointers that arrived at the top were existing facts moved up by a
dream, and over the whole history moves up outnumbered moves down by about 35 to 1.

The dream follows its rules. The rules have no cost side:

- "If a pass would grow the store, it is wrong" counts facts. A move to the top keeps the fact
  count and makes every session in the tree read the pointer.
- The corroboration gate guards promotion; a move filed as a MISPLACEMENT repair has no gate, and
  the "could this rule fire elsewhere" test passes for nearly every lesson.
- The meta-dream-tree step that forbids rewriting a hook merely for exceeding the soft cap
  contradicts the passes note that size is met by representation.
- `reconcile_memory_index.py`'s large-index warning tells the reader to "let the dream
  lift/dedup/promote", which itself pushes facts up.

Joining near-duplicate rules saves under a tenth of the top block: a lexical scan found no pair
above 0.45, and semantic reviewers kept most candidate groups apart for naming a case the other
does not cover.

## Phase 1: cost report and compaction

**Cost report.** Every dream and nap prints the top block's bytes and pointer count before and
after, and how many pointers moved up and down. A move to the top names its cost in the report.
Until phase 2 lands, no new gate is added; the report makes the cost visible.

**Compaction**, applied through the engine:

- the merges, moves off the top and hook trims the semantic review proved safe;
- dropping the title from pointer lines (the slug stays the link);
- hooks shortened towards about 300 characters.

The last two change what a session sees mid-work, because the hook is the only part of a fact in
context then. They ship only if the firing test passes.

**Firing test.** Headless `claude -p --model opus` sessions in a throwaway directory with their own
config and no plugins; the arm's index is that directory's `CLAUDE.local.md`. About 24 candidate
rules are screened without any index, and the 12 that discriminate (the model does the wrong thing
without the rule) are kept; a rule that does not fire in the today arm is reported as no signal.
Four arms: today, no titles, hooks at 300, both. Arms are interleaved, 3 runs per rule per arm,
and the model is asserted from each run's init record. The hooks-at-300 arm needs every long hook
rewritten in a scratch copy.

**Pass rule.** An arm passes when it fires at most 2 runs fewer than today (out of 36) and no rule
falls from at least 2 of 3 to 0 of 3. Passing arms ship. If neither change passes, only the joins,
moves and the cost report ship. The input-token estimate is about 9.6 million; the price is
unmeasured.

## Phase 2: placement by topic

A rule reaches only the directories it is about: its pointer goes as far up as the directories
below have something in common. With `/a/python/x1`, `/a/python/x2`, `/b/python/y1` and
`/b/python/y2`, python rules get a pointer in `/a/python` and `/b/python`, and `/c/rust` or
`/d/machines` never read them. Parents are read in too, so a pointer is never repeated below an
ancestor that holds it.

**Data.** A fact's body gains a `topics:` list in its frontmatter; an empty list means universal.
A directory's descriptor gains a `TOPICS:` line. Both are written through the engine.

**Topic list.** Open tags, then clusters: opus subagents propose free tags from the hooks of every
fact at an inner level, the tags are merged into one list, and the user reviews it. The list is
then closed; a new kind of project leads the dream to propose a list change.

**Assignment.** TypeSafe Jev picks topics from the list for every fact (one batched request each)
and for every directory from its own descriptor, which the dream's template already defines as
true for the whole subtree. A container directory with two stacks gets both. Descriptors are
checked against what really sits below them first, because a wrong descriptor misplaces every rule
of its topic.

**Generation.** The engine renders pointers: a topic-bound fact gets a pointer at each directory
that has its topic and no ancestor with it. When every child of a directory has a topic, the
pointer rolls up to that directory instead of one copy per child. Untagged facts, and facts whose
topic no directory declares, stay at the top. Only rendered lines may share a slug, and
`reconcile` checks that the rendered pointers equal a fresh computation, so copies cannot drift.

**Scope.** Only facts that would otherwise sit at an inner level take part. A fact captured at its
own project stays there. The dream stops moving facts up and instead tags and re-renders.

**Nap.** A nap checks the current directory: it writes the descriptor if there is none, has Jev
re-tag it when it has no topics or its descriptor changed since the last tagging, renders the
chain's pointers skipping every pointer a parent holds, and drops rendered copies in its chain that
an ancestor now holds. It never writes a sibling: each sibling's own nap cleans it, and the full
dream sweeps what no nap reached. A new project therefore gets its rules at its first nap.

**Safeguards.**

- A fact that would end up with no pointer falls back to the top; no rule becomes unreachable.
- A wrong tag can still be found by keyword recall.
- Pinned facts stay where they are.
- The top's descriptor decides what every session loads, so a change to its topics is never
  applied by a nap or dream: it is proposed to the user.

## Migration of the existing top pointers

Runs after phase 1 has shipped and passed its firing test.

1. Build the topic list (open tags, clusters, user review).
2. Check every descriptor against what sits below it, and fix the wrong ones.
3. Jev pilot: about 60 facts labelled by hand plus a planted control, against an agreement
   threshold fixed before Jev's answers are read. A logged dream-placement shadow agreed with the
   dream agent on only 58% of rows, so the pilot is not optional. If Jev misses, opus tags
   instead, at the cost the pilot measured.
4. Tag every fact and directory through the engine.
5. Render into a scratch copy of the tree and report, per directory, the size before and after,
   which rules moved where, and which stayed at the top. The user sees this before anything is
   applied.
6. Run the generated index as its own firing-test arm, under the phase 1 pass rule.
7. Apply in one dream run with a backup and manifest first and `reconcile --check-tree` after;
   restoring the backup undoes it. One run rather than gradually, so the cost report and
   reconcile never have to understand both systems at once.

## Expected effect

A keyword-based estimate, which is optimistic because nearly every session also uses git, ssh
and subagents: a session in a repository that touches most topics keeps about 89% of today's top
block, a single-stack library about 65%, an infrastructure repository about 61%, and a directory
with none of the bound topics about 49%. Phase 1 compaction comes on top and helps every session.

## Not chosen

- Judging every rule against every directory: about 236,000 pairs and a judge that agreed 58% of
  the time.
- One pointer per rule lifted only to the common parent: rules shared by `/a/python` and
  `/b/python` would still reach `/c/rust`.
- Delivering command-tied rules from a PreToolUse hook: covers only rules tied to a command,
  arrives after planning, and is unprobed on the current Claude Code version.
- A curated topic list: the user chose open tags with clustering.
- Retiring pointers whose skill holds the detail: none passed the check that the trigger is
  reachable only through that skill.
