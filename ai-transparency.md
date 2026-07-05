# AI transparency

The author and owner of this project is the human, [@bitranox](https://github.com/bitranox).
Every design and engineering decision is theirs, and they answer for everything published here.
An AI assistant (Claude, run through the Claude Code CLI) is used as a tool under that direction,
mostly for the typing and the legwork. This page says where, plainly, so you can weigh the work
on its merits. The reasoning behind working this way is in [ai-stance.md](ai-stance.md).

One honest twist up front: this repo is a collection of Claude Code skills and hooks, so it is
partly a tool for directing an AI. The AI helps build the very thing that helps direct it. That
changes nothing about who decides - the human sets every rule the skills encode and owns the
result; the AI writes prose and code to that brief.

## The human's work

- The problem is theirs: make a Claude Code assistant compound over time instead of re-learning
  the same lessons, and package a set of software-engineering skills so they install anywhere.
- Every design decision is the human's: the skill taxonomy and naming; the layered memory model
  and all of its rules - knowledge filed by how far it reaches, facts promoted concrete rather
  than watered down, links pointing only upward, a corroboration gate before an inferred rule
  reaches the always-loaded top, and NO forgetting by age or use (because "used" cannot be
  honestly measured) - only dedup, obsolete-pruning, and manual removal.
- The operating policy is the human's: the propose / auto / off modes; the informed-consent knobs
  (a recommendation plus the consequence, recorded once, never re-asked); the append-only
  marketplace rule enforced with branch protection; and the cross-platform rules every shipped
  hook follows.
- The human reviews and corrects the work at every step, including overruling the AI's direction.
  What ships is what they sign off on. Every commit goes out under the human's name and
  authority, with no AI co-author line.

## Where the AI is used

As a tool, under the human's direction, it does the mechanical and exploratory parts: writing the
`SKILL.md` instructions and the Python hooks, helpers, and their sibling tests to the human's
design; drafting the documentation, including this page; laying out options at each fork for the
human to choose from; and running adversarial review rounds over designs before they are built.
Where a design depends on Claude Code behavior, it verifies the assumption with scripted probes
in real sessions instead of trusting its own recollection, and it pressure-tests skills with
throwaway subagents to confirm an agent following them behaves correctly. None of the decisions,
and none of the accountability, are the AI's.

## What is verified, and how

Every Python file that ships - every hook and every skill helper - has sibling tests, and the
whole suite runs green (`python3 -m pytest -q`, several hundred tests). A repository gate runs on
every change and enforces skill naming, sibling tests for every shipped `.py`, a
secret/private-hostname scan, LF endings, valid hook JSON, a version bump when the plugin
changes, and - for skill changes - the skill-writer checklist artifacts and a trigger-first
description lint. Derived artifacts cannot rot: the skill router's trigger map and the
[skill catalog](docs/skills.md) are generated from the skills' own descriptions, with sync tests
that fail when either goes stale. The memory consolidation has an acceptance harness of its own:
it builds a synthetic knowledge tree, runs each dream against it, and asserts the outcome
per scope - including byte-level checks that the quick nap leaves sibling projects untouched.

What CI cannot check is live hook behavior across real sessions - a `UserPromptSubmit` or `Stop`
hook only fires inside an actual Claude Code session - so those paths are exercised by hand in
real sessions. The memory itself is machine-local and never committed to this public repository.

## Checking it yourself

Everything here is plain text and small. Each skill is a single `SKILL.md` you can read; the
hooks are short, standard-library Python with their tests next to them. Run the tests with
`python3 -m pytest -q` - they need nothing beyond Python. The marketplace history is append-only,
so every change is an additive commit with a version bump, and the reasoning lives in the commits
and the `CHANGELOG`. The ideas behind the memory system, in plain language, are in
[docs/concepts.md](docs/concepts.md).

## What this isn't

It is not an Anthropic product, and Anthropic has not reviewed or endorsed it - it is an
independent collection of skills and hooks for Claude Code. The skills encode one developer's
working habits and opinions; they are defaults to adopt or adapt, not received wisdom. And the
layered memory is a convenience that compounds over time, not a guarantee: read the skills it
runs so you know what it records, promotes, and proposes on your behalf.

## License and attribution

The text and code here are under the MIT License (see [`LICENSE`](LICENSE)). Anthropic's terms
put ownership of model output with the user, so the human owns this and answers for it. Under the
MIT License you are free to use, modify, and redistribute it, provided the copyright notice and
license text are kept.
