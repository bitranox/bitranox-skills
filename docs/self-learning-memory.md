# How the self-learning memory works (the ideas behind it)

This is the plain-language version: what the bitranox memory is trying to do and why it is built
the way it is. No file paths or code here, just the principles. If you want the mechanics, the
skills themselves spell those out.

The goal is simple to state and hard to do well: Claude should get better the more you work with
it, and a lesson learned in one project should not be lost the moment you switch to another.

The mental model throughout is a brain. Not as a slogan - as the actual design guide.

## 1. Learn as you go, then sleep on it

Two different jobs, kept separate.

While you work, the system notices when something worth keeping happens - a correction you made, a
rule you stated, a mistake it does not want to repeat - and writes it down right away. That is the
fast, in-the-moment part.

Then, every so often, it "dreams": a slower pass over the whole pile that tidies it the way sleep
consolidates a day. It merges duplicates, sharpens wording, connects related notes, throws out the
stale, and lifts the broadly useful up where everything can reach it. Capture is quick and additive;
dreaming makes the store smaller and sharper, not bigger.

## 2. Put knowledge where it belongs, by reach

Some things are true only for one project. Some are true for a whole family of projects. Some are
true everywhere you work. The system files each lesson at the level that matches how far it reaches.

The important subtlety: this is about reach, not about how "general" the wording is. "Log into the
fleet with this key and accept host-key changes on our subnet" is very specific, but it is useful
in every project - so it lives at the top, kept concrete and ready to use. Watering it down into a
vague principle would only make it useless. Things get abstracted only when the specifics genuinely
fit nowhere else; then the reusable idea moves up and the local detail stays home.

## 3. Always within reach, never "maybe"

A note that might be loaded when relevant is a note that will be missed when it matters. So the
knowledge the system relies on is always present in context, not fetched on a hunch. We learned this
the hard way: a memory you have to go looking for is a memory you forget to consult.

The flip side is discipline. Context is finite, so what is always present has to stay lean. That is
a big part of what dreaming is for - keeping the always-on layer short and high-signal, with the
long details a step away rather than underfoot.

## 4. Connect, do not copy

When a general rule and a specific case overlap, the system does not store both in full. It keeps
the general rule once and lets the specific note point at it and add only what is different. You get
the full picture when both are read together, without the same words living in two places.

Connections only ever point "upward" - from the specific toward the general, from the short-lived
toward the durable. That way deleting a project never leaves a dangling pointer behind: what was
promoted up survives, and only the local details disappear with it, which is exactly right.

## 5. Forget what you never use

A brain lets unused links fade. So does this. Notes that never get touched drift out of the always-on
layer over time, archived rather than deleted. Without that, the memory would only ever grow, and a
memory that only grows eventually drowns out its own signal. Genuine must-follow rules are never
forgotten - only the clutter.

## 6. Fast thinking and slow thinking

Some work is genuinely novel and deserves real reasoning. Other work is the same handful of steps,
again and again. When a routine gets repetitive, the system can turn it into a skill - often backed
by a small script - so it runs the same way every time instead of being re-derived (and second-
guessed) on each pass. That is the shift from deliberate effort to habit. It is meant for routines,
not for the rules that must stay front of mind.

## 7. Your memory, your call

Where a sensible default depends on how you work, the system recommends what it thinks is best,
explains the trade-off in plain terms, and then lets you decide. Your choice is remembered and
applied from then on - it does not ask again. You can review, change, or reset any of these settings
whenever you like.

This covers the questions that do not have one right answer for everyone: how eagerly to share a
lesson across projects, how aggressively to forget, where new skills should live, and how cautious
to be with anything sensitive. Before anything is reorganized, the whole store is backed up, so every
change is reversible.

## 8. What helps everyone, shared

Now and then a lesson turns out to be useful far beyond your setup. When that happens, the system can
package it as a skill and offer it back to the shared marketplace, so other people benefit too. That
is opt-in and proposed, never automatic - but it is how individual learning turns into something the
whole community compounds on.

---

In one line: capture quickly, consolidate like sleep, keep the useful things concrete and within
reach, connect instead of copy, forget the noise, automate the routine, and leave the judgment calls
to you.