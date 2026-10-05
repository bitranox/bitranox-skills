# Scratch-collision jigs: `mutation_arm --revert` and `fanout_crosscheck`

Design, validated section by section with the user on 2026-10-05.

## Problem

Subagents in one session share its scratchpad, and a fan-out shares a tree. The memory fact
`feedback-a-parallel-write-agent-can-clobber-a-sibling-target-and-report-success` records five
incidents. Every one reported success, and every one was caught only from ground truth. They come
from three mechanisms:

| Mechanism                                                               | Incidents | Covered by               |
|-------------------------------------------------------------------------|-----------|--------------------------|
| Hand-rolled copy-aside under a generic name, restored from a wrong copy | 2         | `mutation_arm --revert`  |
| Parallel readers writing intermediate files to one shared scratch dir   | 2         | brief (not covered here) |
| An agent writing into a sibling's target                                | 1         | `fanout_crosscheck`      |

A PreToolUse guard on the dispatch prompt was priced on 1,222 real dispatches and rejected:
precision 0, and it cannot see a wrong-target write at all. The fact's recurrence count reached 5,
so prose is exhausted and the remaining endpoint is a jig.

In the 2026-10-05 incident the dispatch brief itself prescribed the hand-rolled copy-aside
("copy the file aside, restore the old one with `git show HEAD:...`, run the test, restore your
copy"). `mutation_arm` already owns that job safely, but only for an exact-text mutation, not for
"run this test against the committed version of the whole file".

## Part 1: `mutation_arm --revert FILE REV`

**CLI.** `mutation_arm.py --revert FILE REV --test NODEID [--timeout S] [--json]`. Repeatable and
combinable with `--mutate`; every revert and mutation is applied together as ONE arm, all or
nothing, as today.

**Mechanism.** An arm is a list of `(path, old_text, new_text)` that is planned, applied, run and
restored. A revert is one more entry: `old` is the file's current full text, `new` is
`git show REV:<path relative to its work tree>`. Planning, the copy taken before the first write,
the `finally` restore with byte comparison, the bytecode purge and the timeout all apply unchanged.
There is no second restore path.

**Refusals, with nothing written (exit 2):**

- the file is not inside a git work tree, or does not exist at `REV`;
- `REV` does not resolve (`git rev-parse --verify -q`);
- the work-tree text already equals the text at `REV`: the arm would change nothing, so its
  SURVIVED would be vacuous.

**Report.** Each revert entry names `path`, `rev` as given, and the resolved 40-character sha, so a
recorded "killed against HEAD" stays meaningful after HEAD moves.

**Reading it in a RED proof.** KILLED: the test notices the old code, the fix is pinned. SURVIVED:
it does not.

**Out of scope.** Whole directories and revision ranges: one file per `--revert`.

## Part 2: `fanout_crosscheck`

**Purpose.** After N agents each worked their own target, find text that landed in the wrong one:
a sibling's package name in a docstring, one level's descriptor written into another.

**CLI.** `fanout_crosscheck.py --target NAME=PATH ... [--since REV] [--ident NAME=TOKEN ...]
[--allow NAME=TOKEN ...] [--json]`

**What it examines.** Only the lines each target ADDED: `git diff -U0` against `--since` (default:
uncommitted work tree plus index). Whole-file scanning is noisy, because old changelog entries
legitimately name dependencies. A PATH that is a plain file rather than a git work tree has all its
lines treated as added, which covers non-git targets such as memory levels.

**What it looks for.** Each target's identifiers inside the other targets' added lines. Identifiers
default to the target NAME in its `snake_case`, `kebab-case` and space-separated spellings,
case-insensitive, plus any `--ident`. A token that is a declared dependency of the target being
scanned is allowed (for Python, read from its `pyproject.toml`); `--allow` adds more by hand.

**Output and exit codes.** One finding per hit: target, file, line number, the foreign identifier,
the line text. Exit 0 clean, 1 findings, 2 usage or IO error. It always reports how much it
examined (targets, files, added lines), and zero added lines across all targets is exit 2, not a
clean pass, so a wrong `--since` cannot print a green that means nothing. `--json` emits the house
envelope; warnings go to stderr.

## Part 3: testing, placement, wiring

**Tests, written first (RED), all against real temporary git repos:**

- `--revert`: KILLED when the reverted file breaks the test, SURVIVED when it does not; each
  refusal leaves the tree untouched; byte-exact restore after a timeout; combined with `--mutate`
  in one arm; a CRLF file round-trips.
- `fanout_crosscheck`: the 2026-10-05 shape as a fixture (three small repos, one with a sibling's
  name on an added line) exits 1 naming that file and line; a declared-dependency mention is not
  flagged; a pre-existing line holding a sibling name is not flagged; plain-file targets work;
  zero added lines exits 2. A planted negative and a planted positive prove each check can answer
  both ways.

**Placement.** Both ship in `bitranox:compuse-toolbox`, with a plugin version bump per shipped
change. Each gets a SKILL.md row phrased in the user's words ("did an agent write into the wrong
repo?", "run the test against the committed version of a file"), and a row is registered only
after an isolated retrieval test picks it for that question with NONE offered as acceptable.

**Wiring, so the rule stops being prose:**

- the memory fact points at both jigs instead of at a `mktemp -d` instruction;
- `bitranox:process-agents-dispatching-parallel` gains one Verification line: run
  `fanout_crosscheck` after any per-target fan-out;
- the PreToolUse tool nudge gains a signature that points a hand-rolled
  `git show HEAD:<file> > <file>` during a test run at `mutation_arm --revert` (a nudge, not a
  block).

**Order.** `--revert` first (smallest, removes the most frequent mechanism), then
`fanout_crosscheck`, then the wiring; each its own commit and version bump.
