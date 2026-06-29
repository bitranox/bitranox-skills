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

There are two kinds of dream, for two depths of rest. The everyday one is a **short nap to sort your
thoughts** - it tidies only the project you are working in: quick, cheap, run often (`dream-project`).
The other is the **deep sleep you get when you need it** - it ranges across all your projects at once,
carrying a lesson learned in one over to where it helps in another and lifting the broadly-useful up so
everything can reach it (`dream-global`). You take the nap frequently; you get the deep sleep now and
then.

One caution before you rely on either, and the deep one most of all: take your own backup of your
memory and `CLAUDE.md` files before the first full dream, and keep doing it until you have watched it a
few times and trust how it reshapes things. The dream always backs itself up first, so every run is
reversible - but the global pass can lift rules into the layer that loads in every project, and it is
worth seeing that behave on your own data before you let it run unwatched.

A dream does not always finish in one night. Some tangles take several passes to settle: the system
keeps dreaming the same store until a pass changes nothing, the way a mind returns to the same dream
night after night until the open question is worked through. A single consolidation that does not catch
everything is normal - the next one picks up where it left off, and eventually the dreams go quiet
because there is nothing left to resolve.

What is not healthy is going in circles - redoing the same change every pass and never settling. The
system watches for that and, instead of looping forever, stops and hands it to you, the way friends step
in with an intervention when someone is stuck repeating the same pattern. You break the cycle and point
it the right way.

And for the choices that are simply yours to make - where a rule belongs, whether a duplicate should go,
whether the folders should be reshaped - it does not guess either. It asks, the way you would talk
something through with a therapist, then carries out what you decide.

## 2. Put knowledge where it belongs, by reach

Some things are true only for one project. Some are true for a whole family of projects. Some are
true everywhere you work. The system files each lesson at the level that matches how far it reaches.

The important subtlety: this is about reach, not about how "general" the wording is. "Log into the
fleet with this key and accept host-key changes on our subnet" is very specific, but it is useful
in every project - so it lives at the top, kept concrete and ready to use. Watering it down into a
vague principle would only make it useless. Things get abstracted only when the specifics genuinely
fit nowhere else; then the reusable idea moves up and the local detail stays home.

## 3. Group your projects like departments in a company

That filing only works if your folders mirror how your knowledge is actually divided. Picture a company:
there is head office, there are departments - accounting, production, sales - and there are individual
desks. Each department owns the knowledge its people share; head office holds what everyone must follow;
a desk keeps its own notes.

Your project tree is that org chart. The top is head office - the layer known in every project. Each
grouping folder is a department, and its shared shelf holds what everything inside it needs. A single
project is a desk with its own memory. A lesson settles at the lowest department whose whole domain it
serves, so it reaches exactly the people who need it and no one else.

This is why the shape of your folders matters. Put related projects together under a common parent and
that parent becomes a real department, with a real place to keep their shared rules. Leave everything
flat and unrelated and there are no departments - only desks and head office - so a rule shared by five
related projects has nowhere sensible to live: it gets pushed all the way up to head office (where it
loads for everyone, needed or not) or copied into all five desks (wasted room in every session).

The rule of thumb is simple: if two projects would share a rule, they belong in the same department -
put them under the same parent folder. A rough shape:

    workspace/                 head office: rules for everything
      python-libs/             a department: shared Python-library rules
        lib-a/  lib-b/         desks
      client-acme/             a department: one client's work
        app-1/  app-2/
      infra/                   a department: fleet and host rules
        host-1/  host-2/

Each department folder carries a one-line note about what it is for, so the system knows which shelf a
lesson belongs on. Shaping the tree to match your real domains is the single biggest thing you can do to
make the layering save room instead of wasting it. And if the shape drifts - a project that has grown
into a different domain - the deep dream will notice and suggest moving it; only ever a suggestion, you
make the call.

It also spots a missing rung. When several related projects keep learning the same rule but the folder
that contains them has no shared shelf - no department - the deep dream sees the rule trying to settle
with nowhere to land, and offers to create that department (and, at the very top, a head office if there
is none). It only suggests; you decide whether the department is real.

## 4. Always within reach, never "maybe"

A note that might be loaded when relevant is a note that will be missed when it matters. So the
knowledge the system relies on is always present in context, not fetched on a hunch. We learned this
the hard way: a memory you have to go looking for is a memory you forget to consult.

The flip side is discipline. Context is finite, so what is always present has to stay lean. That is
a big part of what dreaming is for - keeping the always-on layer short and high-signal, with the
long details a step away rather than underfoot.

There is one more reflex on top of the always-present layer: when a new request comes in, the system
does a quick search of everything it has noted before - across all your projects - and, if it finds
something similar it has done, lays that note open on the desk for this turn. Think of it as checking
your own notebook before reinventing the wheel, or asking "have I solved this before?" instead of
starting from a blank page. It is deterministic (a relevance match, not a guess), it only adds notes
from elsewhere that you do not already have here, and it shows each one once - so it helps without
crowding the desk.

A fair worry here: doesn't pulling in old notes on every turn waste tokens? At the very start it can
feel that way - a little extra context for notes you may not need. That feeling fades fast, and the
balance tips the other way. Re-deriving something you already worked out once - re-reading the same
files, re-making the same mistake, re-discovering the same flag - costs far more tokens than a short
note that hands you the answer up front. Glancing at the notebook is cheap; reinventing the wheel is
expensive. The longer you use it, the more it saves.

