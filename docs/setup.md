# Setup

This chapter answers: what happens automatically in your first session, which decisions are yours
to make, and how to shape your workspace so the layered memory files knowledge well.

## What happens on its own

The first session in a project needs no ceremony:

- The SessionStart hook scaffolds and heals the memory structure for the current knowledge tree
  (pointer blocks in `CLAUDE.local.md`, the central store at the tree top) and shows any due
  nudges (consolidation due, auto-update reminder).
- The Stop-hook gate starts watching for learning signals (a correction, a "remember this", a
  self-admitted miss) and nudges the capture skill when one appears.
- The per-prompt recall hook starts surfacing previously filed knowledge that matches what you
  are asking.

Everything below is optional tuning.

## The knobs, at a glance

All behavior choices live in one machine-local file, `~/.claude/.bitranox-memory.json`, managed
through `/bitranox:meta-memory-settings` (never hand-edited). Each has a recommended default and
is asked at most once; [reference.md](reference.md) documents every knob with values and
consequences. The ones worth a deliberate look:

- **`dream_mode`** - how much the consolidation may do on its own: `propose` (default - asks
  before it changes version-controlled files), `auto`, or `off`.
- **`discovery_roots`** - only needed when your projects live outside your home directory or
  span several filesystems: the roots the system walks to discover your knowledge trees.
- **`cross_tree_search`** - whether per-prompt recall may look into your OTHER knowledge trees
  (default yes). Set to `false` when independent trees (say, two clients) must not see each
  other's notes.

## Shape the tree like your real domains

The memory files each lesson at the level that matches its reach, so the folder shape decides how
well that works: projects that share rules belong under a common parent, because that parent is
where their shared rules live. [concepts.md](concepts.md) explains this with the
company-and-departments picture. A rough shape:

```text
workspace/                 tree top: rules for everything
  python-libs/             a department: shared Python-library rules
    lib-a/  lib-b/         projects
  client-acme/             a department: one client's work
    app-1/  app-2/
```

## Recommended: a one-paragraph stanza at the tree top

The engine manages the pointer blocks in each level's `CLAUDE.local.md` on its own. What it will
only ever PROPOSE is a short hand-written note in the tree top's `CLAUDE.md` that tells every
session what the store is and that the pinned rules bind:

```markdown
This directory is the top of the <name> knowledge tree. Durable memory lives in the
`.claude-memory/` store here, indexed by the engine-managed pointer blocks in each level's
`CLAUDE.local.md` (never hand-edit those). The entries under `## Iron rules` in the pointer
block are the binding, always-on rules for everything below - treat them as MUST.
```

## Iron rules: pin what must always hold

Most memories are ordinary: loaded, useful, and free to be merged or re-leveled by a
consolidation. A rule you never want touched or dropped - "no secrets in tracked files", "ask one
decision at a time" - can be **pinned**: it moves under the `## Iron rules` heading of its pointer
block and every consolidation leaves it alone. Say "pin that rule" when capturing one, or ask for
an existing memory to be pinned.

## Seeding a fresh project

A brand-new project starts with an empty desk, but your other projects may already know things it
needs. `/bitranox:meta-collect-knowledge` gathers topic-matched knowledge from sibling projects
and other trees into the new project - descriptor-first, so it imports what fits instead of
everything. Run it once after the first session has established what the project is about.

Next: [usage.md](usage.md) for the daily flow.
