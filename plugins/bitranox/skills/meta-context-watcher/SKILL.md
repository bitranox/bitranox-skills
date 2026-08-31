---
name: meta-context-watcher
description: Use when a session's context is large enough that quality is degrading or compaction is close, when a Stop nudge reports the handover threshold was crossed, or on "write a handover", "hand this over", "context is getting full", or "let's start a fresh session". Also use when unfinished work or an unmet user request must outlive the session and belongs in the standing backlog OPEN-WORK.md, when open items keep sinking under whatever was worked on last, or on "add this to the backlog", "what is still open"
---

# Write the handover, then start clean

A long session gets worse before it gets full. Accuracy falls from roughly 300-400k tokens on a 1M
window and from about 50k on a 200k one, while Claude Code does not auto-compact until around 83% -
and compaction DISCARDS working detail rather than preserving it.

Both numbers are dated, and neither is measured here. The accuracy figures are Chroma's 2025
context-rot study, read second-hand from a summary rather than from the paper; the 83% is Claude
Code product behaviour that can move in any release. Treat them as the order of magnitude that
justifies handing over early, never as thresholds to tune against - and re-check both before
quoting either as current. Between those two points is where
a session should be handed over deliberately instead of truncated.

## The one rule

**Write only what the next session cannot re-derive.**

It inherits the repository, the git history, the CLAUDE.md cascade and the memory store. Only one
thing dies with this session: what you were part-way through, and why you chose it.

## Two files, because they have opposite lifetimes

`handover.md` describes ONE MOMENT and is replaced wholesale every time. `OPEN-WORK.md` is the
STANDING BACKLOG and is only ever edited line by line.

Keeping both in one file is what made the backlog rot. A handover is rewritten from what the
writing session has in mind, so every item is re-encoded from memory once per session, and it is
re-encoded in proportion to how recently it was TOUCHED. The item nobody worked loses one
attribute per rewrite: first its method, then its count, then its own heading, until it is a
clause in a sentence. Measured over one day in this repo, five tracked items - an 88-target audit
the user had asked for, a reviewer pass, 206 unframed bodies, 57 flagged candidates, 5 queued
contributions - went from named bullets with counts to absent, with no line saying any of them had
been closed.

| Goes in `handover.md`                        | Goes in `OPEN-WORK.md`                          |
|----------------------------------------------|-------------------------------------------------|
| what is part-done RIGHT NOW, and its state   | anything not finished that outlives the session |
| what is uncommitted                          | anything the user asked for and has not got     |
| decisions this session took, with the reason | work that is blocked, and on whom               |
| the one next action                          | the ranked list that next action is drawn from  |

`OPEN-WORK.md` sits at the repo root, tracked, one item per line:

```
- [ ] (YYYY-MM-DD) [rank] ORIGIN: what it is | size: how much is left | open: why | next: the action
```

The date is when it was FIRST raised and never changes. `ORIGIN` is `USER:` (their own words where
they gave any) or `FOUND:`. `size` is how much is left; it is the field that disappears first when
a list is retyped, and it breaks ties within an origin, so it is not optional. It is NOT the first
ranking key - see below, where reading it as one is a named failure. Closing an item is `- [x]` plus
`| closed: <reason>`; the line stays. A SessionStart hook prints the top ranks with their age.

**Rank in TENS** - 10, 20, 30. An insertion is then a new number instead of a renumbering of
every line below it, which keeps a reorder out of the diff of an unrelated change.

**How rank is decided, in this order:**

1. A `USER:` item outranks every `FOUND:` item. Someone is waiting on the first kind and nobody is
   waiting on the second, and no count changes that. Size is a tiebreak, never the first key: read
   the other way round, a big internal sweep displaces the thing the user actually asked for, which
   is the failure in a new costume.
2. A `USER:` item the USER has deferred sits below the live `USER:` items and still above every
   `FOUND:` one. They asked for it and put it off; they did not stop wanting it. Record who
   deferred it and when in the `open:` field, because a deferral with no owner reads as your
   judgement a week later.
3. Among items of the same origin, the bigger `size` goes first. A big item is the one that never
   fits into a spare moment, so it is the one that starves. An item whose size is unknown sorts
   after the sized ones of its origin, and sizing it is then its own next action.
4. Blocked keeps its rank. Being blocked on the user is a reason to go and ask, not a demotion.
   Blocked is a value for `open:`, never a third `ORIGIN` - there are two origins and inventing a
   third puts the item in a category nothing sorts.

**Never infer a date you do not have.** When the source does not say when an item was first
raised, write TODAY's date with a question mark - `(2026-08-31?)` - or the bare word
`(unknown)`, and say `first seen here` in the `open:` field. Both parse, and an undated item
sorts last within its rank because it makes no age claim. An estimated date is worse than an admitted unknown: age is the entire signal
that makes a long-carried item conspicuous, and a plausible guess silently resets it. The same
goes for `size`: `size: unknown` is a usable line, an invented count is not.

## What belongs in it

