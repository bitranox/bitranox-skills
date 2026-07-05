# Usage

This chapter answers: what the system does during a normal working day, which commands you run
when, and what its nudges mean.

## The daily flow

You mostly just work. The system runs alongside:

1. **Capture** - when a turn produces a learning (you correct Claude, state a rule, it admits a
   miss, it discovers something reusable), the Stop-hook gate nudges Claude to run
   `bitranox:meta-self-improve`. The lesson lands as ONE small fact in the current project's
   memory: a pointer line in the index plus a body in the central store. You can also trigger it
   yourself: "self-improve" or "capture what we learned".
2. **Recall** - on each prompt, a cheap keyword scan lays matching notes from your other projects
   open on the desk. Deterministic, once per note per session, no guessing.
3. **Consolidation** - every so often you let it sleep on what it collected (next section).

## The consolidation ladder

Three dreams, three scopes. Run the cheapest one that covers what changed:

| Command            | Scope                                                     | When                                                                                              |
|--------------------|-----------------------------------------------------------|---------------------------------------------------------------------------------------------------|
| `/dream-nap`       | Only the current directory's chain (project -> ancestors) | Around a context compaction, or when signals piled up mid-session. Minutes.                       |
| `/dream-tree`      | ONE whole knowledge tree, siblings included               | When the SessionStart nudge says consolidation is due, or the store feels noisy. Tens of minutes. |
| `/dream-crosstree` | Across ALL your knowledge trees                           | Occasionally, after several tree dreams, or when two trees have learned related things.           |

Each dream backs the store up first and reports what it changed. The nap is partial by design and
ends with an explicit "deferred to the full dream" list; a consolidation-due nudge is only
satisfied by `/dream-tree`. The deep variant `/dream-crosstree-deep` forces the exhaustive
cross-tree scan without the convergence shortcut - rarely needed.

Two more commands round out the set:

- `/collect-knowledge` - the inbound gather: pull topic-relevant knowledge from your other
  projects or trees into this one (also how you seed a fresh project, see [setup.md](setup.md)).
- `/memory-settings` - view or change the behavior knobs ([reference.md](reference.md)).

## Reading the memory index

Each level's `CLAUDE.local.md` carries an engine-managed pointer block: one line per fact,

```markdown
- [Keep-newest by mtime, never by name](mem:keep-newest-by-mtime) - When trimming timestamped
  files to keep newest, sort by mtime, never lexicographically by name.
```

The line IS the always-loaded part - a title and a "when ..., do ..." hook. The full body lives
one `Read` away in the tree top's `.claude-memory/facts/` store, and the block tells Claude how to
fetch it mid-task. Lines under `## Iron rules` are pinned: binding, never touched by a
consolidation. Do not hand-edit pointer blocks or the store - a guard blocks stray writes; the
engine is the only write path.

## The nudges, decoded

- **"A memory consolidation is due"** (session start) - run `/dream-tree`, or say "skip". Silence
  these with the `nudges` knob.
- **A capture nudge after your turn** (Stop gate) - the turn contained a learning signal; let
  `meta-self-improve` file it, or say there is nothing durable.
- **After a context compaction** (PostCompact) - details from the compacted conversation are at
  risk; a `/dream-nap` folds the salvaged learnings in while they are warm.
- **A skill suggestion under your prompt** (router) - your prompt matched a skill's triggers;
  Claude is reminded the skill exists. At most two skills, once per session.

## A worked example

You correct Claude mid-review: "never sort backup dirs by filename, sort by mtime". The Stop gate
notices the correction and nudges; `meta-self-improve` dedups against the existing index, then
files one fact at the project level with a trigger-first hook ("When trimming timestamped
files..."). Weeks later, a session in a SIBLING project asks about pruning old snapshots - recall
surfaces the note on the first prompt. The next `/dream-tree` notices the rule held in two
projects and lifts it to their common parent, so from then on it is always loaded for the whole
department - one fact, filed once, available exactly where it applies.
