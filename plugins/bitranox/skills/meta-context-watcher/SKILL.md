---
name: meta-context-watcher
description: Use when a session's context is large enough that quality is degrading or compaction is close, when a Stop nudge reports the handover threshold was crossed, or on "write a handover", "hand this over", "context is getting full", or "let's start a fresh session"
---

# Write the handover, then start clean

A long session gets worse before it gets full. Accuracy falls from roughly 300-400k tokens on a 1M
window and from about 50k on a 200k one, while Claude Code does not auto-compact until around 83% -
and compaction DISCARDS working detail rather than preserving it. Between those two points is where
a session should be handed over deliberately instead of truncated.

## The one rule

**Write only what the next session cannot re-derive.**

It inherits the repository, the git history, the CLAUDE.md cascade and the memory store. Only one
thing dies with this session: what you were part-way through, and why you chose it.

## What belongs in it

- **In flight** - what is part-done, how far it got, and what state it is in right now.
- **Committed, or not** - uncommitted work can vanish; the reader cannot guess which they got.
- **Decided, and why** - choices a reader would otherwise reopen, with the reason that settled them.
- **Deliberately not done** - so it is not mistaken for an oversight and redone.
- **The exact next action** - the command or edit to start with, not a direction of travel.
- **Files that matter** - repo-relative PATHS, not bare filenames; inferring them is the work
  this file exists to save.
- **How to verify** - the commands that prove the work still stands.

## What does NOT belong

| Excuse for including it              | Why it is wrong                                                            |
|--------------------------------------|----------------------------------------------------------------------------|
| "The conventions are important"      | CLAUDE.md loads automatically. Restating it wastes the handover.           |
| "Recent commits give context"        | `git log` re-derives that in one command. Say what is UNCOMMITTED.         |
| "Explain how this file was produced" | Provenance is narrative. The reader needs state, not a session story.      |
| "Include the lessons we learned"     | Durable learnings go to the memory store via `bitranox:meta-self-improve`. |
| "Summarise everything, to be safe"   | A handover nobody finishes reading is a handover that failed.              |

## Procedure

1. **Capture learnings first** with `bitranox:meta-self-improve`, so durable facts reach the store
   rather than dying in a file that is about to be superseded.
2. **Write `handover.md` at the repo root, OVERWRITING whatever is there.** A stale handover from an
   earlier session is superseded the moment you write yours - replace it wholesale, never append to
   it and never keep both. There is exactly one `handover.md`, and it describes one moment; two of
   them, or one with two moments in it, leaves the reader deciding which half is true. It is session
   scaffolding, so it MUST be gitignored - add it if it is not, the same way
   `EXECUTION-USER-REVIEW.md` is.
3. **End the file with its own expiry instruction:**

   > Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not
   > delete it - if this session ends badly it is the only record of where things stood.

4. **Re-read it as the next session.** Any line the repo could have told them is a line to cut.
5. **Tell the user to type `/clear`.** You cannot run it - built-in slash commands are not invocable
   by the model - so say so plainly rather than implying the session clears itself.

## When you are the one READING a handover

Absorb it, then **mark it STALE in place**. Both alternatives fail: left untouched, the session
after next reads a passed moment as current; deleted, the record is gone the instant it is read, so
a crash mid-task leaves nothing saying where the work stood.

Never amend a stale handover to update it - write a NEW one and replace the file. An edited handover
holds two moments with no way to tell them apart.

## When it fires on its own

A `Stop` hook measures context from the transcript's last recorded usage - the real per-request
figure, not an estimate - and blocks when it crosses
`min(context_handover_pct` of the window, `context_handover_cap)`.

The window is detected from the model this project has used, so nothing needs configuring. Declining
is not permanent: the next ask waits until context has grown another tenth of the window, because a
decline at 40% is "not yet" while 90% is a different question.

If it ever reports measuring MORE context than the window, the detection failed - set
`context_window` explicitly via `bitranox:meta-memory-settings`. That is reported rather than
ignored because a threshold nothing can reach looks exactly like a watcher that works.

## Not the same as its neighbours

- `bitranox:meta-dream-nap` - consolidates MEMORY after a compaction; it prunes task state as noise.
- `bitranox:meta-dream-tree` - the periodic store consolidation, which also ends by nudging `/clear`.
- `bitranox:meta-self-improve` - durable facts. Run it BEFORE the handover, not instead of it.

This skill is the only one that preserves TASK state, and it runs BEFORE the wall, not after.