- **In flight** - what is part-done, how far it got, and what state it is in right now.
- **Committed, or not** - uncommitted work can vanish; the reader cannot guess which they got.
- **Decided, and why** - choices a reader would otherwise reopen, with the reason that settled them.
- **Decided against, and why** - so it is not mistaken for an oversight and redone.
- **Still open, untouched** - ONE LINE each, pointing at `OPEN-WORK.md` for the detail. Never a
  summary of the backlog: a summary is the re-encoding, and re-encoding is what loses it. These two
  were one heading once, and merging them is what let an undecided item sit under a heading that
  reads as decided.
- **The exact next action** - the command or edit to start with, not a direction of travel. **It
  must be the top-ranked open item in `OPEN-WORK.md`, or the file must say plainly why a
  lower-ranked one goes first.** Recency is not a reason. "It is what I was working on", "it is
  nearly done", "the user mentioned it most recently" and "it is small" are the four that get
  written, and none of them outranks a bigger item the user is still waiting on.
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
2. **RECONCILE the outgoing handover into `OPEN-WORK.md` BEFORE you overwrite it.** Read the file
   you are about to destroy and take every item in it that is not finished. Each one either
   already has a line in `OPEN-WORK.md`, or you add it now with its first-raised date, its size
   and its next action; an item you believe is finished gets `- [x]` and a reason, in the file,
   not in your head. What you do not carry across goes SILENTLY, because a missing item looks
   exactly like an item that was closed - and nobody diffs a handover against its predecessor
   looking for absences. Being able to recover the old text from git is not the same as noticing
   there was something to recover. Do this reconcile FIRST, while the outgoing file is still in
   front of you: afterwards you are auditing from memory, which is the failure itself.

   Add the same way anything the USER asked for in this session and did not get, in their own
   words. A request that lives only in the sentence they typed is one re-ask away from being lost,
   and they will not know to re-ask.

3. **Write `handover.md` at the repo root, OVERWRITING whatever is there.** A stale handover from an
   earlier session is superseded the moment you write yours - replace it wholesale, never append to
   it and never keep both. There is exactly one `handover.md`, and it describes one moment; two of
   them, or one with two moments in it, leaves the reader deciding which half is true. Commit it
   along with `OPEN-WORK.md`: tracking them costs one diff per session and buys a history for the
   one file that is destroyed on purpose every time, so a dropped item can be recovered once
   somebody notices. Check first that neither carries a secret, an internal hostname or a private
   address, because a tracked file in a public repo publishes all three permanently.
4. **End the file with its own expiry instruction:**

   > Read this, then replace the first line with `# STALE - read <date>, work continued`. Do not
   > delete it - if this session ends badly it is the only record of where things stood.

5. **Re-read it as the next session.** Any line the repo could have told them is a line to cut.
6. **STOP. The handover is the LAST thing you do in this session.** Writing it ends the session's
   work. Do NOT start a new task, resume the one you were part-way through, or "just finish" the
   small thing first - not even the next action you have just written into the file. Every edit made
   after the handover is work the handover does not describe, so the next session inherits a file
   that is already wrong about the state it exists to report, which is worse than no handover at all.
   If the user asks for something new, write the handover, stop, and let them re-ask after the clear.
7. **Make the `/clear` nudge the last line, then stop.** Say the handover is written, name the file,
   and tell the user to type `/clear`. It is an instruction, not an invitation: "type `/clear` when
   you're ready" hands back a decision nobody asked them to make. You cannot run it yourself -
   built-in slash commands are not invocable by the model - and that is the half that goes missing
   when the wording is rebuilt from scratch, so send it as written, changing one thing only - the
   path:

   > Handover written to `handover.md`. Type `/clear` to start the next session - I cannot run it
   > for you.

   `handover.md` there is the path slot, not a literal to copy. Send the path that reaches the file
   from where the user is standing, and a bare basename only when that is unambiguous: a second
   `handover.md` in another worktree, checkout or package makes the bare name point at somebody
   else's file, and the reader cannot tell which one they opened.

   **Nothing follows it.** Not a recap of what you just wrote, not an offer to keep going, not "let
   me know if you want X first", not a question. A reply that ends by inviting more work invites it
   into THIS session, which is the one thing the handover exists to prevent.

   Anything you genuinely owe the user goes BEFORE that line, in one sentence. A question they asked
   while you were writing is the case that matters: say you are not answering it in this session and
   that they should re-ask after the clear, then send the nudge. Step 6 sends them back to re-ask,
   which only works if they know the question was heard - dropping it in silence reads as ignored.

## When you are the one READING a handover

Absorb it, then **mark it STALE in place**. Both alternatives fail: left untouched, the session
after next reads a passed moment as current; deleted, the record is gone the instant it is read, so
a crash mid-task leaves nothing saying where the work stood.

Never amend a stale handover to update it - write a NEW one and replace the file. An edited handover
holds two moments with no way to tell them apart.

**Read `OPEN-WORK.md` too, and read it FIRST.** The handover tells you where the last session
stopped; the backlog tells you what is actually worth doing, and the two answers are routinely
different. A handover's next action is one session's view of one moment, and the item that has
been waiting longest is the one least likely to be in it.

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
