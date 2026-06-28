# AI transparency

The author and owner of this project is the human, [@bitranox](https://github.com/bitranox).
Every design and engineering decision is theirs, and they answer for everything published
here. An AI assistant (Claude, run through the Claude Code CLI) was used as a tool along the
way, mostly for the typing and the legwork under that direction. This page says where, plainly,
so you can weigh the work on its merits. The reasoning behind working this way is in
[ai-stance.md](ai-stance.md).

There is an honest twist worth stating up front: this repo is a collection of Claude Code
skills and hooks, so it is partly a tool for directing an AI. The AI helped build the very
thing that helps direct it. That does not change who decided what - the human set every rule
the skills encode and owns the result; the AI wrote prose and code to that brief.

## The human's work

The shape of this project is the human's, start to finish. They set the problem, made every
call, and own the result.

- The problem is theirs: make a Claude Code assistant compound over time instead of re-learning
  the same lessons, and package a set of software-engineering skills so they install anywhere.
- Every design decision was the human's. The skill taxonomy and the category-prefixed naming;
  the layered, self-maintaining memory model and all of its rules - knowledge filed by how far it
  reaches (per-project, a global `~/.claude/rules/bitranox/` layer, `CLAUDE.md` only as a last
  resort), concrete-but-universal facts promoted as-is rather than watered down, normalization by
  reference-plus-delta with references pointing only upward (so deleting a project never dangles a
  pointer), a corroboration gate before anything reaches the always-loaded global layer, and the
  decision that there is NO forgetting by age or use (because "used" cannot be honestly measured) -
  only dedup, obsolete-pruning, and manual removal. The "look in the notebook before reinventing"
  recall reflex, the filler-word handling that keeps it precise, and the rule that the slow
  classification happens off the per-prompt hot path were the human's calls too.
- The operating policy is the human's: the propose / auto / off modes; the informed-consent knobs
  (a recommendation plus the consequence, recorded once, never re-asked); the "right tool for the
  right job" model-tier doctrine for subagents; the append-only marketplace rule (never squash or
  force-push a published marketplace) enforced with branch protection; and the cross-platform rules
  every shipped hook must follow (LF endings, forced UTF-8, a portable Python launcher, fail-open
  on Windows).
- The human reviewed and corrected the work at each step - including reversing the AI's own
  earlier direction (an age-based "forget unused notes" mechanism was built, then removed once the
  human ruled that age and use are the wrong signals). What ships is what they signed off on.
- Every commit went out under the human's name and authority, with no AI co-author line. The
  human is responsible for what is published.

## Where the AI was used

As a tool, under the human's direction, it did the mechanical and exploratory parts: writing the
`SKILL.md` instructions and the Python hooks, helpers, and their sibling tests to the human's
design; turning the memory design into concrete code (the altitude resolution, the index
reconciler and its reference-integrity and cap checks, the cross-tree gather grep, the per-prompt
recall hook, the filler-word blacklist and queue); drafting the documentation and these pages;
laying out options at each fork for the human to choose from; and running adversarial review
rounds over the design before it was built. It also ran the test suite and the repository gate on
every change, and pressure-tested skills with throwaway subagents to confirm an agent following
them behaves correctly. None of the decisions, and none of the accountability, were the AI's -
the human directed and approved every action and owns the result.

## What's been checked, and what hasn't

The Python that ships - every hook and every skill helper - has sibling tests, and the whole
suite runs green (`python3 -m pytest -q`, several hundred tests). A repository gate
(`repo-gate.py --ci`) runs on every change and enforces skill naming, that the catalog in
`meta-using-bitranox-skills` stays in sync with the shipped skill directories, that every shipped
`.py` has a sibling test, a secret / private-hostname denylist scan, LF line endings, valid hook
JSON, and a version bump when the plugin changes. Human-facing prose is run through the
AI-writing-tell sweep before it ships.

What CI cannot check is the live behavior of the hooks across real sessions - a `UserPromptSubmit`
or `Stop` hook only fires inside an actual Claude Code session, not in a test harness - so those
paths are exercised by hand in real sessions. The presence of the global `~/.claude/rules/bitranox/`
layer in a fresh session was confirmed once by a manual spike, since it too cannot be proven in CI.
The memory itself is machine-local and never committed to this public repository.

## Checking it yourself

Everything here is plain text and small. Each skill is a single `SKILL.md` you can read; the hooks
are short, standard-library Python with their tests next to them. Run the tests with
`python3 -m pytest -q` - they need nothing installed beyond Python. The marketplace is append-only,
so the history shows every change as an additive commit with a version bump, and the reasoning lives
in the commits and the `CHANGELOG`. The ideas behind the memory system, in plain language, are in
[docs/self-learning-memory.md](docs/self-learning-memory.md).

## What this isn't

It isn't an Anthropic product, and Anthropic hasn't reviewed or endorsed it - it is an independent
collection of skills and hooks for Claude Code. The skills encode one developer's working habits and
opinions; they are defaults to adopt or adapt, not received wisdom. And the layered memory is a
convenience that compounds over time, not a guarantee: read the skills it runs so you know what it
records, promotes, and proposes on your behalf.

## License and attribution

The text and code here are under the MIT License (see [`LICENSE`](LICENSE)). Anthropic's terms put
ownership of model output with the user, so the human owns this and answers for it. Under the MIT
License you are free to use, modify, and redistribute it, provided the copyright notice and license
text are kept.