Two things keep that glance cheap. First, the slow, expensive part of learning - generalizing,
re-filing, deciding what is worth keeping - does not happen during your live turns at all. It is
moved into the consolidation pass (the "dream"), which runs out of band: when one is due at the start
of a session, around a context compaction, or whenever you ask. Your working turns stay fast; the
heavy lifting happens off the clock. Second, the search itself gets sharper over time: the dream
learns which words are just conversational filler ("again", "previous", "normal") versus real topics,
so the notebook check stops matching on noise and only surfaces things that actually relate.

That last filter is learned per project, not globally, and the reason matters. A word can be noise in
one project and a real subject in another - "compression" is chatter in a documentation project but a
genuine topic in a codec one. So each project keeps its own learned filter, and only the
universally-generic words - the kind that are noise everywhere - are shared across all of them. One
project's judgment never silences a word you actually search on in another.

## 5. Connect, do not copy

When a general rule and a specific case overlap, the system does not store both in full. It keeps
the general rule once and lets the specific note point at it and add only what is different. You get
the full picture when both are read together, without the same words living in two places.

Connections only ever point "upward" - from the specific toward the general, from the short-lived
toward the durable. That way deleting a project never leaves a dangling pointer behind: what was
promoted up survives, and only the local details disappear with it, which is exactly right.

## 6. Remove what is wrong, not what is quiet

It is tempting to let old or rarely-touched notes fade the way a brain drops unused links. We tried
that and backed it out, because the signal it needs does not exist: a note sits in context and Claude
reads it silently, so there is no honest way to tell that a note was "used" - and a note being old,
or long, or quiet says nothing about whether it is still true. Forgetting by the clock would throw
away good notes.

So nothing is removed just for being old or unused. A note leaves only for a content reason: it
duplicates another (the two are merged into one sharper note), or it is genuinely obsolete - it points
at a file or flag that no longer exists, an issue that was resolved, or it has been superseded by a
newer note - or you ask for it to go. Those are judgment calls the dream makes by reading the note,
proposing the change, never deleting silently; and the whole store is backed up first, so it is always
reversible. Must-follow rules are never dropped. The store stays lean not by forgetting, but because
the always-on part is just tight one-line summaries - the detail lives a step away and costs nothing
until it is read.

## 7. Fast thinking and slow thinking

Some work is genuinely novel and deserves real reasoning. Other work is the same handful of steps,
again and again. When a routine gets repetitive, the system can turn it into a skill - often backed
by a small script - so it runs the same way every time instead of being re-derived (and second-
guessed) on each pass. That is the shift from deliberate effort to habit. It is meant for routines,
not for the rules that must stay front of mind.

There is a second version of the same idea: the right tool for the right job. When the system hands a
piece of work to a helper, it picks the model that fits the work - like a craftsperson reaching for
the right tool rather than using the same one for everything. Deep, get-it-right reasoning goes to the
most capable model; routine, parallelizable work goes to a fast, capable workhorse; purely mechanical
steps go to the quickest, cheapest one. You get strong judgment where being wrong is costly, and speed
and low cost where it is not - matched automatically, job by job. And because the line-up of models
changes over time, the dream periodically re-checks which tool belongs to which job and adjusts.

## 8. Your memory, your call

Where a sensible default depends on how you work, the system recommends what it thinks is best,
explains the trade-off in plain terms, and then lets you decide. Your choice is remembered and
applied from then on - it does not ask again. You can review, change, or reset any of these settings
whenever you like.

This covers the questions that do not have one right answer for everyone: how eagerly to share a
lesson across projects, where new skills should live, how much the dream should do on its own versus
ask first, and how cautious to be with anything sensitive. Before anything is reorganized, the whole
store is backed up, so every change is reversible.

## 9. What helps everyone, shared

Now and then a lesson turns out to be useful far beyond your setup. When that happens, the system can
package it as a skill and offer it back to the shared marketplace, so other people benefit too. That
is opt-in and proposed, never automatic - but it is how individual learning turns into something the
whole community compounds on.

## 10. A curated library you can still mark up

Think of every skill out there as a library of books by different authors. They overlap, and now and
then they flatly contradict each other. What you want is not the raw pile but a good compilation - an
Encyclopaedia Britannica: the best of it gathered in one place, the duplicates merged, the
disagreements reconciled, the whole thing aligned into one coherent voice. That is what bringing in a
good outside skill does here - it is adopted, deduplicated against what you already have, and aligned
to the rest, instead of dumped in next to three near-copies.

But even the best encyclopaedia has a line or two that does not match how YOU see the world. You do not
throw the volume out - you take a marker and cross that line out, or write your correction in the
margin. Same here: when a skill does something you would rather it did not, you do not fork it or delete
it. You just say so, and it is recorded as your override - "when using skill X, do this instead; do it
my way like ...". Your instruction outranks the skill (you are in control), and that note rides along
every time the skill comes up, exactly like your annotation in the book.

So the collection grows by pulling in the best from elsewhere and harmonising it, and it stays YOURS:
any part of it can be overruled by a single note in your own hand.

---

In one line: capture quickly, consolidate like sleep, keep the useful things concrete and within
reach, check the notebook before reinventing, connect instead of copy, prune only what is wrong,
automate the routine with the right tool for each job, draw in the best from elsewhere and align it,
mark up whatever does not fit your way, and leave the judgment calls to you.