# Top Index Phase 2 (Placement by Topic) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use bitranox:process-agents-subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A rule reaches only the directories it is about: a fact carries the topics it is bound
to, a directory's descriptor declares the topics it has, and the engine renders the fact's
pointer line at every level that has one of its topics and no ancestor that has one; then the
existing tree-top pointers are migrated to that placement.

**Architecture:** Topics are data in two places the engine already owns: a `topics:` line in a
body's frontmatter and a `TOPICS:` line in a level's descriptor, both checked against one closed
list per tree (`<anchor>/.claude-memory/topics.json`). A pure module computes placements from
the level map; the engine renders pointer lines from each body's own `title:` and
`description:`, and `reconcile --check-tree` compares the rendered lines with a fresh
computation. No marker is added to a pointer line: a fact is topic-placed exactly when its body
carries a non-empty `topics:` list and no pointer of it is pinned. The dream and the nap stop
moving such facts up and tag and re-render instead. The migration is a store run with a scratch
render, a paid firing-test arm and one apply.

**Tech Stack:** Python 3.14 stdlib scripts with pytest tests, Markdown SKILL.md files, the
per-skill decision ledger, the `jev-judge` CLI (TypeSafe Jev) for tagging, headless Claude Code
CLI for the firing arm.

**Design:** `docs/plans/2026-11-09-top-index-cost-side-design.md`, sections "Phase 2: placement
by topic", "Migration of the existing top pointers" and "Not chosen" (commit `a58c6b8c` of this
branch holds the text this plan was written against). Phase 1's plan:
`docs/plans/2026-11-09-top-index-phase1.md`.

## Global Constraints

- ASCII only in every file; no em-dashes, curly quotes or other typographic tells.
- No Claude/AI attribution anywhere: no Co-Authored-By, no "Generated with" footer, no mention in
  a commit message, changelog or doc.
- Commit with `git commit -F <file> -- <paths>`, the message file written in an EARLIER Bash call;
  never `-m`. Work in the worktree `<repo>/.claude/worktrees/top-index-design` (branch
  `design/top-index-topics`); push as `git push origin design/top-index-topics:master`. Never
  write into the main checkout `<repo>` (other sessions use it) except the git-ignored
  `<repo>/EXECUTION-USER-REVIEW.md` decision log, which is appended to, never rewritten.
- `$ANCHOR` means the knowledge tree's anchor (the topmost dir holding a `CLAUDE.md` and a
  `.claude-memory/`); `export ANCHOR=<that dir>` before any run step. `<repo>` means this repo's
  main checkout. `$SCRATCH` means the session's scratchpad directory; never `/tmp`, never
  `$TMPDIR` (empty here).
- Never edit anything under `.github/`. History is append-only: no force-push, no rewrite.
- Public-repo docs state what a skill or tool does, never private provenance (no private hosts,
  paths, project names, live counts).
- Every SKILL.md or reference change goes through `bitranox:meta-skill-writer` (receipt, Step 0b
  ledger read, RED/GREEN probes, a `.skillwriter/checklist-<date>-<topic>.md` with a
  `Decisions:` line).
- Every shipped `.py` has sibling tests; run them with CI's dependency set:
  `env -u VIRTUAL_ENV uv run --with pytest --with PyYAML --with lxml --with defusedxml --with ruamel.yaml --with httpx2 python -m pytest <paths> -q`
- CI runs Linux (3.14, 3.15), Windows and macOS (3.15): every new test builds paths with
  `pathlib`, sets `USERPROFILE` wherever it sets `HOME`, and compares levels as path parts, never
  as `/`-joined strings read back from the OS.
- The store (`$ANCHOR/.claude-memory/` and every `CLAUDE.local.md` pointer block) is written only
  through the engine tools, never by Write/Edit, and only after a `store_manifest.py backup`.
- Do not touch the running phase 1 firing test: nothing under
  `~/.claude/self-improve-audit/p1b-20261110T143224Z` is written, and nothing under
  `<repo>/.claude/worktrees/p1b`. No LIVE store write of this plan (a descriptor fix, a topic, a
  rendered pointer) happens before that test's grid has finished (gate G1 below): its sessions
  read the live chain.
- Executions (implementers, fixers, reviewers, taggers, labellers) run on `opus` subagents, pinned
  in the dispatch; reviews at effort medium. While the phase 1 firing test is still running,
  dispatch ONE subagent at a time: it shares the account's usage limit, and a limit pause there
  stops until someone resumes it.
- Memory bound: a scan over the tree's bodies reads one body's head at a time
  (`FRONTMATTER_HEAD_BYTES` = 16384) and holds nothing per body; what may grow is stated per task
  (one small record per LEVEL, one pointer block per level being rendered, one row per batch
  entry up to `MAX_TOPIC_BATCH` = 5000). A task that builds such a path prescribes a peak-memory
  test at two store sizes.
- Release: each code milestone is one minor bump with
  `uv run plugins/bitranox/hooks/bump_version.py --part minor --changelog <notes>` from the
  version origin holds at that time, as the FIRST commit of the milestone (the commit gate
  refuses a `plugins/` commit whose version equals origin's); `--merge` if origin moved; then
  the full gate, a review, the push and CI watched to green.
- User instruction for this work (2026-11-11): "full auto no human". Where the design says the
  user reviews (the topic list, the tree top's topics at migration, the scratch-render report),
  the executing session decides, appends the decision with its reasons to
  `<repo>/EXECUTION-USER-REVIEW.md` (newest first, dated, naming the task) BEFORE acting on it,
  and continues. One thing is not decided by the session: the apply to the live store (Task 26)
  runs only after the firing arm (Task 25) returned PASS.
- After the migration the rule stands as the design states it: a nap or dream never changes the
  tree top's `TOPICS:` line; it proposes the change in its report. The engine enforces it with a
  verb of its own (`set-top-topics`).

---

## HIGH: milestones

| Milestone | Delivers                                                                                                                              | Ships as      | Gate before it / decision after it                         |
|-----------|---------------------------------------------------------------------------------------------------------------------------------------|---------------|------------------------------------------------------------|
| P2a       | placement rules (pure); `topics:` in bodies; closed topic list; `TOPICS:` in descriptors; the topic verbs; reference docs             | plugin minor  | CHECKPOINT A: which consumers assume one pointer per slug  |
| P2b       | the renderer (`render-topics`, tree and chain scope); `--check-tree` render check; the consumers the checkpoint named; tagging helper | plugin minor  | none                                                       |
| P2c       | dream-tree, dream-core, dream-passes, nap, crosstree and self-improve texts: tag and re-render instead of moving up                   | plugin minor  | none                                                       |
| G1        | (gate) the phase 1 firing test has a verdict                                                                                          | -             | PASS, FAIL, VOID_NOISE or INCOMPLETE decide what runs next |
| P2-prep   | topic list; descriptor check; tagger pilot; scratch tag and render; the per-directory report                                          | evidence only | CHECKPOINT B: the session's go or no-go on the report      |
| P2-arm    | the generated index as a firing-test arm under the phase 1 pass rule (paid)                                                           | evidence only | CHECKPOINT C: PASS is the only way to the apply            |
| P2-apply  | list, descriptor topics, fact topics and rendered pointers applied to the live store in one run, verified                             | store commit  | none                                                       |

MVP slice: P2a, P2b, P2c and P2-prep (the tree keeps working exactly as today until a topic list
exists; the scratch render shows what placement would do). Cut from this plan: topics for facts
that sit at a level BELOW the tree top (they keep their one pointer; the migration is of the top
pointers), roll-up into the tree top, dropping titles from rendered lines, any PreToolUse
delivery of rules.

All three code milestones can be built and released before G1: none of them writes the store,
and with no topic list in a tree every new code path is inert (the tests pin that).

Risks, ranked: (1) the store invariant "one pointer per slug" is assumed by more code than the
renderer touches, so CHECKPOINT A measures the consumers before the renderer is written; (2) a
wrong tag hides a rule from a directory that needs it, so the tagger is piloted against
reference labels with the threshold fixed first, recall of topics is weighted over precision,
and the fallback keeps every rule reachable at the top; (3) a wrong descriptor misplaces every
rule of its topic, so descriptors are checked against what sits below them before tagging; (4)
the firing arm measures placement in ONE chain (this repo's), so it shows that a pointer rendered
below the top fires like one at the top, not that every directory got the right rules - the
scratch report's per-directory tables are the evidence for that; (5) an older plugin version in
a still-open session heals a level file: it re-renders lines canonically, which is harmless here
because rendered lines carry no marker it could strip.

**What a phase 1 verdict other than PASS means for phase 2.** The design says the migration
"runs after phase 1 has shipped and passed its firing test". That gate has two purposes: the
baseline must be the store that will exist, and the instrument must be proven. Phase 2 does not
shorten a hook: a rendered line carries the hook the body holds, byte for byte.
- PASS: phase 1c ships the shortened hooks first; P2-prep freezes its inputs after that.
- FAIL (shortened hooks fire less): the hooks stay long, which changes nothing phase 2 does. The
  verdict was reached with the two today arms inside their own bound, so the instrument works.
  P2-prep and P2-arm run on today's hooks. This reads the design's sentence by its purpose, not
  its letter; the decision is logged in `EXECUTION-USER-REVIEW.md` before Task 20 starts.
- VOID_NOISE (the two today arms disagree beyond their bound): the instrument is not usable, and
  P2-arm uses the same instrument and pass rule. P2-prep runs (it needs no firing test); P2-arm
  and P2-apply do not, and the plan stops at CHECKPOINT B with the report. Repairing the
  instrument (more rules, more runs) is a cost decision for the user.
- INCOMPLETE: wait and resume it; nothing of P2-prep starts.

**Tasks 7-19 (P2b, P2c) were written at CHECKPOINT A, against the released P2a code; Tasks 20-27
(the migration) are written below in operational form against the MID interfaces and are re-read
against the released code at CHECKPOINT B before anything runs.**

## MID: components and verification

**M1 placement rules (`hooks/topic_placement.py`, pure).** A level is its path parts below the
anchor; the anchor is `()`. `LevelMap(declared)` holds one record per level. A level HAS a topic
when its descriptor declares it or when it has two or more child levels and every one has it
(roll-up); the anchor has only what it declares. `placements(topics)` returns every level that
has one of the topics while no level above it has one, and `(TOP,)` when none does. Also here:
the tag grammar (`[a-z0-9][a-z0-9-]{0,31}`, at most 12 per item), the stored forms (`[a, b]`),
and the descriptor's `TOPICS:` line (read, set, and a digest of the descriptor without it).
Verified by unit tests on the design's own example tree and a hand mutation of each rule.

**M2 topics as data (`hooks/memory_engine.py`, `hooks/topic_store.py`).**
- Body: a top-level frontmatter line `topics: [a, b]` after `title:`. No line = never tagged;
  `topics: []` = tagged, bound to no topic. An ordinary write (`add`, `amend-pinned`, factedit
  `apply`) keeps the STORED line whatever the handed-in body says; only `set-topics` changes it.
- List: `<anchor>/.claude-memory/topics.json` =
  `{"version": 1, "tagger": "jev"|"opus", "topics": {tag: one-line meaning}, "levels": {posix path below the anchor: descriptor digest}}`,
  at most 64 topics. No file = the tree has no list and nothing is placed by topic.
- Descriptor: a line `TOPICS: a, b` after `STACK:`. `set-scope` carries the stored line over when
  the new text has none and refuses a text that changes it.
- Verbs: `topics-show --proj D [--json]` (exit 1: no list), `topics-set-list --proj D --from-file F`
  (refuses dropping a topic a fact or level still uses), `set-topics --proj D (--slug S
  (--topics a,b | --universal | --clear) | --batch F.jsonl) [--dry-run]` (every row checked
  before any is written; refuses a pinned fact, a tag outside the list, a slug no level points
  at, an unframed body), `set-level-topics --proj LEVEL --topics a,b` (refuses the anchor),
  `set-top-topics --proj ANCHOR --topics a,b` (refuses any other level), `topics-stale --proj
  LEVEL` (exit 1 with the reason: no descriptor, never tagged, or the descriptor changed since
  its topics were chosen).
- Verified by tests through `memory_engine.main`, a mutation battery over every refusal, and a
  peak-memory test of the body scan at two store sizes.

**M3 renderer (`hooks/memory_engine.py`: `render_topics`, verb `render-topics --proj D --scope
tree|chain [--dry-run] [--json]`).** Detailed at CHECKPOINT A; the contract:
- The level map is every curated level whose descriptor is non-empty (a scaffold-only level is
  no level and must not block a roll-up), keyed by path parts, with its declared topics.
- A fact is MANAGED when its body's `topics:` is non-empty and none of its pointers is pinned.
  Everything else is never added, removed or rewritten by the renderer.
- A rendered line is built from the body alone: title from `title:`, hook from `description:`,
  no pin. A managed fact whose body lacks either stays where it is and is reported.
- Tree scope (the dream): an ADD phase over every level that has a topic, plus the anchor: one
  streaming pass of `iter_fact_topics` per level collects that level's lines (the one thing held:
  a level's block, refused past 1 MiB with a typed error), adds the missing ones and refreshes a
  managed line whose title or hook differs from its body, under that level's lock. Only when the
  ADD phase finished without an error does the REMOVE phase run: per curated level, each managed
  line at a level outside its fact's placements is dropped. Adds always precede removes, so an
  interrupted run leaves a surplus copy, never an unreachable rule.
- Chain scope (the nap): levels on `altitude_chain(D)` only. From the anchor down: add the lines
  placed at this level unless a level above already holds the slug; drop a managed line that a
  level above holds. It never drops a line merely because it is no longer placed there (other
  subtrees may still read it; the tree-scope run sweeps), and never writes outside the chain.
- A fact un-bound with `set-topics --universal/--clear` while it has several lines is collapsed
  by the same code: a line at the anchor first, then the others dropped.
- Cost: levels-with-a-topic times bodies head reads. Measured on the scratch tree in Task 24;
  over ten minutes there is a finding to fix before the apply, not a reason to hold more in
  memory.
- Verified by tests on a planted tree: the design's example; roll-up; fallback to the anchor;
  pinned and untagged facts byte-identical; the order of adds and removes observed through a
  recording write seam; an ADD-phase failure leaves every old line; chain scope leaves sibling
  files byte-identical; `--dry-run` writes nothing; peak memory at two store sizes; and with no
  topic list the verb prints that and changes nothing.

**M4 the check and the consumers (`skills/meta-self-improve/reconcile_memory_index.py` and
whatever CHECKPOINT A names).** `--check-tree` today reports every slug at more than one level
as a hard `duplicate pointer`. New: a managed fact's copies are legal, and a new hard problem
`render drift` lists, per managed slug, the levels where a line is missing, extra, or differs
from its body; an unmanaged slug at two levels stays a duplicate. `--check` over a chain reports
a managed line that a level above also holds. Engine guards: `move` and `relocate` refuse a
managed fact (its placement is computed; change its topics), a cross-tree `relocate` clears the
`topics:` line (topics belong to one tree's list), `--archive` of a managed fact drops every
copy, `rename` rewrites every copy, and an engine write that changes a managed fact's hook or
title refreshes its other copies. Verified by tests per behaviour and by `--check-tree` printing
`TOTAL tree problems: 0` on a rendered planted tree and non-zero after each planted drift.

**M5 tagging helper (`skills/meta-dream-tree/topic_tagging.py`).** Builds the `jev-judge` inputs
from the store and turns its rows into a `set-topics --batch` file: `questions` (one yes/no
question per topic of the list, from its meaning), `items --facts-at LEVEL | --levels` (state:
title and hook of a fact; the descriptor without its `TOPICS:` line for a level; one item per
line, streamed), `decide --rows R --threshold T` (a topic is taken at probability >= T; a row
with any answer inside the unsure band, or a failed row, goes to a second file for a model to
tag). It never calls Jev itself and never writes the store. The row format of `jev-judge` is
read from its `--help` and the `bitranox:ai-llm-jev-judge` skill at CHECKPOINT A, not assumed
here. Verified by tests on recorded rows.

**M6 skill texts (P2c).** Each new step opens with its condition "when `topics-show` exits 0", so
a tree without a list behaves as today.
- `meta-dream-tree/SKILL.md` step 0b: the descriptor template gains `TOPICS:` (set with
  `set-level-topics`, never typed into `set-scope` text); a level whose `topics-stale` exits 1 is
  re-tagged; the tree top's topics are never set, a wanted change is listed in the report.
  Step 5: a fact the routing sends to an inner level BECAUSE it holds wherever a stack or tool
  is used is tagged (`set-topics`) and rendered instead of moved; a fact that is about a place
  (a container, the whole tree) moves as today, a move to the top still by the mode and with
  its cost. Final step: `render-topics --scope tree`, then the verify contract.
- `references/dream-core.md`: the routing prompt names the two outcomes (a level, or topics);
  the report contract lists lines rendered and removed per level and proposed top-topic
  changes; `references/dream-passes.md`: "belongs higher: lift" becomes tag-and-render for a
  topic-bound rule.
- `meta-dream-nap/SKILL.md`: the current directory only - write its descriptor if it has none
  (this leaves the nap's deferred list), re-tag it when `topics-stale` exits 1, then
  `render-topics --scope chain`; one directory is below the item count Jev is for, so the nap's
  own model picks its topics from `topics-show`. Sibling files stay byte-identical.
- `meta-dream-crosstree` (+deep): a fact lifted or copied into another tree arrives untagged.
- `meta-self-improve`: capture is unchanged (a new fact has no topics); `memory-backend.md` and
  `docs/reference.md` document the data and verbs (P2a already adds the data part).
- Verified by the skill-writer RED/GREEN probes per passage, the decision ledger gate, and the
  dream acceptance harness.

**P2-prep, P2-arm, P2-apply (operational).** A run dir outside the tree holds every artifact; the
scratch tree lives in `$SCRATCH`, never under `~/.claude` (that directory is itself an anchor
with a store, so a tree copied below it would resolve to the wrong anchor). The topic list comes
from free tags proposed by opus subagents over the hooks of every fact at an inner level, merged
and reviewed adversarially. Descriptors are checked by one opus subagent per level against what
sits below. The tagger pilot compares Jev with reference labels under a threshold committed
first. The scratch tree is tagged and rendered with the released engine and reported per
directory. The firing arm reuses the phase 1 tool with one change (an arm is a set of level
files, each bound over its live file). The apply repeats on the live store exactly what the
scratch run did, between a backup and a verify.

---

## DETAILED: P2a tasks

Conventions for every task below.

- `W` is the worktree root, `<repo>/.claude/worktrees/top-index-design`. Every command starts
  with `cd <W> &&` (written out in full; a bare `cd` does not carry between calls in a
  subagent). `P` is `<W>/plugins/bitranox`.
- `TEST <paths>` stands for the CI command written out in full:
  `env -u VIRTUAL_ENV uv run --with pytest --with PyYAML --with lxml --with defusedxml --with ruamel.yaml --with httpx2 python -m pytest <paths> -q`.
  Run it in the foreground and read pytest's own last line (`N passed` / `N failed`), never
  through a pipe.
- Commit: write the message file with the Write tool in an EARLIER call, then `git status
  --porcelain`, then `git commit -F <msgfile> -- <paths>` (a NEW file is `git add`ed first). The
  PreToolUse commit gate runs the hooks suite (4-8 minutes). A refusal is read and fixed at its
  cause; never `--no-verify`. No attribution line of any kind.
- Python: 3.14 floor, ASCII only. New modules declare `__all__`; `memory_engine.py` declares
  none today and gains none.
- The code and tests of Tasks 1-4 were extracted into a scratch copy of `plugins/` and run
  before this plan was written: the 63 new tests green, the neighbouring suites
  (`hooks/tests -k "memory_engine or topic or uuid_store or pin_gate"`: 585 passed;
  `skills/meta-self-improve/tests` and `skills/meta-dream-tree/tests`: 1237 passed), the whole
  hooks suite with no failure outside tests that need the real checkout (a `.git`, `.github/`,
  `githooks/`, the backlog file), and the hand mutations listed in the tasks, every arm killed.
  A mutation that survives during execution is a finding to report, not to wave through.
- A mutation arm that keeps a file's size (`< 2` to `< 1`) needs `PYTHONDONTWRITEBYTECODE=1` and
  a removed `__pycache__`, or the stale bytecode runs and the arm reads as survived. Use
  `bitranox:compuse-toolbox` `mutation_arm.py`, which handles it.

### Task 1: M1 - open the release and add the placement rules

**Files:**
- Modify: `plugins/bitranox/.claude-plugin/plugin.json`, `pyproject.toml`, `CHANGELOG.md` (via
  `bump_version.py`)
- Create: `plugins/bitranox/hooks/topic_placement.py`
- Test: `plugins/bitranox/hooks/tests/test_topic_placement.py`

**Interfaces:**
- Produces (all in `topic_placement`, imported as `tp`): `Level = tuple[str, ...]`, `TOP = ()`,
  `MAX_TOPICS = 12`, `InvalidTopic(ValueError)`,
  `normalise_topics(raw: Iterable[str]) -> tuple[str, ...]`,
  `parse_topics(value: str) -> tuple[str, ...]`, `format_topics(topics) -> str`,
  `descriptor_topics(scope: str) -> tuple[str, ...] | None`,
  `with_descriptor_topics(scope: str, topics) -> str`, `descriptor_digest(scope: str) -> str`,
  `LevelMap(declared: Mapping[Level, Iterable[str]])` with `.levels() -> list[Level]`,
  `.parent(level) -> Level | None`, `.topics(level) -> frozenset[str]`,
  `.placements(topics) -> tuple[Level, ...]`, `.placed_at(level, topics) -> bool`.

**Out of scope** - do NOT touch, though they look related:
- `hooks/memory_engine.py` - nothing imports the new module yet (Task 2 does).
- `hooks/tests/conftest.py` `_HOOK_MODULES` - that map is for hyphenated hook files; an
  underscore module in `hooks/` is importable as it is.

**STOP conditions** - stop and report rather than improvise, if:
- `git fetch origin` shows `origin/master` changed `hooks/memory_engine.py`,
  `hooks/uuid_store.py` or `skills/meta-self-improve/reconcile_memory_index.py` since `d7ae747e`
  (re-read the changed file against Tasks 2-4 before going on);
- the bump jig reports a version origin already holds;
- a step's verification fails twice after one reasonable fix attempt.

- [ ] **Step 1: Open the release.** Write `$SCRATCH/p2a-notes.md`:

```markdown
### Added

- Facts and directories can carry topics. A fact body's frontmatter takes a `topics:` list, a
  level's descriptor a `TOPICS:` line, and each knowledge tree one closed topic list
  (`.claude-memory/topics.json`). New `memory_engine.py` verbs: `topics-show`,
  `topics-set-list`, `set-topics`, `set-level-topics`, `set-top-topics`, `topics-stale`.
  Nothing is placed by topic yet, and a tree without a topic list behaves as before.
- `hooks/topic_placement.py`: the rules that decide where a topic-bound fact's pointer lines go.

### Changed

- `set-scope` keeps a level's `TOPICS:` line when the new descriptor text has none, and refuses
  a text that changes it: topics change only through `set-level-topics` and `set-top-topics`.
```

  Then `cd <W> && git fetch origin && uv run plugins/bitranox/hooks/bump_version.py --part minor --changelog $SCRATCH/p2a-notes.md`
  and commit the three files it changed (message: "release: open the topics-as-data minor").

- [ ] **Step 2: Write the failing tests.** Create
  `plugins/bitranox/hooks/tests/test_topic_placement.py`. The seam is the pure module itself: no
  file, no engine.

```python
"""Tests for the pure placement rules: which levels a topic-bound fact's pointer lines go to."""

import pytest

import topic_placement as tp

A_PY, B_PY, C_RUST, D_MACH = ("a", "python"), ("b", "python"), ("c", "rust"), ("d", "machines")


def _design_tree(**extra):
    """The design's example: /a/python/{x1,x2}, /b/python/{y1,y2}, /c/rust, /d/machines."""
    levels = {
        tp.TOP: [], ("a",): [], ("b",): [], ("c",): [], ("d",): [],
        A_PY: ["python"], A_PY + ("x1",): [], A_PY + ("x2",): [],
        B_PY: ["python"], B_PY + ("y1",): [], B_PY + ("y2",): [],
        C_RUST: ["rust"], D_MACH: ["machines"],
    }
    levels.update(extra)
    return tp.LevelMap(levels)


def test_a_python_rule_is_placed_at_both_python_dirs_and_nowhere_else():
    assert _design_tree().placements(["python"]) == (A_PY, B_PY)


def test_a_level_below_one_that_has_the_topic_gets_no_second_copy():
    tree = tp.LevelMap({tp.TOP: [], ("a",): ["python"], ("a", "x"): ["python"], ("b",): []})
    assert tree.placements(["python"]) == (("a",),)


def test_a_single_child_does_not_roll_up():
    tree = _design_tree()
    assert tree.topics(("a",)) == frozenset()
    assert tree.topics(A_PY) == frozenset({"python"})


def test_a_topic_every_child_has_rolls_up_to_the_parent():
    rolled = tp.LevelMap({tp.TOP: [], ("p",): [], ("p", "one"): ["python", "ci"], ("p", "two"): ["python"]})
    assert rolled.topics(("p",)) == frozenset({"python"})
    assert rolled.placements(["python"]) == (("p",),)
    assert rolled.placements(["ci"]) == (("p", "one"),)


def test_a_roll_up_carries_on_to_the_grandparent():
    tree = tp.LevelMap({tp.TOP: [], ("g",): [], ("g", "p"): [], ("g", "q"): ["python"],
                        ("g", "p", "one"): ["python"], ("g", "p", "two"): ["python"]})
    assert tree.placements(["python"]) == (("g",),)


def test_one_child_without_the_topic_stops_the_roll_up():
    tree = tp.LevelMap({tp.TOP: [], ("p",): [], ("p", "one"): ["python"], ("p", "two"): ["rust"]})
    assert tree.topics(("p",)) == frozenset()
    assert tree.placements(["python"]) == (("p", "one"),)


def test_a_topic_every_child_has_does_not_roll_up_into_the_top():
    tree = tp.LevelMap({tp.TOP: [], ("one",): ["python"], ("two",): ["python"]})
    assert tree.topics(tp.TOP) == frozenset()
    assert tree.placements(["python"]) == (("one",), ("two",))


def test_a_topic_the_top_declares_is_placed_at_the_top_only():
    tree = tp.LevelMap({tp.TOP: ["git"], ("one",): ["git", "python"]})
    assert tree.placements(["git"]) == (tp.TOP,)
    assert tree.placements(["git", "python"]) == (tp.TOP,)


def test_a_fact_whose_topic_no_level_has_falls_back_to_the_top():
    assert _design_tree().placements(["cobol"]) == (tp.TOP,)


def test_two_topics_place_the_fact_at_the_topmost_level_of_each_branch():
    assert _design_tree().placements(["python", "rust"]) == (A_PY, B_PY, C_RUST)
    tree = tp.LevelMap({tp.TOP: [], ("a",): ["ci"], ("a", "x"): ["python"], ("b",): ["python"]})
    assert tree.placements(["python", "ci"]) == (("a",), ("b",))


def test_a_gap_dir_that_is_no_level_is_skipped_when_finding_the_parent():
    tree = tp.LevelMap({tp.TOP: [], ("a",): ["python"], ("a", "gap", "deep"): ["python"]})
    assert tree.parent(("a", "gap", "deep")) == ("a",)
    assert tree.placements(["python"]) == (("a",),)


def test_placed_at_answers_for_one_level():
    tree = _design_tree()
    assert tree.placed_at(A_PY, ["python"]) is True
    assert tree.placed_at(C_RUST, ["python"]) is False
    assert tree.placed_at(tp.TOP, ["cobol"]) is True


def test_normalise_sorts_dedups_and_refuses_a_bad_tag():
    assert tp.normalise_topics(["uv", "python", "uv"]) == ("python", "uv")
    for bad in ("Python", "has space", "", "-lead", "x" * 33, "a,b", "new\nline"):
        with pytest.raises(tp.InvalidTopic):
            tp.normalise_topics([bad])
    with pytest.raises(tp.InvalidTopic):
        tp.normalise_topics("t%d" % i for i in range(tp.MAX_TOPICS + 1))


def test_parse_and_format_round_trip_including_the_empty_list():
    assert tp.parse_topics("[python, uv]") == ("python", "uv")
    assert tp.parse_topics("uv,python") == ("python", "uv")
    assert tp.parse_topics("[]") == () and tp.parse_topics("") == ()
    assert tp.format_topics(["uv", "python"]) == "[python, uv]"
    assert tp.format_topics([]) == "[]"


def test_descriptor_topics_tells_never_tagged_from_tagged_with_none():
    assert tp.descriptor_topics("WHAT: x\nSTACK: y") is None
    assert tp.descriptor_topics("WHAT: x\nTOPICS:\nPLACE-HERE: z") == ()
    assert tp.descriptor_topics("WHAT: x\nTOPICS: uv, python") == ("python", "uv")
    assert tp.descriptor_topics("WHAT: about TOPICS: nothing") is None


def test_with_descriptor_topics_inserts_after_stack_and_replaces_in_place():
    scope = "WHAT: x\nSTACK: y\nCHILDREN:\n- a/: b\nPLACE-HERE: z"
    tagged = tp.with_descriptor_topics(scope, ["uv", "python"])
    assert tagged.split("\n")[2] == "TOPICS: python, uv"
    assert tagged.replace("TOPICS: python, uv\n", "") == scope
    again = tp.with_descriptor_topics(tagged, ["rust"])
    assert again.split("\n")[2] == "TOPICS: rust" and again.count("TOPICS:") == 1
    assert tp.with_descriptor_topics("WHAT: x", []) == "WHAT: x\nTOPICS: "
    assert tp.with_descriptor_topics("", ["a"]) == "TOPICS: a"


def test_descriptor_digest_ignores_the_topics_line_and_sees_every_other_change():
    scope = "WHAT: x\nSTACK: y"
    assert tp.descriptor_digest(scope) == tp.descriptor_digest(tp.with_descriptor_topics(scope, ["a"]))
    assert tp.descriptor_digest(scope) == tp.descriptor_digest("WHAT: x\r\n\nSTACK: y\n")
    assert tp.descriptor_digest(scope) != tp.descriptor_digest("WHAT: x\nSTACK: z")
```

- [ ] **Step 3: Run them to see them fail.**
  `cd <W> && TEST plugins/bitranox/hooks/tests/test_topic_placement.py` - expected: a collection
  error, `ModuleNotFoundError: No module named 'topic_placement'`.

- [ ] **Step 4: Write the module.** Create `plugins/bitranox/hooks/topic_placement.py`:

```python
#!/usr/bin/env python3
"""Where a topic-bound fact's pointer lines go: the pure rules, no file access.

A fact tagged with topics is read only where its topics are: its pointer is rendered at every
level that has one of its topics and no ancestor that has one. A level HAS a topic when its
descriptor declares it (the `TOPICS:` line) or when it has two or more child levels and every
one of them has it, in which case one line at the parent replaces a copy per child. Nothing here opens a file; memory_engine reads the
tree and asks.

Decisions:
    - The tree top's topics are only the ones its descriptor declares; a topic every child has
      does not roll up into it. Why: the top's block is read by every session of the tree, so
      what it holds is the user's choice and never a computed consequence of what sits below.
      Evidence: argued (the design's safeguard that a change to the top's topics is proposed,
      never applied). Reopen if: a tree keeps one topic at every child of the top and the
      per-child copies are measured to cost more than one line at the top would.
      Pinned by: tests/test_topic_placement.py::test_a_topic_every_child_has_does_not_roll_up_into_the_top
    - A level with ONE child level takes nothing from it. Why: rolling up exists to replace
      several copies by one line, and with one child there is one copy either way, while the
      parent's own sessions would start reading a rule nobody placed there. Evidence: the
      design's example (/a/python and /b/python keep their lines, /a and /b get none).
      Reopen if: never for cost; only if a single-child container should read its child's rules.
      Pinned by: tests/test_topic_placement.py::test_a_single_child_does_not_roll_up
    - A fact whose topics no level has is placed at the top. Why: a rule nobody reads is lost,
      and a rule read too widely only costs bytes. Reopen if: never - it is the safeguard.
      Pinned by: tests/test_topic_placement.py::test_a_fact_whose_topic_no_level_has_falls_back_to_the_top
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable, Mapping

__all__ = [
    "MAX_TOPICS",
    "TOP",
    "InvalidTopic",
    "Level",
    "LevelMap",
    "descriptor_digest",
    "descriptor_topics",
    "format_topics",
    "normalise_topics",
    "parse_topics",
    "with_descriptor_topics",
]

Level = tuple[str, ...]
"""A level as its path parts below the tree top; the top itself is the empty tuple."""

TOP: Level = ()
MAX_TOPICS = 12
"""Most topics one fact or one descriptor may carry: a bound on a field, so one item cannot make
a pointer line or a descriptor arbitrarily long."""

_TOPIC_RX = re.compile(r"[a-z0-9][a-z0-9-]{0,31}")
_TOPICS_LINE_RX = re.compile(r"(?m)^TOPICS:[ \t]*([^\r\n]*)$")


class InvalidTopic(ValueError):
    """A topic that is not a plain tag, or more topics than one item may carry."""


def normalise_topics(raw: Iterable[str]) -> tuple[str, ...]:
    """`raw` as a sorted tuple without repeats. Raises InvalidTopic for a tag that is not lower
    case letters, digits and dashes (at most 32 characters, starting with a letter or digit), and
    for more than MAX_TOPICS tags."""
    seen: set[str] = set()
    for item in raw:
        tag = item.strip() if isinstance(item, str) else item
        if not isinstance(tag, str) or not _TOPIC_RX.fullmatch(tag):
            raise InvalidTopic("invalid topic %r - use lower case letters, digits and dashes, "
                               "at most 32 characters" % (item,))
        seen.add(tag)
        if len(seen) > MAX_TOPICS:
            raise InvalidTopic("more than %d topics" % MAX_TOPICS)
    return tuple(sorted(seen))


def parse_topics(value: str) -> tuple[str, ...]:
    """The topics in a stored value: `[a, b]`, `a, b` or an empty list `[]`."""
    inner = value.strip()
    if inner.startswith("[") and inner.endswith("]"):
        inner = inner[1:-1]
    return normalise_topics(part for part in inner.split(",") if part.strip())


def format_topics(topics: Iterable[str]) -> str:
    """The stored form of a topic list: `[a, b]`, and `[]` for none."""
    return "[%s]" % ", ".join(normalise_topics(topics))


def descriptor_topics(scope: str) -> tuple[str, ...] | None:
    """The topics a level's descriptor declares on its `TOPICS:` line; None when it has no such
    line (the level was never tagged), an empty tuple when the line is there and empty."""
    m = _TOPICS_LINE_RX.search(scope or "")
    return None if m is None else parse_topics(m.group(1))


def with_descriptor_topics(scope: str, topics: Iterable[str]) -> str:
    """`scope` with its `TOPICS:` line set. A descriptor without the line gains it after the
    `STACK:` line, or at the end when it has none; every other line is kept as it is."""
    line = "TOPICS: %s" % ", ".join(normalise_topics(topics))
    text = (scope or "").strip("\n")
    if _TOPICS_LINE_RX.search(text):
        return _TOPICS_LINE_RX.sub(lambda _m: line, text, count=1)
    out, placed = [], False
    for row in text.split("\n") if text else []:
        out.append(row)
        if not placed and row.startswith("STACK:"):
            out.append(line)
            placed = True
    if not placed:
        out.append(line)
    return "\n".join(out)


def descriptor_digest(scope: str) -> str:
    """A digest of what a descriptor SAYS, its `TOPICS:` line left out and blank lines and line
    ends ignored: equal digests mean the text the topics were chosen from has not changed."""
    rows = [row.strip() for row in _TOPICS_LINE_RX.sub("", scope or "").split("\n")]
    return hashlib.sha256("\n".join(row for row in rows if row).encode("utf-8")).hexdigest()


class LevelMap:
    """The levels of one tree and the topics each one has. Holds one small record per level."""

    def __init__(self, declared: Mapping[Level, Iterable[str]]) -> None:
        self._declared = {tuple(level): frozenset(normalise_topics(topics))
                          for level, topics in declared.items()}
        self._declared.setdefault(TOP, frozenset())
        self._children: dict[Level, list[Level]] = {level: [] for level in self._declared}
        for level in self._declared:
            parent = self.parent(level)
            if parent is not None:
                self._children[parent].append(level)
        self._effective: dict[Level, frozenset[str]] = {}
        for level in sorted(self._declared, key=len, reverse=True):   # children before parents
            self._effective[level] = self._declared[level] | self._rolled_up(level)

    def parent(self, level: Level) -> Level | None:
        """The nearest level above `level` that is in the map; None for the top."""
        for cut in range(len(level) - 1, -1, -1):
            if level[:cut] in self._declared:
                return level[:cut]
        return None

    def _rolled_up(self, level: Level) -> frozenset[str]:
        children = self._children[level]
        if level == TOP or len(children) < 2:
            return frozenset()
        return frozenset.intersection(*(self._effective[child] for child in children))

    def levels(self) -> list[Level]:
        """Every level, the top first, then by path."""
        return sorted(self._declared, key=lambda level: (len(level), level))

    def topics(self, level: Level) -> frozenset[str]:
        """The topics `level` has: declared there, or had by every one of its two or more
        child levels."""
        return self._effective[tuple(level)]

    def placements(self, topics: Iterable[str]) -> tuple[Level, ...]:
        """The levels a fact with `topics` gets a pointer line at: each level that has one of the
        topics while no level above it does. `(TOP,)` when no level has any of them."""
        wanted = frozenset(topics)
        hit = {level for level in self._declared if self._effective[level] & wanted}
        out = [level for level in hit if not self._has_ancestor_in(level, hit)]
        return tuple(sorted(out, key=lambda level: (len(level), level))) or (TOP,)

    def placed_at(self, level: Level, topics: Iterable[str]) -> bool:
        """True when a fact with `topics` gets a pointer line at `level`."""
        return tuple(level) in self.placements(topics)

    def _has_ancestor_in(self, level: Level, hit: set[Level]) -> bool:
        parent = self.parent(level)
        while parent is not None:
            if parent in hit:
                return True
            parent = self.parent(parent)
        return False
```

- [ ] **Step 5: Run the tests.** Same command as Step 3 - expected: `17 passed`.

- [ ] **Step 6: Mutation check.** With `mutation_arm.py` (bitranox:compuse-toolbox), one arm
  each; every arm must turn a test RED: `len(children) < 2` to `len(children) < 1`;
  `if level == TOP or len(children) < 2:` to `if len(children) < 2:`; `or (TOP,)` to `or ()`;
  `if not self._has_ancestor_in(level, hit)` to `if True`; `frozenset.intersection` to
  `frozenset.union`.

- [ ] **Step 7: Commit.** `git add` the two new files; message "topic_placement: where a
  topic-bound fact's pointer lines go"; `git commit -F <msg> -- plugins/bitranox/hooks/topic_placement.py plugins/bitranox/hooks/tests/test_topic_placement.py`.

### Task 2: M2a - a body keeps its `topics:` line

**Files:**
- Modify: `plugins/bitranox/hooks/memory_engine.py` (imports at lines 39-42; new helpers before
  `_retype_body`, line 704; one expression in `upsert_entry`, line 440)
- Test: `plugins/bitranox/hooks/tests/test_memory_engine_topics_field.py`

**Interfaces:**
- Consumes: `tp.parse_topics`, `tp.format_topics`, `tp.InvalidTopic` (Task 1); `_frontmatter`,
  `_with_frame` (existing).
- Produces: `memory_engine._body_topics(text) -> tuple[str, ...] | None`,
  `memory_engine._with_topics(text, topics: tuple[str, ...] | None) -> str`; and the behaviour
  that `upsert_entry` keeps the stored `topics:` line on every update.

**Out of scope:**
- `backfill_titles`, `retitle_entry`, `rename_entry` - they rewrite one frontmatter line in
  place and keep every other line, the `topics:` line included.
- Any verb (Task 4).

**STOP conditions:**
- the `upsert_entry` line quoted in Step 4 is not found exactly once;
- a test of `test_memory_engine_body_round_trip.py`, `test_memory_engine_title_field.py` or
  `test_memory_engine_skill_field.py` fails after the change.

- [ ] **Step 1: Write the failing tests.** Create
  `plugins/bitranox/hooks/tests/test_memory_engine_topics_field.py`. The helper tests drive the
  two functions; the three update tests drive `add_or_update_entry`, the real write path, and
  read the stored body file.

```python
"""Tests for the body frontmatter `topics:` line - the topics a fact is bound to, kept as data.

A fact with topics is read only where its topics are; the list lives in the body's frontmatter
and changes only through `set-topics`. `topics: []` means tagged and bound to no topic; no line
means never tagged. An ordinary write to the fact keeps the stored line. All content ASCII.
"""

import pytest

import memory_engine as E
import uuid_store as us

HOOK = "When a fact carries topics, keep them through every ordinary write."
FRAME = "---\nname: s\ndescription: d\ntitle: T\nmetadata:\n  type: feedback\n---\n\nprose\n"


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch):
    h = tmp_path / "home"
    h.mkdir(exist_ok=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    return h


def _tree(tmp_path):
    anchor = tmp_path / "tree"
    proj = anchor / "proj"
    proj.mkdir(parents=True)
    for d in (anchor, proj):
        (d / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (anchor / us.STORE_DIRNAME).mkdir()
    return str(anchor), str(proj)


def _stored(anchor, slug):
    return us.body_path(anchor, slug).read_text(encoding="utf-8")


def test_body_topics_tells_never_tagged_from_bound_to_none():
    assert E._body_topics(FRAME) is None
    assert E._body_topics(E._with_topics(FRAME, ())) == ()
    assert E._body_topics(E._with_topics(FRAME, ("uv", "python"))) == ("python", "uv")


def test_with_topics_adds_the_line_after_the_title_and_touches_nothing_else():
    tagged = E._with_topics(FRAME, ("python",))
    assert tagged.split("\n")[3:5] == ["title: T", "topics: [python]"]
    assert tagged.replace("topics: [python]\n", "") == FRAME


def test_with_topics_replaces_in_place_and_none_removes_the_line():
    tagged = E._with_topics(E._with_topics(FRAME, ("python",)), ("rust",))
    assert tagged.count("topics:") == 1 and "topics: [rust]" in tagged
    assert E._with_topics(tagged, None) == FRAME


def test_with_topics_falls_back_to_description_then_name_when_there_is_no_title():
    no_title = FRAME.replace("title: T\n", "")
    assert E._with_topics(no_title, ("a",)).split("\n")[2:4] == ["description: d", "topics: [a]"]
    bare = "---\nname: s\n---\n\nprose\n"
    assert E._with_topics(bare, ("a",)).split("\n")[1:3] == ["name: s", "topics: [a]"]


def test_a_topics_line_in_the_prose_or_an_unframed_body_is_not_the_field():
    assert E._body_topics("topics: [python]\n\nprose") is None
    assert E._body_topics(FRAME + "topics: [python]\n") is None
    assert E._with_topics("just prose", ("a",)) == "just prose"


def test_a_line_that_is_no_topic_list_reads_as_never_tagged():
    assert E._body_topics(FRAME.replace("title: T\n", "title: T\ntopics: [Not A Tag]\n")) is None


def test_an_update_with_an_unframed_body_keeps_the_stored_topics(tmp_path):
    anchor, proj = _tree(tmp_path)
    slug = E.add_or_update_entry(proj, title="T", hook=HOOK, body="first", type_="feedback")
    us.put_body(anchor, slug, E._with_topics(_stored(anchor, slug), ("python",)))
    E.add_or_update_entry(proj, title="T", hook=HOOK, body="second, unframed", slug=slug)
    stored = _stored(anchor, slug)
    assert "second, unframed" in stored and E._body_topics(stored) == ("python",)


def test_an_update_whose_framed_body_carries_other_topics_keeps_the_stored_ones(tmp_path):
    anchor, proj = _tree(tmp_path)
    slug = E.add_or_update_entry(proj, title="T", hook=HOOK, body="first", type_="feedback")
    us.put_body(anchor, slug, E._with_topics(_stored(anchor, slug), ("python",)))
    edited = E._with_topics(_stored(anchor, slug), ("rust",)).replace("first", "edited")
    E.add_or_update_entry(proj, title="T", hook=HOOK, body=edited, slug=slug)
    stored = _stored(anchor, slug)
    assert "edited" in stored and E._body_topics(stored) == ("python",)


def test_an_update_of_a_fact_never_tagged_does_not_gain_a_topics_line(tmp_path):
    anchor, proj = _tree(tmp_path)
    slug = E.add_or_update_entry(proj, title="T", hook=HOOK, body="first", type_="feedback")
    E.add_or_update_entry(proj, title="T", hook=HOOK, body="second", slug=slug)
    assert "topics:" not in _stored(anchor, slug)
```

- [ ] **Step 2: Run them to see them fail.**
  `cd <W> && TEST plugins/bitranox/hooks/tests/test_memory_engine_topics_field.py` - expected:
  9 failed, each with `AttributeError: module 'memory_engine' has no attribute '_body_topics'`
  or `'_with_topics'`.

- [ ] **Step 3: Import the placement module.** In `memory_engine.py` replace

```python
import tell_chars
import uuid_store as us
```

  with

```python
import tell_chars
import topic_placement as tp
import uuid_store as us
```

- [ ] **Step 4: Add the helpers and keep the line through an update.** Insert directly above
  `def _retype_body(slug, hook, type_, text):`:

```python
def _body_topics(text):
    """The topics a framed body's frontmatter carries on its `topics:` line: None when the line is
    absent (the fact was never tagged), an empty tuple for `topics: []` (tagged, and bound to no
    topic), else the sorted tags. Scoped to the leading frontmatter block (see `_frontmatter`),
    like `_body_title`. A line that does not parse as a topic list reads as None: the fact is
    then placed by nothing, and stays where its pointer is."""
    _head, m = _frontmatter(text)
    if m is None:
        return None
    t = re.search(r"(?m)^topics:[ \t]*([^\r\n]*)", m.group(1))
    if t is None:
        return None
    try:
        return tp.parse_topics(t.group(1))
    except tp.InvalidTopic:
        return None


def _with_topics(text, topics):
    """Return framed `text` with its frontmatter `topics:` line set to `topics`, prose untouched;
    `topics=None` removes the line. A frame without the key gains it after `title:` (else after
    `description:`, else after `name:`). An unframed `text` is returned unchanged: every write
    path frames first."""
    head, m = _frontmatter(text)
    if m is None:
        return text
    inner = m.group(1)
    nl = "\r\n" if inner.endswith("\r\n") else "\n"
    if topics is None:
        new_inner = re.sub(r"(?m)^topics:[^\r\n]*\r?\n", "", inner, count=1)
        return _with_frame(head, m, new_inner)
    line = "topics: %s" % tp.format_topics(topics)
    new_inner, n = re.subn(r"(?m)^topics:[^\r\n]*", lambda _t: line, inner, count=1)
    for key in ("title", "description", "name"):
        if n:
            break
        new_inner, n = re.subn(r"(?m)^(%s:[^\r\n]*)(?=\r?$)" % key,
                               lambda t: "%s%s%s" % (t.group(1), nl, line), inner, count=1)
    return _with_frame(head, m, new_inner) if n else text
```

  Then, in `upsert_entry`, replace the one line

```python
                e.body = _with_skill(_synced_frame(slug, e.hook, type_, framed), kept_skill)
```

  with

```python
                # The stored topics win over whatever the new body's frame says or lacks: topics
                # change only through set-topics.
                e.body = _with_topics(_with_skill(_synced_frame(slug, e.hook, type_, framed),
                                                  kept_skill), _body_topics(e.body))
```

  (`e.body` on the right is still the STORED body: the assignment has not happened yet.)

- [ ] **Step 5: Run the tests.** Step 2's command - expected: `9 passed`. Then
  `cd <W> && TEST plugins/bitranox/hooks/tests -k "memory_engine or pin_gate"` - expected: no
  failure.

- [ ] **Step 6: Mutation check.** Two arms on the new `upsert_entry` expression, both must go
  RED: `_body_topics(e.body)` to `_body_topics(framed)` (the handed-in frame would win), and to
  `None` (the line would be dropped).

- [ ] **Step 7: Commit** `memory_engine.py` and the new test file; message "memory_engine: a
  body's topics: line is kept through every ordinary write".

### Task 3: M2b - the tree's closed topic list

**Files:**
- Create: `plugins/bitranox/hooks/topic_store.py`
- Test: `plugins/bitranox/hooks/tests/test_topic_store.py`

**Interfaces:**
- Consumes: `us.read_store_text`, `us.write_if_changed`, `us.STORE_DIRNAME`, `sig.memory_lock`,
  `sig.refuse_if_memory_writes_off`, `tp.normalise_topics`.
- Produces: `topic_store.store_path(anchor) -> Path`, `level_key(anchor, level) -> str`,
  `load(anchor) -> dict | None` (keys `version`, `tagger`, `topics`, `levels`),
  `save_list(anchor, topics: Mapping[str, str], tagger: str) -> bool`,
  `record_level(anchor, level, digest: str) -> bool`, `TopicStoreError(ValueError)`,
  `MAX_LIST = 64`, `MAX_MEANING = 200`, `TAGGERS = ("jev", "opus")`.

**Out of scope:**
- Whether a dropped topic is still in use: the module never reads a fact; Task 4's
  `set_topic_list` asks before it calls `save_list`.
- `store_manifest.py`: the topic file sits in the store dir, which the backup already copies
  whole. CHECKPOINT A confirms that with a backup of a planted tree (Task 6, Step 3).

**STOP conditions:**
- `us.read_store_text` no longer returns `""` for a missing file (the "no list" answer rests on
  it; `uuid_store.py` line 514).

- [ ] **Step 1: Write the failing tests.** Create `plugins/bitranox/hooks/tests/test_topic_store.py`:

```python
"""Tests for the topic file: a tree's closed topic list and the per-level descriptor digests."""

import json

import pytest

import self_improve_signals as sig
import topic_placement as tp
import topic_store
import uuid_store as us


def _anchor(tmp_path):
    anchor = tmp_path / "tree"
    (anchor / us.STORE_DIRNAME).mkdir(parents=True)
    return anchor


def test_no_file_means_no_list(tmp_path):
    assert topic_store.load(_anchor(tmp_path)) is None


def test_save_then_load_round_trips_and_the_file_is_sorted_json(tmp_path):
    anchor = _anchor(tmp_path)
    assert topic_store.save_list(anchor, {"uv": "uv projects", "python": "Python code"}, "jev") is True
    data = topic_store.load(anchor)
    assert data["topics"] == {"python": "Python code", "uv": "uv projects"} and data["tagger"] == "jev"
    raw = topic_store.store_path(anchor).read_text(encoding="utf-8")
    assert json.loads(raw) == data and raw.index('"python"') < raw.index('"uv"')
    assert topic_store.save_list(anchor, {"uv": "uv projects", "python": "Python code"}, "jev") is False


def test_a_new_list_keeps_the_recorded_levels(tmp_path):
    anchor = _anchor(tmp_path)
    topic_store.save_list(anchor, {"python": "Python code"}, "opus")
    (anchor / "a" / "b").mkdir(parents=True)
    topic_store.record_level(anchor, anchor / "a" / "b", "d1")
    topic_store.record_level(anchor, anchor, "d0")
    topic_store.save_list(anchor, {"rust": "Rust code"}, "opus")
    assert topic_store.load(anchor)["levels"] == {"": "d0", "a/b": "d1"}


@pytest.mark.parametrize("topics, tagger", [
    ({"python": "ok"}, "gpt"),
    ({"python": ""}, "jev"),
    ({"python": "two\nlines"}, "jev"),
    ({"python": "x" * (topic_store.MAX_MEANING + 1)}, "jev"),
    ({"python": 7}, "jev"),
    ({"t%d" % i: "m" for i in range(topic_store.MAX_LIST + 1)}, "jev"),
])
def test_an_unacceptable_list_is_refused_and_nothing_is_written(tmp_path, topics, tagger):
    anchor = _anchor(tmp_path)
    with pytest.raises((topic_store.TopicStoreError, tp.InvalidTopic)):
        topic_store.save_list(anchor, topics, tagger)
    assert not topic_store.store_path(anchor).exists()


def test_a_bad_tag_name_is_refused(tmp_path):
    with pytest.raises(tp.InvalidTopic):
        topic_store.save_list(_anchor(tmp_path), {"Not A Tag": "m"}, "jev")


def test_a_damaged_file_is_an_error_never_an_absent_list(tmp_path):
    anchor = _anchor(tmp_path)
    topic_store.store_path(anchor).write_text("{not json", encoding="utf-8")
    with pytest.raises(topic_store.TopicStoreError):
        topic_store.load(anchor)
    topic_store.store_path(anchor).write_text('["a list"]', encoding="utf-8")
    with pytest.raises(topic_store.TopicStoreError):
        topic_store.load(anchor)


def test_recording_a_level_needs_a_list(tmp_path):
    anchor = _anchor(tmp_path)
    with pytest.raises(topic_store.TopicStoreError):
        topic_store.record_level(anchor, anchor, "d")


def test_writes_are_refused_when_memory_writes_are_off(tmp_path, monkeypatch):
    anchor = _anchor(tmp_path)
    monkeypatch.setenv("BITRANOX_MEMORY_WRITES", "off")
    with pytest.raises(sig.MemoryWritesOff):
        topic_store.save_list(anchor, {"python": "m"}, "jev")
    assert not topic_store.store_path(anchor).exists()


def test_level_key_is_posix_relative_and_keeps_a_leading_dot_name(tmp_path):
    anchor = _anchor(tmp_path)
    (anchor / ".cfg" / "x").mkdir(parents=True)
    assert topic_store.level_key(anchor, anchor) == ""
    assert topic_store.level_key(anchor, anchor / ".cfg" / "x") == ".cfg/x"
```

- [ ] **Step 2: Run them to see them fail.**
  `cd <W> && TEST plugins/bitranox/hooks/tests/test_topic_store.py` - expected: a collection
  error, `ModuleNotFoundError: No module named 'topic_store'`.

- [ ] **Step 3: Write the module.** Create `plugins/bitranox/hooks/topic_store.py`:

```python
#!/usr/bin/env python3
"""The closed topic list of one knowledge tree, and what each level was tagged from.

One JSON file beside the fact bodies, `<anchor>/.claude-memory/topics.json`:

    {"version": 1, "tagger": "jev", "topics": {"python": "Python code and its tooling"},
     "levels": {"projects/libs": "<digest of the descriptor its topics were chosen from>"}}

`topics` is the list a fact or a level may be tagged from; a tag outside it is refused by the
engine, so the list is closed until someone replaces it. `levels` lets a later run see that a
level's descriptor changed since its topics were chosen. No file means the tree has no topic
list, and nothing is placed by topic there. Written only through memory_engine.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

import self_improve_signals as sig
import topic_placement as tp
import uuid_store as us

__all__ = ["MAX_LIST", "MAX_MEANING", "TAGGERS", "TopicStoreError", "level_key", "load",
           "record_level", "save_list", "store_path"]

MAX_LIST = 64
"""Most topics a tree's list may hold: every one becomes a question about every fact."""
MAX_MEANING = 200
TAGGERS = ("jev", "opus")
_EMPTY = {"version": 1, "tagger": "opus", "topics": {}, "levels": {}}


class TopicStoreError(ValueError):
    """The topic file cannot be used as it is, or a new list is not acceptable."""


def store_path(anchor) -> Path:
    """`<anchor>/.claude-memory/topics.json`."""
    return Path(anchor) / us.STORE_DIRNAME / "topics.json"


def level_key(anchor, level) -> str:
    """A level as the file records it: its path below the anchor with `/` separators, and the
    empty string for the anchor itself."""
    rel = Path(level).resolve().relative_to(Path(anchor).resolve()).as_posix()
    return "" if rel == "." else rel


def load(anchor) -> dict | None:
    """The topic file's content, or None when the tree has none. Raises TopicStoreError for a
    file that is not the JSON object this module writes, and TreeWalkError for one that cannot
    be read: a list read as absent would switch placement by topic off without a word."""
    text = us.read_store_text(store_path(anchor))
    if text == "":
        return None
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise TopicStoreError("%s is not valid JSON (%s)" % (store_path(anchor), exc)) from exc
    if not (isinstance(data, dict) and isinstance(data.get("topics"), dict)
            and isinstance(data.get("levels", {}), dict)):
        raise TopicStoreError("%s is not a topic file (no 'topics' object)" % store_path(anchor))
    data.setdefault("levels", {})
    data.setdefault("tagger", "opus")
    return data


def _write(anchor, data) -> bool:
    text = json.dumps(data, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    json.loads(text)                                  # what is written must load again
    return us.write_if_changed(store_path(anchor), text)


def save_list(anchor, topics: Mapping[str, str], tagger: str) -> bool:
    """Replace the tree's topic list, keeping what the file records per level. True if written.

    Raises TopicStoreError for a tagger outside TAGGERS, more than MAX_LIST topics, or a meaning
    that is not one line of at most MAX_MEANING characters; InvalidTopic for a name that is not
    a plain tag. Whether a dropped topic is still in use is the caller's question: this module
    never reads a fact."""
    sig.refuse_if_memory_writes_off()
    if tagger not in TAGGERS:
        raise TopicStoreError("unknown tagger %r - use one of %s" % (tagger, ", ".join(TAGGERS)))
    if len(topics) > MAX_LIST:
        raise TopicStoreError("%d topics, over the limit of %d" % (len(topics), MAX_LIST))
    clean = {}
    for name in tp.normalise_topics(topics):
        meaning = topics[name]
        if not isinstance(meaning, str) or not meaning.strip() or len(meaning) > MAX_MEANING \
                or meaning.splitlines() != [meaning]:
            raise TopicStoreError("the meaning of %r must be one line of 1 to %d characters"
                                  % (name, MAX_MEANING))
        clean[name] = meaning.strip()
    with sig.memory_lock(store_path(anchor)):
        data = load(anchor) or dict(_EMPTY)
        return _write(anchor, {"version": 1, "tagger": tagger, "topics": clean,
                               "levels": dict(data["levels"])})


def record_level(anchor, level, digest: str) -> bool:
    """Record the descriptor digest `level`'s topics were chosen from. True if written."""
    sig.refuse_if_memory_writes_off()
    with sig.memory_lock(store_path(anchor)):
        data = load(anchor)
        if data is None:
            raise TopicStoreError("this tree has no topic list yet")
        levels = dict(data["levels"])
        levels[level_key(anchor, level)] = digest
        return _write(anchor, {**data, "levels": levels})
```

- [ ] **Step 4: Run the tests.** Step 2's command - expected: `14 passed`.

- [ ] **Step 5: Commit** the two new files; message "topic_store: one closed topic list per
  knowledge tree".

### Task 4: M2c - the topic verbs

**Files:**
- Modify: `plugins/bitranox/hooks/memory_engine.py` (imports; `WRITE_VERBS`, lines 44-45; a new
  section above the `# ---- multi-tree:` comment, line 1893; `_topic_write` above the
  `# ---- CLI:` comment, line 1996; the parser, before `raw = sys.argv[1:] if argv is None else
  argv`, line 2145; the dispatch, before `if args.cmd == "ensure-all-trees":`, line 2163; the
  `set-scope` branch, lines 2247-2258. Line numbers are those before Task 2; find each anchor by
  its text.)
- Test: `plugins/bitranox/hooks/tests/test_memory_engine_topics_verbs.py`

**Interfaces:**
- Consumes: Tasks 1-3; `curated_levels_under`, `read_store_text`, `_read_input_file`,
  `_input_error`, `_refused`, `_anchor` (existing).
- Produces: `FRONTMATTER_HEAD_BYTES = 16384`, `MAX_TOPIC_BATCH = 5000`,
  `TopicRefusal(ValueError)` with `.reasons` and `.total`,
  `read_body_topics(path) -> tuple[str, ...] | None`,
  `iter_fact_topics(anchor) -> Iterator[tuple[str, tuple[str, ...]]]`,
  `set_topic_list(proj, topics: Mapping[str, str], tagger: str) -> bool`,
  `set_fact_topics(proj, rows: Mapping[str, tuple[str, ...] | None], dry_run=False) -> dict`
  (`{"set": [slug], "unchanged": int}`), `set_level_topics(level, topics, top=False) -> bool`,
  `level_topics_stale(level) -> tuple[bool, str]`,
  `scope_keeping_topics(old_scope, new_scope) -> str`; the six CLI verbs of M2; exit codes in
  the engine's scheme (0 done, 1 the check's "no" for `topics-show` and `topics-stale`, 2 a
  usage error or a refusal with `! refused:` on stdout).

**Out of scope:**
- Pointer lines: no verb here adds, moves or removes one (the renderer is Task 7+).
- `hooks/tests/test_memory_writes_switch.py`: it is parametrized over `WRITE_VERBS` and picks
  the four new write verbs up by itself.
- `block-write-after-sibling-cd.py`: its `WRITE_VERBS` is a set of its own (git subcommands),
  unrelated to the engine's despite the name.

**STOP conditions:**
- an anchor text of Step 3 is not found exactly once;
- `test_memory_writes_switch.py` fails for a new verb (the refusal must precede argparse, as for
  every write verb);
- a mutation arm of Step 5 survives.

**What is held in memory:** `set_fact_topics` holds the batch (`rows`, at most 5000 entries) and
one owner entry per row; the level walk holds one level file at a time; `iter_fact_topics` holds
one body head (16384 bytes) at a time; `set_topic_list` holds the first 20 users of a dropped
topic and a count.

- [ ] **Step 1: Write the failing tests.** Create
  `plugins/bitranox/hooks/tests/test_memory_engine_topics_verbs.py`. Every behaviour is driven
  through `E.main([...])` or the public function and asserted on the stored file; the scan's
  memory test plants bodies of 200 KB each and requires the peak to stay under one body.

```python
"""Tests for the topic verbs: the closed list, a fact's topics, a level's TOPICS line.

Topics are data the placement of pointer lines is later computed from, so each write is checked
whole before anything is written, the tree top's topics have a verb of their own, and a rewritten
descriptor can neither drop nor change a level's topics. All content ASCII.
"""

import json
import tracemalloc

import pytest

import memory_engine as E
import self_improve_signals as sig
import topic_placement as tp
import topic_store
import uuid_store as us

HOOK = "When a rule is about one stack, bind it to that stack's topic."
SCOPE = "WHAT: a level\nSTACK: python\nCHILDREN:\n- x/: y\nPLACE-HERE: a\nPLACE-ELSEWHERE: b"
LIST = {"python": "Python code and its tooling", "rust": "Rust code", "git": "git and GitHub"}


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch):
    h = tmp_path / "home"
    h.mkdir(exist_ok=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    return h


def _tree(tmp_path, with_list=True):
    anchor = tmp_path / "tree"
    proj = anchor / "proj"
    proj.mkdir(parents=True)
    for d in (anchor, proj):
        (d / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (anchor / us.STORE_DIRNAME).mkdir()
    if with_list:
        topic_store.save_list(anchor, LIST, "jev")
    return str(anchor), str(proj)


def _fact(proj, slug, pin=False):
    return E.add_or_update_entry(proj, title="T " + slug, hook=HOOK, body="body of " + slug,
                                 type_="feedback", slug=slug, pin=pin)


def _topics(anchor, slug):
    return E._body_topics(us.body_path(anchor, slug).read_text(encoding="utf-8"))


def _scope(level):
    return us.parse_pointer_index(sig.claude_local_md_path(level).read_text(encoding="utf-8"))[0]


def _list_file(tmp_path, topics, tagger="jev"):
    f = tmp_path / "list.json"
    f.write_text(json.dumps({"tagger": tagger, "topics": topics}), encoding="utf-8")
    return str(f)


# ---- the list ----------------------------------------------------------------------------------

def test_topics_show_exits_1_without_a_list_and_prints_it_with_one(tmp_path, capsys):
    anchor, proj = _tree(tmp_path, with_list=False)
    assert E.main(["topics-show", "--proj", proj]) == 1
    assert "no topic list" in capsys.readouterr().out
    assert E.main(["topics-set-list", "--proj", proj, "--from-file", _list_file(tmp_path, LIST)]) == 0
    capsys.readouterr()
    assert E.main(["topics-show", "--proj", proj, "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == {"tagger": "jev", "topics": LIST}


def test_a_list_that_drops_a_topic_in_use_is_refused_and_names_the_users(tmp_path, capsys):
    anchor, proj = _tree(tmp_path)
    _fact(proj, "feedback-uses-python")
    E.set_fact_topics(proj, {"feedback-uses-python": ("python",)})
    E.main(["set-scope", "--proj", proj, "--scope", SCOPE])
    E.set_level_topics(proj, ("rust",))
    capsys.readouterr()
    rc = E.main(["topics-set-list", "--proj", proj, "--from-file", _list_file(tmp_path, {"git": "git"})])
    out = capsys.readouterr().out
    assert rc == 2 and "feedback-uses-python carries python" in out and "declares rust" in out
    assert topic_store.load(anchor)["topics"] == LIST


def test_a_list_file_that_is_not_the_expected_json_is_a_usage_error(tmp_path, capsys):
    anchor, proj = _tree(tmp_path, with_list=False)
    bad = tmp_path / "bad.json"
    bad.write_text('{"tagger": "jev", "topics": ["python"]}', encoding="utf-8")
    assert E.main(["topics-set-list", "--proj", proj, "--from-file", str(bad)]) == 2
    assert "must be an object" in capsys.readouterr().err
    assert topic_store.load(anchor) is None


# ---- a fact's topics ---------------------------------------------------------------------------

def test_set_topics_writes_the_line_and_leaves_the_pointer_block_alone(tmp_path, capsys):
    anchor, proj = _tree(tmp_path)
    _fact(proj, "feedback-one")
    before = sig.claude_local_md_path(proj).read_text(encoding="utf-8")
    assert E.main(["set-topics", "--proj", proj, "--slug", "feedback-one", "--topics", "rust,python"]) == 0
    assert "set topics on 1 fact(s); 0 unchanged" in capsys.readouterr().out
    assert _topics(anchor, "feedback-one") == ("python", "rust")
    assert sig.claude_local_md_path(proj).read_text(encoding="utf-8") == before


def test_universal_and_clear_are_different_states(tmp_path):
    anchor, proj = _tree(tmp_path)
    _fact(proj, "feedback-one")
    assert E.main(["set-topics", "--proj", proj, "--slug", "feedback-one", "--universal"]) == 0
    assert _topics(anchor, "feedback-one") == ()
    assert E.main(["set-topics", "--proj", proj, "--slug", "feedback-one", "--clear"]) == 0
    assert _topics(anchor, "feedback-one") is None


def test_set_topics_needs_exactly_one_way_to_say_which(tmp_path, capsys):
    anchor, proj = _tree(tmp_path)
    _fact(proj, "feedback-one")
    assert E.main(["set-topics", "--proj", proj, "--slug", "feedback-one"]) == 2
    assert E.main(["set-topics", "--proj", proj, "--slug", "feedback-one", "--topics", "python",
                   "--universal"]) == 2
    assert "exactly one of" in capsys.readouterr().err
    assert _topics(anchor, "feedback-one") is None


def test_one_bad_row_refuses_the_whole_batch_and_writes_nothing(tmp_path, capsys):
    anchor, proj = _tree(tmp_path)
    for slug in ("feedback-a", "feedback-b"):
        _fact(proj, slug)
    _fact(proj, "feedback-pinned", pin=True)
    batch = tmp_path / "batch.jsonl"
    rows = [{"slug": "feedback-a", "topics": ["python"]}, {"slug": "feedback-b", "topics": ["cobol"]},
            {"slug": "feedback-pinned", "topics": ["git"]}, {"slug": "feedback-gone", "topics": []}]
    batch.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    assert E.main(["set-topics", "--proj", proj, "--batch", str(batch)]) == 2
    out = capsys.readouterr().out
    assert "feedback-b: cobol not in the topic list" in out
    assert "feedback-pinned is pinned" in out and "feedback-gone: no level points at it" in out
    assert _topics(anchor, "feedback-a") is None


def test_a_good_batch_applies_every_row_and_a_second_run_changes_nothing(tmp_path, capsys):
    anchor, proj = _tree(tmp_path)
    for slug in ("feedback-a", "feedback-b", "feedback-c"):
        _fact(proj, slug)
    E.set_fact_topics(proj, {"feedback-c": ("git",)})
    batch = tmp_path / "batch.jsonl"
    rows = [{"slug": "feedback-a", "topics": ["python"]}, {"slug": "feedback-b", "topics": []},
            {"slug": "feedback-c", "topics": None}]
    batch.write_text("\n".join(json.dumps(r) for r in rows) + "\n\n", encoding="utf-8")
    assert E.main(["set-topics", "--proj", proj, "--batch", str(batch)]) == 0
    assert "set topics on 3 fact(s); 0 unchanged" in capsys.readouterr().out
    assert [_topics(anchor, s) for s in ("feedback-a", "feedback-b", "feedback-c")] == [("python",), (), None]
    assert E.main(["set-topics", "--proj", proj, "--batch", str(batch)]) == 0
    assert "set topics on 0 fact(s); 3 unchanged" in capsys.readouterr().out


def test_a_dry_run_reports_and_writes_nothing(tmp_path, capsys):
    anchor, proj = _tree(tmp_path)
    _fact(proj, "feedback-a")
    assert E.main(["set-topics", "--proj", proj, "--slug", "feedback-a", "--topics", "python",
                   "--dry-run"]) == 0
    assert "would set topics on 1 fact(s)" in capsys.readouterr().out
    assert _topics(anchor, "feedback-a") is None


@pytest.mark.parametrize("line", ['{"slug": "feedback-a", "topics": "python"}', '{"slug": "feedback-a"}',
                                  'not json', '{"slug": 7, "topics": []}'])
def test_a_malformed_batch_line_is_a_usage_error_naming_the_line(tmp_path, capsys, line):
    anchor, proj = _tree(tmp_path)
    _fact(proj, "feedback-a")
    batch = tmp_path / "batch.jsonl"
    batch.write_text('{"slug": "feedback-a", "topics": []}\n' + line + "\n", encoding="utf-8")
    assert E.main(["set-topics", "--proj", proj, "--batch", str(batch)]) == 2
    assert "line 2" in capsys.readouterr().err
    assert _topics(anchor, "feedback-a") is None


def test_set_topics_without_a_list_is_refused(tmp_path, capsys):
    anchor, proj = _tree(tmp_path, with_list=False)
    _fact(proj, "feedback-a")
    assert E.main(["set-topics", "--proj", proj, "--slug", "feedback-a", "--universal"]) == 2
    assert "no topic list yet" in capsys.readouterr().out


def test_the_topic_write_verbs_are_refused_when_memory_writes_are_off(tmp_path, monkeypatch, capsys):
    anchor, proj = _tree(tmp_path)
    _fact(proj, "feedback-a")
    monkeypatch.setenv("BITRANOX_MEMORY_WRITES", "off")
    for argv in (["set-topics", "--proj", proj, "--slug", "feedback-a", "--universal"],
                 ["set-level-topics", "--proj", proj, "--topics", "python"],
                 ["set-top-topics", "--proj", anchor, "--topics", "git"],
                 ["topics-set-list", "--proj", proj, "--from-file", _list_file(tmp_path, LIST)]):
        assert E.main(argv) == 2
        assert "refused" in capsys.readouterr().out
    assert _topics(anchor, "feedback-a") is None


# ---- a level's topics --------------------------------------------------------------------------

def test_set_level_topics_writes_the_line_and_the_level_reads_fresh(tmp_path, capsys):
    anchor, proj = _tree(tmp_path)
    E.main(["set-scope", "--proj", proj, "--scope", SCOPE])
    assert E.main(["topics-stale", "--proj", proj]) == 1
    assert "never tagged" in capsys.readouterr().out
    assert E.main(["set-level-topics", "--proj", proj, "--topics", "rust, python"]) == 0
    assert tp.descriptor_topics(_scope(proj)) == ("python", "rust")
    assert _scope(proj).replace("TOPICS: python, rust\n", "") == SCOPE
    capsys.readouterr()
    assert E.main(["topics-stale", "--proj", proj]) == 0
    assert capsys.readouterr().out.strip() == "fresh"


def test_the_tree_top_takes_its_topics_only_from_its_own_verb(tmp_path, capsys):
    anchor, proj = _tree(tmp_path)
    E.main(["set-scope", "--proj", anchor, "--scope", SCOPE])
    E.main(["set-scope", "--proj", proj, "--scope", SCOPE])
    capsys.readouterr()
    assert E.main(["set-level-topics", "--proj", anchor, "--topics", "git"]) == 2
    assert "is the tree top" in capsys.readouterr().out
    assert tp.descriptor_topics(_scope(anchor)) is None
    assert E.main(["set-top-topics", "--proj", proj, "--topics", "git"]) == 2
    assert "is not the tree top" in capsys.readouterr().out
    assert E.main(["set-top-topics", "--proj", anchor, "--topics", "git"]) == 0
    assert tp.descriptor_topics(_scope(anchor)) == ("git",)


def test_a_tag_outside_the_list_and_a_level_without_a_descriptor_are_refused(tmp_path, capsys):
    anchor, proj = _tree(tmp_path)
    E.ensure_level(proj)
    assert E.main(["set-level-topics", "--proj", proj, "--topics", "python"]) == 2
    assert "no descriptor yet" in capsys.readouterr().out
    E.main(["set-scope", "--proj", proj, "--scope", SCOPE])
    capsys.readouterr()
    assert E.main(["set-level-topics", "--proj", proj, "--topics", "cobol"]) == 2
    assert "cobol not in the topic list" in capsys.readouterr().out
    assert tp.descriptor_topics(_scope(proj)) is None


def test_set_scope_keeps_the_stored_topics_and_the_level_then_reads_stale(tmp_path, capsys):
    anchor, proj = _tree(tmp_path)
    E.main(["set-scope", "--proj", proj, "--scope", SCOPE])
    E.main(["set-level-topics", "--proj", proj, "--topics", "python"])
    rewritten = SCOPE.replace("WHAT: a level", "WHAT: another level")
    assert E.main(["set-scope", "--proj", proj, "--scope", rewritten]) == 0
    assert tp.descriptor_topics(_scope(proj)) == ("python",)
    assert "WHAT: another level" in _scope(proj)
    capsys.readouterr()
    assert E.main(["topics-stale", "--proj", proj]) == 1
    assert "descriptor changed" in capsys.readouterr().out


def test_set_scope_refuses_a_text_that_changes_the_topics_line(tmp_path, capsys):
    anchor, proj = _tree(tmp_path)
    E.main(["set-scope", "--proj", proj, "--scope", SCOPE])
    E.main(["set-level-topics", "--proj", proj, "--topics", "python"])
    before = _scope(proj)
    capsys.readouterr()
    assert E.main(["set-scope", "--proj", proj, "--scope", SCOPE + "\nTOPICS: rust"]) == 2
    assert "changes only through set-level-topics" in capsys.readouterr().out
    assert _scope(proj) == before
    assert E.main(["set-scope", "--proj", proj, "--scope", SCOPE + "\nTOPICS: python"]) == 0


def test_topics_stale_is_fresh_in_a_tree_without_a_list(tmp_path, capsys):
    anchor, proj = _tree(tmp_path, with_list=False)
    E.main(["set-scope", "--proj", proj, "--scope", SCOPE])
    assert E.main(["topics-stale", "--proj", proj]) == 0


# ---- the scan over every body ------------------------------------------------------------------

def _plant_bodies(anchor, count, tagged_every=10):
    facts = us.central_facts_dir(anchor)
    facts.mkdir(parents=True, exist_ok=True)
    prose = "x" * 200_000
    for i in range(count):
        topics = "topics: [python]\n" if i % tagged_every == 0 else ""
        (facts / ("feedback-n%05d.md" % i)).write_text(
            "---\nname: feedback-n%05d\ndescription: d\ntitle: T\n%smetadata:\n  type: feedback\n---\n\n%s\n"
            % (i, topics, prose), encoding="utf-8")


def _scan_peak(anchor):
    tracemalloc.start()
    try:
        found = sum(1 for _ in E.iter_fact_topics(anchor))
        return found, tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()


def test_the_scan_yields_only_tagged_bodies_and_its_peak_does_not_grow_with_the_store(tmp_path):
    small, large = tmp_path / "small", tmp_path / "large"
    _plant_bodies(small, 30)
    _plant_bodies(large, 300)
    found_small, peak_small = _scan_peak(small)
    found_large, peak_large = _scan_peak(large)
    assert (found_small, found_large) == (3, 30)
    assert peak_large < 200_000            # one body is 200 KB; the scan never holds one whole
    assert peak_large < peak_small * 2 + 50_000


def test_the_scan_skips_names_that_are_no_fact_and_a_missing_store_yields_nothing(tmp_path):
    anchor = tmp_path / "tree"
    assert list(E.iter_fact_topics(anchor)) == []
    _plant_bodies(anchor, 1)
    facts = us.central_facts_dir(anchor)
    (facts / "notes.txt").write_text("topics: [python]\n", encoding="utf-8")
    (facts / "Bad Name.md").write_text("---\nname: x\ntopics: [python]\n---\n", encoding="utf-8")
    assert list(E.iter_fact_topics(anchor)) == [("feedback-n00000", ("python",))]
```

- [ ] **Step 2: Run them to see them fail.**
  `cd <W> && TEST plugins/bitranox/hooks/tests/test_memory_engine_topics_verbs.py` - expected:
  23 failed (`AttributeError` for `set_fact_topics` / `iter_fact_topics`, argparse exit for the
  unknown verbs).

- [ ] **Step 3: Write the engine side.** Seven edits to `memory_engine.py`, each anchor asserted
  to occur exactly once before it is replaced.

  (a) After `import topic_placement as tp` add `import topic_store`.

  (b) Replace the `WRITE_VERBS` assignment with

```python
WRITE_VERBS = frozenset({"add", "amend-pinned", "move", "relocate", "rename", "retitle", "set-scope",
                         "heal", "ensure-memory-structure", "ensure-all-trees", "topics-set-list",
                         "set-topics", "set-level-topics", "set-top-topics"})
```

  (c) Insert directly above the comment line
  `# ---- multi-tree: whole-machine discovery + scaffolding ---...`:

```python
# ---- topics: which facts and levels a rule is about ------------------------------------------

FRONTMATTER_HEAD_BYTES = 16384
"""How much of a body a topic scan reads: the frontmatter sits at the head, and a scan over every
body of a tree must not read every body whole."""
MAX_TOPIC_BATCH = 5000
"""Most rows one `set-topics --batch` takes: the batch is held as one dict while it is applied."""
_REFUSALS_SHOWN = 20


class TopicRefusal(ValueError):
    """Raised when a topic write is declined as a whole; nothing was written. `reasons` holds the
    first refusals and `total` how many there were."""

    def __init__(self, reasons, total=None):
        self.reasons = list(reasons)
        self.total = len(self.reasons) if total is None else total
        more = "" if self.total <= len(self.reasons) else " (and %d more)" % (self.total - len(self.reasons))
        super().__init__("; ".join(self.reasons) + more)


def read_body_topics(path):
    """`_body_topics` of the body at `path`, reading only its first FRONTMATTER_HEAD_BYTES.
    None too when the file is missing. Raises TreeWalkError when it exists and cannot be read."""
    try:
        with open(path, "rb") as fh:
            head = fh.read(FRONTMATTER_HEAD_BYTES)
    except (FileNotFoundError, NotADirectoryError):
        return None
    except OSError as exc:
        raise TreeWalkError(path, "unreadable: %s" % exc) from exc
    return _body_topics(head.decode("utf-8", errors="replace"))


def iter_fact_topics(anchor):
    """Yield (slug, topics) for every body of the tree that carries a `topics:` line, one body at a
    time: nothing is held but the body's head being read."""
    facts = us.central_facts_dir(anchor)
    try:
        scan = os.scandir(facts)
    except (FileNotFoundError, NotADirectoryError):
        return
    except OSError as exc:
        raise TreeWalkError(facts, "cannot list this directory: %s" % exc) from exc
    with scan:
        for item in scan:
            if not item.name.endswith(".md") or not us.is_valid_slug(item.name[:-3]):
                continue
            topics = read_body_topics(item.path)
            if topics is not None:
                yield item.name[:-3], topics


def _topic_list(anchor):
    """The tree's topic list as {name: meaning}. Raises TopicRefusal when the tree has none."""
    data = topic_store.load(anchor)
    if data is None:
        raise TopicRefusal(["this tree has no topic list yet (topics-set-list writes one)"])
    return data["topics"]


def _outside_list(topics, allowed):
    return [t for t in topics if t not in allowed]


def set_topic_list(proj, topics, tagger):
    """Replace the tree's closed topic list. Raises TopicRefusal, before writing, when a topic the
    new list drops is still carried by a fact or declared by a level, naming the first users."""
    sig.refuse_if_memory_writes_off()
    anchor = _anchor(proj)
    old = topic_store.load(anchor)
    dropped = set(old["topics"]) - set(topics) if old else set()
    users, total = [], 0
    if dropped:
        for slug, carried in iter_fact_topics(anchor):
            if dropped & set(carried):
                total += 1
                if len(users) < _REFUSALS_SHOWN:
                    users.append("fact %s carries %s" % (slug, ", ".join(sorted(dropped & set(carried)))))
        for level in curated_levels_under(anchor):
            scope = us.parse_pointer_index(read_store_text(sig.claude_local_md_path(level)))[0]
            declared = set(tp.descriptor_topics(scope) or ())
            if dropped & declared:
                total += 1
                if len(users) < _REFUSALS_SHOWN:
                    users.append("level %s declares %s" % (level, ", ".join(sorted(dropped & declared))))
    if total:
        raise TopicRefusal(users, total)
    return topic_store.save_list(anchor, topics, tagger)


def _pointer_owners(anchor, wanted):
    """{slug: (first level pointing at it, pinned anywhere)} for the slugs in `wanted`, from one
    walk over the tree's levels. Holds one entry per wanted slug."""
    owners = {}
    for level in curated_levels_under(anchor):
        for ptr in us.parse_pointer_index(read_store_text(sig.claude_local_md_path(level)))[1]:
            if ptr.slug in wanted:
                first, pinned = owners.get(ptr.slug, (level, False))
                owners[ptr.slug] = (first, pinned or ptr.pin)
    return owners


def _topic_row_problem(slug, topics, anchor, allowed, owners):
    """Why this row cannot be applied, or None."""
    if not us.is_valid_slug(slug):
        return "%r is not a valid slug" % (slug,)
    if slug not in owners:
        return "%s: no level points at it" % slug
    if owners[slug][1]:
        return "%s is pinned; a pinned fact stays where it is" % slug
    if topics and _outside_list(topics, allowed):
        return "%s: %s not in the topic list" % (slug, ", ".join(_outside_list(topics, allowed)))
    body = read_store_text(us.body_path(anchor, slug))
    if _frontmatter(body)[1] is None:
        return "%s: its body has no frontmatter to carry topics" % slug
    return None


def set_fact_topics(proj, rows, dry_run=False):
    """Set the `topics:` line of each fact in `rows`, a {slug: topics} mapping where topics is a
    tuple of tags, an empty tuple (bound to no topic) or None (remove the line).

    Every row is checked before any is written: a slug no level points at, a pinned fact, a tag
    outside the tree's list or a body without frontmatter refuses the WHOLE call with TopicRefusal
    (the first refusals and their total). Each body is then read and written under the lock of
    the first level that points at it, the lock an ordinary write to that fact holds. Pointer
    lines are not touched: `render-topics` places them. Returns {'set': [slugs], 'unchanged': n}.
    Holds `rows` and one owner entry per row; a batch over MAX_TOPIC_BATCH rows is refused."""
    if not dry_run:
        sig.refuse_if_memory_writes_off()
    if len(rows) > MAX_TOPIC_BATCH:
        raise TopicRefusal(["%d rows, over the limit of %d per call" % (len(rows), MAX_TOPIC_BATCH)])
    anchor = _anchor(proj)
    allowed = _topic_list(anchor)
    owners = _pointer_owners(anchor, set(rows))
    problems, total = [], 0
    for slug in sorted(rows):
        why = _topic_row_problem(slug, rows[slug], anchor, allowed, owners)
        if why:
            total += 1
            if len(problems) < _REFUSALS_SHOWN:
                problems.append(why)
    if total:
        raise TopicRefusal(problems, total)
    rep = {"set": [], "unchanged": 0}
    for slug in sorted(rows):
        with sig.memory_lock(sig.claude_local_md_path(owners[slug][0])):
            body = read_store_text(us.body_path(anchor, slug)).rstrip("\n")
            tagged = _with_topics(body, rows[slug])
            if tagged == body:
                rep["unchanged"] += 1
                continue
            if not dry_run:
                us.put_body(str(anchor), slug, tagged)
            rep["set"].append(slug)
    return rep


def set_level_topics(level, topics, top=False):
    """Set the `TOPICS:` line of `level`'s descriptor and record the descriptor it was chosen from.

    `top` says which verb is asking. The tree top's topics decide what every session of the tree
    loads, so they change only through `set-top-topics`, a verb of its own that a nap or dream is
    told never to run; `set-level-topics` refuses the top, and `set-top-topics` refuses any other
    level. Raises TopicRefusal before writing for that, for a tag outside the list, and for a
    level with no descriptor to tag. Returns True if the descriptor changed."""
    sig.refuse_if_memory_writes_off()
    level = os.path.abspath(str(level))
    anchor = _anchor(level)
    is_top = Path(level).resolve() == Path(anchor).resolve()
    if is_top and not top:
        raise TopicRefusal(["%s is the tree top: its topics are the user's decision "
                            "(set-top-topics, on the user's word)" % level])
    if top and not is_top:
        raise TopicRefusal(["%s is not the tree top (%s); use set-level-topics" % (level, anchor)])
    topics = tp.normalise_topics(topics)
    bad = _outside_list(topics, _topic_list(anchor))
    if bad:
        raise TopicRefusal(["%s not in the topic list" % ", ".join(bad)])
    local = sig.claude_local_md_path(level)
    with sig.memory_lock(local):
        text = read_store_text(local)
        scope, pointers = us.parse_pointer_index(text)
        if not scope.strip():
            raise TopicRefusal(["%s has no descriptor yet (set-scope writes one)" % level])
        tagged = tp.with_descriptor_topics(scope, topics)
        changed = us.write_if_changed(local, us.upsert_pointer_block(text, tagged, pointers))
    topic_store.record_level(anchor, level, tp.descriptor_digest(tagged))
    return changed


def level_topics_stale(level):
    """(stale, why) for one level: stale when its descriptor has no `TOPICS:` line, or says
    something other than the text its topics were chosen from. (False, "") when fresh, and when
    the tree has no topic list (nothing is tagged there at all)."""
    level = os.path.abspath(str(level))
    anchor = _anchor(level)
    data = topic_store.load(anchor)
    if data is None:
        return False, ""
    scope = us.parse_pointer_index(read_store_text(sig.claude_local_md_path(level)))[0]
    if not scope.strip():
        return True, "no descriptor"
    if tp.descriptor_topics(scope) is None:
        return True, "never tagged"
    if data["levels"].get(topic_store.level_key(anchor, level)) != tp.descriptor_digest(scope):
        return True, "descriptor changed since its topics were chosen"
    return False, ""


def scope_keeping_topics(old_scope, new_scope):
    """`new_scope` for a `set-scope` write, with the stored `TOPICS:` line carried over when the
    new text has none. Raises TopicRefusal when the new text carries a DIFFERENT `TOPICS:` line:
    topics change only through set-level-topics / set-top-topics, so a rewritten descriptor can
    neither drop nor change them by accident."""
    old, new = tp.descriptor_topics(old_scope), tp.descriptor_topics(new_scope)
    if new is not None and new != (old or ()):
        raise TopicRefusal(["a descriptor's TOPICS line changes only through set-level-topics "
                            "(set-top-topics at the tree top); leave the line out of the new text"])
    if old is None or new is not None:
        return new_scope
    return tp.with_descriptor_topics(new_scope, old)


def _read_topic_batch(path):
    """({slug: topics}, error_message) from a JSONL batch file: one `{"slug": ..., "topics": [...]}`
    object per line, `[]` for bound to no topic, `null` to remove the line."""
    text, err = _read_input_file(path)
    if err:
        return None, err
    rows = {}
    for n, line in enumerate(text.split("\n"), 1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
            slug, raw = obj["slug"], obj["topics"]
            if not isinstance(slug, str) or not (raw is None or isinstance(raw, list)):
                raise TypeError("'slug' must be a string and 'topics' a list or null")
            rows[slug] = None if raw is None else tp.normalise_topics(raw)
        except (ValueError, KeyError, TypeError) as exc:
            return None, "! error: %s line %d: %s" % (path, n, exc)
        if len(rows) > MAX_TOPIC_BATCH:
            return None, "! error: %s holds more than %d rows" % (path, MAX_TOPIC_BATCH)
    return rows, None
```

  (d) Insert directly above the comment line
  `# ---- CLI: the capture procedure invokes this (never hand-writes memory files) ---...`:

```python
def _topic_write(args):
    """The four topic write verbs; refusals are raised and mapped by the caller."""
    if args.cmd == "topics-set-list":
        text, err = _read_input_file(args.from_file)
        if err:
            return _input_error(err)
        try:
            spec = json.loads(text)
            topics, tagger = spec["topics"], spec["tagger"]
            if not isinstance(topics, dict):
                raise TypeError("'topics' must be an object of tag: meaning")
        except (ValueError, KeyError, TypeError) as exc:
            return _input_error("! error: %s: %s" % (args.from_file, exc))
        changed = set_topic_list(args.proj, topics, tagger)
        print("topic list %s: %d topic(s), tagger %s"
              % ("updated" if changed else "unchanged", len(topics), tagger))
        return 0
    if args.cmd == "set-topics":
        if args.batch:
            rows, err = _read_topic_batch(args.batch)
            if err:
                return _input_error(err)
        else:
            given = [args.topics is not None, args.universal, args.clear]
            if not args.slug or sum(given) != 1:
                return _input_error("! error: pass --batch, or --slug with exactly one of "
                                    "--topics, --universal, --clear")
            rows = {args.slug: None if args.clear else
                    tp.parse_topics("" if args.universal else args.topics)}
        rep = set_fact_topics(args.proj, rows, dry_run=args.dry_run)
        print("%s topics on %d fact(s); %d unchanged"
              % ("would set" if args.dry_run else "set", len(rep["set"]), rep["unchanged"]))
        return 0
    changed = set_level_topics(args.proj, tp.parse_topics(args.topics),
                               top=args.cmd == "set-top-topics")
    print("topics %s: %s" % ("updated" if changed else "unchanged", args.proj))
    return 0
```

  (e) In `_main`, insert directly above `    raw = sys.argv[1:] if argv is None else argv`:

```python
    tl = sub.add_parser("topics-show", help="print the tree's closed topic list (exit 1: none yet)")
    tl.add_argument("--proj", required=True)
    tl.add_argument("--json", action="store_true", dest="as_json")
    ts = sub.add_parser("topics-set-list", help="replace the tree's closed topic list")
    ts.add_argument("--proj", required=True)
    ts.add_argument("--from-file", required=True, dest="from_file",
                    help='a JSON file: {"tagger": "jev" or "opus", "topics": {"<tag>": "<one-line meaning>"}}')
    st = sub.add_parser("set-topics", help="set the topics a fact is bound to (its body's topics: line)")
    st.add_argument("--proj", required=True, help="any dir of the tree")
    st.add_argument("--slug", default=None)
    st.add_argument("--topics", default=None, help="comma-separated tags from the tree's list")
    st.add_argument("--universal", action="store_true", help="bound to no topic (topics: [])")
    st.add_argument("--clear", action="store_true", help="remove the topics: line (never tagged)")
    st.add_argument("--batch", default=None,
                    help='a JSONL file, one {"slug": ..., "topics": [...]} per line ([] universal, null clear)')
    st.add_argument("--dry-run", action="store_true", dest="dry_run")
    for verb, text in (("set-level-topics", "set a level's TOPICS: line (refused at the tree top)"),
                       ("set-top-topics", "set the tree top's TOPICS: line - the user's decision only")):
        lt = sub.add_parser(verb, help=text)
        lt.add_argument("--proj", required=True, help="the level dir")
        lt.add_argument("--topics", required=True, help="comma-separated tags; '' for none")
    sl = sub.add_parser("topics-stale", help="exit 1 when a level's topics need choosing again")
    sl.add_argument("--proj", required=True, help="the level dir")
```

  (f) In `_main`, insert directly above `    if args.cmd == "ensure-all-trees":`:

```python
    if args.cmd == "topics-show":
        data = topic_store.load(_anchor(args.proj))
        if data is None:
            print("no topic list in this tree")
            return 1
        if args.as_json:
            print(json.dumps({"tagger": data["tagger"], "topics": data["topics"]}, sort_keys=True))
            return 0
        print("tagger: %s" % data["tagger"])
        for name in sorted(data["topics"]):
            print("%s - %s" % (name, data["topics"][name]))
        return 0

    if args.cmd in ("topics-set-list", "set-topics", "set-level-topics", "set-top-topics"):
        try:
            return _topic_write(args)
        except (TopicRefusal, tp.InvalidTopic, topic_store.TopicStoreError) as exc:
            return _refused(exc)

    if args.cmd == "topics-stale":
        stale, why = level_topics_stale(args.proj)
        print("stale: %s" % why if stale else "fresh")
        return 1 if stale else 0
```

  (g) In the `set-scope` branch replace

```python
        _scope, pointers = us.parse_pointer_index(text)
        changed = us.write_if_changed(local, us.upsert_pointer_block(text, scope.strip(), pointers))
        print("scope %s: %s" % ("updated" if changed else "unchanged", local))
```

  with

```python
        old_scope, pointers = us.parse_pointer_index(text)
        try:
            scope = scope_keeping_topics(old_scope, scope.strip())
        except TopicRefusal as exc:
            return _refused(exc)
        changed = us.write_if_changed(local, us.upsert_pointer_block(text, scope, pointers))
        print("scope %s: %s" % ("updated" if changed else "unchanged", local))
```

  Also extend `main`'s docstring: exit 1 is "`lint --tree` found something, `topics-show` found
  no list, or `topics-stale` found the level stale"; the refusal list gains "a refused topic
  write".

- [ ] **Step 4: Run the tests.** Step 2's command - expected: `23 passed`. Then
  `cd <W> && TEST plugins/bitranox/hooks/tests` - expected: no failure (the whole hooks suite;
  `test_memory_writes_switch.py` now also covers the four new write verbs).

- [ ] **Step 5: Mutation battery.** Write `$SCRATCH/t4-battery.json` for `mutation_arm.py
  --battery` with these arms on `memory_engine.py`, test command the two topic test files; every
  arm must be KILLED:

```text
head-read-whole          fh.read(FRONTMATTER_HEAD_BYTES)                      -> fh.read()
pin-not-refused          if owners[slug][1]:                                   -> if False:
check-pass-skipped       if total:\n        raise TopicRefusal(problems, total) -> if False: ...
top-not-refused          if is_top and not top:                                -> if False and not top:
nontop-not-refused       if top and not is_top:                                -> if False:
scope-change-allowed     if new is not None and new != (old or ()):            -> if False:
scope-topics-not-carried return tp.with_descriptor_topics(new_scope, old)      -> return new_scope
digest-not-recorded      the topic_store.record_level(...) line                -> removed
dry-run-writes           if not dry_run:\n                us.put_body(...)     -> if True: ...
dropped-in-use-allowed   if total:\n        raise TopicRefusal(users, total)   -> if False: ...
list-not-required        raise TopicRefusal(["this tree has no topic list ...  -> return {}
string-topics-accepted   if not isinstance(slug, str) or not (raw is None ...  -> if False:
```

- [ ] **Step 6: Commit** `memory_engine.py` and the new test file; message "memory_engine: the
  topic verbs (list, fact topics, level topics, staleness)".

### Task 5: M2d - the references document topics as data

**Files:**
- Modify: `plugins/bitranox/skills/meta-self-improve/references/memory-backend.md` (the "Store
  format" section, the frame paragraph near line 73, the command table near line 192, the
  exit-code paragraph near line 228)
- Modify: `docs/reference.md` (the engine command table near line 96)
- Create: `plugins/bitranox/skills/meta-self-improve/.skillwriter/checklist-20261111-topics-as-data.md`

**Interfaces:** none for code. The text must agree with Task 4's verbs and messages.

**Out of scope:**
- Any instruction to a dream or nap to USE topics (P2c): this task documents the data and the
  verbs, and says in one sentence that nothing is placed by topic yet.

**STOP conditions:**
- `skill_decisions.py show meta-self-improve` lists a `rule` entry whose anchor the edit would
  remove.

REQUIRED SUB-SKILL: `bitranox:meta-skill-writer` (invoke it first; receipt with
`python3 <P>/hooks/skill_receipt.py start meta-skill-writer`, closed with `end`).

- [ ] **Step 1:** `python3 <P>/hooks/skill_decisions.py show meta-self-improve` and read it.
- [ ] **Step 2: RED probe.** A `bitranox:baseline-probe` agent on opus gets the CURRENT "Store
  format" section and command table pasted in and the question: "A fact should be read only in
  directories that use Python. Which engine command records that on the fact, and which on a
  directory? Answer with the commands or say the text does not tell you." Expected: it does not
  tell.
- [ ] **Step 3: Edit `memory-backend.md`.**
  In the frame paragraph, after the sentence about `title:`, add:

```markdown
  A `topics:` line (`topics: [python, uv]`) lists the topics the fact is bound to, from the
  tree's closed list; `topics: []` means it was tagged and is bound to none, and no line means
  it was never tagged. Only `set-topics` changes it: an `add`, `amend-pinned` or factedit
  `apply` keeps the stored line, whatever the body handed in says.
```

  At the end of "Store format" add:

```markdown
A level's scope descriptor may carry one line `TOPICS: python, uv`: the topics this directory
has. It is set with `set-level-topics` (`set-top-topics` at the tree top, which is the user's
decision alone, because the top's block is read by every session of the tree); `set-scope` keeps
the line when the new text has none and refuses a text that changes it. The tree's closed topic
list, with a one-line meaning per topic, is `<anchor>/.claude-memory/topics.json`, written by
`topics-set-list`; a tree without that file has no topics, and every topic verb except
`topics-show` and `topics-stale` refuses there. Topics are data for now: no pointer line is
placed by them yet.
```

  Add to the command table, after the `set-scope` row (then run
  `python3 <P>/skills/docs-md-table-formatting/reformat_tables.py <file>` and read the diff):

```markdown
| `topics-show --proj D [--json]` | prints the tree's topic list; exit 1 when it has none |
| `topics-set-list --proj D --from-file F` (`{"tagger": "jev"\|"opus", "topics": {"<tag>": "<meaning>"}}`) | `topic list updated: N topic(s), tagger T`; refused while a fact or level still uses a dropped topic |
| `set-topics --proj D --slug S --topics a,b\|--universal\|--clear` or `--batch F.jsonl` `[--dry-run]` | `set topics on N fact(s); M unchanged`; every row is checked before any is written |
| `set-level-topics --proj LEVEL --topics a,b` | `topics updated: <level>`; refused at the tree top |
| `set-top-topics --proj ANCHOR --topics a,b` (the user's decision only) | `topics updated: <anchor>`; refused anywhere else |
| `topics-stale --proj LEVEL` | `fresh` (exit 0) or `stale: <why>` (exit 1) |
```

  (Match the table's real column count: read the header row first and give each new row the
  same number of cells.)
  In the exit-code paragraph add `topics-show` without a list and `topics-stale` on a stale
  level to the exit-1 cases, and "a refused topic write" to the refusals.
- [ ] **Step 4: Edit `docs/reference.md`:** the same six rows in its two-column form (command,
  success line), after its `set-scope` row; reformat the table; read the diff.
- [ ] **Step 5: GREEN probe.** The same probe with the NEW text: it must answer `set-topics` and
  `set-level-topics`, and say `set-top-topics` is not a nap's or dream's to run. Then re-run the
  probe once more on the final text after any fix.
- [ ] **Step 6:** Write the checklist file with a `Decisions:` line (`Decisions: none - documents
  data and verbs added in the same release, changes no rule` unless Step 1 named one), add the
  `CHANGELOG.md` line if the text differs from Task 1's notes, run
  `cd <W> && python3 plugins/bitranox/hooks/skill_decisions.py check` (exit 0), commit the three
  paths.

### Task 6: CHECKPOINT A - release P2a, then measure every consumer of "one pointer per slug"

**Files:** none in `plugins/` beyond a release re-bump; this plan file gains Tasks 7-19.

**STOP conditions:**
- the full gate fails on something this plan did not touch (report it; fix it in its own
  worktree);
- a peer session is pushing this repo (ListAgents; message it to hold);
- the sweep finds a consumer that WRITES the store on the one-pointer assumption and that M4
  does not list: that is a new task, never a note.

- [ ] **Step 1: Release P2a.** `cd <W> && git fetch origin && git log --oneline HEAD..origin/master`;
  if origin's `plugin.json` version moved, `uv run plugins/bitranox/hooks/bump_version.py --merge`
  and re-read the CHANGELOG section. Full gate:
  `cd <W> && python3 plugins/bitranox/hooks/repo-gate.py --ci` (exit 0, pytest's `N passed`) and
  `python3 plugins/bitranox/hooks/skill_decisions.py check` (exit 0). Dispatch an opus code
  reviewer (effort medium) with `git diff origin/master...HEAD` and the authority to contradict
  this plan; each finding needs a concrete failing input; fix confirmed findings, re-run the
  gate. Push: `git push origin design/top-index-topics:master`; verify
  `git rev-list --count origin/master..HEAD` prints 0. Watch CI:
  `python3 <P>/skills/compuse-toolbox/scripts/ci_wait.py --ref HEAD` (18-35 minutes) to green.

- [ ] **Step 2: Enumerate the consumers, uncapped.**

```bash
cd <W> && grep -rnE "parse_pointer_index|curated_levels_under|_all_curated_levels|read_store\(|slug_levels|duplicate pointer|_other_levels_pointing|_slug_owned_elsewhere|find_pointer_owners" plugins/bitranox --include=*.py | grep -v "/tests/" > $SCRATCH/consumers.txt; wc -l $SCRATCH/consumers.txt
```

  Known at plan time (files outside `/tests/` that read a pointer block): `hooks/memory_engine.py`,
  `hooks/uuid_store.py`, `hooks/migrate_to_slug_store.py`,
  `skills/meta-self-improve/reconcile_memory_index.py`, `ref_map.py`, `jev_shadow_ports.py`,
  `jev_shadow_sites.py`, `skills/meta-dream-tree/store_manifest.py`, `factedit.py`,
  `dedup_scan.py`, `statusrot.py`, `skills/compuse-toolbox/scripts/mem_levels.py`. Add every
  hook that reads the store without those names (`grep -rln "claude_local_md_path\|mem:" plugins/bitranox/hooks --include=*.py`,
  `recall-memory.py` among them).

- [ ] **Step 3: Classify each consumer by RUNNING it on a planted tree, not by reading.** Build
  in `$SCRATCH/sweep-tree` a tree with a list, two sibling levels that both declare `python`,
  and one fact with `topics: [python]` whose pointer line is present at BOTH siblings (written
  with two `add` calls into a copy of the tree is not possible - the engine refuses the second;
  plant the second line with a scratch script that parses and re-renders the block through
  `uuid_store.upsert_pointer_block`). Before any write, assert
  `python3 <P>/hooks/memory_engine.py tree-top --proj $SCRATCH/sweep-tree` prints that directory
  as the top. Then run each consumer's entry point against it and record what it does with the
  two copies. Known at plan time, with the line that decides:
  - `reconcile_memory_index.py:713` and `:1083-1086`: reports `! duplicate pointer`, a hard
    problem. M4 changes it.
  - `reconcile_memory_index.py:311` `_other_levels_pointing` and `archive_entry` (`:422`):
    dropping one of several pointers keeps the body. For a managed fact M4 drops every copy.
  - `memory_engine.py:978` `move_entry`: validates "duplicate pointers at the target", moves one
    line. M4 refuses a managed fact.
  - `memory_engine.py:561` `_slug_owned_elsewhere` (chain only) and `:413-459` in
    `upsert_entry`: an `add` of a managed slug from a cwd whose chain holds no copy ends in
    `SlugCollision`; factedit's `--level` is the retry (`factedit.py:375-390` prints "N levels
    point at it (a duplicate pointer)", which M4 rewords for a managed fact).
  - `memory_engine.py:1685` `retitle_entry`: already rewrites every level ("also retitled at").
  - `memory_engine.py:1272` `backfill_titles`: already handles a slug at two levels (first wins).
  - `store_manifest.py:344` `_diff_slug`: keyed by (level, slug); copies appearing are `added`,
    not `moved`. The cost report counts state per level and needs no change; confirm.
  - `uuid_store.py:643` `resolve`: dedups by slug, narrowest first. No change.
  Also confirm here that `store_manifest.py backup` copies `topics.json` (back up the planted
  tree, list the backup dir).

- [ ] **Step 4: Write the decision table** into `$SCRATCH/checkpoint-a.md`: one row per consumer -
  file:line, what it did with the two copies (pasted output), whether it reads or writes, the
  change it needs (none / reword / behaviour), and the M4 task that will carry it. Log the
  session's decisions in `<repo>/EXECUTION-USER-REVIEW.md`.

- [ ] **Step 5: Write Tasks 7-19** into this file, in the DETAILED format with complete code and
  tests, from the MID contracts of M3, M4, M5 and M6 and the table of Step 4: Task 7 opens the
  P2b release, Tasks 8-10 the renderer (level map and line building; tree scope; chain scope and
  the collapse), Tasks 11-13 the check and the consumers, Task 14 the tagging helper, Task 15
  the P2b release; Task 16 opens P2c, Tasks 17-18 the skill texts, Task 19 the P2c release. Run
  each task's code in a scratch copy of `plugins/` before committing the plan change, as Tasks
  1-4 were.

## DETAILED: P2b and P2c tasks (Tasks 7-19)

Written at CHECKPOINT A (Task 6, Step 5), 2026-11-12, against the released P2a code (11.2.0).
The conventions of the P2a tasks apply (`W`, `P`, `TEST <paths>`, the commit procedure, no
attribution, ASCII, `mutation_arm.py`).

**What CHECKPOINT A measured.** The enumeration of Task 6 Step 2 listed 114 lines in 12 files.
Each consumer was run on a planted tree holding one fact bound to `python` with a pointer line at
two sibling levels that both declare `python`, plus an unbound fact and a tree-top fact. The
result, by what each needs:

```text
consumer                                   did with the two lines              needs
reconcile --check-tree                     hard `duplicate pointer`; a ref to it = `sideways ref` (NEW)  Task 11: legal for a placed fact; render drift
reconcile --check (chain)                  saw no repeat; a ref from above = `orphan ref`  Task 11: ref exempt; repeated line reported
reconcile --archive                        dropped one line, kept the body     Task 13: drops every line
reconcile plain / --rehome / --check-misplaced  no finding, no write           none
engine move (up; sideways is refused already)  moved one line, left the other  Task 12: refuses a placed fact
engine relocate (cross-tree)               dropped one line, copied the body: one fact in two trees  Task 12: refuses a placed fact
engine rename, retitle                     rewrote every line, warned of a duplicate  Task 12: no warning for a placed fact
engine add from a level with a line        updated body and THAT line only     Task 12: refreshes every line
engine add from a level without a line     adopted the fact (a third line)     Task 12: refused, PlacedElsewhere (NEW)
engine add --pin on the fact               pinned one line                     Task 12: refused (NEW)
engine heal, ensure-memory-structure, lint no change, no finding               none
engine set-topics --universal / --clear    left two lines of an unbound fact   Task 10: collapse to one line at the top
engine set-topics (bind)                   bound a fact whose line differs from its body  Task 8: refused (NEW)
engine set-scope, set-level-topics, topics-stale  unaffected                   none
factedit show / apply                      "N levels point at it (a duplicate pointer)"  Task 13: reworded
store_manifest backup / verify             keyed by (level, slug); copies topics.json    none
dedup_scan, statusrot, versionrot          one row per body, first level       none
ref_map                                    last level won silently             Task 11: first level, `also at`, move conflict (NEW)
mem_levels                                 `duplicates`                        Task 11: `placed by topic` (NEW)
migrate_to_slug_store, recall-memory, gather_scan, uuid_store.resolve  dedup by slug or read-only  none
jev_shadow_ports, jev_shadow_sites         read-only samples per level         none
```

Rows marked NEW are changes M4 did not list. Three of them are writes the sweep found (adoption
by `add`, `add --pin`, binding a fact whose line is not what its body renders), so by Task 6's
STOP rule they are tasks, not notes: they are in Tasks 8 and 12. `mem_levels` and `ref_map` are
read-only and ride in Task 11.

**Decisions taken at CHECKPOINT A (no human was available; each is the default until the user
says otherwise; they are also in the session's report):**

1. `add` of a placed fact from a level that holds no line of it is REFUSED (`PlacedElsewhere`,
   a `SlugCollision`), naming the levels that hold one. Measured before: silent adoption, which
   plants a line the next render removes.
2. A `[[ref]]` to a placed fact is neither a sideways ref nor a chain orphan. Its levels are
   computed, so no citer can be required to sit above all of them; a fallback keeps it readable
   at the tree top when no level has its topic.
3. `set-topics` refuses to bind a fact whose pointer line differs from the line its body
   renders, or whose body lacks `title:` or `description:`. The renderer writes lines from the
   body alone; binding such a fact would reword or strand it. `heal --backfill-titles` and
   factedit repair it first.
4. Un-binding a fact that has several lines collapses it inside `set-topics` (a line at the tree
   top first, then the others dropped), not in a later render.
5. `add --pin` on a placed fact is refused; clear its topics first. A pinned fact is never
   placed by topic.
6. Render drift is reported per LEVEL with counts and a few example slugs, never as one row per
   slug, so the check's memory does not grow with the number of placed facts.
7. A level whose `TOPICS:` line does not parse, or a tree top without a pointer block, refuses
   the whole render before any write.
8. The reference documents gain the placement paragraph in P2b (Task 13), not P2c: the P2a
   sentence "no pointer line is placed by them yet" would be false in the P2b release.

**What this changes for Tasks 20-27 (re-read at CHECKPOINT B).** The helper takes the tree as
`--from D` on every subcommand (`items --from $TREE --levels`, `items --from $TREE --facts-at
$TREE`, `decide --from $TREE --rows ... --kind facts|levels --threshold T --out ... --unsure-out
...`). `set-topics --batch --dry-run` now also names every fact whose line differs from its
body: repair those before the real run, or leave them unbound and list them in the report.

**Proof before writing.** Every code block and test below was applied, task by task and in
order, to a scratch copy of `plugins/` taken from the released code, with the task's tests run
BEFORE its edits (the RED result each Step 2 names) and after (GREEN): 10, 17, 13, 18, 12, 6 and
19 tests, 95 together. In the final state the hooks suite and the skill suites of
`meta-*` and `compuse-toolbox` ran with no failure outside the tests that need the real checkout
(a `.git`, `.github/`, `githooks/`, `docs/`, the backlog file). The 56 mutation arms listed in the
tasks were run by hand in a second copy; every one was killed (one more arm proved equivalent
and is not listed; one survived, and the test that kills it,
`test_the_function_itself_refuses_a_real_run_while_writes_are_off`, was added).

### Task 7: open the P2b release

**Files:**
- Modify: `plugins/bitranox/.claude-plugin/plugin.json`, `pyproject.toml`, `CHANGELOG.md` (via
  `bump_version.py`)

**Interfaces:** none. The notes must agree with what Tasks 8-14 ship; Task 15 re-reads them.

**Out of scope:** any code.

**STOP conditions:**
- `git fetch origin` shows `origin/master` changed `hooks/memory_engine.py`,
  `skills/meta-self-improve/reconcile_memory_index.py`, `ref_map.py`,
  `skills/compuse-toolbox/scripts/mem_levels.py` or `skills/meta-dream-tree/factedit.py` since
  the P2a release (re-read the changed file against the anchors of Tasks 8-13 before going on);
- the bump jig reports a version origin already holds.

- [ ] **Step 1: Write `$SCRATCH/p2b-notes.md`:**

```markdown
### Added

- `memory_engine.py render-topics --proj D --scope tree|chain [--dry-run] [--json]` places the
  pointer line of every fact bound to a topic: at each level that has one of its topics while no
  level above it does, and at the tree top when no level has one. Lines are added before any is
  removed, a pinned or untagged fact is never touched, and a tree without a topic list is left
  as it is.
- `reconcile_memory_index.py --check-tree` reports `render drift` (a line missing, differing
  from its body, or placed elsewhere), and `--check` a `repeated line` that a level above
  already holds.
- `topic_tagging.py` (meta-dream-tree) builds the questions and items a bulk judge needs to
  choose topics for facts or levels, and turns its rows into a `set-topics --batch` file.

### Changed

- A fact placed by topic may have a pointer line at several levels: `--check-tree`,
  `mem_levels.py` and `ref_map.py` no longer report those as duplicates, and a `[[ref]]` to it is
  no sideways ref or orphan.
- `move` and `relocate` refuse a fact placed by topic; `add` from a level that holds no line of
  it is refused, naming the levels that do; `add --pin` on it is refused. `rename`, `retitle`,
  an `add` that changes its title or hook, and `--archive` act on every line.
- `set-topics` refuses to bind a fact whose body has no `title:` or `description:`, or whose
  pointer line differs from what its body renders. Un-binding a fact that has lines at several
  levels leaves it one line, at the tree top.
```

- [ ] **Step 2: Bump.**
  `cd <W> && git fetch origin && uv run plugins/bitranox/hooks/bump_version.py --part minor --changelog $SCRATCH/p2b-notes.md`
  - expected: the jig names the new version, 11.3.0 unless origin moved. Read the new
  `CHANGELOG.md` section back.

- [ ] **Step 3: Commit** the three files the jig changed; message "release: open the
  placement-by-topic minor".

### Task 8: M3a - the parts a render is built from

**Files:**
- Modify: `plugins/bitranox/hooks/memory_engine.py` (a new block above `read_body_topics`;
  `read_body_topics`, `iter_fact_topics`, `_pointer_owners`, `_topic_row_problem`)
- Test: `plugins/bitranox/hooks/tests/test_memory_engine_render_parts.py`

**Interfaces:**
- Consumes: Tasks 1-4 (`tp.LevelMap`, `tp.descriptor_topics`, `TopicRefusal`, `TreeWalkError`,
  `FRONTMATTER_HEAD_BYTES`, `_body_topics`, `curated_levels_under`, `read_store_text`).
- Produces: `MAX_RENDER_BLOCK_BYTES = 1 << 20`, `RenderBlockTooLarge(TopicRefusal)` with `.level`
  and `.size`, `_read_body_head(path) -> str | None`,
  `_iter_body_heads(anchor) -> Iterator[tuple[str, str]]` (slug, head),
  `_level_parts(anchor, level) -> tuple[str, ...]`,
  `_line_from_head(slug, head) -> us.Pointer | None` (title from `title:`, hook from
  `description:`, never pinned; None when either is missing),
  `topic_level_map(anchor, levels=None) -> tuple[tp.LevelMap, dict[tuple, str]]` (levels with a
  non-empty descriptor only; raises `TopicRefusal` naming every level whose `TOPICS:` line does
  not parse), `_pinned_slugs(levels) -> set[str]`,
  `_line_problem(slug, anchor, stored_line) -> str | None`. `_pointer_owners` now returns
  3-tuples `(first level, pinned anywhere, the first pointer's index line)`.
- Behaviour change: `set-topics` refuses to BIND a fact (non-empty topics) whose body has no
  `title:` or `description:`, or whose pointer line differs from the line its body renders. The
  renderer builds lines from the body alone, so binding such a fact would silently reword it.

**Out of scope:**
- Any write of a pointer line (Task 9).
- Repairing a fact whose line differs from its body: `heal --backfill-titles` and factedit do
  that; this task only refuses to bind it and names the repair.

**STOP conditions:**
- an anchor text of Step 3 is not found exactly once (the code moved since CHECKPOINT A: read the
  function it names and report, do not guess);
- `hooks/tests/test_memory_engine_topics_verbs.py` or `test_memory_engine_topics_field.py` fails
  after Step 3 (a P2a test bound a fact whose line differs from its body: report which);
- a mutation arm of Step 5 survives.

**What is held in memory:** one body head (16384 bytes) at a time; one small record per level (its
  parts, its declared topics, its directory); the set of pinned slugs (one short string per pinned
  pointer); for `set-topics`, one owner entry with one pointer line per batch row (at most 5000).

- [ ] **Step 1: Write the failing tests.**

  Create `plugins/bitranox/hooks/tests/test_memory_engine_render_parts.py`:

```python
"""Tests for the parts `render-topics` is built from: the streamed body heads, a level as path
parts, the line a body renders, the tree's level map, and the set-topics guard that keeps a
fact's stored line equal to what its body renders before the fact is bound. All content ASCII.
"""

import os
import tracemalloc
from pathlib import Path

import pytest

import memory_engine as E
import self_improve_signals as sig
import topic_placement as tp
import topic_store
import uuid_store as us

HOOK = "When a rule is about one stack, bind it to that stack's topic."
SCOPE = "WHAT: a level\nSTACK: python"
LIST = {"python": "Python code and its tooling", "rust": "Rust code", "git": "git and GitHub"}


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch):
    h = tmp_path / "home"
    h.mkdir(exist_ok=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    return h


def _tree(tmp_path):
    anchor = tmp_path / "tree"
    anchor.mkdir()
    (anchor / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (anchor / us.STORE_DIRNAME).mkdir()
    topic_store.save_list(anchor, LIST, "jev")
    assert E.main(["set-scope", "--proj", str(anchor), "--scope", "WHAT: the top\nSTACK: none"]) == 0
    return str(anchor)


def _level(anchor, rel, topics=None, scope=SCOPE):
    level = Path(anchor, *rel.split("/"))
    level.mkdir(parents=True, exist_ok=True)
    (level / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    if scope:
        assert E.main(["set-scope", "--proj", str(level), "--scope", scope]) == 0
    if topics is not None:
        E.set_level_topics(str(level), topics)
    return str(level)


def _fact(level, slug, pin=False):
    return E.add_or_update_entry(level, title="T " + slug, hook=HOOK, body="body of " + slug,
                                 type_="feedback", slug=slug, pin=pin)


def _plant_scope(level, scope):
    local = sig.claude_local_md_path(level)
    text = local.read_text(encoding="utf-8")
    local.write_text(us.upsert_pointer_block(text, scope, us.parse_pointer_index(text)[1]),
                     encoding="utf-8")


def _plant_bodies(anchor, count):
    facts = us.central_facts_dir(anchor)
    facts.mkdir(parents=True, exist_ok=True)
    prose = "x" * 200_000
    for i in range(count):
        (facts / ("feedback-n%05d.md" % i)).write_text(
            "---\nname: feedback-n%05d\ndescription: d\ntitle: T\ntopics: [python]\nmetadata:\n"
            "  type: feedback\n---\n\n%s\n" % (i, prose), encoding="utf-8")


def _heads_peak(anchor):
    tracemalloc.start()
    try:
        longest = max(len(head) for _slug, head in E._iter_body_heads(anchor))
        return longest, tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()


def test_body_heads_are_streamed_one_at_a_time_and_capped(tmp_path):
    small, large = tmp_path / "small", tmp_path / "large"
    _plant_bodies(small, 20)
    _plant_bodies(large, 200)
    (us.central_facts_dir(large) / "notes.txt").write_text("x", encoding="utf-8")
    longest, peak_small = _heads_peak(small)
    _longest, peak_large = _heads_peak(large)
    assert longest == E.FRONTMATTER_HEAD_BYTES
    assert sum(1 for _ in E._iter_body_heads(large)) == 200
    assert peak_large < 200_000 and peak_large < peak_small * 2 + 50_000
    assert list(E._iter_body_heads(tmp_path / "nothing")) == []


def test_a_level_is_its_path_parts_below_the_anchor(tmp_path):
    anchor = _tree(tmp_path)
    assert E._level_parts(anchor, anchor) == tp.TOP == ()
    assert E._level_parts(anchor, os.path.join(anchor, "a", "py")) == ("a", "py")
    with pytest.raises(topic_store.TopicStoreError):
        E._level_parts(anchor, str(tmp_path / "elsewhere"))


def test_a_line_is_built_from_the_body_alone(tmp_path):
    anchor = _tree(tmp_path)
    _fact(anchor, "feedback-a")
    head = us.body_path(anchor, "feedback-a").read_text(encoding="utf-8")
    line = E._line_from_head("feedback-a", head)
    stored = us.parse_pointer_index(sig.claude_local_md_path(anchor).read_text(encoding="utf-8"))[1][0]
    assert line.index_line() == stored.index_line() and line.pin is False
    assert E._line_from_head("feedback-a", head.replace("title: T feedback-a\n", "")) is None
    assert E._line_from_head("feedback-a", head.replace("description: " + HOOK + "\n", "")) is None


def test_the_level_map_holds_described_levels_with_their_topics(tmp_path):
    anchor = _tree(tmp_path)
    _level(anchor, "a/py", ("python",))
    _level(anchor, "c", ())
    _level(anchor, "d")                                   # a descriptor, never tagged
    bare = _level(anchor, "e", scope=None)
    _fact(bare, "feedback-at-bare")                       # a pointer block with no descriptor
    level_map, dirs = E.topic_level_map(anchor)
    assert level_map.levels() == [(), ("c",), ("d",), ("a", "py")]
    assert level_map.topics(("a", "py")) == {"python"} and level_map.topics(("d",)) == frozenset()
    assert dirs[("a", "py")] == os.path.join(anchor, "a", "py") and dirs[()] == anchor


def test_a_level_without_a_descriptor_does_not_block_a_roll_up(tmp_path):
    anchor = _tree(tmp_path)
    _level(anchor, "a", ())
    _level(anchor, "a/x1", ("python",))
    _level(anchor, "a/x2", ("python",))
    _fact(_level(anchor, "a/x3", scope=None), "feedback-at-bare")
    level_map, _dirs = E.topic_level_map(anchor)
    assert level_map.placements(("python",)) == (("a",),)


def test_a_topics_line_that_does_not_parse_refuses_the_map_and_names_the_level(tmp_path):
    anchor = _tree(tmp_path)
    level = _level(anchor, "a", ("python",))
    _plant_scope(level, SCOPE + "\nTOPICS: Not A Tag")
    with pytest.raises(E.TopicRefusal) as exc:
        E.topic_level_map(anchor)
    assert level in str(exc.value) and "does not parse" in str(exc.value)


def test_pinned_slugs_are_found_at_any_level(tmp_path):
    anchor = _tree(tmp_path)
    level = _level(anchor, "a")
    _fact(level, "feedback-pinned", pin=True)
    _fact(anchor, "feedback-free")
    assert E._pinned_slugs(E.curated_levels_under(anchor)) == {"feedback-pinned"}


# ---- set-topics: a fact is bound only when its line equals what its body renders ---------------

def _replant_pointer(level, slug, hook):
    local = sig.claude_local_md_path(level)
    text = local.read_text(encoding="utf-8")
    scope, pointers = us.parse_pointer_index(text)
    for p in pointers:
        if p.slug == slug:
            p.hook = hook
    local.write_text(us.upsert_pointer_block(text, scope, pointers), encoding="utf-8")


def test_binding_a_fact_whose_line_differs_from_its_body_is_refused(tmp_path, capsys):
    anchor = _tree(tmp_path)
    _fact(anchor, "feedback-a")
    _replant_pointer(anchor, "feedback-a", "When the line was edited by hand, it says this.")
    body = us.body_path(anchor, "feedback-a").read_bytes()
    assert E.main(["set-topics", "--proj", anchor, "--slug", "feedback-a", "--topics", "python"]) == 2
    out = capsys.readouterr().out
    assert "! refused" in out and "differs from what its body would render" in out
    assert us.body_path(anchor, "feedback-a").read_bytes() == body
    # un-binding hands nothing to the renderer, so it stays allowed
    assert E.main(["set-topics", "--proj", anchor, "--slug", "feedback-a", "--universal"]) == 0


def test_binding_a_fact_whose_body_has_no_title_is_refused(tmp_path, capsys):
    anchor = _tree(tmp_path)
    _fact(anchor, "feedback-a")
    path = us.body_path(anchor, "feedback-a")
    path.write_text(path.read_text(encoding="utf-8").replace("title: T feedback-a\n", ""),
                    encoding="utf-8")
    before = path.read_bytes()
    assert E.main(["set-topics", "--proj", anchor, "--slug", "feedback-a", "--topics", "python"]) == 2
    assert "lacks title: or description:" in capsys.readouterr().out
    assert path.read_bytes() == before


def test_binding_a_fact_whose_line_equals_its_body_goes_through(tmp_path):
    anchor = _tree(tmp_path)
    _fact(anchor, "feedback-a")
    assert E.main(["set-topics", "--proj", anchor, "--slug", "feedback-a", "--topics", "python"]) == 0
    assert E.read_body_topics(us.body_path(anchor, "feedback-a")) == ("python",)
    assert list(E.iter_fact_topics(anchor)) == [("feedback-a", ("python",))]
```

- [ ] **Step 2: Run them to see them fail.**
  `cd <W> && TEST plugins/bitranox/hooks/tests/test_memory_engine_render_parts.py` - expected: `9 failed, 1 passed` (the one passing test pins what `iter_fact_topics` already yields). This is the RED proof: the same files were run
  against the code before this task in the scratch copy with exactly that result.

- [ ] **Step 3: Implement.** Each anchor below occurs exactly once in its file; assert
  that before editing.

  (a) In `plugins/bitranox/hooks/memory_engine.py` insert this block directly above the line `def read_body_topics(path):` (two blank lines between top-level definitions, as the block itself ends):

```python
# ---- render: the parts a pointer line placed by topic is built from ---------------------------

MAX_RENDER_BLOCK_BYTES = 1 << 20
"""Most bytes of pointer lines `render-topics` collects for ONE level: a level's lines are the
one thing a render holds, and a block past this is a tagging mistake to fix, not text to load."""
_RENDER_SHOWN = 20


class RenderBlockTooLarge(TopicRefusal):
    """Raised, before that level is written, when the lines placed at one level pass
    MAX_RENDER_BLOCK_BYTES."""

    def __init__(self, level, size):
        self.level, self.size = level, size
        super().__init__(["the lines placed at %s come to over %d bytes (%d and counting), the most "
                          "one level's block may hold; too many facts carry a topic this level has"
                          % (level, MAX_RENDER_BLOCK_BYTES, size)])


def _read_body_head(path):
    """The first FRONTMATTER_HEAD_BYTES of the body at `path` as text, None when the file is
    missing. Raises TreeWalkError when it exists and cannot be read."""
    try:
        with open(path, "rb") as fh:
            head = fh.read(FRONTMATTER_HEAD_BYTES)
    except (FileNotFoundError, NotADirectoryError):
        return None
    except OSError as exc:
        raise TreeWalkError(path, "unreadable: %s" % exc) from exc
    return head.decode("utf-8", errors="replace")


def _iter_body_heads(anchor):
    """Yield (slug, head text) for every body of the tree, one at a time: nothing is held but the
    head being read."""
    facts = us.central_facts_dir(anchor)
    try:
        scan = os.scandir(facts)
    except (FileNotFoundError, NotADirectoryError):
        return
    except OSError as exc:
        raise TreeWalkError(facts, "cannot list this directory: %s" % exc) from exc
    with scan:
        for item in scan:
            if not item.name.endswith(".md") or not us.is_valid_slug(item.name[:-3]):
                continue
            head = _read_body_head(item.path)
            if head is not None:
                yield item.name[:-3], head


def _level_parts(anchor, level):
    """`level` as the path parts below `anchor` that `topic_placement` works on; () for the anchor.
    Lexical, like `topic_store.level_key` it is built on."""
    key = topic_store.level_key(anchor, level)
    return tuple(key.split("/")) if key else tp.TOP


def _line_from_head(slug, head):
    """The pointer line a managed fact gets, built from its body alone: title from `title:`, hook
    from `description:`, never pinned. None when the body lacks either: such a fact is never
    rendered, it stays where its pointer is."""
    title, hook = _body_title(head), _body_description(head)
    if not title or not hook:
        return None
    return us.Pointer(slug=slug, title=title, hook=hook)


def topic_level_map(anchor, levels=None):
    """(LevelMap, {parts: level dir}) of the tree: every curated level whose descriptor is not
    empty, with the topics its `TOPICS:` line declares (none without the line), plus the anchor.
    A level with no descriptor is left out, so a scaffold-only level cannot block a roll-up.
    Raises TopicRefusal, naming the levels, when a `TOPICS:` line does not parse: placing by a
    guessed line would move rules. Holds one small record per level."""
    declared, dirs, bad, total = {}, {tp.TOP: os.path.abspath(str(anchor))}, [], 0
    for level in curated_levels_under(anchor) if levels is None else levels:
        scope = us.parse_pointer_index(read_store_text(sig.claude_local_md_path(level)))[0]
        if not scope.strip():
            continue
        try:
            topics = tp.descriptor_topics(scope) or ()
        except tp.InvalidTopic as exc:
            total += 1
            if len(bad) < _RENDER_SHOWN:
                bad.append("%s: its TOPICS line does not parse (%s); set-level-topics replaces it"
                           % (level, exc))
            continue
        parts = _level_parts(anchor, level)
        declared[parts], dirs[parts] = topics, os.path.abspath(str(level))
    if total:
        raise TopicRefusal(bad, total)
    return tp.LevelMap(declared), dirs


def _pinned_slugs(levels):
    """The slugs pinned at any of `levels`: one record per pinned pointer."""
    pinned = set()
    for level in levels:
        for ptr in us.parse_pointer_index(read_store_text(sig.claude_local_md_path(level)))[1]:
            if ptr.pin:
                pinned.add(ptr.slug)
    return pinned


def _line_problem(slug, anchor, stored_line):
    """Why `slug` cannot be bound to a topic yet, or None: a rendered line is built from the body
    alone, so a body without `title:` or `description:`, or a stored line that says something else
    than the body would render, has to be made to agree first."""
    line = _line_from_head(slug, _read_body_head(us.body_path(anchor, slug)) or "")
    if line is None:
        return ("%s: its body lacks title: or description:, so no line can be rendered from it; "
                "write it once through factedit apply (or add), then tag it" % slug)
    if line.index_line() != stored_line:
        return ("%s: its pointer line differs from what its body would render; apply the wanted "
                "title and hook once through factedit apply (or add), then tag it" % slug)
    return None
```

  (b) In `plugins/bitranox/hooks/memory_engine.py` replace

```python
    try:
        with open(path, "rb") as fh:
            head = fh.read(FRONTMATTER_HEAD_BYTES)
    except (FileNotFoundError, NotADirectoryError):
        return None
    except OSError as exc:
        raise TreeWalkError(path, "unreadable: %s" % exc) from exc
    return _body_topics(head.decode("utf-8", errors="replace"))
```

  with

```python
    head = _read_body_head(path)
    return None if head is None else _body_topics(head)
```

  (c) In `plugins/bitranox/hooks/memory_engine.py` replace

```python
    facts = us.central_facts_dir(anchor)
    try:
        scan = os.scandir(facts)
    except (FileNotFoundError, NotADirectoryError):
        return
    except OSError as exc:
        raise TreeWalkError(facts, "cannot list this directory: %s" % exc) from exc
    with scan:
        for item in scan:
            if not item.name.endswith(".md") or not us.is_valid_slug(item.name[:-3]):
                continue
            topics = read_body_topics(item.path)
            if topics is not None:
                yield item.name[:-3], topics
```

  with

```python
    for slug, head in _iter_body_heads(anchor):
        topics = _body_topics(head)
        if topics is not None:
            yield slug, topics
```

  (d) In `plugins/bitranox/hooks/memory_engine.py` replace

```python
    """{slug: (first level pointing at it, pinned anywhere)} for the slugs in `wanted`, from one
    walk over the tree's levels. Holds one entry per wanted slug."""
    owners = {}
    for level in curated_levels_under(anchor):
        for ptr in us.parse_pointer_index(read_store_text(sig.claude_local_md_path(level)))[1]:
            if ptr.slug in wanted:
                first, pinned = owners.get(ptr.slug, (level, False))
                owners[ptr.slug] = (first, pinned or ptr.pin)
    return owners
```

  with

```python
    """{slug: (first level pointing at it, pinned anywhere, that first pointer's line)} for the
    slugs in `wanted`, from one walk over the tree's levels. Holds one entry per wanted slug."""
    owners = {}
    for level in curated_levels_under(anchor):
        for ptr in us.parse_pointer_index(read_store_text(sig.claude_local_md_path(level)))[1]:
            if ptr.slug in wanted:
                first, pinned, line = owners.get(ptr.slug, (level, False, ptr.index_line()))
                owners[ptr.slug] = (first, pinned or ptr.pin, line)
    return owners
```

  (e) In `plugins/bitranox/hooks/memory_engine.py` replace

```python
        return "%s: its body has no frontmatter to carry topics" % slug
    return None
```

  with

```python
        return "%s: its body has no frontmatter to carry topics" % slug
    if topics:
        # Binding a fact hands its lines to the renderer, which builds them from the body alone.
        return _line_problem(slug, anchor, owners[slug][2])
    return None
```

- [ ] **Step 4: Run the tests.** Step 2's command - expected: `10 passed`. Then
  `cd <W> && TEST plugins/bitranox/hooks/tests` - expected: no failure (measured in the scratch copy for the engine-related part, `-k "memory_engine or topic or uuid_store or pin_gate or mod_bridge or memory"`: 924 passed, 1 skipped, before this file's tests).

- [ ] **Step 5: Mutation battery.** Write `$SCRATCH/t8-battery.json` for `mutation_arm.py
  --battery` (`<P>/skills/compuse-toolbox/scripts/mutation_arm.py`, run with `--with PyYAML
  --with lxml --with defusedxml --with ruamel.yaml --with httpx2`), tests: this task's test files.
  One arm per row: arm name, file, the line(s) the arm takes out, what it puts there. Each arm
  changes only the code this task added or edited; every arm must be KILLED (all were, by hand,
  in the scratch copy):

```text
head-read-whole          memory_engine.py  head = fh.read(FRONTMATTER_HEAD_BYTES)  ->  head = fh.read()
line-without-title       memory_engine.py  if not title or not hook:  ->  if not hook:
bare-level-in-map        memory_engine.py  if not scope.strip(): / continue  ->  (removed)  (in `def topic_level_map`, next to: topics = tp.descriptor_topics(scope) or ())
bad-topics-line-skipped  memory_engine.py  if total: / raise TopicRefusal(bad, total)  ->  (removed)  (in `def topic_level_map`, next to: raise TopicRefusal(bad, total))
line-guard-off           memory_engine.py  if topics:  ->  if False:
line-differs-accepted    memory_engine.py  if line.index_line() != stored_line:  ->  if False:
```

- [ ] **Step 6: Commit** `memory_engine.py` and the new test file; message "memory_engine: body heads, the level map and the body-rendered line a topic render is built from".

### Task 9: M3b - `render-topics --scope tree`

**Files:**
- Modify: `plugins/bitranox/hooks/memory_engine.py` (a new block above `_read_topic_batch`;
  `WRITE_VERBS`, `TOPIC_WRITE_VERBS`, `_is_topic_dry_run`, `_topic_write`, the parser)
- Test: `plugins/bitranox/hooks/tests/test_memory_engine_render_tree.py`

**Interfaces:**
- Consumes: Task 8; `us.write_if_changed`, `us.upsert_pointer_block`, `us.parse_pointer_index`,
  `sig.claude_local_md_path`, `sig.refuse_if_memory_writes_off`, the level lock the engine's
  writers use.
- Produces: `render_topics(proj, scope="tree", dry_run=False, write=None) -> dict` and the verb
  `render-topics --proj D --scope tree [--dry-run] [--json]`. Report keys: `list` (False alone
  when the tree has no topic list), `scope`, `dry_run`, `managed`, `incomplete` (at most 20
  slugs), `incomplete_total`, `levels` = {level dir: {`added`, `refreshed`, `removed`, example
  slugs}}. Output: one `  <level>: +N added, N refreshed, -N removed` line per changed level,
  a `~ N tagged fact(s) have a body without title: or description: ...` line when any, then
  `render-topics (tree): N managed fact(s); changed|would change N level(s)`; without a list
  `no topic list in this tree: nothing is placed by topic`. Exit 0 done, 2 refused (`! refused:`
  on stdout) or unusable input (`! error` on stderr).
- `write(path, text)` is the port a level file is written through; tests pass a recording one.
  No monkeypatching.

**Out of scope:**
- `--scope chain` and the collapse on un-binding (Task 10): this task's `render_topics` raises
  `ValueError` for any scope but `tree`, and the parser offers only `tree`.
- The tree top's `TOPICS:` line: read, never written.

**STOP conditions:**
- an anchor text of Step 3 is not found exactly once (the code moved since CHECKPOINT A: read the
  function it names and report, do not guess);
- `hooks/tests/test_memory_writes_switch.py` fails for `render-topics` (the refusal must precede
  argparse; `--dry-run` is the one form allowed while writes are off);
- `test_every_line_is_added_before_any_is_removed` cannot be made to pass without reordering
  the two phases: the order is the safety property, report instead;
- a mutation arm of Step 5 survives.

**What is held in memory:** one record per level; the set of pinned slugs; the lines of the ONE
  level being written (refused past `MAX_RENDER_BLOCK_BYTES`, 1 MiB, before any line is dropped); a
  placement cache of at most 512 topic tuples; at most 20 example slugs per report list. Bodies are
  read one head at a time, once per level that has a topic plus once for the census. The test
  `test_a_render_holds_no_body_and_its_peak_does_not_grow_with_the_store` measures the peak at two
  store sizes.

- [ ] **Step 1: Write the failing tests.**

  Create `plugins/bitranox/hooks/tests/test_memory_engine_render_tree.py`:

```python
"""Tests for `render-topics --scope tree`: a topic-bound fact gets a pointer line at each level
that has one of its topics while no level above it does, lines are added before any is removed,
and a pinned, untagged or unrenderable fact is never touched. All content ASCII.
"""

import json
import os
import tracemalloc
from pathlib import Path

import pytest

import memory_engine as E
import self_improve_signals as sig
import topic_store
import uuid_store as us

HOOK = "When a rule is about one stack, bind it to that stack's topic."
SCOPE = "WHAT: a level\nSTACK: python"
LIST = {"python": "Python code and its tooling", "rust": "Rust code", "git": "git and GitHub"}


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch):
    h = tmp_path / "home"
    h.mkdir(exist_ok=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    return h


def _tree(tmp_path, with_list=True):
    anchor = tmp_path / "tree"
    anchor.mkdir()
    (anchor / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (anchor / us.STORE_DIRNAME).mkdir()
    if with_list:
        topic_store.save_list(anchor, LIST, "jev")
    assert E.main(["set-scope", "--proj", str(anchor), "--scope", "WHAT: the top\nSTACK: none"]) == 0
    return str(anchor)


def _level(anchor, rel, topics=None):
    level = Path(anchor, *rel.split("/"))
    level.mkdir(parents=True, exist_ok=True)
    (level / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    assert E.main(["set-scope", "--proj", str(level), "--scope", SCOPE]) == 0
    if topics is not None:
        E.set_level_topics(str(level), topics)
    return str(level)


def _fact(level, slug, topics=None, pin=False):
    E.add_or_update_entry(level, title="T " + slug, hook=HOOK, body="body of " + slug,
                          type_="feedback", slug=slug, pin=pin)
    if topics is not None:
        E.set_fact_topics(level, {slug: topics})


def _slugs(level):
    text = sig.claude_local_md_path(level).read_text(encoding="utf-8")
    return sorted(p.slug for p in us.parse_pointer_index(text)[1])


def _snapshot(anchor):
    return {str(p): p.read_bytes() for p in sorted(Path(anchor).rglob("*"))
            if p.is_file() and not p.name.endswith(".lock")}


def _example(tmp_path):
    """The design's tree: python under a and b, rust at c, nothing at d; one python rule at the top."""
    anchor = _tree(tmp_path)
    levels = {rel: _level(anchor, rel, topics) for rel, topics in (
        ("a", ()), ("a/py", ("python",)), ("a/other", ()), ("b", ()), ("b/py", ("python",)),
        ("b/other", ()), ("c", ("rust",)), ("d", ()))}
    _fact(anchor, "feedback-py-rule", ("python",))
    return anchor, levels


def test_a_python_rule_is_read_under_both_python_levels_and_nowhere_else(tmp_path, capsys):
    anchor, levels = _example(tmp_path)
    assert E.main(["render-topics", "--proj", levels["d"], "--scope", "tree"]) == 0
    out = capsys.readouterr().out
    assert "render-topics (tree): 1 managed fact(s); changed 3 level(s)" in out
    assert _slugs(levels["a/py"]) == _slugs(levels["b/py"]) == ["feedback-py-rule"]
    for rel in ("a", "a/other", "b", "b/other", "c", "d"):
        assert _slugs(levels[rel]) == []
    assert _slugs(anchor) == []
    rendered = sig.claude_local_md_path(levels["a/py"]).read_text(encoding="utf-8")
    assert "- [T feedback-py-rule](mem:feedback-py-rule) - %s\n" % HOOK in rendered


def test_a_second_render_changes_nothing(tmp_path, capsys):
    anchor, levels = _example(tmp_path)
    E.render_topics(anchor)
    before = _snapshot(anchor)
    capsys.readouterr()
    assert E.main(["render-topics", "--proj", anchor, "--scope", "tree", "--json"]) == 0
    rep = json.loads(capsys.readouterr().out)
    assert rep["levels"] == {} and rep["managed"] == 1 and _snapshot(anchor) == before


def test_a_topic_every_child_has_rolls_up_to_the_parent(tmp_path):
    anchor = _tree(tmp_path)
    parent = _level(anchor, "a", ())
    x1, x2 = _level(anchor, "a/x1", ("python",)), _level(anchor, "a/x2", ("python", "rust"))
    _fact(anchor, "feedback-py-rule", ("python",))
    _fact(anchor, "feedback-rust-rule", ("rust",))
    E.render_topics(anchor)
    assert _slugs(parent) == ["feedback-py-rule"]
    assert (_slugs(x1), _slugs(x2), _slugs(anchor)) == ([], ["feedback-rust-rule"], [])


def test_a_fact_whose_topic_no_level_has_falls_back_to_the_top(tmp_path):
    anchor = _tree(tmp_path)
    inner = _level(anchor, "c", ("rust",))
    _fact(anchor, "feedback-stays", ("git",))
    _fact(inner, "feedback-comes-up", ("git",))
    E.render_topics(anchor)
    assert _slugs(anchor) == ["feedback-comes-up", "feedback-stays"] and _slugs(inner) == []


def test_pinned_untagged_and_unbound_facts_stay_where_they_are(tmp_path):
    anchor, levels = _example(tmp_path)
    _fact(levels["c"], "feedback-untagged")
    _fact(levels["c"], "feedback-universal", ())
    _fact(levels["d"], "feedback-pinned", pin=True)
    pinned_body = us.body_path(anchor, "feedback-pinned")
    us.put_body(anchor, "feedback-pinned", E._with_topics(pinned_body.read_text(encoding="utf-8"), ("python",)))
    kept = {rel: sig.claude_local_md_path(levels[rel]).read_bytes() for rel in ("c", "d")}
    rep = E.render_topics(anchor)
    assert rep["managed"] == 1
    assert {rel: sig.claude_local_md_path(levels[rel]).read_bytes() for rel in ("c", "d")} == kept
    assert "feedback-pinned" not in _slugs(levels["a/py"])


def test_a_tagged_fact_whose_body_renders_no_line_is_reported_and_stays(tmp_path, capsys):
    anchor, levels = _example(tmp_path)
    _fact(levels["c"], "feedback-no-title", ("python",))
    path = us.body_path(anchor, "feedback-no-title")
    path.write_text(path.read_text(encoding="utf-8").replace("title: T feedback-no-title\n", ""),
                    encoding="utf-8")
    assert E.main(["render-topics", "--proj", anchor, "--scope", "tree"]) == 0
    out = capsys.readouterr().out
    assert "1 tagged fact(s) have a body without title: or description:" in out
    assert "feedback-no-title" in out and _slugs(levels["c"]) == ["feedback-no-title"]
    assert "feedback-no-title" not in _slugs(levels["a/py"])


def test_a_line_that_says_something_else_than_its_body_is_refreshed(tmp_path):
    anchor, levels = _example(tmp_path)
    E.render_topics(anchor)
    local = sig.claude_local_md_path(levels["b/py"])
    text = local.read_text(encoding="utf-8")
    scope, pointers = us.parse_pointer_index(text)
    pointers[0].hook = "When this line went stale, it says this."
    local.write_text(us.upsert_pointer_block(text, scope, pointers), encoding="utf-8")
    rep = E.render_topics(anchor)
    assert rep["levels"][levels["b/py"]]["refreshed"] == 1
    assert HOOK in local.read_text(encoding="utf-8")


def _recording(calls, fail_at=None):
    def write(path, text):
        if fail_at is not None and str(path) == str(fail_at):
            raise OSError(28, "No space left on device", str(path))
        calls.append(str(path))
        return us.write_if_changed(path, text)
    return write


def test_every_line_is_added_before_any_is_removed(tmp_path):
    anchor, levels = _example(tmp_path)
    calls = []
    E.render_topics(anchor, write=_recording(calls))
    top = str(sig.claude_local_md_path(anchor))
    assert calls[-1] == top and len(calls) == 3
    assert {calls[0], calls[1]} == {str(sig.claude_local_md_path(levels[rel])) for rel in ("a/py", "b/py")}


def test_a_failed_add_leaves_every_old_line(tmp_path):
    anchor, levels = _example(tmp_path)
    calls = []
    with pytest.raises(OSError):
        E.render_topics(anchor, write=_recording(calls, fail_at=sig.claude_local_md_path(levels["b/py"])))
    assert _slugs(anchor) == ["feedback-py-rule"] and _slugs(levels["a/py"]) == ["feedback-py-rule"]
    assert _slugs(levels["b/py"]) == []


def test_dry_run_reports_and_writes_nothing_even_with_writes_off(tmp_path, capsys, monkeypatch):
    anchor, levels = _example(tmp_path)
    before = _snapshot(anchor)
    monkeypatch.setenv("BITRANOX_MEMORY_WRITES", "off")
    capsys.readouterr()
    assert E.main(["render-topics", "--proj", anchor, "--scope", "tree", "--dry-run", "--json"]) == 0
    rep = json.loads(capsys.readouterr().out)
    assert rep["dry_run"] is True and rep["levels"][levels["a/py"]]["added"] == 1
    assert rep["levels"][anchor]["removed"] == 1 and _snapshot(anchor) == before
    assert E.main(["render-topics", "--proj", anchor, "--scope", "tree"]) == 2
    assert "! refused" in capsys.readouterr().out and _snapshot(anchor) == before


def test_the_function_itself_refuses_a_real_run_while_writes_are_off(tmp_path, monkeypatch):
    anchor, _levels = _example(tmp_path)
    before = _snapshot(anchor)
    monkeypatch.setenv("BITRANOX_MEMORY_WRITES", "off")
    with pytest.raises(sig.MemoryWritesOff):
        E.render_topics(anchor)
    assert _snapshot(anchor) == before


def test_without_a_topic_list_the_verb_says_so_and_changes_nothing(tmp_path, capsys):
    anchor = _tree(tmp_path, with_list=False)
    _fact(anchor, "feedback-a")
    before = _snapshot(anchor)
    assert E.main(["render-topics", "--proj", anchor, "--scope", "tree"]) == 0
    assert "no topic list in this tree" in capsys.readouterr().out
    assert _snapshot(anchor) == before and E.render_topics(anchor) == {"list": False}


def test_a_level_topics_line_that_does_not_parse_refuses_the_render_before_any_write(tmp_path, capsys):
    anchor, levels = _example(tmp_path)
    local = sig.claude_local_md_path(levels["c"])
    text = local.read_text(encoding="utf-8")
    local.write_text(us.upsert_pointer_block(text, SCOPE + "\nTOPICS: Not A Tag", []), encoding="utf-8")
    before = _snapshot(anchor)
    assert E.main(["render-topics", "--proj", anchor, "--scope", "tree"]) == 2
    out = capsys.readouterr().out
    assert "! refused" in out and levels["c"] in out and _snapshot(anchor) == before


def test_a_tree_top_without_a_pointer_block_refuses_the_render(tmp_path):
    anchor = tmp_path / "tree"
    anchor.mkdir()
    (anchor / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (anchor / us.STORE_DIRNAME).mkdir()
    topic_store.save_list(anchor, LIST, "jev")
    _level(str(anchor), "a", ("python",))
    with pytest.raises(E.TopicRefusal) as exc:
        E.render_topics(str(anchor))
    assert "has no pointer block" in str(exc.value)


def _plant_bodies(anchor, count, prose=200_000, description="d", tagged_every=10):
    facts = us.central_facts_dir(anchor)
    facts.mkdir(parents=True, exist_ok=True)
    filler = "x" * prose
    for i in range(count):
        topics = "topics: [python]\n" if i % tagged_every == 0 else ""
        (facts / ("feedback-n%05d.md" % i)).write_text(
            "---\nname: feedback-n%05d\ndescription: %s\ntitle: T\n%smetadata:\n  type: feedback\n"
            "---\n\n%s\n" % (i, description, topics, filler), encoding="utf-8")


def test_the_lines_of_one_level_are_capped_and_the_refusal_drops_nothing(tmp_path, capsys):
    anchor = _tree(tmp_path)
    level = _level(anchor, "a", ("python",))
    _fact(anchor, "feedback-py-rule", ("python",))
    _plant_bodies(anchor, 1200, prose=1, description="y" * 1000, tagged_every=1)
    before = _snapshot(anchor)
    with pytest.raises(E.RenderBlockTooLarge) as exc:
        E.render_topics(anchor)
    assert exc.value.level == level and exc.value.size > E.MAX_RENDER_BLOCK_BYTES
    assert E.main(["render-topics", "--proj", anchor, "--scope", "tree"]) == 2
    assert "! refused" in capsys.readouterr().out and _snapshot(anchor) == before


def _render_peak(tmp_path, name, count):
    anchor = _tree(tmp_path / name)
    level = _level(anchor, "a", ("python",))
    _plant_bodies(anchor, count)
    tracemalloc.start()
    try:
        E.render_topics(anchor)
        return len(_slugs(level)), tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()


def test_a_render_holds_no_body_and_its_peak_does_not_grow_with_the_store(tmp_path):
    (tmp_path / "small").mkdir()
    (tmp_path / "large").mkdir()
    placed_small, peak_small = _render_peak(tmp_path, "small", 30)
    placed_large, peak_large = _render_peak(tmp_path, "large", 300)
    # a tagged body no level points at yet still gets its lines
    assert (placed_small, placed_large) == (3, 30)
    assert peak_large < 400_000                # two bodies of 200 KB would already pass this
    assert peak_large < peak_small * 2 + 100_000


def test_an_unknown_scope_is_a_usage_error(tmp_path, capsys):
    anchor = _tree(tmp_path)
    with pytest.raises(SystemExit) as exc:
        E.main(["render-topics", "--proj", anchor, "--scope", "sideways"])
    assert exc.value.code == 2
    with pytest.raises(ValueError):
        E.render_topics(anchor, scope="sideways")
```

- [ ] **Step 2: Run them to see them fail.**
  `cd <W> && TEST plugins/bitranox/hooks/tests/test_memory_engine_render_tree.py` - expected: `17 failed`. This is the RED proof: the same files were run
  against the code before this task in the scratch copy with exactly that result.

- [ ] **Step 3: Implement.** Each anchor below occurs exactly once in its file; assert
  that before editing.

  (a) In `plugins/bitranox/hooks/memory_engine.py` insert this block directly above the line `def _read_topic_batch(path):` (two blank lines between top-level definitions, as the block itself ends):

```python
# ---- render: place the lines ---------------------------------------------------------------

_PLACEMENT_CACHE = 512


class _Placer:
    """`LevelMap.placements` remembered per topic set. Facts share few distinct sets, so the cache
    stays small; it is emptied when it reaches _PLACEMENT_CACHE entries rather than grown."""

    def __init__(self, level_map):
        self._map, self._seen = level_map, {}

    def __call__(self, topics):
        hit = self._seen.get(topics)
        if hit is None:
            if len(self._seen) >= _PLACEMENT_CACHE:
                self._seen.clear()
            hit = self._seen[topics] = frozenset(self._map.placements(topics))
        return hit


def _managed_topics(slug, head, pinned):
    """The topics a body head binds its fact to when the renderer manages it, else None: managed
    means a non-empty `topics:` line, no pointer of it pinned, and a body a line can be built from."""
    topics = _body_topics(head)
    if not topics or slug in pinned or _line_from_head(slug, head) is None:
        return None
    return topics


def _render_census(anchor, pinned):
    """One pass over the bodies: how many facts are managed, and the tagged unpinned ones no line
    can be built from (the first _RENDER_SHOWN and their total)."""
    managed, incomplete, total = 0, [], 0
    for slug, head in _iter_body_heads(anchor):
        if not _body_topics(head) or slug in pinned:
            continue
        if _line_from_head(slug, head) is None:
            total += 1
            if len(incomplete) < _RENDER_SHOWN:
                incomplete.append(slug)
        else:
            managed += 1
    return {"managed": managed, "incomplete": sorted(incomplete), "incomplete_total": total}


def _wanted_lines(anchor, place, pinned, parts, level_dir, skip=frozenset()):
    """{slug: Pointer} for every managed fact placed at the level `parts`, from one streaming pass
    over the bodies. This dict is what a render holds; past MAX_RENDER_BLOCK_BYTES of lines it
    raises RenderBlockTooLarge."""
    wanted, size = {}, 0
    for slug, head in _iter_body_heads(anchor):
        topics = _managed_topics(slug, head, pinned)
        if topics is None or slug in skip or parts not in place(topics):
            continue
        line = _line_from_head(slug, head)
        size += len(line.index_line().encode("utf-8")) + 1
        if size > MAX_RENDER_BLOCK_BYTES:
            raise RenderBlockTooLarge(level_dir, size)
        wanted[slug] = line
    return wanted


def _note(rep, level_dir, kind, slugs):
    """Count `slugs` under `kind` for `level_dir` in the report, keeping the first few as examples."""
    if not slugs:
        return
    row = rep["levels"].setdefault(level_dir, {"added": 0, "refreshed": 0, "removed": 0, "examples": {}})
    row[kind] += len(slugs)
    shown = row["examples"].setdefault(kind, [])
    shown.extend(sorted(slugs)[:_RENDER_SHOWN - len(shown)])


def _add_lines(level_dir, wanted, rep, dry_run, write):
    """Add the missing lines of `wanted` to one level and refresh an unpinned line that says
    something else than its body, under the level's lock. Returns the slugs the level now holds."""
    local = sig.claude_local_md_path(level_dir)
    with sig.memory_lock(local):
        text = read_store_text(local)
        scope, pointers = us.parse_pointer_index(text)
        held = {p.slug: p for p in pointers}
        added, refreshed = [], []
        for slug in sorted(wanted):
            line, have = wanted[slug], held.get(slug)
            if have is None:
                pointers.append(line)
                added.append(slug)
            elif not have.pin and not have.legacy and have.index_line() != line.index_line():
                have.title, have.hook = line.title, line.hook
                refreshed.append(slug)
        if (added or refreshed) and not dry_run:
            write(local, us.upsert_pointer_block(text, scope, pointers))
    _note(rep, level_dir, "added", added)
    _note(rep, level_dir, "refreshed", refreshed)
    return set(held) | set(added)


def _drop_lines(level_dir, doomed, rep, dry_run, write):
    """Drop the unpinned lines of `doomed` from one level, under its lock."""
    if not doomed:
        return
    local = sig.claude_local_md_path(level_dir)
    with sig.memory_lock(local):
        text = read_store_text(local)
        scope, pointers = us.parse_pointer_index(text)
        kept = [p for p in pointers if p.slug not in doomed or p.pin or p.legacy]
        removed = [p.slug for p in pointers if p.slug in doomed and not (p.pin or p.legacy)]
        if removed and not dry_run:
            write(local, us.upsert_pointer_block(text, scope, kept))
    _note(rep, level_dir, "removed", removed)


def _misplaced_lines(anchor, place, pinned, parts, level_dir):
    """The slugs of the managed lines at one level that are placed elsewhere: one body head is read
    per line of the level's block."""
    doomed = set()
    for ptr in us.parse_pointer_index(read_store_text(sig.claude_local_md_path(level_dir)))[1]:
        if ptr.pin or ptr.legacy:
            continue
        head = _read_body_head(us.body_path(anchor, ptr.slug))
        topics = None if head is None else _managed_topics(ptr.slug, head, pinned)
        if topics is not None and parts not in place(topics):
            doomed.add(ptr.slug)
    return doomed


def _render_tree(anchor, levels, level_map, dirs, pinned, rep, dry_run, write):
    """Tree scope. ADD over every level that has a topic, plus the anchor; then, only when every
    add went through, REMOVE over every curated level. An error in the ADD phase is raised before
    a single line is dropped, so an interrupted run leaves a surplus copy, never a fact with no line."""
    place = _Placer(level_map)
    for parts in level_map.levels():
        if parts != tp.TOP and not level_map.topics(parts):
            continue
        _add_lines(dirs[parts], _wanted_lines(anchor, place, pinned, parts, dirs[parts]), rep,
                   dry_run, write)
    for level in levels:
        parts = _level_parts(anchor, level)
        level = os.path.abspath(str(level))
        _drop_lines(level, _misplaced_lines(anchor, place, pinned, parts, level), rep, dry_run, write)


def render_topics(proj, scope="tree", dry_run=False, write=None):
    """Place the pointer lines of every MANAGED fact of `proj`'s tree by topic.

    A fact is managed when its body's `topics:` is non-empty, no pointer of it is pinned, and its
    body holds the `title:` and `description:` a line is built from. Every other line is never
    added, dropped or rewritten here. `scope` is 'tree' (every level; adds, then removes).
    `write(path, text)` is the port a
    level file is written through (default `uuid_store.write_if_changed`); a test passes a
    recording one. Returns a report: {'list': False} alone when the tree has no topic list (then
    nothing is read further and nothing written), else scope, dry_run, managed, incomplete,
    incomplete_total and, per changed level dir, the counts added / refreshed / removed with a
    few example slugs.

    Checked before the first write: a level whose TOPICS line does not parse and a tree top with
    no pointer block raise TopicRefusal. Raises RenderBlockTooLarge for a level whose lines pass
    MAX_RENDER_BLOCK_BYTES; in tree scope that is before any line is dropped.
    Holds: one record per level, one per pinned pointer, the lines of the ONE level being written."""
    if scope != "tree":
        raise ValueError("scope must be 'tree', not %r" % (scope,))
    if not dry_run:
        sig.refuse_if_memory_writes_off()
    proj = os.path.abspath(str(proj))
    anchor = _anchor(proj)
    if topic_store.load(anchor) is None:
        return {"list": False}
    levels = curated_levels_under(anchor)
    level_map, dirs = topic_level_map(anchor, levels)
    if not any(_level_parts(anchor, level) == tp.TOP for level in levels):
        raise TopicRefusal(["the tree top %s has no pointer block for the lines that fall back to "
                            "it (ensure-memory-structure writes one)" % anchor])
    pinned = _pinned_slugs(levels)
    rep = {"list": True, "scope": scope, "dry_run": bool(dry_run), "levels": {}}
    rep.update(_render_census(anchor, pinned))
    write = write or us.write_if_changed
    _render_tree(anchor, levels, level_map, dirs, pinned, rep, dry_run, write)
    return rep


def _print_render(rep, as_json):
    """Print a render report; the verb's whole output."""
    if as_json:
        print(json.dumps(rep, sort_keys=True))
        return
    if not rep["list"]:
        print("no topic list in this tree: nothing is placed by topic")
        return
    verb = "would change" if rep["dry_run"] else "changed"
    for level in sorted(rep["levels"]):
        row = rep["levels"][level]
        print("  %s: +%d added, %d refreshed, -%d removed" % (level, row["added"], row["refreshed"],
                                                               row["removed"]))
    if rep["incomplete_total"]:
        print("~ %d tagged fact(s) have a body without title: or description: and stay where they "
              "are: %s%s" % (rep["incomplete_total"], ", ".join(rep["incomplete"]),
                             " ..." if rep["incomplete_total"] > len(rep["incomplete"]) else ""))
    print("render-topics (%s): %d managed fact(s); %s %d level(s)"
          % (rep["scope"], rep["managed"], verb, len(rep["levels"])))
```

  (b) In `plugins/bitranox/hooks/memory_engine.py` replace

```python
                         "set-topics", "set-level-topics", "set-top-topics"})
```

  with

```python
                         "set-topics", "set-level-topics", "set-top-topics", "render-topics"})
```

  (c) In `plugins/bitranox/hooks/memory_engine.py` replace

```python
TOPIC_WRITE_VERBS = frozenset({"topics-set-list", "set-topics", "set-level-topics", "set-top-topics"})
```

  with

```python
TOPIC_WRITE_VERBS = frozenset({"topics-set-list", "set-topics", "set-level-topics", "set-top-topics",
                               "render-topics"})
```

  (d) In `plugins/bitranox/hooks/memory_engine.py` replace

```python
    memory writes are off. Only `set-topics` has the flag (argparse refuses it on the others), and
    `set_fact_topics` refuses a real write under the switch whatever this says."""
```

  with

```python
    memory writes are off. Only `set-topics` and `render-topics` have the flag (argparse refuses
    it on the others), and both refuse a real write under the switch whatever this says."""
```

  (e) In `plugins/bitranox/hooks/memory_engine.py` replace

```python
    """The four topic write verbs; refusals are raised and mapped by the caller."""
```

  with

```python
    """The topic write verbs; refusals are raised and mapped by the caller."""
    if args.cmd == "render-topics":
        _print_render(render_topics(args.proj, scope=args.scope, dry_run=args.dry_run), args.as_json)
        return 0
```

  (f) In `plugins/bitranox/hooks/memory_engine.py` replace

```python
    sl = sub.add_parser("topics-stale", help="exit 1 when a level's topics need choosing again")
```

  with

```python
    rd = sub.add_parser("render-topics",
                        help="place the pointer lines of topic-bound facts: at each level that has "
                             "one of a fact's topics while no level above it does")
    rd.add_argument("--proj", required=True, help="any dir of the tree")
    rd.add_argument("--scope", required=True, choices=["tree"],
                    help="tree: every level, adds then removes (the dream)")
    rd.add_argument("--dry-run", action="store_true", dest="dry_run")
    rd.add_argument("--json", action="store_true", dest="as_json")
    sl = sub.add_parser("topics-stale", help="exit 1 when a level's topics need choosing again")
```

- [ ] **Step 4: Run the tests.** Step 2's command - expected: `17 passed`. Then
  `cd <W> && TEST plugins/bitranox/hooks/tests` - expected: no failure (measured in the scratch copy for the engine-related part, `-k "memory_engine or topic or uuid_store or pin_gate or mod_bridge or memory"`: 924 passed, 1 skipped, before this file's tests).

- [ ] **Step 5: Mutation battery.** Write `$SCRATCH/t9-battery.json` for `mutation_arm.py
  --battery` (`<P>/skills/compuse-toolbox/scripts/mutation_arm.py`, run with `--with PyYAML
  --with lxml --with defusedxml --with ruamel.yaml --with httpx2`), tests: this task's test files.
  One arm per row: arm name, file, the line(s) the arm takes out, what it puts there. Each arm
  changes only the code this task added or edited; every arm must be KILLED (all were, by hand,
  in the scratch copy):

```text
pinned-managed                             memory_engine.py  if not topics or slug in pinned or _line_from_head(slug, head) is None:  ->  if not topics or _line_from_head(slug, head) is None:
universal-managed                          memory_engine.py  if not topics or slug in pinned or _line_from_head(slug, head) is None:  ->  if topics is None or slug in pinned or _line_from_head(slug, head) is None:
cap-off                                    memory_engine.py  if size > MAX_RENDER_BLOCK_BYTES:  ->  if False:
refresh-off                                memory_engine.py  have.title, have.hook = line.title, line.hook  ->  (removed)
dry-run-adds                               memory_engine.py  if (added or refreshed) and not dry_run:  ->  if added or refreshed:
dry-run-drops                              memory_engine.py  if removed and not dry_run:  ->  if removed:
remove-first                               memory_engine.py  _add_lines(dirs[parts], _wanted_lines(anchor, place, pinned, parts, dirs[parts]), rep, / dry_run, write)  ->  pass
drop-unplaced-off                          memory_engine.py  if topics is not None and parts not in place(topics):  ->  if False:
no-list-ignored                            memory_engine.py  if topic_store.load(anchor) is None: / return {"list": False}  ->  (removed)
top-block-not-required                     memory_engine.py  if not any(_level_parts(anchor, level) == tp.TOP for level in levels):  ->  if False:
writes-off-ignored                         memory_engine.py  if not dry_run: / sig.refuse_if_memory_writes_off()  ->  (removed)  (in `def render_topics`)
levels-without-topic-scanned-for-top-only  memory_engine.py  if parts != tp.TOP and not level_map.topics(parts):  ->  if parts == tp.TOP:
```

- [ ] **Step 6: Commit** `memory_engine.py` and the new test file; message "memory_engine: render-topics places the lines of topic-bound facts, tree scope".

### Task 10: M3c - `--scope chain`, and one line again for an un-bound fact

**Files:**
- Modify: `plugins/bitranox/hooks/memory_engine.py` (a new block above `render_topics`;
  `render_topics`, the `render-topics` parser, `set_fact_topics`, the `set-topics` output)
- Test: `plugins/bitranox/hooks/tests/test_memory_engine_render_chain.py`

**Interfaces:**
- Consumes: Tasks 8-9; `altitude_chain`, `us.add_pointer`, `_drop_pointer`.
- Produces: `render_topics(..., scope="chain")`: only levels on `proj`'s chain, from the tree
  top down; a line placed at a level is added unless a level above on the chain holds the slug;
  a managed line a level above holds is dropped; a line that is merely no longer placed there
  stays (the tree-scope run sweeps); no file outside the chain is written.
- `set_fact_topics` returns `{"set", "unchanged", "collapsed"}`: a fact that WAS bound, is not
  pinned and has more than one line, when un-bound (`--universal` or `--clear`), gets a line at
  the tree top first and then loses the others. CLI: `~ note: N un-bound fact(s) had a line at
  several levels; each now has one line, at the tree top: <slugs>` (`would keep` on a dry run).

**Out of scope:**
- A nap's use of chain scope (Task 18).
- Collapsing a duplicate of a fact that was never bound: that is a duplicate pointer, reported
  by `--check-tree` as before.

**STOP conditions:**
- an anchor text of Step 3 is not found exactly once (the code moved since CHECKPOINT A: read the
  function it names and report, do not guess);
- a chain-scope test shows a write outside the chain;
- a mutation arm of Step 5 survives.

**What is held in memory:** as Task 9, for the chain's levels only, plus the set of slugs the
  levels above hold (one short string per pointer on the chain); for the collapse, the levels
  holding each un-bound row's slug (batch rows times copies).

- [ ] **Step 1: Write the failing tests.**

  Create `plugins/bitranox/hooks/tests/test_memory_engine_render_chain.py`:

```python
"""Tests for `render-topics --scope chain` (the nap's render: only the levels from a directory up
to the tree top are read for their lines or written) and for what `set-topics` does with the
lines of a fact it un-binds. All content ASCII.
"""

import os
from pathlib import Path

import pytest

import memory_engine as E
import self_improve_signals as sig
import topic_store
import uuid_store as us

HOOK = "When a rule is about one stack, bind it to that stack's topic."
SCOPE = "WHAT: a level\nSTACK: python"
LIST = {"python": "Python code and its tooling", "rust": "Rust code", "git": "git and GitHub"}


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch):
    h = tmp_path / "home"
    h.mkdir(exist_ok=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    return h


def _tree(tmp_path, with_list=True):
    anchor = tmp_path / "tree"
    anchor.mkdir()
    (anchor / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (anchor / us.STORE_DIRNAME).mkdir()
    if with_list:
        topic_store.save_list(anchor, LIST, "jev")
    assert E.main(["set-scope", "--proj", str(anchor), "--scope", "WHAT: the top\nSTACK: none"]) == 0
    return str(anchor)


def _level(anchor, rel, topics=None):
    level = Path(anchor, *rel.split("/"))
    level.mkdir(parents=True, exist_ok=True)
    (level / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    assert E.main(["set-scope", "--proj", str(level), "--scope", SCOPE]) == 0
    if topics is not None:
        E.set_level_topics(str(level), topics)
    return str(level)


def _fact(level, slug, topics=None, pin=False):
    E.add_or_update_entry(level, title="T " + slug, hook=HOOK, body="body of " + slug,
                          type_="feedback", slug=slug, pin=pin)
    if topics is not None:
        E.set_fact_topics(level, {slug: topics})


def _slugs(level):
    text = sig.claude_local_md_path(level).read_text(encoding="utf-8")
    return sorted(p.slug for p in us.parse_pointer_index(text)[1])


def _snapshot(anchor):
    return {str(p): p.read_bytes() for p in sorted(Path(anchor).rglob("*"))
            if p.is_file() and not p.name.endswith(".lock")}


def _two_python_levels(tmp_path):
    anchor = _tree(tmp_path)
    levels = {rel: _level(anchor, rel, topics) for rel, topics in (
        ("a", ()), ("a/py", ("python",)), ("a/other", ()), ("b", ()), ("b/py", ("python",)),
        ("b/other", ()))}
    return anchor, levels


def _recording(calls, fail_at=None):
    def write(path, text):
        if fail_at is not None and str(path) == str(fail_at):
            raise OSError(28, "No space left on device", str(path))
        calls.append(str(path))
        return us.write_if_changed(path, text)
    return write


def _local(level):
    return str(sig.claude_local_md_path(level))


def test_a_chain_render_writes_only_its_own_levels(tmp_path, capsys):
    anchor, levels = _two_python_levels(tmp_path)
    _fact(levels["a/other"], "feedback-py-rule", ("python",))
    siblings = {rel: sig.claude_local_md_path(levels[rel]).read_bytes()
                for rel in ("a/other", "b", "b/py", "b/other")}
    assert E.main(["render-topics", "--proj", levels["a/py"], "--scope", "chain"]) == 0
    assert "render-topics (chain): 1 managed fact(s); changed 1 level(s)" in capsys.readouterr().out
    assert _slugs(levels["a/py"]) == ["feedback-py-rule"]
    assert {rel: sig.claude_local_md_path(levels[rel]).read_bytes() for rel in siblings} == siblings
    calls = []
    E.render_topics(levels["b/py"], scope="chain", write=_recording(calls))
    assert calls == [_local(levels["b/py"])]


def test_a_line_a_level_above_holds_is_not_repeated_below(tmp_path):
    anchor, levels = _two_python_levels(tmp_path)
    _fact(anchor, "feedback-py-rule", ("python",))
    rep = E.render_topics(levels["a/py"], scope="chain")
    # the top still holds the line, so the chain reads it already; the tree render moves it
    assert rep["levels"] == {} and _slugs(levels["a/py"]) == [] and _slugs(anchor) == ["feedback-py-rule"]


def test_a_chain_render_never_drops_a_line_for_being_placed_elsewhere(tmp_path):
    anchor, levels = _two_python_levels(tmp_path)
    _fact(levels["a"], "feedback-py-rule", ("python",))
    E.render_topics(levels["a/other"], scope="chain")
    assert _slugs(levels["a"]) == ["feedback-py-rule"]


def test_a_copy_below_a_level_that_now_holds_the_line_is_dropped(tmp_path):
    anchor, levels = _two_python_levels(tmp_path)
    _fact(anchor, "feedback-py-rule", ("python",))
    E.render_topics(anchor)
    assert _slugs(levels["a/py"]) == _slugs(levels["b/py"]) == ["feedback-py-rule"]
    E.set_level_topics(levels["a"], ("python",))           # a itself is about python now
    other_subtree = sig.claude_local_md_path(levels["b/py"]).read_bytes()
    calls = []
    rep = E.render_topics(levels["a/py"], scope="chain", write=_recording(calls))
    assert calls == [_local(levels["a"]), _local(levels["a/py"])]      # the add, then the drop
    assert _slugs(levels["a"]) == ["feedback-py-rule"] and _slugs(levels["a/py"]) == []
    assert rep["levels"][levels["a/py"]]["removed"] == 1
    assert sig.claude_local_md_path(levels["b/py"]).read_bytes() == other_subtree


def test_a_failed_chain_add_drops_nothing(tmp_path):
    anchor, levels = _two_python_levels(tmp_path)
    _fact(anchor, "feedback-py-rule", ("python",))
    E.render_topics(anchor)
    E.set_level_topics(levels["a"], ("python",))
    with pytest.raises(OSError):
        E.render_topics(levels["a/py"], scope="chain",
                        write=_recording([], fail_at=sig.claude_local_md_path(levels["a"])))
    assert _slugs(levels["a/py"]) == ["feedback-py-rule"] and _slugs(levels["a"]) == []


def test_a_pinned_or_untagged_copy_below_is_left_alone(tmp_path):
    anchor, levels = _two_python_levels(tmp_path)
    _fact(anchor, "feedback-plain")
    local = sig.claude_local_md_path(levels["a/py"])
    text = local.read_text(encoding="utf-8")
    scope, pointers = us.parse_pointer_index(text)
    pointers.append(us.Pointer(slug="feedback-plain", title="T feedback-plain", hook=HOOK))
    local.write_text(us.upsert_pointer_block(text, scope, pointers), encoding="utf-8")
    before = local.read_bytes()
    E.render_topics(levels["a/py"], scope="chain")
    assert local.read_bytes() == before


def test_a_chain_dry_run_writes_nothing(tmp_path):
    anchor, levels = _two_python_levels(tmp_path)
    _fact(levels["a/other"], "feedback-py-rule", ("python",))
    before = _snapshot(anchor)
    rep = E.render_topics(levels["a/py"], scope="chain", dry_run=True)
    assert rep["levels"][levels["a/py"]]["added"] == 1 and _snapshot(anchor) == before


# ---- set-topics: a fact that is un-bound keeps one line -----------------------------------------

@pytest.mark.parametrize("how", ["--universal", "--clear"])
def test_un_binding_a_fact_with_several_lines_leaves_one_at_the_top(tmp_path, capsys, how):
    anchor, levels = _two_python_levels(tmp_path)
    _fact(anchor, "feedback-py-rule", ("python",))
    E.render_topics(anchor)
    capsys.readouterr()
    assert E.main(["set-topics", "--proj", anchor, "--slug", "feedback-py-rule", how]) == 0
    assert "1 un-bound fact(s) had a line at several levels" in capsys.readouterr().out
    assert _slugs(anchor) == ["feedback-py-rule"]
    assert _slugs(levels["a/py"]) == _slugs(levels["b/py"]) == []
    assert HOOK in sig.claude_local_md_path(anchor).read_text(encoding="utf-8")


def test_the_top_line_is_written_before_the_others_are_dropped(tmp_path):
    anchor, levels = _two_python_levels(tmp_path)
    _fact(anchor, "feedback-py-rule", ("python",))
    E.render_topics(anchor)
    # a level file that cannot be rewritten stops the collapse at its first drop
    blocked = sig.claude_local_md_path(levels["a/py"])
    os.chmod(blocked, 0o444)
    try:
        with pytest.raises(OSError):
            E.set_fact_topics(anchor, {"feedback-py-rule": ()})
    finally:
        os.chmod(blocked, 0o644)
    assert _slugs(anchor) == ["feedback-py-rule"] and _slugs(levels["a/py"]) == ["feedback-py-rule"]


def test_un_binding_a_fact_with_one_line_leaves_it_where_it_is(tmp_path):
    anchor, levels = _two_python_levels(tmp_path)
    _fact(levels["a/py"], "feedback-py-rule", ("python",))
    rep = E.set_fact_topics(anchor, {"feedback-py-rule": ()})
    assert rep["collapsed"] == [] and _slugs(levels["a/py"]) == ["feedback-py-rule"]
    assert _slugs(anchor) == []


def test_a_never_bound_duplicate_is_not_collapsed(tmp_path):
    anchor, levels = _two_python_levels(tmp_path)
    _fact(levels["a/py"], "feedback-plain")
    local = sig.claude_local_md_path(levels["b/py"])
    text = local.read_text(encoding="utf-8")
    scope, pointers = us.parse_pointer_index(text)
    pointers.append(us.Pointer(slug="feedback-plain", title="T feedback-plain", hook=HOOK))
    local.write_text(us.upsert_pointer_block(text, scope, pointers), encoding="utf-8")
    rep = E.set_fact_topics(anchor, {"feedback-plain": ()})
    assert rep["collapsed"] == [] and _slugs(levels["b/py"]) == ["feedback-plain"]


def test_a_dry_run_names_the_collapse_and_writes_nothing(tmp_path, capsys):
    anchor, levels = _two_python_levels(tmp_path)
    _fact(anchor, "feedback-py-rule", ("python",))
    E.render_topics(anchor)
    before = _snapshot(anchor)
    capsys.readouterr()
    assert E.main(["set-topics", "--proj", anchor, "--slug", "feedback-py-rule", "--clear", "--dry-run"]) == 0
    assert "each would keep one line" in capsys.readouterr().out and _snapshot(anchor) == before
```

- [ ] **Step 2: Run them to see them fail.**
  `cd <W> && TEST plugins/bitranox/hooks/tests/test_memory_engine_render_chain.py` - expected: `13 failed`. This is the RED proof: the same files were run
  against the code before this task in the scratch copy with exactly that result.

- [ ] **Step 3: Implement.** Each anchor below occurs exactly once in its file; assert
  that before editing.

  (a) In `plugins/bitranox/hooks/memory_engine.py` insert this block directly above the line `def render_topics(proj, scope="tree", dry_run=False, write=None):` (two blank lines between top-level definitions, as the block itself ends):

```python
def _chain_levels(anchor, proj, levels):
    """The curated levels from the tree top down to `proj`, as (parts, level dir), top first. Found
    lexically, as levels are keyed: a level reached through a symlink is the level its path names."""
    here = _level_parts(anchor, proj)
    by_parts = {_level_parts(anchor, level): level for level in levels}
    return [(here[:cut], by_parts[here[:cut]]) for cut in range(len(here) + 1) if here[:cut] in by_parts]


def _render_chain(anchor, proj, levels, level_map, dirs, pinned, rep, dry_run, write):
    """Chain scope: only the levels from the tree top down to `proj` are read for their lines or
    written. Top first, a level gets the lines placed at it unless a level above holds the slug;
    then, when every add went through, a managed line a level above holds is dropped. A line is
    never dropped for being placed elsewhere: another subtree may still read it, and the tree
    scope sweeps. Holds the slugs of the chain's own blocks."""
    place = _Placer(level_map)
    chain = _chain_levels(anchor, proj, levels)
    above = set()
    for parts, level in chain:
        wanted = {}
        if parts in dirs and (parts == tp.TOP or level_map.topics(parts)):
            wanted = _wanted_lines(anchor, place, pinned, parts, level, skip=above)
        above |= _add_lines(level, wanted, rep, dry_run, write)
    above = set()
    for parts, level in chain:
        doomed, here = set(), set()
        for ptr in us.parse_pointer_index(read_store_text(sig.claude_local_md_path(level)))[1]:
            here.add(ptr.slug)
            if ptr.slug not in above or ptr.pin or ptr.legacy:
                continue
            head = _read_body_head(us.body_path(anchor, ptr.slug))
            if head is not None and _managed_topics(ptr.slug, head, pinned) is not None:
                doomed.add(ptr.slug)
        _drop_lines(level, doomed, rep, dry_run, write)
        above |= here


def _copy_levels(anchor, wanted):
    """{slug: [every level dir holding a line of it]} for the slugs in `wanted`, top first, from
    one walk over the tree's levels."""
    found = {}
    for level in sorted(curated_levels_under(anchor), key=lambda d: len(_level_parts(anchor, d))):
        for ptr in us.parse_pointer_index(read_store_text(sig.claude_local_md_path(level)))[1]:
            if ptr.slug in wanted:
                found.setdefault(ptr.slug, []).append(level)
    return found


def _collapse_copies(anchor, slug, holders):
    """Leave ONE line of an un-bound fact: at the tree top, written before the others are dropped,
    so no moment has the fact without a line. `holders` are the levels holding one, top first."""
    top = os.path.abspath(str(anchor))
    if _level_parts(anchor, holders[0]) != tp.TOP:
        src = next(p for p in us.parse_pointer_index(
            read_store_text(sig.claude_local_md_path(holders[0])))[1] if p.slug == slug)
        us.add_pointer(top, slug, src.title, src.hook)
    for level in holders:
        if _level_parts(anchor, level) != tp.TOP:
            _drop_pointer(level, slug)
```

  (b) In `plugins/bitranox/hooks/memory_engine.py` replace

```python
    if scope != "tree":
        raise ValueError("scope must be 'tree', not %r" % (scope,))
```

  with

```python
    if scope not in ("tree", "chain"):
        raise ValueError("scope must be 'tree' or 'chain', not %r" % (scope,))
```

  (c) In `plugins/bitranox/hooks/memory_engine.py` replace

```python
    _render_tree(anchor, levels, level_map, dirs, pinned, rep, dry_run, write)
    return rep
```

  with

```python
    if scope == "tree":
        _render_tree(anchor, levels, level_map, dirs, pinned, rep, dry_run, write)
    else:
        _render_chain(anchor, proj, levels, level_map, dirs, pinned, rep, dry_run, write)
    return rep
```

  (d) In `plugins/bitranox/hooks/memory_engine.py` replace

```python
added, dropped or rewritten here. `scope` is 'tree' (every level; adds, then removes).
    `write(path, text)`
```

  with

```python
added, dropped or rewritten here. `scope` is 'tree' (every level; adds, then removes) or
    'chain' (only the levels from `proj` up to the tree top). `write(path, text)`
```

  (e) In `plugins/bitranox/hooks/memory_engine.py` replace

```python
    rd.add_argument("--proj", required=True, help="any dir of the tree")
    rd.add_argument("--scope", required=True, choices=["tree"],
                    help="tree: every level, adds then removes (the dream)")
```

  with

```python
    rd.add_argument("--proj", required=True,
                    help="any dir of the tree (tree) / the dir whose chain is rendered (chain)")
    rd.add_argument("--scope", required=True, choices=["tree", "chain"],
                    help="tree: every level, adds then removes (the dream); chain: only the levels "
                         "from --proj up to the tree top (the nap)")
```

  (f) In `plugins/bitranox/hooks/memory_engine.py` replace

```python
    rep = {"set": [], "unchanged": 0}
    for slug in sorted(rows):
        with sig.memory_lock(sig.claude_local_md_path(owners[slug][0])):
            body = read_store_text(us.body_path(anchor, slug)).rstrip("\n")
            tagged = _with_topics(body, rows[slug])
            if tagged == body:
                rep["unchanged"] += 1
                continue
            if not dry_run:
                us.put_body(str(anchor), slug, tagged)
            rep["set"].append(slug)
    return rep
```

  with

```python
    unbound = {slug for slug in rows if not rows[slug] and not owners[slug][1]}
    copies = _copy_levels(anchor, unbound) if unbound else {}
    rep = {"set": [], "unchanged": 0, "collapsed": []}
    for slug in sorted(rows):
        with sig.memory_lock(sig.claude_local_md_path(owners[slug][0])):
            body = read_store_text(us.body_path(anchor, slug)).rstrip("\n")
            was_bound = bool(_body_topics(body))
            tagged = _with_topics(body, rows[slug])
            if tagged == body:
                rep["unchanged"] += 1
            else:
                if not dry_run:
                    us.put_body(str(anchor), slug, tagged)
                rep["set"].append(slug)
        if was_bound and len(copies.get(slug, ())) > 1:
            # The fact was placed by topic at several levels and is bound to none now: one line,
            # at the tree top. Outside the lock above: the pointer writers take their own.
            if not dry_run:
                _collapse_copies(anchor, slug, copies[slug])
            rep["collapsed"].append(slug)
    return rep
```

  (g) In `plugins/bitranox/hooks/memory_engine.py` replace

```python
              % ("would set" if args.dry_run else "set", len(rep["set"]), rep["unchanged"]))
        return 0
```

  with

```python
              % ("would set" if args.dry_run else "set", len(rep["set"]), rep["unchanged"]))
        if rep["collapsed"]:
            print("~ note: %d un-bound fact(s) had a line at several levels; each %s one line, at "
                  "the tree top: %s" % (len(rep["collapsed"]), "would keep" if args.dry_run else "now has",
                                        ", ".join(rep["collapsed"][:_REFUSALS_SHOWN])))
        return 0
```

- [ ] **Step 4: Run the tests.** Step 2's command - expected: `13 passed`. Then
  `cd <W> && TEST plugins/bitranox/hooks/tests` - expected: no failure (measured in the scratch copy for the engine-related part, `-k "memory_engine or topic or uuid_store or pin_gate or mod_bridge or memory"`: 924 passed, 1 skipped, before this file's tests).

- [ ] **Step 5: Mutation battery.** Write `$SCRATCH/t10-battery.json` for `mutation_arm.py
  --battery` (`<P>/skills/compuse-toolbox/scripts/mutation_arm.py`, run with `--with PyYAML
  --with lxml --with defusedxml --with ruamel.yaml --with httpx2`), tests: this task's test files.
  One arm per row: arm name, file, the line(s) the arm takes out, what it puts there. Each arm
  changes only the code this task added or edited; every arm must be KILLED (all were, by hand,
  in the scratch copy):

```text
above-not-skipped       memory_engine.py  wanted = _wanted_lines(anchor, place, pinned, parts, level, skip=above)  ->  wanted = _wanted_lines(anchor, place, pinned, parts, level)
chain-drops-unmanaged   memory_engine.py  if head is not None and _managed_topics(ptr.slug, head, pinned) is not None:  ->  if head is not None:
chain-no-drop           memory_engine.py  _drop_lines(level, doomed, rep, dry_run, write)  ->  (removed)
collapse-any-duplicate  memory_engine.py  if was_bound and len(copies.get(slug, ())) > 1:  ->  if len(copies.get(slug, ())) > 1:
collapse-on-dry-run     memory_engine.py  if not dry_run:  ->  if True:  (in `def set_fact_topics`, next to: _collapse_copies(anchor, slug, copies[slug]))
collapse-drops-first    memory_engine.py  us.add_pointer(top, slug, src.title, src.hook)  ->  pass
collapse-off            memory_engine.py  rep["collapsed"].append(slug)  ->  (removed)
```

- [ ] **Step 6: Commit** `memory_engine.py` and the new test file; message "memory_engine: render-topics chain scope; an un-bound fact keeps one line at the tree top".

### Task 11: M4a - the checks know a fact placed by topic

**Files:**
- Modify: `plugins/bitranox/skills/meta-self-improve/reconcile_memory_index.py` (a new block above
  `check_tree`; `check_tree`, `check_references`, their CLI output, the module docstring)
- Modify: `plugins/bitranox/skills/compuse-toolbox/scripts/mem_levels.py`,
  `plugins/bitranox/skills/meta-self-improve/ref_map.py`
- Test: `plugins/bitranox/skills/meta-self-improve/tests/test_reconcile_topic_copies.py`,
  `test_ref_map_topic_copies.py`;
  `plugins/bitranox/skills/compuse-toolbox/tests/test_mem_levels_topic_copies.py`

**Interfaces:**
- Consumes: Tasks 8-10 (`ME.render_topics(..., dry_run=True)`, `ME._read_body_head`,
  `ME._body_topics`, `ME._managed_topics`).
- Produces: `render_drift(anchor) -> tuple[list[tuple[level, missing, differing, extra,
  examples]], refused: str]`; `chain_repeats(dirs)`; `check_tree` report keys `render_drift` and
  `render_refused`; `check_references` key `repeated`. Output lines: `! render drift: <level> ->
  N line(s) missing, N differing from the body, N placed elsewhere (<examples>);
  render-topics --scope tree repairs it`, `! the placement by topic could not be checked:
  <why>`, `! repeated line: ...; render-topics --scope chain drops the lower copy`. Each counts
  as a problem (exit 1). A fact placed by topic at several levels is no `duplicate pointer`,
  and a `[[ref]]` to it is neither a sideways ref (`--check-tree`) nor a chain orphan
  (`--check`): where it is read is computed, so a citer cannot be asked to sit above it.
- `mem_levels.py`: `Report.placed` and `Report.pinned`; a placed fact prints `= placed by
  topic: <slug> at <levels>` instead of a duplicate. `ref_map.py`: an entry gains `also_at`;
  `judge_moves` reports conflict kind `placed-by-topic` for a move of such a fact.

**Out of scope:**
- Repairing drift: the check only reports; `render-topics` repairs.
- `store_manifest.py`, `dedup_scan.py`, `statusrot.py`, `versionrot.py`, `uuid_store.resolve`,
  `recall-memory.py`, `migrate_to_slug_store.py`, `gather_scan.py`, the `jev_shadow_*` ports:
  measured at CHECKPOINT A on a tree with a fact at two levels, each already keys by (level,
  slug) or takes the first level, and needs no change.

**STOP conditions:**
- an anchor text of Step 3 is not found exactly once (the code moved since CHECKPOINT A: read the
  function it names and report, do not guess);
- `--check-tree` on a rendered planted tree does not print `TOTAL tree problems: 0`;
- a mutation arm of Step 5 survives.

**What is held in memory:** the checks hold what they held (one entry per pointer of the tree for
  `--check-tree`); new: the render report of a dry run (one row per changed level with at most 20
  example slugs), never a list per slug. `_bound_to_a_topic` reads one body head per asked slug.

- [ ] **Step 1: Write the failing tests.**

  Create `plugins/bitranox/skills/meta-self-improve/tests/test_reconcile_topic_copies.py`:

```python
"""Tests for what the integrity checks say about facts placed by topic: their copies are no
duplicates, a tree whose lines differ from a fresh render has drift, and a ref to such a fact
resolves through its body wherever its lines stand. All content ASCII.
"""

from pathlib import Path

import pytest

import reconcile_memory_index as R

import memory_engine as ME  # noqa: E402  (reconcile put hooks/ on sys.path at import)
import self_improve_signals as sig  # noqa: E402
import topic_store  # noqa: E402
import uuid_store as us  # noqa: E402

HOOK = "When a rule is about one stack, bind it to that stack's topic."
SCOPE = "WHAT: a level\nSTACK: python"
LIST = {"python": "Python code and its tooling", "rust": "Rust code"}


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch):
    h = tmp_path / "home"
    h.mkdir(exist_ok=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    return h


def _level(anchor, rel, topics=None):
    level = Path(anchor, *rel.split("/")) if rel else Path(anchor)
    level.mkdir(parents=True, exist_ok=True)
    (level / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    assert ME.main(["set-scope", "--proj", str(level), "--scope", SCOPE]) == 0
    if topics is not None:
        ME.set_level_topics(str(level), topics)
    return str(level)


def _fact(level, slug, topics=None, pin=False, body=None):
    ME.add_or_update_entry(level, title="T " + slug, hook=HOOK, body=body or "body of " + slug,
                           type_="feedback", slug=slug, pin=pin)
    if topics is not None:
        ME.set_fact_topics(level, {slug: topics})


def _rendered(tmp_path):
    """A tree with python at a/py and b/py, one python rule rendered at both, one plain top rule."""
    anchor = tmp_path / "tree"
    anchor.mkdir()
    (anchor / us.STORE_DIRNAME).mkdir()
    topic_store.save_list(anchor, LIST, "jev")
    levels = {rel: _level(str(anchor), rel, topics) for rel, topics in (
        ("", None), ("a", ()), ("a/py", ("python",)), ("a/other", ()), ("b", ()),
        ("b/py", ("python",)), ("b/other", ()))}
    _fact(levels[""], "feedback-py-rule", ("python",))
    _fact(levels[""], "feedback-top-rule")
    ME.render_topics(levels[""])
    return levels


def _plant_line(level, slug, hook=HOOK, pin=False):
    local = sig.claude_local_md_path(level)
    text = local.read_text(encoding="utf-8")
    scope, pointers = us.parse_pointer_index(text)
    pointers = [p for p in pointers if p.slug != slug]
    pointers.append(us.Pointer(slug=slug, title="T " + slug, hook=hook, pin=pin))
    local.write_text(us.upsert_pointer_block(text, scope, pointers), encoding="utf-8")


def _check_tree(levels, capsys):
    capsys.readouterr()
    rc = R.main(["--check-tree", levels[""]])
    return rc, capsys.readouterr().out


def test_a_rendered_tree_has_no_problem(tmp_path, capsys):
    levels = _rendered(tmp_path)
    rc, out = _check_tree(levels, capsys)
    assert rc == 0 and "TOTAL tree problems: 0" in out and "duplicate pointer" not in out
    rep = R.check_tree(levels[""])
    assert rep["duplicates"] == {} and rep["render_drift"] == [] and rep["render_refused"] == ""


def test_a_missing_copy_is_render_drift(tmp_path, capsys):
    levels = _rendered(tmp_path)
    ME._drop_pointer(levels["b/py"], "feedback-py-rule")
    rc, out = _check_tree(levels, capsys)
    assert rc == 1 and "TOTAL tree problems: 1" in out
    assert "! render drift: %s -> 1 line(s) missing, 0 differing from the body, 0 placed elsewhere " \
           "(feedback-py-rule)" % levels["b/py"] in out


def test_a_copy_that_differs_from_its_body_is_render_drift(tmp_path, capsys):
    levels = _rendered(tmp_path)
    _plant_line(levels["a/py"], "feedback-py-rule", hook="When this line went stale, it says this.")
    rc, out = _check_tree(levels, capsys)
    assert rc == 1 and "0 line(s) missing, 1 differing from the body, 0 placed elsewhere" in out


def test_a_copy_at_a_level_it_is_not_placed_at_is_render_drift_not_a_duplicate(tmp_path, capsys):
    levels = _rendered(tmp_path)
    _plant_line(levels["a/other"], "feedback-py-rule")
    rc, out = _check_tree(levels, capsys)
    assert rc == 1 and "duplicate pointer" not in out
    assert "! render drift: %s -> 0 line(s) missing, 0 differing from the body, 1 placed elsewhere" \
           % levels["a/other"] in out


def test_an_unbound_fact_at_two_levels_stays_a_duplicate(tmp_path, capsys):
    levels = _rendered(tmp_path)
    _plant_line(levels["a/other"], "feedback-top-rule")
    rc, out = _check_tree(levels, capsys)
    assert rc == 1 and "! duplicate pointer: feedback-top-rule at 2 levels" in out


def test_a_pinned_tagged_fact_at_two_levels_stays_a_duplicate(tmp_path, capsys):
    levels = _rendered(tmp_path)
    _fact(levels["a"], "feedback-pinned", pin=True)
    path = us.body_path(levels[""], "feedback-pinned")
    us.put_body(levels[""], "feedback-pinned", ME._with_topics(path.read_text(encoding="utf-8"), ("python",)))
    _plant_line(levels["b"], "feedback-pinned", pin=True)
    rc, out = _check_tree(levels, capsys)
    assert rc == 1 and "! duplicate pointer: feedback-pinned at 2 levels" in out


def test_a_ref_to_a_topic_placed_fact_is_no_sideways_ref(tmp_path, capsys):
    levels = _rendered(tmp_path)
    _fact(levels[""], "feedback-citer", body="See [[feedback-py-rule]] for the stack rule.")
    _fact(levels["a/other"], "feedback-plain")
    rc, out = _check_tree(levels, capsys)
    assert rc == 0 and "sideways/downward ref" not in out
    # a ref to a fact that is NOT placed by topic is still judged by its level
    _fact(levels[""], "feedback-citer-2", body="See [[feedback-plain]].")
    rc, out = _check_tree(levels, capsys)
    assert rc == 1 and "[[feedback-plain]] in feedback-citer-2" in out


def test_a_topics_line_that_does_not_parse_is_reported_as_an_unchecked_placement(tmp_path, capsys):
    levels = _rendered(tmp_path)
    local = sig.claude_local_md_path(levels["b"])
    text = local.read_text(encoding="utf-8")
    local.write_text(us.upsert_pointer_block(text, SCOPE + "\nTOPICS: Not A Tag", []), encoding="utf-8")
    rc, out = _check_tree(levels, capsys)
    assert rc == 1 and "! the placement by topic could not be checked" in out and levels["b"] in out


# ---- --check over a chain -----------------------------------------------------------------------

def test_a_clean_chain_has_no_problem_and_a_ref_to_a_placed_fact_is_no_orphan(tmp_path, capsys):
    levels = _rendered(tmp_path)
    _fact(levels[""], "feedback-citer", body="See [[feedback-py-rule]] for the stack rule.")
    capsys.readouterr()
    assert R.main(["--check", levels["a/py"]]) == 0
    assert R.main(["--check", levels[""]]) == 0
    assert "orphan ref" not in capsys.readouterr().out
    assert R.check_references([levels[""]])["checked"] == 1


def test_a_placed_line_a_level_above_also_holds_is_a_chain_problem(tmp_path, capsys):
    levels = _rendered(tmp_path)
    _plant_line(levels["a"], "feedback-py-rule")
    capsys.readouterr()
    assert R.main(["--check", levels["a/py"]]) == 1
    out = capsys.readouterr().out
    assert "! repeated line: feedback-py-rule at %s is also held by %s above it" \
           % (levels["a/py"], levels["a"]) in out and "TOTAL problems: 1" in out
    # the other subtree's chain does not include a, so it is clean
    assert R.main(["--check", levels["b/py"]]) == 0


def test_an_unbound_line_repeated_above_is_left_to_check_tree(tmp_path):
    levels = _rendered(tmp_path)
    _plant_line(levels["a/py"], "feedback-top-rule")
    assert R.chain_repeats([levels["a/py"]]) == []


def test_a_tree_without_a_topic_list_has_no_drift(tmp_path):
    anchor = tmp_path / "tree"
    anchor.mkdir()
    (anchor / us.STORE_DIRNAME).mkdir()
    level = _level(str(anchor), "")
    _fact(level, "feedback-a")
    assert R.render_drift(level) == ([], "")
```

  Create `plugins/bitranox/skills/meta-self-improve/tests/test_ref_map_topic_copies.py`:

```python
"""Tests for ref_map on a fact held at several levels (the engine places it by topic): the map
names every level, a planned move of it is a conflict, and a ref to it is not judged by one of
its levels. All content ASCII.
"""
import io
import json
import sys
from pathlib import Path

import pytest

import ref_map

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "hooks"))
import uuid_store as US  # noqa: E402


@pytest.fixture
def tree(tmp_path):
    root = tmp_path / "t"
    facts = root / ".claude-memory" / "facts"
    facts.mkdir(parents=True)
    levels = {"": {"top-citer": "Cites [[py-rule]].\n"},
              "a": {"py-rule": "A python rule.\n", "a-citer": "Cites [[py-rule]].\n"},
              "b": {"py-rule": "A python rule.\n"}}
    for rel, entries in levels.items():
        d = root / rel if rel else root
        d.mkdir(parents=True, exist_ok=True)
        lines = [US.INDEX_BEGIN, "", "## Memory index"]
        lines += ["- [%s](mem:%s) - When something, do something." % (s, s) for s in entries]
        (d / "CLAUDE.local.md").write_text("\n".join(lines + [US.INDEX_END]) + "\n", encoding="utf-8")
        for slug, body in entries.items():
            (facts / (slug + ".md")).write_text(body, encoding="utf-8")
    return root


def _run(argv):
    out, err = io.StringIO(), io.StringIO()
    return ref_map.main(argv, out=out, err=err), out.getvalue(), err.getvalue()


def test_the_map_names_every_level_holding_a_line(tree):
    assert ref_map.read_levels(tree)["py-rule"] == str(tree / "a")
    assert ref_map.read_copies(tree) == {"py-rule": [str(tree / "a"), str(tree / "b")]}
    code, out, _ = _run(["--root", str(tree), "--json", "py-rule"])
    entry = json.loads(out)["data"]["entries"][0]
    assert code == 0 and entry["level"] == str(tree / "a") and entry["also_at"] == [str(tree / "b")]
    _code, text, _ = _run(["--root", str(tree), "py-rule"])
    assert "also at  : %s" % (tree / "b") in text


def test_a_planned_move_of_a_fact_with_several_lines_is_a_conflict(tree, tmp_path):
    plan = tmp_path / "moves.jsonl"
    plan.write_text(json.dumps({"slug": "py-rule", "to": str(tree)}) + "\n", encoding="utf-8")
    code, out, _ = _run(["--root", str(tree), "--moves", str(plan)])
    assert code == 1 and "placed-by-topic" in out and "py-rule" in out


def test_moving_a_citer_does_not_strand_its_ref_to_a_fact_with_several_lines(tree, tmp_path):
    plan = tmp_path / "moves.jsonl"
    plan.write_text(json.dumps({"slug": "a-citer", "to": str(tree)}) + "\n", encoding="utf-8")
    code, out, _ = _run(["--root", str(tree), "--moves", str(plan)])
    assert code == 0 and "0 conflict(s)" in out
```

  Create `plugins/bitranox/skills/compuse-toolbox/tests/test_mem_levels_topic_copies.py`:

```python
"""Tests for how mem_levels reports a fact held at several levels: one the engine places by topic
is listed as placed, anything else stays a duplicate pointer. All content ASCII.
"""

from pathlib import Path

import mem_levels

BLOCK = """<!-- BITRANOX-MEMORY-INDEX:BEGIN managed by bitranox self-improve; do not hand-edit. -->
<!-- bitranox:self-learning -->
WHAT: a level
<!-- /bitranox:self-learning -->

## Memory index
{rows}
<!-- BITRANOX-MEMORY-INDEX:END -->
"""


def _tree(root: Path, levels: dict[str, list[str]], frames: dict[str, str]) -> Path:
    """{relative level dir: [pointer lines]} plus {slug: extra frontmatter lines}."""
    for rel, rows in levels.items():
        d = root / rel if rel != "." else root
        d.mkdir(parents=True, exist_ok=True)
        (d / "CLAUDE.local.md").write_text(BLOCK.format(rows="\n".join(rows)), encoding="utf-8")
    facts = root / ".claude-memory" / "facts"
    facts.mkdir(parents=True, exist_ok=True)
    for slug, extra in frames.items():
        (facts / (slug + ".md")).write_text("---\nname: %s\n%s---\n\nbody\ntopics: [prose]\n"
                                            % (slug, extra), encoding="utf-8")
    return root


def _row(slug, pin=False):
    return "- [T](mem:%s) - When x, do y.%s" % (slug, " <!-- bx:pin -->" if pin else "")


def test_a_topic_bound_fact_at_two_levels_is_placed_not_a_duplicate(tmp_path, capsys):
    root = _tree(tmp_path / "t", {"a": [_row("py-rule")], "b": [_row("py-rule")]},
                 {"py-rule": "topics: [python]\n"})
    report = mem_levels.scan(root)
    assert report.placed == {"py-rule": ["a", "b"]} and report.duplicates == {}
    assert report.as_dict()["placed"] == {"py-rule": ["a", "b"]}
    assert mem_levels.main(["--root", str(root)]) == 0
    out = capsys.readouterr().out
    assert "= placed by topic: py-rule at a, b" in out and "duplicate pointer" not in out


def test_an_untagged_an_unbound_and_a_pinned_fact_stay_duplicates(tmp_path):
    rows = {"a": [_row("plain"), _row("universal"), _row("pinned", pin=True)],
            "b": [_row("plain"), _row("universal"), _row("pinned")]}
    root = _tree(tmp_path / "t", rows, {"plain": "", "universal": "topics: []\n",
                                        "pinned": "topics: [python]\n"})
    report = mem_levels.scan(root)
    assert report.placed == {} and sorted(report.duplicates) == ["pinned", "plain", "universal"]


def test_a_topics_line_in_the_prose_is_no_binding(tmp_path):
    root = _tree(tmp_path / "t", {"a": [_row("plain")], "b": [_row("plain")]}, {"plain": ""})
    assert mem_levels.scan(root).duplicates == {"plain": ["a", "b"]}
```

- [ ] **Step 2: Run them to see them fail.**
  `cd <W> && TEST plugins/bitranox/skills/meta-self-improve/tests/test_reconcile_topic_copies.py plugins/bitranox/skills/meta-self-improve/tests/test_ref_map_topic_copies.py plugins/bitranox/skills/compuse-toolbox/tests/test_mem_levels_topic_copies.py` - expected: `15 failed, 3 passed` (the three pin behaviour that must not change: an unbound duplicate is still a duplicate). This is the RED proof: the same files were run
  against the code before this task in the scratch copy with exactly that result.

- [ ] **Step 3: Implement.** Each anchor below occurs exactly once in its file; assert
  that before editing.

  (a) In `plugins/bitranox/skills/meta-self-improve/reconcile_memory_index.py` insert this block directly above the line `def check_tree(anchor):` (two blank lines between top-level definitions, as the block itself ends):

```python
def render_drift(anchor):
    """([(level, missing, differing, extra, example slugs)], refused) for `anchor`'s tree: what a
    `render-topics --scope tree` would change, read from its dry run, so the check and the
    renderer cannot disagree. Per level with a few examples, never one row per fact. `refused` is
    the reason the render could not be computed at all (a TOPICS line that does not parse, a
    damaged topic file, a level over the block limit), else ''. A tree with no topic list has no
    drift."""
    try:
        rep = ME.render_topics(str(anchor), scope="tree", dry_run=True)
    except (ME.TopicRefusal, ME.topic_store.TopicStoreError) as exc:
        return [], str(exc)
    rows = []
    for level in sorted(rep.get("levels", {})):
        row = rep["levels"][level]
        examples = sorted({slug for slugs in row["examples"].values() for slug in slugs})[:5]
        rows.append((level, row["added"], row["refreshed"], row["removed"], examples))
    return rows, ""


def _bound_to_a_topic(anchor, slug):
    """True when the body of `slug` carries a non-empty `topics:` line: its lines are placed by
    topic, at levels a citing fact's chain need not include."""
    head = ME._read_body_head(us.body_path(anchor, slug))
    return bool(head and ME._body_topics(head))


def chain_repeats(dirs):
    """[(slug, level, level above)] for every topic-placed line at one of `dirs` that a level
    above it also holds: both are read in the same session, so the lower copy is surplus
    (`render-topics --scope chain` drops it). A pinned line is never placed by topic."""
    out = []
    passed = _narrow_to_broad([Path(d) for d in dirs])
    above = {}                                    # level -> {slug: pinned}, read once per level
    for d in passed:
        if not is_curated(d):
            continue
        anchor = ME._anchor(str(d))
        mine = us.parse_pointer_index(ME.read_store_text(sig.claude_local_md_path(d)))[1]
        for lvl in sig.altitude_chain(str(d))[1:]:
            if lvl not in above:
                above[lvl] = ({p.slug: p.pin for p in us.parse_pointer_index(
                    ME.read_store_text(sig.claude_local_md_path(lvl)))[1]} if is_curated(lvl) else {})
            for p in mine:
                if p.pin or p.legacy or p.slug not in above[lvl] or above[lvl][p.slug]:
                    continue                      # not held above, or pinned there
                if _bound_to_a_topic(anchor, p.slug):
                    out.append((p.slug, str(d), str(lvl)))
    return sorted(set(out))
```

  (b) In `plugins/bitranox/skills/meta-self-improve/reconcile_memory_index.py` replace

```python
    all_targets = set()                         # every slug offered anywhere in the tree
```

  with

```python
    all_targets = set()                         # every slug offered anywhere in the tree
    tagged, pinned = set(), set()               # canonical slugs: renderable topic-bound / pinned
```

  (c) In `plugins/bitranox/skills/meta-self-improve/reconcile_memory_index.py` replace

```python
            all_targets.add(cslug)
            body_p =
```

  with

```python
            all_targets.add(cslug)
            if e.pin:
                pinned.add(cslug)
            if not e.legacy and ME._managed_topics(e.slug, bodies.get(e.slug, ""), ()) is not None:
                tagged.add(cslug)
            body_p =
```

  (d) In `plugins/bitranox/skills/meta-self-improve/reconcile_memory_index.py` replace

```python
    duplicates = {s: sorted(lv) for s, lv in slug_levels.items() if len(lv) > 1}
```

  with

```python
    # A MANAGED fact (topic-bound, never pinned) has one line per level it is placed at: those
    # copies are the renderer's, and `render_drift` below says whether they are the right ones.
    managed = tagged - pinned
    duplicates = {s: sorted(lv) for s, lv in slug_levels.items() if len(lv) > 1 and s not in managed}
```

  (e) In `plugins/bitranox/skills/meta-self-improve/reconcile_memory_index.py` replace

```python
    def _reachable(ref_canon, citing_level):
        cl = Path(citing_level).resolve()
```

  with

```python
    def _reachable(ref_canon, citing_level):
        if ref_canon in managed:
            # placed by topic: where its lines stand follows the levels' topics, not the citer,
            # and the ref resolves through the central body wherever they are
            return True
        cl = Path(citing_level).resolve()
```

  (f) In `plugins/bitranox/skills/meta-self-improve/reconcile_memory_index.py` replace

```python
    if unreadable:
        danglers = []                           # a store dir the listing itself could not read
    return {"anchor": str(anchor), "levels": len(levels), "duplicates": duplicates,
```

  with

```python
    if unreadable:
        danglers = []                           # a store dir the listing itself could not read
    # With a level unreadable the render cannot be computed either; that finding already fails.
    drift, refused = ([], "") if unreadable else render_drift(anchor)
    return {"anchor": str(anchor), "levels": len(levels), "duplicates": duplicates,
            "render_drift": drift, "render_refused": refused,
```

  (g) In `plugins/bitranox/skills/meta-self-improve/reconcile_memory_index.py` replace

```python
        for lvl, slug in rep["orphan_pointers"]:
            print("    ! orphan pointer (no central body): %s [%s]" % (slug, lvl))
            problems += 1
        for lvl, src, ref in rep["orphan_refs"]:
            print("    ! orphan ref: [[%s]] in %s (%s) -> no such entry anywhere in the tree"
```

  with

```python
        for level, missing, differing, extra, examples in rep["render_drift"]:
            print("    ! render drift: %s -> %d line(s) missing, %d differing from the body, %d "
                  "placed elsewhere (%s); render-topics --scope tree repairs it"
                  % (level, missing, differing, extra, ", ".join(examples)))
            problems += 1
        if rep["render_refused"]:
            print("    ! the placement by topic could not be checked: %s" % rep["render_refused"])
            problems += 1
        for lvl, slug in rep["orphan_pointers"]:
            print("    ! orphan pointer (no central body): %s [%s]" % (slug, lvl))
            problems += 1
        for lvl, src, ref in rep["orphan_refs"]:
            print("    ! orphan ref: [[%s]] in %s (%s) -> no such entry anywhere in the tree"
```

  (h) In `plugins/bitranox/skills/meta-self-improve/reconcile_memory_index.py` replace

```python
                where = targets.get(ref)
                if not where:
                    orphans.append((label, ref))
```

  with

```python
                where = targets.get(ref)
                if not where and _bound_to_a_topic(ME._anchor(str(d)), ref):
                    continue                      # placed by topic: its lines need not be on this chain
                if not where:
                    orphans.append((label, ref))
```

  (i) In `plugins/bitranox/skills/meta-self-improve/reconcile_memory_index.py` replace

```python
    return {"checked": checked, "orphans": sorted(set(orphans)), "downward": sorted(set(downward))}
```

  with

```python
    return {"checked": checked, "orphans": sorted(set(orphans)), "downward": sorted(set(downward)),
            "repeated": chain_repeats(dirs)}
```

  (j) In `plugins/bitranox/skills/meta-self-improve/reconcile_memory_index.py` replace

```python
            print("    ! downward ref: %s -> [[%s]] points to a NARROWER altitude" % (src, ref))
            problems += 1
```

  with

```python
            print("    ! downward ref: %s -> [[%s]] points to a NARROWER altitude" % (src, ref))
            problems += 1
        for slug, level, upper in refs["repeated"]:
            print("    ! repeated line: %s at %s is also held by %s above it; render-topics "
                  "--scope chain drops the lower copy" % (slug, level, upper))
            problems += 1
```

  (k) In `plugins/bitranox/skills/meta-self-improve/reconcile_memory_index.py` replace

```python
Exit codes: 0 clean; 1 a problem was found (orphan pointer or ref, downward ref, duplicate, decoy,
```

  with

```python
Exit codes: 0 clean; 1 a problem was found (orphan pointer or ref, downward ref, duplicate, render
drift or a topic-placed line repeated below a level that holds it, decoy,
```

  (l) In `plugins/bitranox/skills/compuse-toolbox/scripts/mem_levels.py` replace

```python
import sys
from dataclasses import dataclass, field
```

  with

```python
import re
import sys
from dataclasses import dataclass, field
```

  (m) In `plugins/bitranox/skills/compuse-toolbox/scripts/mem_levels.py` replace

```python
    duplicates: dict[str, list[str]] = field(default_factory=dict)
    dangling: list[str] = field(default_factory=list)
```

  with

```python
    duplicates: dict[str, list[str]] = field(default_factory=dict)
    # slug -> levels, for a fact the engine places by topic: one line per level is how it is stored
    placed: dict[str, list[str]] = field(default_factory=dict)
    pinned: set[str] = field(default_factory=set)
    dangling: list[str] = field(default_factory=list)
```

  (n) In `plugins/bitranox/skills/compuse-toolbox/scripts/mem_levels.py` replace

```python
            "duplicates": self.duplicates,
```

  with

```python
            "duplicates": self.duplicates,
            "placed": self.placed,
```

  (o) In `plugins/bitranox/skills/compuse-toolbox/scripts/mem_levels.py` replace

```python
        report.levels[rel] = [p.slug for p in pointers]
```

  with

```python
        report.levels[rel] = [p.slug for p in pointers]
        report.pinned.update(p.slug for p in pointers if p.pin)
```

  (p) In `plugins/bitranox/skills/compuse-toolbox/scripts/mem_levels.py` replace

```python
def scan(root: str | Path) -> Report:
```

  with

```python
_BOUND_RX = re.compile(r"(?m)^topics:[ \t]*\[[ \t]*[a-z0-9]")
_HEAD_BYTES = 16384


def _bound_to_a_topic(root: Path, slug: str) -> bool:
    """Whether the body of `slug` carries a non-empty `topics:` line in its frontmatter: the engine
    places such a fact's lines by topic (unless it is pinned). Reads the head of the body only."""
    try:
        with open(root / STORE_DIR / "facts" / (slug + ".md"), "rb") as fh:
            head = fh.read(_HEAD_BYTES).decode("utf-8", errors="replace")
    except OSError:
        return False
    if not head.startswith("---"):
        return False
    end = head.find("\n---", 3)
    return bool(_BOUND_RX.search(head if end == -1 else head[:end]))


def scan(root: str | Path) -> Report:
```

  (q) In `plugins/bitranox/skills/compuse-toolbox/scripts/mem_levels.py` replace

```python
    report.duplicates = {s: sorted(l) for s, l in pointed.items() if len(set(l)) > 1}
```

  with

```python
    several = {s: sorted(l) for s, l in pointed.items() if len(set(l)) > 1}
    report.placed = {s: l for s, l in several.items()
                     if s not in report.pinned and _bound_to_a_topic(root, s)}
    report.duplicates = {s: l for s, l in several.items() if s not in report.placed}
```

  (r) In `plugins/bitranox/skills/compuse-toolbox/scripts/mem_levels.py` replace

```python
    for slug in report.dangling:
        print("  ~ dangling body (no pointer at any level): %s" % slug, file=out)
```

  with

```python
    for slug, lvls in sorted(report.placed.items()):
        print("  = placed by topic: %s at %s" % (slug, ", ".join(lvls)), file=out)
    for slug in report.dangling:
        print("  ~ dangling body (no pointer at any level): %s" % slug, file=out)
```

  (s) In `plugins/bitranox/skills/meta-self-improve/ref_map.py` replace

```python
def read_levels(root: Path) -> dict[str, str]:
    """{canonical slug: level dir} for every pointer under `root`."""
    return {canon(p.slug): str(level) for level, pointers in _pointers(root) for p in pointers}
```

  with

```python
def read_levels(root: Path) -> dict[str, str]:
    """{canonical slug: level dir} for every pointer under `root`. A fact with a line at several
    levels (placed by topic) is given its FIRST level in path order; `read_copies` has the rest."""
    levels: dict[str, str] = {}
    for level, pointers in _pointers(root):
        for p in pointers:
            levels.setdefault(canon(p.slug), str(level))
    return levels


def read_copies(root: Path) -> dict[str, list[str]]:
    """{canonical slug: [every level dir holding a line of it]} for the slugs held at more than
    one level, in path order."""
    held: dict[str, list[str]] = {}
    for level, pointers in _pointers(root):
        for p in pointers:
            held.setdefault(canon(p.slug), []).append(str(level))
    return {slug: levels for slug, levels in held.items() if len(levels) > 1}
```

  (t) In `plugins/bitranox/skills/meta-self-improve/ref_map.py` replace

```python
    levels = read_levels(root)
    texts = _fact_texts(root, read_hooks(root))
```

  with

```python
    levels = read_levels(root)
    copies = read_copies(root)
    texts = _fact_texts(root, read_hooks(root))
```

  (u) In `plugins/bitranox/skills/meta-self-improve/ref_map.py` replace

```python
            "level": levels.get(slug),
            "unknown": False,
```

  with

```python
            "level": levels.get(slug),
            "also_at": copies.get(slug, [])[1:],
            "unknown": False,
```

  (v) In `plugins/bitranox/skills/meta-self-improve/ref_map.py` replace

```python
    levels = {slug: str(Path(level).resolve()) for slug, level in read_levels(root).items()}
    outbound, inbound = read_refs(root)
    final = dict(levels)
    conflicts = []
    for mv in moves:
        cur = levels.get(mv["slug"])
```

  with

```python
    levels = {slug: str(Path(level).resolve()) for slug, level in read_levels(root).items()}
    copies = read_copies(root)
    outbound, inbound = read_refs(root)
    final = dict(levels)
    conflicts = []
    for mv in moves:
        if mv["slug"] in copies:
            # one line per level its topics place it at: the engine refuses to move such a fact
            conflicts.append({"kind": "placed-by-topic", "slug": mv["slug"], "other": None,
                              "slug_level": levels[mv["slug"]], "other_level": None})
            continue
        cur = levels.get(mv["slug"])
```

  (w) In `plugins/bitranox/skills/meta-self-improve/ref_map.py` replace

```python
    for mv in moves:
        slug = mv["slug"]
        if slug not in levels:
            continue
        here = final[slug]
        for target in outbound.get(slug, []):
            there = final.get(target)
            if there is not None and not _visible_from(there, here):
```

  with

```python
    for mv in moves:
        slug = mv["slug"]
        if slug not in levels or slug in copies:
            continue
        here = final[slug]
        for target in outbound.get(slug, []):
            there = final.get(target)
            if target in copies:
                continue                          # resolved through the central body, not a level
            if there is not None and not _visible_from(there, here):
```

  (x) In `plugins/bitranox/skills/meta-self-improve/ref_map.py` replace

```python
        print("%s\n  level    : %s" % (entry["slug"], entry["level"] or "NO POINTER"), file=out)
```

  with

```python
        print("%s\n  level    : %s" % (entry["slug"], entry["level"] or "NO POINTER"), file=out)
        if entry.get("also_at"):
            print("  also at  : %s  (a line per level: placed by topic, or a duplicate "
                  "--check-tree names)" % ", ".join(entry["also_at"]), file=out)
```

- [ ] **Step 4: Run the tests.** Step 2's command - expected: `18 passed`. Then
  `cd <W> && TEST plugins/bitranox/skills/meta-self-improve/tests plugins/bitranox/skills/meta-dream-tree/tests plugins/bitranox/skills/compuse-toolbox/tests plugins/bitranox/skills/meta-collect-knowledge/tests` - expected: no failure.

- [ ] **Step 5: Mutation battery.** Write `$SCRATCH/t11-battery.json` for `mutation_arm.py
  --battery` (`<P>/skills/compuse-toolbox/scripts/mutation_arm.py`, run with `--with PyYAML
  --with lxml --with defusedxml --with ruamel.yaml --with httpx2`), tests: this task's test files.
  One arm per row: arm name, file, the line(s) the arm takes out, what it puts there. Each arm
  changes only the code this task added or edited; every arm must be KILLED (all were, by hand,
  in the scratch copy):

```text
managed-still-duplicate   reconcile_memory_index.py  if len(lv) > 1 and s not in managed}  ->  if len(lv) > 1}
pinned-counts-as-managed  reconcile_memory_index.py  managed = tagged - pinned  ->  managed = tagged
managed-ref-not-exempt    reconcile_memory_index.py  if ref_canon in managed:  ->  if False:
drift-not-computed        reconcile_memory_index.py  drift, refused = ([], "") if unreadable else render_drift(anchor)  ->  drift, refused = [], ""
drift-not-a-problem       reconcile_memory_index.py  problems += 1  ->  (removed)  (in `def _main`, next to: % (level, missing, differing, extra, ", ".join(examples))))
refusal-swallowed         reconcile_memory_index.py  return [], str(exc)  ->  return [], ""
chain-orphan-not-exempt   reconcile_memory_index.py  if not where and _bound_to_a_topic(ME._anchor(str(d)), ref):  ->  if False:
repeat-unbound-reported   reconcile_memory_index.py  if _bound_to_a_topic(anchor, p.slug):  ->  if True:
repeat-not-a-problem      reconcile_memory_index.py  problems += 1  ->  (removed)  (in `def _main`, next to: "--scope chain drops the lower copy" % (slug, level, upper)))
mem-levels-pinned-placed  mem_levels.py              if s not in report.pinned and _bound_to_a_topic(root, s)}  ->  if _bound_to_a_topic(root, s)}
mem-levels-prose-line     mem_levels.py              return bool(_BOUND_RX.search(head if end == -1 else head[:end]))  ->  return bool(_BOUND_RX.search(head))
```

- [ ] **Step 6: Commit** the three scripts and the three test files; message "reconcile, mem_levels, ref_map: a fact placed by topic has legal copies; render drift is a problem".

### Task 12: M4b - the engine's writers guard a fact placed by topic

**Files:**
- Modify: `plugins/bitranox/hooks/memory_engine.py` (a new block above the comment `# A slug that
  is not a plain filename`; `upsert_entry`, `move_entry`, `relocate_entry`, `rename_entry`,
  `retitle_entry`)
- Modify: `plugins/bitranox/hooks/tests/test_memory_engine_topics_field.py` (three P2a tests that
  moved or relocated a bound, unpinned fact)
- Test: `plugins/bitranox/hooks/tests/test_memory_engine_topic_guards.py`

**Interfaces:**
- Consumes: Tasks 8-10.
- Produces: `PlacedElsewhere(SlugCollision)` with `.levels` (`suggestion` is None), raised by
  `add` for a fact placed by topic from a level that holds no line of it; the message names the
  levels that do. It subclasses `SlugCollision`, so `ADD_REFUSALS` and `mod_bridge.REFUSALS`
  already cover it. `add --pin` on a placed fact raises `TopicRefusal` before any write.
  An `add` from a level that holds a line updates the body and then every other line of the
  fact. `move` and a cross-tree `relocate` refuse a placed fact (`! refused:`, exit 2, nothing
  written): its place follows its topics. `rename` and `retitle` rewrite every line and no
  longer warn of a pre-existing duplicate for a placed fact.

**Out of scope:**
- `--archive` (Task 13).
- A pinned fact: it is never placed by topic, so every guard here lets it through unchanged.

**STOP conditions:**
- an anchor text of Step 3 is not found exactly once (the code moved since CHECKPOINT A: read the
  function it names and report, do not guess);
- a P2a test other than the three edited here fails (it relied on moving a bound fact: report);
- `test_mod_bridge*.py` fails (a new refusal type escaped the bridge's list);
- a mutation arm of Step 5 survives.

**What is held in memory:** the levels holding the ONE slug being written (one small entry per
  copy) and one body head.

- [ ] **Step 1: Write the failing tests.**

  Create `plugins/bitranox/hooks/tests/test_memory_engine_topic_guards.py`:

```python
"""Tests for what the ordinary write verbs do with a fact that is placed by topic: move and
relocate refuse it, add writes it only from a level holding one of its lines and refreshes the
others, a bound fact cannot be pinned, and rename and retitle reach every line without calling
them duplicates. All content ASCII.
"""

from pathlib import Path

import pytest

import memory_engine as E
import mod_bridge
import self_improve_signals as sig
import topic_store
import uuid_store as us

HOOK = "When a rule is about one stack, bind it to that stack's topic."
SCOPE = "WHAT: a level\nSTACK: python"
LIST = {"python": "Python code and its tooling", "rust": "Rust code", "git": "git and GitHub"}


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch):
    h = tmp_path / "home"
    h.mkdir(exist_ok=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    return h


def _tree(tmp_path, with_list=True):
    anchor = tmp_path / "tree"
    anchor.mkdir()
    (anchor / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (anchor / us.STORE_DIRNAME).mkdir()
    if with_list:
        topic_store.save_list(anchor, LIST, "jev")
    assert E.main(["set-scope", "--proj", str(anchor), "--scope", "WHAT: the top\nSTACK: none"]) == 0
    return str(anchor)


def _level(anchor, rel, topics=None):
    level = Path(anchor, *rel.split("/"))
    level.mkdir(parents=True, exist_ok=True)
    (level / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    assert E.main(["set-scope", "--proj", str(level), "--scope", SCOPE]) == 0
    if topics is not None:
        E.set_level_topics(str(level), topics)
    return str(level)


def _fact(level, slug, topics=None, pin=False):
    E.add_or_update_entry(level, title="T " + slug, hook=HOOK, body="body of " + slug,
                          type_="feedback", slug=slug, pin=pin)
    if topics is not None:
        E.set_fact_topics(level, {slug: topics})


def _slugs(level):
    text = sig.claude_local_md_path(level).read_text(encoding="utf-8")
    return sorted(p.slug for p in us.parse_pointer_index(text)[1])


def _snapshot(anchor):
    return {str(p): p.read_bytes() for p in sorted(Path(anchor).rglob("*"))
            if p.is_file() and not p.name.endswith(".lock")}


def _two_python_levels(tmp_path):
    anchor = _tree(tmp_path)
    levels = {rel: _level(anchor, rel, topics) for rel, topics in (
        ("a", ()), ("a/py", ("python",)), ("a/other", ()), ("b", ()), ("b/py", ("python",)),
        ("b/other", ()))}
    return anchor, levels


def _rendered(tmp_path):
    anchor, levels = _two_python_levels(tmp_path)
    _fact(anchor, "feedback-py-rule", ("python",))
    _fact(anchor, "feedback-plain")
    E.render_topics(anchor)
    return anchor, levels


def _line(level, slug):
    text = sig.claude_local_md_path(level).read_text(encoding="utf-8")
    return next(p for p in us.parse_pointer_index(text)[1] if p.slug == slug)


# ---- move and relocate ---------------------------------------------------------------------------

def test_move_refuses_a_fact_placed_by_topic_and_moves_nothing(tmp_path, capsys):
    anchor, levels = _rendered(tmp_path)
    before = _snapshot(anchor)
    rc = E.main(["move", "--from-level", levels["a/py"], "--to-level", levels["a"],
                 "--slug", "feedback-py-rule"])
    out = capsys.readouterr().out
    assert rc == 2 and "! refused" in out and "is placed by topic" in out
    assert "set-topics --slug feedback-py-rule --clear" in out and _snapshot(anchor) == before


def test_a_set_holding_one_placed_fact_is_refused_whole(tmp_path):
    anchor, levels = _rendered(tmp_path)
    _fact(levels["a/py"], "feedback-local")
    rep = E.move_entry(levels["a/py"], levels["a"], ["feedback-local", "feedback-py-rule"])
    assert rep["moved"] is False and "placed by topic" in rep["refused"]
    assert _slugs(levels["a/py"]) == ["feedback-local", "feedback-py-rule"]


def test_move_still_moves_an_untagged_an_unbound_and_a_pinned_tagged_fact(tmp_path):
    anchor, levels = _rendered(tmp_path)
    _fact(levels["a/py"], "feedback-local")
    _fact(levels["a/py"], "feedback-universal", ())
    _fact(levels["a/py"], "feedback-pinned", pin=True)
    path = us.body_path(anchor, "feedback-pinned")
    us.put_body(anchor, "feedback-pinned", E._with_topics(path.read_text(encoding="utf-8"), ("python",)))
    for slug in ("feedback-local", "feedback-universal", "feedback-pinned"):
        rep = E.move_entry(levels["a/py"], levels["a"], slug)
        assert rep["moved"] is True and rep["refused"] is None, slug
    assert _slugs(levels["a"]) == ["feedback-local", "feedback-pinned", "feedback-universal"]


def _second_tree(tmp_path):
    other = tmp_path / "tree2"
    other.mkdir()
    (other / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (other / us.STORE_DIRNAME).mkdir()
    assert E.main(["set-scope", "--proj", str(other), "--scope", "WHAT: another tree"]) == 0
    return str(other)


def test_a_cross_tree_relocate_refuses_a_fact_placed_by_topic(tmp_path, capsys):
    anchor, levels = _rendered(tmp_path)
    other = _second_tree(tmp_path)
    before = (_snapshot(anchor), _snapshot(other))
    capsys.readouterr()
    rc = E.main(["relocate", "--from-level", levels["a/py"], "--to-level", other,
                 "--slug", "feedback-py-rule"])
    assert rc == 2 and "is placed by topic" in capsys.readouterr().out
    assert (_snapshot(anchor), _snapshot(other)) == before
    # un-bound, it relocates as any fact does
    assert E.main(["set-topics", "--proj", anchor, "--slug", "feedback-py-rule", "--clear"]) == 0
    assert E.main(["relocate", "--from-level", anchor, "--to-level", other,
                   "--slug", "feedback-py-rule"]) == 0
    assert _slugs(other) == ["feedback-py-rule"]


# ---- add ------------------------------------------------------------------------------------------

def test_add_from_a_level_without_a_line_is_refused_and_writes_nothing(tmp_path, capsys):
    anchor, levels = _rendered(tmp_path)
    for where in (anchor, levels["a/other"], str(Path(anchor, "new-level"))):
        before = _snapshot(anchor)
        rc = E.main(["add", "--proj", where, "--title", "T feedback-py-rule", "--slug",
                     "feedback-py-rule", "--hook", "When this is the new hook, say so."])
        out = capsys.readouterr().out
        assert rc == 2 and "is placed by topic and has no line at this level" in out
        assert levels["a/py"] in out and levels["b/py"] in out and _snapshot(anchor) == before
    with pytest.raises(E.SlugCollision) as exc:
        E.add_or_update_entry(anchor, title="T", hook=HOOK, slug="feedback-py-rule")
    assert isinstance(exc.value, E.PlacedElsewhere) and exc.value.suggestion is None
    assert issubclass(E.PlacedElsewhere, mod_bridge.REFUSALS)


def test_an_update_at_one_line_refreshes_the_others(tmp_path):
    anchor, levels = _rendered(tmp_path)
    new_hook = "When the rule changes, every level that reads it says the new thing."
    E.add_or_update_entry(levels["a/py"], title="New title", hook=new_hook, body="new body",
                          slug="feedback-py-rule")
    for rel in ("a/py", "b/py"):
        line = _line(levels[rel], "feedback-py-rule")
        assert (line.title, line.hook, line.pin) == ("New title", new_hook, False)
    body = us.body_path(anchor, "feedback-py-rule").read_text(encoding="utf-8")
    assert E._body_topics(body) == ("python",) and "new body" in body
    assert E.render_topics(anchor, dry_run=True)["levels"] == {}


def test_a_dangling_bound_body_is_still_adopted(tmp_path):
    anchor, levels = _rendered(tmp_path)
    for rel in ("a/py", "b/py"):
        E._drop_pointer(levels[rel], "feedback-py-rule")
    E.add_or_update_entry(levels["a"], title="T feedback-py-rule", hook=HOOK, slug="feedback-py-rule")
    assert _slugs(levels["a"]) == ["feedback-py-rule"]


def test_pinning_a_bound_fact_is_refused_before_any_write(tmp_path, capsys):
    anchor, levels = _rendered(tmp_path)
    before = _snapshot(anchor)
    rc = E.main(["add", "--proj", levels["a/py"], "--title", "T feedback-py-rule", "--slug",
                 "feedback-py-rule", "--hook", HOOK, "--pin"])
    out = capsys.readouterr().out
    assert rc == 2 and "a pinned fact is never placed by topic" in out and _snapshot(anchor) == before
    # un-bound first, the pin goes through
    assert E.main(["set-topics", "--proj", anchor, "--slug", "feedback-py-rule", "--clear"]) == 0
    assert E.main(["add", "--proj", anchor, "--title", "T feedback-py-rule", "--slug",
                   "feedback-py-rule", "--hook", HOOK, "--pin"]) == 0
    assert _line(anchor, "feedback-py-rule").pin is True


def test_an_ordinary_fact_is_written_as_before(tmp_path):
    anchor, levels = _rendered(tmp_path)
    E.add_or_update_entry(anchor, title="T feedback-plain", hook="When plain, stay plain.",
                          slug="feedback-plain", pin=True)
    assert _line(anchor, "feedback-plain").pin is True


# ---- rename and retitle ---------------------------------------------------------------------------

def test_rename_reaches_every_line_without_calling_them_duplicates(tmp_path):
    anchor, levels = _rendered(tmp_path)
    rep = E.rename_entry(levels["a/py"], "feedback-py-rule", "feedback-py-rule-2")
    assert rep["refused"] is None and not any("duplicate" in w for w in rep["warnings"])
    assert _slugs(levels["a/py"]) == _slugs(levels["b/py"]) == ["feedback-py-rule-2"]
    assert E.read_body_topics(us.body_path(anchor, "feedback-py-rule-2")) == ("python",)


def test_retitle_reaches_every_line_without_calling_them_duplicates(tmp_path):
    anchor, levels = _rendered(tmp_path)
    rep = E.retitle_entry(levels["a/py"], "feedback-py-rule", "A better title")
    assert rep["refused"] is None and not any("duplicate" in w for w in rep["warnings"])
    assert _line(levels["b/py"], "feedback-py-rule").title == "A better title"
    assert E.render_topics(anchor, dry_run=True)["levels"] == {}


def test_a_real_duplicate_is_still_named_by_rename(tmp_path):
    anchor, levels = _rendered(tmp_path)
    local = sig.claude_local_md_path(levels["b/py"])
    text = local.read_text(encoding="utf-8")
    scope, pointers = us.parse_pointer_index(text)
    pointers.append(us.Pointer(slug="feedback-plain", title="T feedback-plain", hook=HOOK))
    local.write_text(us.upsert_pointer_block(text, scope, pointers), encoding="utf-8")
    rep = E.rename_entry(anchor, "feedback-plain", "feedback-plain-2")
    assert any("a pre-existing duplicate" in w for w in rep["warnings"])
```

- [ ] **Step 2: Run them to see them fail.**
  `cd <W> && TEST plugins/bitranox/hooks/tests/test_memory_engine_topic_guards.py` - expected: `8 failed, 4 passed` (the four pin that an unbound or pinned fact still moves, relocates and is adopted as before). This is the RED proof: the same files were run
  against the code before this task in the scratch copy with exactly that result.

- [ ] **Step 3: Implement.** The last three edits change P2a tests that moved or relocated a bound fact; they now use an unbound one, which is what they were about. Each anchor below occurs exactly once in its file; assert
  that before editing.

  (a) In `plugins/bitranox/hooks/memory_engine.py` insert this block directly above the line `# A slug that is not a plain filename (`uuid_store.is_valid_slug`). Defined by the store, whose path` (two blank lines between top-level definitions, as the block itself ends):

```python
class PlacedElsewhere(SlugCollision):
    """Raised when `add` names a fact that is placed by topic from a level holding none of its
    lines. Adopting it there would add a line the placement does not have; the write goes to a
    level that holds one. A SlugCollision, so every caller that reports a collision reports this."""

    def __init__(self, slug, levels):
        ValueError.__init__(self, "slug %r is placed by topic and has no line at this level; it is "
                                  "read at %s. Write it from one of those levels (factedit apply "
                                  "finds one), or change where it is read with set-topics"
                            % (slug, ", ".join(str(level) for level in levels)))
        self.slug, self.suggestion, self.levels = slug, None, list(levels)


def _bound_topics(anchor, slug):
    """The non-empty topics the stored body of `slug` is bound to, else None. Reads the head of
    the body only."""
    head = _read_body_head(us.body_path(anchor, slug))
    return (_body_topics(head) or None) if head is not None else None


def _copies_of(anchor, slug):
    """[(level dir, Pointer)] for every line of `slug` in the tree, from one walk over its levels."""
    out = []
    for level in curated_levels_under(anchor):
        for ptr in us.parse_pointer_index(read_store_text(sig.claude_local_md_path(level)))[1]:
            if ptr.slug == slug:
                out.append((level, ptr))
    return out


def _same_level(a, b):
    return os.path.normcase(os.path.abspath(str(a))) == os.path.normcase(os.path.abspath(str(b)))


_PLACED_BY_TOPIC = ("%r is placed by topic: where it is read follows its topics and the levels' "
                    "(set-topics, set-level-topics, then render-topics). To place it by hand, "
                    "un-bind it first: set-topics --slug %s --clear")
```

  (b) In `plugins/bitranox/hooks/memory_engine.py` replace

```python
    store_dir = us.central_facts_dir(anchor).parent   # the `.claude-memory` store dir for this tree
```

  with

```python
    # A fact placed by topic (topic-bound, no line pinned) has a line at each level its topics
    # place it at. Checked here, before the level is scaffolded, so each refusal writes nothing:
    # it is not pinned (a pinned fact is never placed by topic), and it is written from a level
    # that holds one of its lines (adopting it elsewhere would add a line the placement lacks).
    # One tree walk, and only for a body that is bound; a new fact has no body and skips it.
    copies = _copies_of(anchor, slug) if _bound_topics(anchor, slug) else []
    placed = bool(copies) and not any(ptr.pin for _level, ptr in copies)
    if placed and pin:
        raise TopicRefusal(["%s is bound to topics, and a pinned fact is never placed by topic; "
                            "un-bind it first (set-topics --slug %s --clear), then pin it"
                            % (slug, slug)])
    if placed and not any(_same_level(level, proj) for level, _ptr in copies):
        raise PlacedElsewhere(slug, [level for level, _ptr in copies])
    store_dir = us.central_facts_dir(anchor).parent   # the `.claude-memory` store dir for this tree
```

  (c) In `plugins/bitranox/hooks/memory_engine.py` replace

```python
        _commit_store(proj, scope or scope_default, entries, bodies)
    if not store_existed and store_dir.exists():      # this add created a brand-new store dir:
```

  with

```python
        _commit_store(proj, scope or scope_default, entries, bodies)
    if placed:
        # The other lines of a fact placed by topic say what this one now says. After the commit
        # and outside its lock (add_pointer takes each level's own): a failure here leaves the
        # body and this level written and the rest as render drift, which --check-tree names.
        for level, ptr in copies:
            if not _same_level(level, proj) and (ptr.title, ptr.hook) != (e.title, e.hook):
                us.add_pointer(str(level), slug, e.title, e.hook)
    if not store_existed and store_dir.exists():      # this add created a brand-new store dir:
```

  (d) In `plugins/bitranox/hooks/memory_engine.py` replace

```python
            rep["refused"] = ("entry %r is an unmigrated legacy pointer - run "
                              "migrate_to_slug_store.py first" % s)
            return rep
```

  with

```python
            rep["refused"] = ("entry %r is an unmigrated legacy pointer - run "
                              "migrate_to_slug_store.py first" % s)
            return rep
        if not entry.pin and _bound_topics(a_from, s):
            rep["refused"] = _PLACED_BY_TOPIC % (s, s)
            return rep
```

  (e) In `plugins/bitranox/hooks/memory_engine.py` replace

```python
        rep["refused"] = "entry is an unmigrated legacy pointer - run migrate_to_slug_store.py first"
        return rep

    # Slugs are TREE-unique, so a divergent slug already in the target tree is a different fact.
```

  with

```python
        rep["refused"] = "entry is an unmigrated legacy pointer - run migrate_to_slug_store.py first"
        return rep
    if not entry.pin and _bound_topics(a_from, slug):
        # its other lines would stay behind in the source tree, pointing at an archived body
        rep["refused"] = _PLACED_BY_TOPIC % (slug, slug)
        return rep

    # Slugs are TREE-unique, so a divergent slug already in the target tree is a different fact.
```

  (f) In `plugins/bitranox/hooks/memory_engine.py` replace

```python
        _drop_pointer(str(other), slug)
        rep["warnings"].append("slug was ALSO pointed at from %s - a pre-existing duplicate; "
                               "renamed there too, dedup it deliberately" % other)
```

  with

```python
        _drop_pointer(str(other), slug)
        if not dup.pin and _bound_topics(anchor, slug):
            continue                                 # placed by topic: one line per level, by design
        rep["warnings"].append("slug was ALSO pointed at from %s - a pre-existing duplicate; "
                               "renamed there too, dedup it deliberately" % other)
```

  (g) In `plugins/bitranox/hooks/memory_engine.py` replace

```python
        rep["levels"].append(str(other))
        rep["warnings"].append("slug was ALSO pointed at from %s - a pre-existing duplicate; "
                               "retitled there too, dedup it deliberately" % other)
```

  with

```python
        rep["levels"].append(str(other))
        if not dup.pin and _bound_topics(anchor, slug):
            continue                                 # placed by topic: one line per level, by design
        rep["warnings"].append("slug was ALSO pointed at from %s - a pre-existing duplicate; "
                               "retitled there too, dedup it deliberately" % other)
```

  (h) In `plugins/bitranox/hooks/tests/test_memory_engine_topics_field.py` replace

```python
@pytest.mark.parametrize("line", ["topics: [python]", "topics: []", "topics: [Not A Tag]"])
def test_a_cross_tree_relocate_drops_the_topics_line_and_says_so(
```

  with

```python
@pytest.mark.parametrize("line", ["topics: []", "topics: [Not A Tag]"])
def test_a_cross_tree_relocate_drops_the_topics_line_and_says_so(
```

  (i) In `plugins/bitranox/hooks/tests/test_memory_engine_topics_field.py` replace

```python
    tagged = E._with_topics(path.read_text(encoding="utf-8"), ("python",))
    path.write_bytes(tagged.replace("\n", "\r\n").encode("utf-8"))
    E.relocate_entry(src, dst, slug)
```

  with

```python
    tagged = E._with_topics(path.read_text(encoding="utf-8"), ())
    path.write_bytes(tagged.replace("\n", "\r\n").encode("utf-8"))
    E.relocate_entry(src, dst, slug)
```

  (j) In `plugins/bitranox/hooks/tests/test_memory_engine_topics_field.py` replace

```python
    _tag_raw(str(anchor), slug, "topics: [python]")
    before = us.body_path(anchor, slug).read_bytes()
    rep = E.relocate_entry(str(proj), str(anchor), slug)
```

  with

```python
    _tag_raw(str(anchor), slug, "topics: []")
    before = us.body_path(anchor, slug).read_bytes()
    rep = E.relocate_entry(str(proj), str(anchor), slug)
```

- [ ] **Step 4: Run the tests.** Step 2's command - expected: `12 passed`. Then
  `cd <W> && TEST plugins/bitranox/hooks/tests` - expected: no failure (measured in the scratch copy for the engine-related part, `-k "memory_engine or topic or uuid_store or pin_gate or mod_bridge or memory"`: 924 passed, 1 skipped, before this file's tests).

- [ ] **Step 5: Mutation battery.** Write `$SCRATCH/t12-battery.json` for `mutation_arm.py
  --battery` (`<P>/skills/compuse-toolbox/scripts/mutation_arm.py`, run with `--with PyYAML
  --with lxml --with defusedxml --with ruamel.yaml --with httpx2`), tests: this task's test files.
  One arm per row: arm name, file, the line(s) the arm takes out, what it puts there. Each arm
  changes only the code this task added or edited; every arm must be KILLED (all were, by hand,
  in the scratch copy):

```text
move-not-refused         memory_engine.py  if not entry.pin and _bound_topics(a_from, s):  ->  if False:
move-refuses-pinned      memory_engine.py  if not entry.pin and _bound_topics(a_from, s):  ->  if _bound_topics(a_from, s):
relocate-not-refused     memory_engine.py  if not entry.pin and _bound_topics(a_from, slug):  ->  if False:
pin-not-refused          memory_engine.py  if placed and pin:  ->  if False:
adoption-allowed         memory_engine.py  if placed and not any(_same_level(level, proj) for level, _ptr in copies):  ->  if False:
copies-not-refreshed     memory_engine.py  us.add_pointer(str(level), slug, e.title, e.hook)  ->  pass
rename-warns-duplicate   memory_engine.py  if not dup.pin and _bound_topics(anchor, slug):  ->  if False:  (in `def rename_entry`, next to: _drop_pointer(str(other), slug))
retitle-warns-duplicate  memory_engine.py  if not dup.pin and _bound_topics(anchor, slug):  ->  if False:  (in `def retitle_entry`, next to: rep["levels"].append(str(other)))
```

- [ ] **Step 6: Commit** `memory_engine.py`, `test_memory_engine_topics_field.py` and the new test file; message "memory_engine: add, move, relocate, rename and retitle guard a fact placed by topic".

### Task 13: M4c - archiving a fact placed by topic, and the reference documents

**Files:**
- Modify: `plugins/bitranox/skills/meta-self-improve/reconcile_memory_index.py` (a new block above
  `archive_entry`; `archive_entry`, the `--archive` output, the module docstring)
- Modify: `plugins/bitranox/skills/meta-dream-tree/factedit.py` (one message)
- Modify: `plugins/bitranox/skills/meta-self-improve/references/memory-backend.md`,
  `docs/reference.md` (Step 6, through `bitranox:meta-skill-writer`)
- Create:
  `plugins/bitranox/skills/meta-self-improve/.skillwriter/checklist-20261112-placed-by-topic.md`
- Test: `plugins/bitranox/skills/meta-self-improve/tests/test_reconcile_archive_topic_copies.py`,
  `plugins/bitranox/skills/meta-dream-tree/tests/test_factedit_several_levels_message.py`

**Interfaces:**
- Consumes: Task 12 (`ME._bound_topics`, `ME._copies_of`).
- Produces: `placed_copies(anchor, level_dir, slug) -> list[str]` (the OTHER levels holding a
  line of a fact placed by topic; empty for any other fact). `--archive` of a placed fact drops
  the other lines first, then archives as before, and always applies the inbound-mention check
  (no other line keeps the body reachable). Output: `archived <slug> (pointer dropped at <level>
  and at the N other level(s) its topics place it at: ...)`. factedit's several-levels message
  reads `(placed by topic, or a duplicate pointer that --check-tree names)`.

**Out of scope:**
- `--rehome`, `--check-misplaced`: measured at CHECKPOINT A, unchanged.

**STOP conditions:**
- an anchor text of Step 3 is not found exactly once (the code moved since CHECKPOINT A: read the
  function it names and report, do not guess);
- an archive test shows the body moved while a line of the fact remains at some level;
- a mutation arm of Step 5 survives.

**What is held in memory:** the levels holding the one slug being archived.

- [ ] **Step 1: Write the failing tests.**

  Create `plugins/bitranox/skills/meta-self-improve/tests/test_reconcile_archive_topic_copies.py`:

```python
"""Tests for archiving a fact that is placed by topic: every line of it goes, the body is
archived once, and whatever still names it blocks the archive as for a last pointer. All content
ASCII.
"""

import os
from pathlib import Path

import pytest

import reconcile_memory_index as R

import memory_engine as ME  # noqa: E402  (reconcile put hooks/ on sys.path at import)
import self_improve_signals as sig  # noqa: E402
import topic_store  # noqa: E402
import uuid_store as us  # noqa: E402

HOOK = "When a rule is about one stack, bind it to that stack's topic."
LIST = {"python": "Python code and its tooling", "rust": "Rust code"}


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch):
    h = tmp_path / "home"
    h.mkdir(exist_ok=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    return h


def _level(anchor, rel, topics=None):
    level = Path(anchor, *rel.split("/")) if rel else Path(anchor)
    level.mkdir(parents=True, exist_ok=True)
    (level / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    assert ME.main(["set-scope", "--proj", str(level), "--scope", "WHAT: a level"]) == 0
    if topics is not None:
        ME.set_level_topics(str(level), topics)
    return str(level)


def _fact(level, slug, topics=None, body=None):
    ME.add_or_update_entry(level, title="T " + slug, hook=HOOK, body=body or "body of " + slug,
                           type_="feedback", slug=slug)
    if topics is not None:
        ME.set_fact_topics(level, {slug: topics})


def _slugs(level):
    text = sig.claude_local_md_path(level).read_text(encoding="utf-8")
    return sorted(p.slug for p in us.parse_pointer_index(text)[1])


def _snapshot(anchor):
    return {str(p): p.read_bytes() for p in sorted(Path(anchor).rglob("*"))
            if p.is_file() and not p.name.endswith(".lock")}


@pytest.fixture
def levels(tmp_path):
    anchor = tmp_path / "tree"
    anchor.mkdir()
    (anchor / us.STORE_DIRNAME).mkdir()
    topic_store.save_list(anchor, LIST, "jev")
    out = {rel: _level(str(anchor), rel, topics) for rel, topics in (
        ("", None), ("a", ("python",)), ("b", ("python",)), ("c", ("rust",)))}
    _fact(out[""], "feedback-py-rule", ("python",))
    _fact(out[""], "feedback-plain")
    ME.render_topics(out[""])
    assert _slugs(out["a"]) == _slugs(out["b"]) == ["feedback-py-rule"]
    return out


def test_archiving_a_placed_fact_drops_every_line_and_archives_the_body_once(levels, capsys):
    capsys.readouterr()
    assert R.main(["--archive", "feedback-py-rule", levels["a"]]) == 0
    out = capsys.readouterr().out
    assert "archived feedback-py-rule (pointer dropped at %s and at the 1 other level(s) its topics " \
           "place it at: %s)" % (levels["a"], levels["b"]) in out
    assert _slugs(levels["a"]) == _slugs(levels["b"]) == []
    store = Path(levels[""], us.STORE_DIRNAME)
    assert not us.body_path(levels[""], "feedback-py-rule").exists()
    assert [p.name for p in (store / ".archive").iterdir()] == ["feedback-py-rule.md"]
    assert R.main(["--check-tree", levels[""]]) == 0


def test_a_dry_run_names_every_level_and_writes_nothing(levels, capsys):
    before = _snapshot(levels[""])
    capsys.readouterr()
    assert R.main(["--archive", "feedback-py-rule", "--dry-run", levels["b"]]) == 0
    out = capsys.readouterr().out
    assert "would archive feedback-py-rule" in out and levels["a"] in out
    assert _snapshot(levels[""]) == before


def test_a_fact_that_still_names_it_blocks_the_archive_at_any_of_its_levels(levels, capsys):
    _fact(levels[""], "feedback-citer", body="See [[feedback-py-rule]] for the stack rule.")
    before = _snapshot(levels[""])
    capsys.readouterr()
    assert R.main(["--archive", "feedback-py-rule", levels["a"]]) == 1
    assert "! refused" in capsys.readouterr().out and _snapshot(levels[""]) == before
    with pytest.raises(R.ArchiveBlocked):
        R.archive_entry(levels["b"], "feedback-py-rule")
    assert R.main(["--archive", "feedback-py-rule", "--force", levels["a"]]) == 0
    assert "--force: these still name feedback-py-rule" in capsys.readouterr().out
    assert _slugs(levels["b"]) == []


def test_a_failed_drop_at_another_level_leaves_the_body_and_this_levels_line(levels):
    blocked = sig.claude_local_md_path(levels["b"])
    os.chmod(blocked, 0o444)
    try:
        with pytest.raises(OSError):
            R.archive_entry(levels["a"], "feedback-py-rule")
    finally:
        os.chmod(blocked, 0o644)
    assert us.body_path(levels[""], "feedback-py-rule").is_file()
    assert _slugs(levels["a"]) == _slugs(levels["b"]) == ["feedback-py-rule"]


def test_an_unbound_duplicate_is_archived_one_pointer_at_a_time_as_before(levels):
    local = sig.claude_local_md_path(levels["c"])
    text = local.read_text(encoding="utf-8")
    scope, pointers = us.parse_pointer_index(text)
    pointers.append(us.Pointer(slug="feedback-plain", title="T feedback-plain", hook=HOOK))
    local.write_text(us.upsert_pointer_block(text, scope, pointers), encoding="utf-8")
    assert R.placed_copies(levels[""], levels["c"], "feedback-plain") == []
    assert R.archive_entry(levels["c"], "feedback-plain") is True
    assert _slugs(levels[""]) == ["feedback-plain"]
    assert us.body_path(levels[""], "feedback-plain").is_file()
```

  Create `plugins/bitranox/skills/meta-dream-tree/tests/test_factedit_several_levels_message.py`:

```python
"""Test for the message factedit gives when several levels hold a line of the fact. ASCII."""

from pathlib import Path

import factedit as FE


def test_several_owners_are_named_without_calling_them_a_defect(tmp_path):
    owners = [tmp_path / "a", tmp_path / "b"]
    text = FE.unknown_fact_message("feedback-x", tmp_path, tmp_path, owners, True)
    assert "2 levels point at it (placed by topic, or a duplicate pointer that --check-tree names)" in text
    assert "--level %s" % owners[0] in text and str(Path(owners[1])) in text
```

- [ ] **Step 2: Run them to see them fail.**
  `cd <W> && TEST plugins/bitranox/skills/meta-self-improve/tests/test_reconcile_archive_topic_copies.py plugins/bitranox/skills/meta-dream-tree/tests/test_factedit_several_levels_message.py` - expected: `6 failed`. This is the RED proof: the same files were run
  against the code before this task in the scratch copy with exactly that result.

- [ ] **Step 3: Implement.** Each anchor below occurs exactly once in its file; assert
  that before editing.

  (a) In `plugins/bitranox/skills/meta-self-improve/reconcile_memory_index.py` insert this block directly above the line `def archive_entry(level_dir, slug, archive_subdir=".archive", dry_run=False, *, move=None,` (two blank lines between top-level definitions, as the block itself ends):

```python
def placed_copies(anchor, level_dir, slug):
    """The OTHER levels holding a line of `slug` when it is placed by topic (bound to topics, no
    line of it pinned), top first; [] for every other fact. Archiving such a fact forgets it at
    every level: one line dropped would only be render drift the next render puts back."""
    if not ME._bound_topics(anchor, slug):
        return []
    copies = ME._copies_of(anchor, slug)
    if any(ptr.pin for _level, ptr in copies):
        return []
    return [str(level) for level, _ptr in copies if not ME._same_level(level, level_dir)]
```

  (b) In `plugins/bitranox/skills/meta-self-improve/reconcile_memory_index.py` replace

```python
    anchor = ME._anchor(str(d))
    if not force and not _other_levels_pointing(anchor, d, slug):
        found = inbound_mentions(anchor, slug)
        if found["refs"] or found["prose"] or found["docs"]:
            raise ArchiveBlocked(slug, found)
    if dry_run:                                  # a dry run reports the outcome and writes NOTHING
        return True
```

  with

```python
    anchor = ME._anchor(str(d))
    # A fact placed by topic is archived at EVERY level it has a line at, so this is its last
    # pointer whatever the other levels hold, and whatever names it is left naming nothing.
    others = placed_copies(anchor, d, slug)
    if not force and (others or not _other_levels_pointing(anchor, d, slug)):
        found = inbound_mentions(anchor, slug)
        if found["refs"] or found["prose"] or found["docs"]:
            raise ArchiveBlocked(slug, found)
    if dry_run:                                  # a dry run reports the outcome and writes NOTHING
        return True
    for other in others:
        # before the body moves: a failure here leaves the body, this level's line and the lines
        # not yet reached, which is render drift a render repairs, never a line with no body
        ME._drop_pointer(other, slug)
```

  (c) In `plugins/bitranox/skills/meta-self-improve/reconcile_memory_index.py` replace

```python
        if args.force and not _other_levels_pointing(anchor, level, args.archive):
            found = inbound_mentions(anchor, args.archive)
```

  with

```python
        others = placed_copies(anchor, level, args.archive)
        if args.force and (others or not _other_levels_pointing(anchor, level, args.archive)):
            found = inbound_mentions(anchor, args.archive)
```

  (d) In `plugins/bitranox/skills/meta-self-improve/reconcile_memory_index.py` replace

```python
            if args.dry_run:
                print("would archive %s (pointer would be dropped at %s) - dry run, nothing written"
                      % (args.archive, level))
            else:
                print("archived %s (pointer dropped at %s)" % (args.archive, level))
```

  with

```python
            also = (" and at the %d other level(s) its topics place it at: %s"
                    % (len(others), ", ".join(others))) if others else ""
            if args.dry_run:
                print("would archive %s (pointer would be dropped at %s%s) - dry run, nothing written"
                      % (args.archive, level, also))
            else:
                print("archived %s (pointer dropped at %s%s)" % (args.archive, level, also))
```

  (e) In `plugins/bitranox/skills/meta-self-improve/reconcile_memory_index.py` replace

```python
    Archiving the LAST pointer is refused while another fact links it (`[[slug]]`), names it in
```

  with

```python
    A fact placed by topic has a line at each level its topics place it at; archiving it drops
    them all. Archiving the LAST pointer is refused while another fact links it (`[[slug]]`), names it in
```

  (f) In `plugins/bitranox/skills/meta-dream-tree/factedit.py` replace

```python
        return (f"{head}; {len(owners)} levels point at it (a duplicate pointer): "
```

  with

```python
        return (f"{head}; {len(owners)} levels point at it (placed by topic, or a duplicate "
                "pointer that --check-tree names): "
```

- [ ] **Step 4: Run the tests.** Step 2's command - expected: `6 passed`. Then
  `cd <W> && TEST plugins/bitranox/skills/meta-self-improve/tests plugins/bitranox/skills/meta-dream-tree/tests plugins/bitranox/skills/compuse-toolbox/tests plugins/bitranox/skills/meta-collect-knowledge/tests` - expected: no failure.

- [ ] **Step 5: Mutation battery.** Write `$SCRATCH/t13-battery.json` for `mutation_arm.py
  --battery` (`<P>/skills/compuse-toolbox/scripts/mutation_arm.py`, run with `--with PyYAML
  --with lxml --with defusedxml --with ruamel.yaml --with httpx2`), tests: this task's test files.
  One arm per row: arm name, file, the line(s) the arm takes out, what it puts there. Each arm
  changes only the code this task added or edited; every arm must be KILLED (all were, by hand,
  in the scratch copy):

```text
one-copy-archived            reconcile_memory_index.py  for other in others:  ->  for other in ():
inbound-check-skipped        reconcile_memory_index.py  if not force and (others or not _other_levels_pointing(anchor, d, slug)):  ->  if not force and not _other_levels_pointing(anchor, d, slug):
unbound-duplicate-as-placed  reconcile_memory_index.py  if not ME._bound_topics(anchor, slug): / return []  ->  (removed)
dry-run-drops                reconcile_memory_index.py  if dry_run:                                  # a dry run reports the outcome and writes NOTHING / return True  ->  (removed)
```

- [ ] **Step 6: The reference documents say what is placed by topic.** REQUIRED SUB-SKILL:
  `bitranox:meta-skill-writer` (receipt `python3 <P>/hooks/skill_receipt.py start
  meta-skill-writer`, closed with `end`; ledger first: `python3 <P>/hooks/skill_decisions.py show
  meta-self-improve`). RED probe (`bitranox:baseline-probe`, opus) with the CURRENT "Store
  format" section and command table of
  `plugins/bitranox/skills/meta-self-improve/references/memory-backend.md` pasted in: "A fact is
  bound to the topic python and two directories have that topic. Which command puts its pointer
  line where it belongs, what does `move` do with such a fact, and what does `--archive` do?"
  Expected: the text does not tell. Then edit:
  - `memory-backend.md`: replace the sentence `Topics are data for now: no pointer line is placed
    by them yet.` with

```markdown
A fact whose `topics:` is non-empty, with no pinned pointer, is PLACED BY TOPIC:
`render-topics` gives it a pointer line at each level that has one of its topics while no level
above it does, and at the tree top when no level has one, so it may have a line at several
levels. Each line is built from its body (`title:` and `description:`). Its place follows its
topics and the levels' `TOPICS:` lines: `move` and `relocate` refuse it, `add` from a level that
holds no line of it is refused naming the levels that do, `add --pin` is refused (clear its
topics first), and `rename`, `retitle`, an `add` that changes its title or hook, and `--archive`
act on every line. `set-topics` refuses to bind a fact whose body lacks `title:` or
`description:` or whose pointer line differs from what its body renders (`heal
--backfill-titles` and factedit repair that); un-binding a fact that has several lines leaves
it one line, at the tree top. `render-topics --scope tree` adds every missing line before it
removes any, so an interrupted run leaves a surplus line, never an unreachable fact; `--scope
chain` writes only the levels from the given directory up to the tree top, adds what is placed
there unless a level above holds it, and drops a line a level above holds. A tree without a
topic list is left as it is.
```

    and add, after the `topics-stale` row of the command table, a row for
    `render-topics --proj D --scope tree|chain [--dry-run] [--json]` with the success line
    `render-topics (<scope>): N managed fact(s); changed N level(s)` (read the header row first
    and give the new row the same number of cells; then
    `python3 <P>/skills/docs-md-table-formatting/reformat_tables.py <file>` and read the diff).
    In the `reconcile_memory_index.py` row or paragraph that lists what `--check-tree` reports,
    add `render drift` and, for `--check`, `repeated line`.
  - `docs/reference.md`: the same row in its two-column form after its `topics-stale` row;
    reformat; read the diff.
  GREEN probe with the new text: it must name `render-topics`, say `move` refuses, and say
  `--archive` drops every line. Re-run it once on the final text. Checklist
  `plugins/bitranox/skills/meta-self-improve/.skillwriter/checklist-20261112-placed-by-topic.md`
  with a `Decisions:` line; `cd <W> && python3 plugins/bitranox/hooks/skill_decisions.py check`
  (exit 0).

- [ ] **Step 7: Commit** the two scripts, the two test files, the two documents and the checklist; message "reconcile: --archive drops every line of a fact placed by topic; the references describe placement".

### Task 14: M5 - the tagging helper

**Files:**
- Create: `plugins/bitranox/skills/meta-dream-tree/topic_tagging.py` (index mode 100644, like
  `factedit.py` beside it; it is launched with `python3`)
- Test: `plugins/bitranox/skills/meta-dream-tree/tests/test_topic_tagging.py`

**Interfaces:**
- Consumes: `topic_store.load`, `topic_store.level_key`, `ME.curated_levels_under`,
  `ME.read_store_text`, `us.parse_pointer_index`. The `jev-judge` row format was read from
  the installed tool's `--help` and the `bitranox:ai-llm-jev-judge` skill at CHECKPOINT A:
  `{"id", "ok", "answers": {<question id>: {"type", "value", "probabilities",
  "confidence"}}, "model", "reason"}`; for a `noul` question `value` is the probability of
  yes.
- Produces: subcommands `questions --from D --out F`, `items --from D (--facts-at LEVEL |
  --levels) --out F`, `decide --from D --rows R --kind facts|levels --threshold T [--band LOW
  HIGH] --out F --unsure-out F`; `TaggingError(ValueError)`; `build_questions(topics)`,
  `iter_fact_items(level)`, `iter_level_items(anchor)`, `judge_row(row, topics, threshold,
  band)`, `decide(...)`. One JSON summary on stdout; exit 0 done, 2 could not run. `facts`
  output lines are `{"slug", "topics"}`, the file `set-topics --batch` takes; `levels` lines
  are `{"level", "topics"}`, one `set-level-topics` call each. A row goes to the unsure file
  when it is not ok, lacks an answer for a topic, has an answer strictly inside the band
  (default 0.2 to 0.8), or is a second row for one id.

**Out of scope:**
- Calling `jev-judge`, and writing the store: the helper does neither.
- The tree top as a level item (its topics are the user's decision) and pinned facts (never
  placed by topic): both are left out of the items.

**STOP conditions:**
- an anchor text of Step 3 is not found exactly once (the code moved since CHECKPOINT A: read the
  function it names and report, do not guess);
- the installed `jev-judge --help` shows a row format other than the one above (re-read it;
  the recorded rows in the test are then wrong and the plan step is too);
- a mutation arm of Step 5 survives.

**What is held in memory:** one item or one row at a time (a row line is refused past 1 MiB); the
  topic list (at most 64 entries); for `decide`, the id of every row seen (one short string per
  row, needed to send a second row for one item to the unsure file); for `items --facts-at`, one
  level's pointer block.

- [ ] **Step 1: Write the failing tests.**

  Create `plugins/bitranox/skills/meta-dream-tree/tests/test_topic_tagging.py`:

```python
"""Tests for topic_tagging: the judge's questions and items are built from the store, and its rows
become an engine batch plus an unsure rest. The rows here are recorded in the shape `jev-judge`
writes; the tool never calls a judge. All content ASCII.
"""

import json
import tracemalloc
from pathlib import Path

import pytest

import topic_tagging as T

import memory_engine as ME  # noqa: E402  (topic_tagging put hooks/ on sys.path at import)
import topic_store  # noqa: E402
import uuid_store as us  # noqa: E402

HOOK = "When a rule is about one stack, bind it to that stack's topic."
LIST = {"python": "Python code and its tooling", "rust": "Rust code"}


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch):
    h = tmp_path / "home"
    h.mkdir(exist_ok=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    return h


@pytest.fixture
def tree(tmp_path):
    anchor = tmp_path / "tree"
    for rel in ("", "a", "a/py", "bare"):
        level = anchor / rel
        level.mkdir(parents=True, exist_ok=True)
        (level / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (anchor / us.STORE_DIRNAME).mkdir()
    topic_store.save_list(anchor, LIST, "jev")
    for rel in ("", "a", "a/py"):
        assert ME.main(["set-scope", "--proj", str(anchor / rel), "--scope",
                        "WHAT: level %s\nSTACK: python" % (rel or "top")]) == 0
    ME.set_level_topics(str(anchor / "a" / "py"), ("python",))
    for slug, pin in (("feedback-one", False), ("feedback-two", False), ("feedback-pinned", True)):
        ME.add_or_update_entry(str(anchor), title="T " + slug, hook=HOOK, body="body", slug=slug, pin=pin)
    ME.add_or_update_entry(str(anchor / "bare"), title="T x", hook=HOOK, body="body", slug="feedback-x")
    return anchor


def _answer(value):
    return {"type": "noul", "value": value, "probabilities": {"true": value, "false": 1 - value},
            "confidence": abs(value - 0.5) * 2}


def _row(ident, python, rust, ok=True, **extra):
    row = {"id": ident, "ok": ok, "model": "jev", "reason": None,
           "answers": {"python": _answer(python), "rust": _answer(rust)}}
    row.update(extra)
    return row


def _rows_file(tmp_path, rows):
    path = tmp_path / "rows.jsonl"
    path.write_text("".join((r if isinstance(r, str) else json.dumps(r)) + "\n" for r in rows),
                    encoding="utf-8")
    return str(path)


def _lines(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines()]


def _decide(tmp_path, tree, rows, kind="facts", threshold="0.8", extra=()):
    out, unsure = tmp_path / "decided.jsonl", tmp_path / "unsure.jsonl"
    rc = T.main(["decide", "--from", str(tree), "--rows", _rows_file(tmp_path, rows), "--kind", kind,
                 "--threshold", threshold, "--out", str(out), "--unsure-out", str(unsure), *extra])
    return rc, out, unsure


def test_one_question_per_topic_with_the_topic_as_its_id(tree, tmp_path, capsys):
    out = tmp_path / "questions.json"
    assert T.main(["questions", "--from", str(tree / "a"), "--out", str(out)]) == 0
    questions = json.loads(out.read_text(encoding="utf-8"))
    assert [q["id"] for q in questions] == ["python", "rust"]
    assert all(q["type"] == "noul" and set(q["criteria"]) == {"true", "false"} for q in questions)
    assert LIST["rust"] in questions[1]["instructions"]
    assert json.loads(capsys.readouterr().out)["questions"] == 2


def test_fact_items_are_the_unpinned_lines_of_one_level(tree, tmp_path):
    out = tmp_path / "items.jsonl"
    assert T.main(["items", "--from", str(tree), "--facts-at", str(tree), "--out", str(out)]) == 0
    items = _lines(out)
    assert [i["id"] for i in items] == ["feedback-one", "feedback-two"]
    assert items[0]["state"] == {"title": "T feedback-one", "hook": HOOK}
    assert all(set(i) == {"id", "state"} for i in items)


def test_level_items_are_the_described_levels_below_the_top_without_their_topics_line(tree, tmp_path):
    out = tmp_path / "items.jsonl"
    assert T.main(["items", "--from", str(tree), "--levels", "--out", str(out)]) == 0
    items = _lines(out)
    assert [i["id"] for i in items] == ["a", "a/py"]
    assert items[1]["state"] == {"path": "a/py", "descriptor": "WHAT: level a/py\nSTACK: python"}


def test_decided_rows_become_a_batch_the_engine_takes(tree, tmp_path, capsys):
    rc, out, unsure = _decide(tmp_path, tree, [_row("feedback-one", 0.95, 0.02),
                                              _row("feedback-two", 0.1, 0.05)])
    assert rc == 0 and _lines(unsure) == []
    assert _lines(out) == [{"slug": "feedback-one", "topics": ["python"]},
                           {"slug": "feedback-two", "topics": []}]
    assert json.loads(capsys.readouterr().out) == {
        "command": "decide", "rows": 2, "decided": 2, "unsure": 0, "out": str(out),
        "unsure_out": str(unsure)}
    assert ME.main(["set-topics", "--proj", str(tree), "--batch", str(out)]) == 0
    assert ME.read_body_topics(us.body_path(tree, "feedback-one")) == ("python",)
    assert ME.read_body_topics(us.body_path(tree, "feedback-two")) == ()


@pytest.mark.parametrize("row, reason", [
    (_row("feedback-one", 0.5, 0.0), "unsure about python (0.50)"),
    (_row("feedback-one", 0.9, 0.79), "unsure about rust (0.79)"),
    (_row("feedback-one", 0.9, 0.0, ok=False, reason="timeout"), "failed: timeout"),
    ({"id": "feedback-one", "ok": True, "answers": {"python": _answer(0.9)}}, "no answer for rust"),
    ({"id": "feedback-one", "ok": True, "answers": {"python": _answer(0.9), "rust": {"value": True}}},
     "no answer for rust"),
    ({"id": 7, "ok": True, "answers": {}}, "no string id"),
    ("not json", "line 1 is not a JSON object"),
])
def test_a_row_that_is_no_decision_goes_to_the_unsure_file_with_its_reason(tree, tmp_path, row, reason):
    rc, out, unsure = _decide(tmp_path, tree, [row])
    assert rc == 0 and _lines(out) == []
    assert [u["reason"] for u in _lines(unsure)] == [reason]


def test_the_band_bounds_are_decided_and_the_threshold_is_inclusive(tree, tmp_path):
    rc, out, unsure = _decide(tmp_path, tree, [_row("feedback-one", 0.8, 0.2)])
    assert _lines(out) == [{"slug": "feedback-one", "topics": ["python"]}] and _lines(unsure) == []
    rc, out, unsure = _decide(tmp_path, tree, [_row("feedback-one", 0.6, 0.0)], threshold="0.6",
                              extra=["--band", "0.3", "0.5"])
    assert _lines(out) == [{"slug": "feedback-one", "topics": ["python"]}]


def test_a_second_row_for_one_id_is_unsure(tree, tmp_path):
    rc, out, unsure = _decide(tmp_path, tree, [_row("feedback-one", 0.9, 0.0),
                                              _row("feedback-one", 0.0, 0.9)])
    assert _lines(out) == [{"slug": "feedback-one", "topics": ["python"]}]
    assert [u["reason"] for u in _lines(unsure)] == ["a second row for this id"]


def test_level_rows_are_keyed_by_level(tree, tmp_path):
    rc, out, _unsure = _decide(tmp_path, tree, [_row("a/py", 0.9, 0.0)], kind="levels")
    assert _lines(out) == [{"level": "a/py", "topics": ["python"]}]


def test_nothing_in_the_store_changes(tree, tmp_path):
    def snapshot():
        return {str(p): p.read_bytes() for p in sorted(tree.rglob("*"))
                if p.is_file() and not p.name.endswith(".lock")}
    before = snapshot()
    T.main(["questions", "--from", str(tree), "--out", str(tmp_path / "q.json")])
    T.main(["items", "--from", str(tree), "--levels", "--out", str(tmp_path / "i.jsonl")])
    _decide(tmp_path, tree, [_row("feedback-one", 0.9, 0.0)])
    assert snapshot() == before


@pytest.mark.parametrize("argv", [["questions"], ["items", "--levels"]])
def test_a_tree_without_a_topic_list_is_an_error(tmp_path, capsys, argv):
    anchor = tmp_path / "plain"
    anchor.mkdir()
    (anchor / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (anchor / us.STORE_DIRNAME).mkdir()
    assert T.main([*argv, "--from", str(anchor), "--out", str(tmp_path / "o")]) == 2
    captured = capsys.readouterr()
    assert "! error" in captured.err and "no topic list" in captured.err and captured.out == ""
    assert not (tmp_path / "o").exists()


def test_a_missing_rows_file_and_a_bad_threshold_are_errors(tree, tmp_path, capsys):
    out, unsure = str(tmp_path / "d"), str(tmp_path / "u")
    base = ["decide", "--from", str(tree), "--kind", "facts", "--out", out, "--unsure-out", unsure]
    assert T.main([*base, "--rows", str(tmp_path / "none.jsonl"), "--threshold", "0.8"]) == 2
    assert "cannot read" in capsys.readouterr().err
    assert T.main([*base, "--rows", _rows_file(tmp_path, []), "--threshold", "1.5"]) == 2
    assert "probabilities" in capsys.readouterr().err


def _decide_peak(tmp_path, tree, count):
    rows = tmp_path / ("rows-%d.jsonl" % count)
    with open(rows, "w", encoding="utf-8") as fh:
        for n in range(count):
            fh.write(json.dumps(_row("feedback-n%06d" % n, 0.9, 0.0, note="x" * 2000)) + "\n")
    tracemalloc.start()
    try:
        T.decide(str(rows), LIST, "facts", 0.8, (0.2, 0.8), str(tmp_path / "d"), str(tmp_path / "u"))
        return tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()


def test_rows_are_streamed_and_only_their_ids_are_kept(tree, tmp_path):
    peak_small = _decide_peak(tmp_path, tree, 200)
    peak_large = _decide_peak(tmp_path, tree, 4000)
    # 4000 rows of 2 KB are 8 MB of text; what grows is one short id per row
    assert peak_large < 1_500_000 and peak_large < peak_small + 1_000_000
```

- [ ] **Step 2: Run them to see them fail.**
  `cd <W> && TEST plugins/bitranox/skills/meta-dream-tree/tests/test_topic_tagging.py` - expected: a collection error (`ModuleNotFoundError: No module named 'topic_tagging'`), exit code 2. This is the RED proof: the same files were run
  against the code before this task in the scratch copy with exactly that result.

- [ ] **Step 3: Implement.** Each anchor below occurs exactly once in its file; assert
  that before editing.

  (a) Create `plugins/bitranox/skills/meta-dream-tree/topic_tagging.py`:

```python
#!/usr/bin/env python3
"""Build the inputs a bulk judge needs to choose topics, and turn its rows into engine batches.

Choosing the topics of many facts, or of every level of a tree, is the same bounded judgment made
over many items: "is this item about topic T", once per topic of the tree's closed list. This
tool prepares that judgment for `jev-judge` (skill `bitranox:ai-llm-jev-judge`) and reads its
answers back. It never calls the judge and never writes the memory store; the engine's
`set-topics --batch` and `set-level-topics` do the writing.

  questions --from D --out questions.json
      One yes/no (`noul`) question per topic of the tree's list, id = the topic, from its meaning.
  items --from D --facts-at LEVEL --out items.jsonl
      One item per unpinned pointer line at LEVEL: {"id": slug, "state": {"title", "hook"}}.
  items --from D --levels --out items.jsonl
      One item per level below the tree top that has a descriptor:
      {"id": path below the top, "state": {"path", "descriptor"}} (its TOPICS line left out).
  decide --from D --rows rows.jsonl --kind facts|levels --threshold T --out decided.jsonl
         --unsure-out unsure.jsonl [--band LOW HIGH]
      A row is DECIDED when it is ok, answers every topic of the list, and no answer lies inside
      the unsure band (default 0.2 to 0.8, bounds excluded): its topics are those answered at
      T or above. facts: {"slug", "topics"} lines, the file `set-topics --batch` takes. levels:
      {"level", "topics"} lines, one `set-level-topics` call each. Every other row goes to the
      unsure file with its reason and answers, for a model to tag by reading.

Items and rows are streamed, one line held at a time; `decide` also keeps the id of each row,
to send a second row for one item to the unsure file. Prints one JSON summary on stdout.
Exit codes: 0 done; 2 could not run (bad arguments, an input it cannot read, no topic list).
"""

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "hooks"))
import memory_engine as ME  # noqa: E402
import self_improve_signals as sig  # noqa: E402
import topic_placement as tp  # noqa: E402
import topic_store  # noqa: E402
import uuid_store as us  # noqa: E402

MAX_ROW_BYTES = 1 << 20
"""Longest line of a rows file this reads: a row holds one answer per topic of a list capped at
`topic_store.MAX_LIST`, far under this."""


class TaggingError(ValueError):
    """An input this tool cannot use; the CLI reports it as `! error` and exits 2."""


def _topic_list(start):
    anchor = ME._anchor(os.path.abspath(str(start)))
    data = topic_store.load(anchor)
    if data is None:
        raise TaggingError("%s has no topic list (topics-set-list writes one)" % anchor)
    return anchor, data["topics"]


def build_questions(topics):
    """The judge's questions for a topic list {tag: meaning}: one `noul` per topic, id = the tag."""
    return [{
        "id": tag,
        "type": "noul",
        "instructions": ("The item is either a rule (its title and one-line trigger) or a "
                         "directory (its path and a description of everything below it). "
                         "Topic '%s': %s. For a rule: does it hold wherever this topic is in "
                         "use, and only there? For a directory: is this topic in use below it?"
                         % (tag, topics[tag])),
        "criteria": {"true": "the item is about topic '%s'" % tag,
                     "false": "the item is not about it, or holds regardless of it"},
    } for tag in sorted(topics)]


def iter_fact_items(level):
    """One item per unpinned, migrated pointer line at `level`, in block order."""
    text = ME.read_store_text(sig.claude_local_md_path(level))
    for ptr in us.parse_pointer_index(text)[1]:
        if not ptr.pin and not ptr.legacy:
            yield {"id": ptr.slug, "state": {"title": ptr.title, "hook": ptr.hook}}


def iter_level_items(anchor):
    """One item per curated level below the tree top that has a descriptor, in path order."""
    for level in sorted(ME.curated_levels_under(anchor)):
        key = topic_store.level_key(anchor, level)
        scope = us.parse_pointer_index(ME.read_store_text(sig.claude_local_md_path(level)))[0]
        if not key or not scope.strip():
            continue
        lines = [ln for ln in scope.splitlines() if not ln.startswith("TOPICS:")]
        yield {"id": key, "state": {"path": key, "descriptor": "\n".join(lines).strip()}}


def judge_row(row, topics, threshold, band):
    """(topics, reason) for one judge row: (sorted tags, None) when decided, else (None, why)."""
    if not isinstance(row, dict) or not isinstance(row.get("id"), str) or not row["id"]:
        return None, "no string id"
    if row.get("ok") is not True:
        return None, "failed: %s" % (row.get("reason") or "not ok")
    answers = row.get("answers")
    if not isinstance(answers, dict):
        return None, "no answers"
    taken = []
    for tag in sorted(topics):
        value = answers.get(tag, {}).get("value") if isinstance(answers.get(tag), dict) else None
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None, "no answer for %s" % tag
        if band[0] < value < band[1]:
            return None, "unsure about %s (%.2f)" % (tag, value)
        if value >= threshold:
            taken.append(tag)
    if len(taken) > tp.MAX_TOPICS:
        return None, "%d topics, over the %d one item may carry" % (len(taken), tp.MAX_TOPICS)
    return taken, None


def _iter_rows(path):
    """Yield (line number, row or None) for each non-blank line of a rows file."""
    try:
        with open(path, "rb") as fh:
            for number, raw in enumerate(iter(lambda: fh.readline(MAX_ROW_BYTES + 1), b""), 1):
                if len(raw) > MAX_ROW_BYTES:
                    raise TaggingError("%s: line %d is over %d bytes" % (path, number, MAX_ROW_BYTES))
                if not raw.strip():
                    continue
                try:
                    yield number, json.loads(raw.decode("utf-8"))
                except (ValueError, RecursionError):
                    yield number, None
    except OSError as exc:
        raise TaggingError("cannot read %s: %s" % (path, exc.strerror or exc)) from exc


def decide(rows_path, topics, kind, threshold, band, out_path, unsure_path):
    """Split a rows file into the decided batch and the unsure rest; returns the counts. An id
    seen twice is unsure the second time: two answers for one item are no decision."""
    key = "slug" if kind == "facts" else "level"
    counts = {"rows": 0, "decided": 0, "unsure": 0}
    seen = set()
    with open(out_path, "w", encoding="utf-8", newline="\n") as out, \
            open(unsure_path, "w", encoding="utf-8", newline="\n") as unsure:
        for number, row in _iter_rows(rows_path):
            counts["rows"] += 1
            taken, why = judge_row(row, topics, threshold, band) if row is not None \
                else (None, "line %d is not a JSON object" % number)
            ident = row.get("id") if isinstance(row, dict) else None
            if why is None and ident in seen:
                taken, why = None, "a second row for this id"
            if isinstance(ident, str):
                seen.add(ident)
            if why is None:
                counts["decided"] += 1
                out.write(json.dumps({key: ident, "topics": taken}, sort_keys=True) + "\n")
            else:
                counts["unsure"] += 1
                answers = row.get("answers") if isinstance(row, dict) else None
                values = {tag: answers[tag].get("value") for tag in sorted(topics)
                          if isinstance(answers, dict) and isinstance(answers.get(tag), dict)}
                unsure.write(json.dumps({"id": ident, "line": number, "reason": why,
                                         "answers": values}, sort_keys=True) + "\n")
    return counts


def _write_items(items, out_path):
    count = 0
    with open(out_path, "w", encoding="utf-8", newline="\n") as out:
        for item in items:
            out.write(json.dumps(item, sort_keys=True) + "\n")
            count += 1
    return count


def _run(args):
    anchor, topics = _topic_list(args.start)
    if args.cmd == "questions":
        questions = build_questions(topics)
        Path(args.out).write_text(json.dumps(questions, indent=2, sort_keys=True) + "\n",
                                  encoding="utf-8")
        return {"command": "questions", "questions": len(questions), "out": args.out}
    if args.cmd == "items":
        items = iter_level_items(anchor) if args.levels else iter_fact_items(os.path.abspath(args.facts_at))
        return {"command": "items", "items": _write_items(items, args.out), "out": args.out}
    low, high = args.band
    if not (0.0 <= low <= high <= 1.0 and 0.0 <= args.threshold <= 1.0):
        raise TaggingError("--threshold and --band take probabilities, LOW <= HIGH, within 0..1")
    counts = decide(args.rows, topics, args.kind, args.threshold, (low, high), args.out, args.unsure_out)
    return dict(counts, command="decide", out=args.out, unsure_out=args.unsure_out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    q = sub.add_parser("questions", help="one yes/no question per topic of the tree's list")
    q.add_argument("--from", dest="start", required=True, help="any dir of the tree")
    q.add_argument("--out", required=True)
    i = sub.add_parser("items", help="the items to judge: the facts at one level, or the levels")
    i.add_argument("--from", dest="start", required=True, help="any dir of the tree")
    what = i.add_mutually_exclusive_group(required=True)
    what.add_argument("--facts-at", dest="facts_at", default=None, help="the level whose facts are judged")
    what.add_argument("--levels", action="store_true", help="every described level below the top")
    i.add_argument("--out", required=True)
    d = sub.add_parser("decide", help="turn judge rows into an engine batch and an unsure rest")
    d.add_argument("--from", dest="start", required=True, help="any dir of the tree")
    d.add_argument("--rows", required=True, help="the judge's rows.jsonl")
    d.add_argument("--kind", required=True, choices=["facts", "levels"])
    d.add_argument("--threshold", required=True, type=float, help="a topic is taken at this probability or above")
    d.add_argument("--band", nargs=2, type=float, default=[0.2, 0.8], metavar=("LOW", "HIGH"),
                   help="an answer strictly between these is unsure (default 0.2 0.8)")
    d.add_argument("--out", required=True)
    d.add_argument("--unsure-out", dest="unsure_out", required=True)
    args = ap.parse_args(argv)
    try:
        summary = _run(args)
    except (TaggingError, topic_store.TopicStoreError, ME.TreeWalkError) as exc:
        print("! error: %s" % exc, file=sys.stderr)
        return 2
    except OSError as exc:
        print("! error: %s: %s" % (exc.strerror or exc, exc.filename or ""), file=sys.stderr)
        return 2
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the tests.** Step 2's command - expected: `19 passed`. Then
  `cd <W> && TEST plugins/bitranox/skills/meta-self-improve/tests plugins/bitranox/skills/meta-dream-tree/tests plugins/bitranox/skills/compuse-toolbox/tests plugins/bitranox/skills/meta-collect-knowledge/tests` - expected: no failure.

- [ ] **Step 5: Mutation battery.** Write `$SCRATCH/t14-battery.json` for `mutation_arm.py
  --battery` (`<P>/skills/compuse-toolbox/scripts/mutation_arm.py`, run with `--with PyYAML
  --with lxml --with defusedxml --with ruamel.yaml --with httpx2`), tests: this task's test files.
  One arm per row: arm name, file, the line(s) the arm takes out, what it puts there. Each arm
  changes only the code this task added or edited; every arm must be KILLED (all were, by hand,
  in the scratch copy):

```text
band-inclusive        topic_tagging.py  if band[0] < value < band[1]:  ->  if band[0] <= value <= band[1]:
threshold-exclusive   topic_tagging.py  if value >= threshold:  ->  if value > threshold:
failed-row-decided    topic_tagging.py  if row.get("ok") is not True: / return None, "failed: %s" % (row.get("reason") or "not ok")  ->  (removed)
missing-answer-is-no  topic_tagging.py  return None, "no answer for %s" % tag  ->  continue
pinned-items          topic_tagging.py  if not ptr.pin and not ptr.legacy:  ->  if not ptr.legacy:
topics-line-sent      topic_tagging.py  lines = [ln for ln in scope.splitlines() if not ln.startswith("TOPICS:")]  ->  lines = scope.splitlines()
top-level-sent        topic_tagging.py  if not key or not scope.strip():  ->  if not scope.strip():
second-row-decided    topic_tagging.py  if why is None and ident in seen:  ->  if False:
```

- [ ] **Step 6: Commit** the new script and its test file (`git add` both first); message "meta-dream-tree: topic_tagging builds the judge's inputs and turns its rows into topic batches".

### Task 15: release P2b

**Files:** none beyond a release re-bump and what the gate asks to regenerate.

**Interfaces:** Consumes Tasks 7-14, all committed.

**Out of scope:** any skill text of P2c; the live store (nothing here runs a write verb against
a real tree).

**STOP conditions:**
- the full gate fails on something this plan did not touch (report it; fix it in its own
  worktree);
- a peer session is pushing this repo (ListAgents; message it to hold);
- the reviewer of Step 3 shows, with a failing input, a way a render leaves a fact with no line.

- [ ] **Step 1: End to end on a planted tree.** In `$SCRATCH/p2b-smoke` build the design's
  example with the engine's own verbs: a tree top, levels `a/py`, `b/py` (topics `python`), `c`
  (`rust`), `d` (none), a topic list, one fact bound to `python` and one unbound at the top.
  Assert `python3 <P>/hooks/memory_engine.py tree-top --proj $SCRATCH/p2b-smoke` prints that
  directory as the top before any write. Then
  `python3 <P>/hooks/memory_engine.py render-topics --proj $SCRATCH/p2b-smoke --scope tree` -
  expected last line `render-topics (tree): 1 managed fact(s); changed 3 level(s)`; and
  `python3 <P>/skills/meta-self-improve/reconcile_memory_index.py --check-tree $SCRATCH/p2b-smoke`
  - expected `TOTAL tree problems: 0`. Delete one rendered line by re-rendering that level file
  through `uuid_store.upsert_pointer_block` in a scratch script; `--check-tree` must then print a
  `! render drift:` line and exit 1; `render-topics --scope tree` repairs it.
- [ ] **Step 2: The gate.** `cd <W> && git fetch origin && git log --oneline HEAD..origin/master`;
  if origin's `plugin.json` version moved, `uv run plugins/bitranox/hooks/bump_version.py --merge`
  and re-read the CHANGELOG section against what Tasks 8-14 shipped. Then
  `cd <W> && python3 plugins/bitranox/hooks/repo-gate.py --ci` (exit 0, pytest's `N passed`) and
  `python3 plugins/bitranox/hooks/skill_decisions.py check` (exit 0). A stale derived artifact
  the gate names is regenerated with the builder it names, in this commit.
- [ ] **Step 3: Review.** Dispatch an opus code reviewer (effort medium) with
  `git diff origin/master...HEAD` and the authority to contradict this plan. Each finding needs
  a concrete failing input; a confirmed finding is fixed test-first and the gate re-run. A
  re-review that finds only an exotic path or a test gap is recorded, not another round.
- [ ] **Step 4: Push and watch.** `git push origin design/top-index-topics:master`; verify
  `git fetch origin && git rev-list --count origin/master..HEAD` prints 0. Watch CI with
  `python3 <P>/skills/compuse-toolbox/scripts/ci_wait.py --ref HEAD` (18-35 minutes) to green;
  the release workflow tags the version.

### Task 16: open the P2c release

**Files:**
- Modify: `plugins/bitranox/.claude-plugin/plugin.json`, `pyproject.toml`, `CHANGELOG.md` (via
  `bump_version.py`)

**Interfaces:** none.

**Out of scope:** any code. P2c changes skill and reference text only.

**STOP conditions:** the bump jig reports a version origin already holds; Task 15's CI is not
green.

- [ ] **Step 1: Write `$SCRATCH/p2c-notes.md`:**

```markdown
### Changed

- In a tree that has a topic list, the tree dream tags a rule that holds wherever a stack or
  tool is used and lets `render-topics` place it, instead of moving it up to a common parent;
  it tags each level whose topics are missing or out of date and never changes the tree top's
  topics, which it proposes instead. A nap tags its own directory and renders its own chain. A
  tree without a topic list is consolidated as before.
- A fact lifted or copied into another tree arrives without topics; that tree's dream tags it.
```

- [ ] **Step 2: Bump.**
  `cd <W> && git fetch origin && uv run plugins/bitranox/hooks/bump_version.py --part minor --changelog $SCRATCH/p2c-notes.md`
  - expected: 11.4.0 unless origin moved. Read the section back.
- [ ] **Step 3: Commit** the three files; message "release: open the tag-and-render dream minor".

### Task 17: M6a - the tree dream tags and renders

**Files:**
- Modify: `plugins/bitranox/skills/meta-dream-tree/SKILL.md` (steps 0b, 5, 8, 11)
- Modify: `plugins/bitranox/skills/meta-dream-tree/references/dream-core.md` ("The placement
  routing prompt", "Verification contract")
- Modify: `plugins/bitranox/skills/meta-dream-tree/references/dream-passes.md` ("Belongs higher")
- Create: `plugins/bitranox/skills/meta-dream-tree/.skillwriter/checklist-<date>-tag-and-render.md`

**Interfaces:** the text must agree with the released verbs and their lines: `topics-show` (exit
1 without a list), `topics-stale` (`fresh` / `stale: <why>`), `set-level-topics` (`topics
updated:`), `set-topics` (`set topics on N fact(s); M unchanged`), `render-topics` (`render-topics
(<scope>): N managed fact(s); changed M level(s)`), `--check-tree` (`! render drift:`),
`topic_tagging.py`.

**Out of scope:**
- The mode rules for a move to the tree top, the corroboration gate, the Jev shadow sites: a
  fact about a place still moves exactly as today.
- `topics-set-list` and `set-top-topics`: no passage tells a dream to run either.
- The skill's `description:` frontmatter (no trigger changes, so no derived artifact changes).

**STOP conditions:**
- `skill_decisions.py show meta-dream-tree` lists a live `rule` entry whose anchor an edit would
  remove (answer with a superseding entry through `skill_decisions.py add --from-file`, with the
  reason, or keep the anchor);
- a GREEN probe still moves the stack rule up after one fix of the text (report the passage and
  the probe's answer).

REQUIRED SUB-SKILL: `bitranox:meta-skill-writer` (invoke it first; receipt with
`python3 <P>/hooks/skill_receipt.py start meta-skill-writer`, closed with `end`). The passages
below are the text to start from; a probe may show a wording that fails, and the fix is then to
the wording, never to the rule. Every passage opens with its condition, so a tree without a
topic list is consolidated as today.

- [ ] **Step 1:** `python3 <P>/hooks/skill_decisions.py show meta-dream-tree` and read it.
- [ ] **Step 2: RED probes** (`bitranox:baseline-probe`, opus, the CURRENT step 5 and routing
  prompt pasted in, plus this situation: "The tree has a topic list with `python`. Levels
  `a/py` and `b/py` have the topic `python`; `c` has `rust`. A fact at `a/py` says: when a
  Python test imports a sibling helper, use the bare module name. It was sighted in `b/py`
  too."). Probe 1: "Which command(s) do you run for this fact?" Expected RED: a `move` to the
  tree top (or a promotion), no `set-topics`. Probe 2: "Level `d` has a descriptor and no
  `TOPICS:` line. What do you do, and what about the tree top's line?" Expected RED: the text
  does not tell.
- [ ] **Step 3: Edit `SKILL.md`.**
  (a) Step 0b, as a new paragraph directly after the sentence that ends `the backup holds just
  the stale version).`:

```markdown
    **Topics of a level (only when `memory_engine.py topics-show --proj <anchor>` exits 0; a
    tree without a topic list skips this paragraph).** A level's descriptor also carries a
    `TOPICS:` line: the topics of the tree's list that hold for EVERYTHING below that directory.
    Never type it into `set-scope` text (`set-scope` keeps the stored line and refuses a text
    that changes it). Once the descriptors are fresh, run `topics-stale --proj <level>` for
    every level below the tree top. For each that exits 1, choose its topics from the list
    `topics-show` prints by reading its descriptor - a container with two stacks gets both, a
    level nothing on the list fits gets none - and write them with
    `set-level-topics --proj <level> --topics a,b` (`--topics ''` for none), requiring
    `topics updated:`. With more than about twenty stale levels, hand the judgment to
    `bitranox:ai-llm-jev-judge`: `topic_tagging.py questions`, `items --levels` and
    `decide --kind levels` (home: `<plugin>/skills/meta-dream-tree/`) build its inputs and read
    its rows, and the rows its unsure file holds are tagged by reading. NEVER run
    `set-top-topics`: the tree top's topics decide what every session loads and are the user's
    decision. A change you would make there goes into the report as a proposal, with the facts
    it would move.
```

  (b) Step 5, as a new paragraph at the end of the step (directly above `6. **Voice + firing
  check`):

```markdown
   **A rule about a stack or tool is tagged, not moved (only when `topics-show` exits 0).**
   When the routing answers with TOPICS instead of a level (references/dream-core.md, the
   routing prompt) - the fact holds wherever a stack or tool on the tree's list is used, in more
   than one branch - do not move it up to the common parent. Bind it:
   `set-topics --proj <anchor> --slug <slug> --topics a,b`, or one `--batch` file for the whole
   pass, run with `--dry-run` first; require `set topics on N fact(s)`. Step 8 then places it. A
   refusal naming a line that differs from its body is repaired first (`factedit.py apply`, or
   `heal --backfill-titles` for a missing title), never forced. A pinned fact is never tagged. A
   fact about a PLACE - one project, one container, the whole tree - gets a level and moves as
   above, a move to the tree top still by the mode and with its cost. `move` refuses a fact
   that is already placed by topic: its place changes only through its topics (`set-topics`) or
   its levels' topics (step 0b). A fact that fits no topic of the list is not forced into one:
   it stays where it is, and three or more such facts about one subject are a proposed list
   change in the report, never a `topics-set-list` run.
```

  (c) Step 8, as a new paragraph directly above `Then re-derive the manifest and diff against
  step 2` (split that sentence off the paragraph before it):

```markdown
   When `topics-show` exits 0, place the lines now, before the manifest diff:
   `memory_engine.py render-topics --proj <anchor> --scope tree --dry-run`, read what it would
   change, then the same without `--dry-run`, requiring its last line
   `render-topics (tree): N managed fact(s); changed M level(s)`. A `! refused:` (a level whose
   `TOPICS:` line does not parse, a level whose lines pass the size cap) is fixed at its cause
   and the render run again; lines are added before any is removed, so a run that stopped
   half-way is completed by running it again. In the diff below, a fact placed by topic shows
   as `added` at each level its line arrived at and `removed` where it left; the render's own
   per-level lines explain those rows.
```

  and in the same step, inside the parenthesis that ends `dedup a duplicate pointer)`, add
  before the closing bracket:

```markdown
; a `render drift` line is repaired by running `render-topics --scope tree` again, never by
editing a line
```

  (d) Step 11, in the report list directly after `placements (with direction),` add:

```markdown
facts tagged and levels tagged, the render's per-level lines as printed, proposed changes to the
tree top's topics or to the topic list,
```

- [ ] **Step 4: Edit `references/dream-core.md`.** In "The placement routing prompt" replace the
  prompt's last line (it starts `> Return:`) with

```markdown
> When the tree has a topic list (`topics-show` exits 0), decide the KIND of reach first: a fact
> that holds wherever a stack or tool named on the list is used, in more than one branch, is
> placed by TOPIC - answer with topics from the list, not a level, and never invent a topic; a
> fact about a place (one project, one container, the whole tree) gets a level as above.
> Return: `LEVEL | CONFIDENCE high/low | WHY`, or `TOPICS a,b | CONFIDENCE high/low | WHY`.
```

  and the sentence `Low/UNSURE never moves.` under it with `Low/UNSURE never moves and is never
  tagged.` In "Verification contract", in the sentence that starts `Report counts (merges,
  placements with direction, prunes, pinned untouched)`, add after `pinned untouched` the first
  line below, and after the sentence about `--check-tree` and `TOTAL tree problems: 0` the
  paragraph below it:

```markdown
, facts and levels tagged, the lines `render-topics` added and removed per level as it printed
them, and every proposed change to the tree top's topics
```

```markdown
In a tree with a topic list, run `render-topics` before these checks (tree scope for a tree-wide
run, chain scope for a nap): `--check-tree` reports a line that is missing, differs from its
body or stands outside its fact's placement as `render drift`, and `--check` reports a
`repeated line` that a level above already holds.
```

- [ ] **Step 5: Edit `references/dream-passes.md`.** After the bullet that starts `- **Belongs
  higher** (recurs across the subtree)` add the bullet:

```markdown
- **Belongs wherever a stack is used** (a memory fact that recurs because several branches use
  the same stack or tool, in a tree with a topic list) -> do not lift it: tag it with
  `set-topics` and let `render-topics` place it at the levels that have the topic
  (meta-dream-tree step 5). Lifting it would load it in every branch below the common parent,
  the ones without that stack included.
```

- [ ] **Step 6: GREEN probes.** The two probes of Step 2 with the NEW text. Probe 1 must answer
  `set-topics ... --topics python` and a render, no `move`; probe 2 must answer `topics-stale`
  then `set-level-topics` for `d`, and for the tree top "propose, never `set-top-topics`". A
  third probe, the control that must answer DIFFERENTLY: the same fact, but the tree has no
  topic list (`topics-show` exits 1) - it must route to a level and move as today. Re-run all
  three once on the final text after any fix.
- [ ] **Step 7:** Write the checklist file with a `Decisions:` line naming the ledger entries
  added or `none - <reason>`; `cd <W> && python3 plugins/bitranox/hooks/skill_decisions.py check`
  (exit 0); `cd <W> && TEST plugins/bitranox/skills/meta-dream-tree/tests` (no failure); commit
  the four paths, message "meta-dream-tree: tag a stack rule and render, instead of moving it up".

### Task 18: M6b - the nap, the crosstree dreams and capture

**Files:**
- Modify: `plugins/bitranox/skills/meta-dream-nap/SKILL.md` (a new step 4b; steps 4 and 6)
- Modify: `plugins/bitranox/skills/meta-dream-crosstree/SKILL.md`,
  `plugins/bitranox/skills/meta-dream-crosstree-deep/SKILL.md` (the lift-or-copy and `relocate`
  passages)
- Modify: `plugins/bitranox/skills/meta-self-improve/SKILL.md` (the capture step that runs `add`)
- Create: one `.skillwriter/checklist-<date>-tag-and-render.md` per touched skill

**Interfaces:** as Task 17, plus the refusals of Task 12 (`PlacedElsewhere` names the levels that
hold a line; `move` and `relocate` refuse a fact placed by topic).

**Out of scope:**
- A nap tagging FACTS: it tags its own directory and renders its chain; a fact the routing
  would place by topic is left for the tree dream and named in the deferred list.
- `meta-collect-knowledge`: P2a already made a copied body leave its topics line behind.
- `memory-backend.md` and `docs/reference.md`: done in Task 13.

**STOP conditions:**
- a ledger of one of the four skills holds a live `rule` whose anchor an edit would remove;
- the nap probe writes, or proposes to write, a sibling level or the tree top's topics.

REQUIRED SUB-SKILL: `bitranox:meta-skill-writer`, once per skill (receipt, ledger read with
`skill_decisions.py show <skill>`, RED probe, edit, GREEN probe, checklist with a `Decisions:`
line).

- [ ] **Step 1: `meta-dream-nap`.** RED probe with the CURRENT steps 4 and 6 and this
  situation: "A nap runs in `a/py`. The tree has a topic list. `a/py` has a descriptor and no
  `TOPICS:` line; a fact bound to `python` has its line at `b/py` only." Question: "What does the
  nap do about topics and that fact's line, and which files may it write?" Expected RED: the
  text does not tell. Then add, directly above `5. **Prune the obvious**`:

```markdown
4b. **Topics of this directory, and the chain's lines (only when `memory_engine.py topics-show`
   exits 0).** For the cwd's level ONLY: if it has no descriptor, write one from the directory's
   own README or CLAUDE.md with the tree dream's template (`set-scope`, at most 120 words);
   when `topics-stale --proj <cwd level>` exits 1, choose its topics from the list
   `topics-show` prints by reading the descriptor, and write them with `set-level-topics`,
   requiring `topics updated:` (one directory is far below the item count a bulk judge is for).
   A cwd level that IS the tree top is left alone: its topics are the user's, and
   `set-top-topics` is never a nap's to run. Then
   `memory_engine.py render-topics --proj <cwd> --scope chain --dry-run`, read it, and the same
   without `--dry-run`: it writes only the chain's levels, adds the lines placed there unless a
   level above holds them, and drops a line that a level above now holds. It never writes a
   sibling; a line that belongs at a sibling, or one no longer placed here, waits for the tree
   dream. So a new project gets the rules of its stack at its first nap.
```

  At the end of step 4 add the first paragraph below. In step 6's deferred list replace
  `descriptor synthesis` with `descriptor synthesis for every level but the cwd's, tagging
  facts by topic`, and add the second paragraph after the sentence about `TOTAL problems: 0`:

```markdown
   A fact the routing would place by topic (it holds wherever a stack is used) is not moved and
   not tagged here: `move` refuses a fact placed by topic, and tagging facts is the tree
   dream's. Name it in the deferred list.
```

```markdown
   After step 4b the chain check also reports a `repeated line` (a line a level above already
   holds); `render-topics --scope chain` drops it.
```

  GREEN probe: it must
  answer descriptor-free tagging of `a/py` with `set-level-topics`, `render-topics --scope
  chain`, and "only files on the chain". Control: the same nap in a tree without a list answers
  as today.
- [ ] **Step 2: `meta-dream-crosstree` and `-deep`.** RED probe with the CURRENT lift-or-copy
  and 4b `relocate` passages: "A fact bound to `python` in tree A is confirmed misfiled; it
  belongs in tree B. What happens to its topics, and which commands do you run?" Expected RED:
  `relocate` alone. Add to the lift-or-copy passage of each skill:

```markdown
A fact lifted or copied into another tree arrives UNTAGGED: topics belong to one tree's list,
and the engine leaves the `topics:` line behind with a `~ note:`. Do not tag it here; the target
tree's own dream tags it against that tree's list. `relocate` refuses a fact that is placed by
topic in its source tree: un-bind it there first (`set-topics --proj <source> --slug <slug>
--clear`, which leaves it one line at that tree's top), then relocate that line.
```

  GREEN probe: `set-topics --clear` in A, then `relocate`, and "B's dream tags it".
- [ ] **Step 3: `meta-self-improve`.** RED probe with the CURRENT capture step: "You capture a
  correction onto the existing fact `feedback-x`. `add` answers `! refused: slug 'feedback-x'
  is placed by topic and has no line at this level` and names two levels. What now?" Expected
  RED: a new slug, or `--force`. Add to the capture step, where the dedup rule sends an
  existing fact to its owning level:

```markdown
A new fact has no topics; never write a `topics:` line by hand (only `set-topics` changes it,
and a dream chooses them). A fact that is PLACED BY TOPIC has a line at several levels: when
`add` refuses with `placed by topic and has no line at this level`, re-run the same `add` with
`--proj` set to one of the levels the refusal names. The engine then updates the body and every
line of the fact. Do not mint a second slug for it, and do not `move` it.
```

  GREEN probe: re-run with `--proj` at a named level; no new slug.
- [ ] **Step 4:** Per skill: the checklist file, then
  `cd <W> && python3 plugins/bitranox/hooks/skill_decisions.py check` (exit 0) and
  `cd <W> && TEST plugins/bitranox/skills/meta-dream-nap plugins/bitranox/skills/meta-dream-crosstree plugins/bitranox/skills/meta-self-improve/tests`
  (no failure; a skill dir without tests collects nothing and is dropped from the command).
  One commit per skill, messages "meta-dream-nap: tag the directory and render the chain",
  "meta-dream-crosstree: a fact crosses trees untagged", "meta-self-improve: capture onto a
  fact placed by topic".

### Task 19: release P2c

**Files:** none beyond a release re-bump.

**Interfaces:** Consumes Tasks 16-18.

**Out of scope:** the migration (Tasks 20-27) and the live store. After this release a tree
still behaves as before until it has a topic list.

**STOP conditions:**
- the acceptance harness misses its bar (all hard assertions, at least 5 of 6 judgment
  assertions, on two consecutive runs): the text change broke the dream for a tree without a
  list;
- the planted-tree run of Step 2 moves the stack rule up, writes the tree top's `TOPICS:` line,
  or leaves `--check-tree` non-zero.

- [ ] **Step 1: The acceptance harness, unchanged fixture.** Follow
  `plugins/bitranox/skills/meta-dream-tree/tests/README-acceptance.md` (the fixture has no topic
  list, so this proves a tree without one is consolidated as before). Runs are headless opus
  sessions, each asserted from its init record; two consecutive runs at the bar.
- [ ] **Step 2: A planted tree WITH a list.** In `$SCRATCH/p2c-smoke`, built with the engine's
  verbs and checked with `tree-top` before any write: the design's example tree with
  descriptors, a topic list (`python`, `rust`), `TOPICS:` set on `a/py` and `c` only (so `b/py`
  is stale), and at `a/py` a fact that plainly holds for any Python project, also sighted at
  `b/py`. Run one tree dream there (headless opus, auto mode, an isolated config dir and HOME
  so no real store or audit file is written). Assert from the files, not from its report:
  `b/py` has a `TOPICS:` line naming `python`; the fact's body has `topics: [python]`; the fact
  has a line at `a/py` and `b/py` and none at the tree top; the tree top's `TOPICS:` line is
  byte-identical to before; `reconcile_memory_index.py --check-tree $SCRATCH/p2c-smoke` prints
  `TOTAL tree problems: 0`. Then one nap in a NEW level `a/py2` (descriptor absent): after it,
  `a/py2` has a descriptor and a `TOPICS:` line, and every file outside the chain `a/py2`, `a`,
  top is byte-identical (hash before and after). Record both runs' model ids and outcomes in
  `<repo>/EXECUTION-USER-REVIEW.md`.
- [ ] **Step 3: The gate, review, push, CI.** As Task 15 Steps 2-4, with the reviewer reading
  the changed skill texts against the released code: every command, flag and success line a
  passage names must exist as written (run each named command's `--help` or the command itself
  on `$SCRATCH/p2c-smoke`).
- [ ] **Step 4: CHECKPOINT note.** Append to backlog item [35] (through the backlog tool) that
  P2a, P2b and P2c are released and that Task 20 waits for G1.

## DETAILED: migration tasks (operational; re-read at CHECKPOINT B)

**Gates.**
- G0: P2a, P2b and P2c are released and CI is green; `<W>` HEAD equals `origin/master`.
- G1: the phase 1 firing test has a verdict. Read it without writing anything:
  `python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['verdict'])" ~/.claude/self-improve-audit/p1b-20261110T143224Z/grid/score.json`
  (the file exists once its `score --phase grid` ran; no file means not finished). PASS: phase
  1c is applied first. FAIL: go on. VOID_NOISE: Tasks 20-24 only. INCOMPLETE or no file: wait.
  Log the reading and the branch taken in `<repo>/EXECUTION-USER-REVIEW.md`.
- G2: Task 25 returned PASS. Nothing else opens Task 26.

**Paths.** `RUN3=~/.claude/self-improve-audit/p2-run-<UTC stamp>` (artifacts, its own git repo
for sealed inputs). `TREE=$SCRATCH/p2-tree` (the scratch tree; in the scratchpad because
`~/.claude` is itself an anchor with a store). `ENG=<P>/hooks/memory_engine.py`,
`SM=<P>/skills/meta-dream-tree/store_manifest.py`,
`REC=<P>/skills/meta-self-improve/reconcile_memory_index.py`,
`TAG=<P>/skills/meta-dream-tree/topic_tagging.py`, all from `<W>` at the released commit;
launch each with `python3`. The store is shared: every difference a verify shows that is not on
this run's lists is a peer's until shown otherwise.

### Task 20: P2-prep R1 - gates, the run dir and the frozen inputs

**STOP if:** G0 or G1 does not hold; `python3 $REC --check-tree $ANCHOR` is not `TOTAL tree
problems: 0` (a pre-existing problem is fixed or reported first); `python3 $ENG topics-show
--proj $ANCHOR` exits 0 (a list already exists: someone ran part of this; find out who).

- [ ] **Step 1:** `export ANCHOR=<anchor>; RUN3=$HOME/.claude/self-improve-audit/p2-run-$(date -u +%Y%m%dT%H%M%SZ); mkdir -p "$RUN3" && git -C "$RUN3" init -q -b main && echo "$RUN3"`.
- [ ] **Step 2: Preflight.** The three STOP checks above; `git -C <W> rev-parse HEAD` equals
  `git -C <W> rev-parse origin/master`; record `git -C $ANCHOR/.claude-memory status --porcelain`
  in `$RUN3/dirty-before.txt`.
- [ ] **Step 3: Freeze.** `python3 $SM backup --from $ANCHOR --scope tree --out $RUN3/backup-inputs`
  (read-only for the store). From the backup, a scratch script writes `$RUN3/inputs/hooks.jsonl`:
  one row per pointer at every level that has at least one curated level below it (an inner
  level): `{"slug", "level", "title", "hook", "pinned"}`; and `$RUN3/inputs/levels.jsonl`: one
  row per curated level with a non-empty descriptor: `{"level", "descriptor", "children"}`.
  Print the counts; commit both in `$RUN3`.
- [ ] **Step 4: Tagger consent.** Jev may be used only if `classifier_backend` is `jev` in the
  memory settings (turning it on is the recorded consent to send hooks and bodies to TypeSafe)
  AND `uvx --from 'btx-skill-jev-judge>=0.3.7' jev-judge check-key` exits 0. Otherwise the tagger
  is opus and Task 23 measures only its cost. Log which.

### Task 21: P2-prep R2 - the topic list

**Files:** `$RUN3/tags/` (proposals), `$RUN3/topics-list.json`; no store write.

**STOP if:** the merged list has more than 64 topics after the review (the engine's limit; merge
further), or fewer than 5 (nothing to place by).

- [ ] **Step 1: Propose.** Opus subagents, one at a time while G1's test still runs (it does not
  here: G1 holds), else up to 4 in parallel: each gets about 150 rows of `hooks.jsonl` (title and
  hook only) and the brief "for each rule, give 0 to 3 free tags naming the stack, tool or
  activity a session must be using for this rule to matter; give none when it holds for any
  work; lower case, dashes; return one JSON line per slug" and writes
  `$RUN3/tags/batch-<n>.txt`. Tick each hand-back off the dispatched list.
- [ ] **Step 2: Merge.** A scratch script counts each free tag and the slugs under it. One opus
  subagent clusters the tags into a list: merge spellings and near-synonyms, drop a tag with
  fewer than 5 rules unless it names a stack some directory is wholly about, write a one-line
  meaning per topic (at most 200 characters) that a yes/no question can be built from.
- [ ] **Step 3: Adversarial review.** A second opus subagent (effort medium) gets the list, the
  tag counts and `levels.jsonl`, and must name: two topics that cannot be told apart from a
  hook; a topic no directory's descriptor could declare; a stack several directories share that
  has no topic; a topic so broad that nearly every directory would declare it (that is a
  universal rule, not a topic). Fix each confirmed finding.
- [ ] **Step 4: Decide and seal.** The executing session accepts or edits the list, writes
  `$RUN3/topics-list.json` (`{"tagger": ..., "topics": {...}}`, the tagger filled in after Task
  23) and appends the decision with the review's findings and what was done about each to
  `<repo>/EXECUTION-USER-REVIEW.md`. Commit in `$RUN3`.

### Task 22: P2-prep R3 - check every descriptor against what sits below it

**Files:** `$RUN3/descriptors/<level-key>.txt` (verdicts and drafts). Store writes: `set-scope`
for a wrong descriptor only, after G1.

**STOP if:** more than a third of the levels come back wrong (the checker's brief is suspect:
read five verdicts against the directories yourself before fixing anything).

- [ ] **Step 1: Check.** One opus subagent per level of `levels.jsonl` (batched, a list of levels
  per agent, parallel write paths namespaced per agent in `$RUN3/descriptors/`): read the
  level's descriptor, the first lines of its README and CLAUDE.md, its build files and its child
  directories; answer "is every WHAT, STACK and PLACE-HERE statement true of this directory
  today?" with the lines that show it; for a wrong one, draft the corrected descriptor in the
  dream's template (no `TOPICS:` line).
- [ ] **Step 2: Fix.** For each wrong descriptor: backup first
  (`python3 $SM backup --from $ANCHOR --scope tree --out $RUN3/backup-descriptors`, once), then
  `python3 $ENG set-scope --proj <level> --scope-file <draft>` and require `scope updated:`.
  After the fan-out, re-read every written level and diff it against the draft its own agent
  returned (a wrong `--proj` clobbers a sibling and still reports success).
- [ ] **Step 3:** `python3 $SM verify --out $RUN3/backup-descriptors` - only the fixed levels
  differ; commit the store (only this run's paths), push it to its backup remote; refresh
  `levels.jsonl` from the live tree and commit it in `$RUN3`.

### Task 23: P2-prep R4 - the tagger pilot

**Files:** `$RUN3/pilot/` (`sample.jsonl`, `labels-a.jsonl`, `labels-b.jsonl`, `reference.jsonl`,
`PREREG.md`, `rows.jsonl`, `result.json`).

**STOP if:** the two labellers agree on the exact topic set of fewer than 70% of the 60 facts
(the list, not the tagger, is unclear: back to Task 21, Step 3).

- [ ] **Step 1: Sample.** A scratch script draws 60 facts from the tree-top rows of
  `hooks.jsonl` with seed 20261111, stratified by the free tags of Task 21 (so every topic with
  at least 10 rules is drawn at least twice, and 12 rules with no tag at all are in). Add 5
  planted controls written by hand for this pilot and stored nowhere: 3 whose hook names exactly
  one topic's stack in its trigger, 2 that hold for any work.
- [ ] **Step 2: Reference labels, before any tagger answer exists.** Two opus subagents label the
  65 items independently from title, hook and body against the list's meanings (a set of topics
  per item, empty for universal). A third adjudicates each disagreement with a written reason.
  `reference.jsonl` is the result. These are model labels: say so wherever the pilot is quoted.
- [ ] **Step 3: Pre-register, then commit.** `PREREG.md` states: the tagger gets title and hook
  only; a topic is taken at probability >= 0.5; the tagger PASSES when (a) the exact topic set
  matches the reference on at least 80% of the 60 sampled facts, (b) of all reference
  (fact, topic) pairs at least 90% are found (a missed topic hides a rule from a directory that
  needs it; an extra one only costs bytes), and (c) all 5 controls are exact; a flat question
  (`summarize` exit 1) is a FAIL of that topic's wording, to be reworded at most twice, then a
  FAIL of the tagger; what each outcome leads to (PASS: Jev tags; FAIL: opus tags, at the cost
  Step 5 measures). `git -C "$RUN3" add pilot && git -C "$RUN3" commit` BEFORE Step 4.
- [ ] **Step 4: Run the tagger.** `python3 $TAG questions` and `items` for the 65, then
  `uvx --from 'btx-skill-jev-judge>=0.3.7' jev-judge run --items ... --questions ... --out $RUN3/pilot/rows.jsonl`
  and `summarize`. Score with a scratch script against `reference.jsonl`; write `result.json`
  with the three figures and the verdict; read the misses one by one.
- [ ] **Step 5: The opus cost, either way.** One opus subagent tags the same 65 from title and
  hook; record its tokens from its transcript's usage and its agreement by the same three
  figures. If Jev failed and opus fails (a) or (b) too, add the body's first 1500 characters to
  the opus brief, re-score, and record that as the tagging brief.
- [ ] **Step 6:** Fill `tagger` in `topics-list.json`, log the verdict and figures in
  `<repo>/EXECUTION-USER-REVIEW.md`, commit in `$RUN3`.

### Task 24: P2-prep R5 - tag and render in a scratch tree, and report (CHECKPOINT B)

**Files:** `$TREE` (scratch), `$RUN3/report/`.

**STOP if:** `python3 $ENG tree-top --proj $TREE` does not print `$TREE` as the top (never run a
write verb against a tree whose top is not the scratch root); the scratch `--check-tree` is not
0 after the render; a rule is unreachable (Step 6).

- [ ] **Step 1: Build the scratch tree.** A scratch script reads the live tree (not the old
  backup: descriptors may have been fixed) and writes under `$TREE`: for every curated level its
  `CLAUDE.local.md` byte for byte and a one-line `CLAUDE.md`; the whole `.claude-memory/facts/`.
  Then the tree-top check of the STOP line, and `python3 $REC --check-tree $TREE` -> 0.
- [ ] **Step 2: The list and the levels.** `python3 $ENG topics-set-list --proj $TREE --from-file
  $RUN3/topics-list.json`. Tag the levels: `python3 $TAG items --levels` for `$TREE`, the tagger
  of Task 23 (Jev, or opus subagents with the same questions), `decide`, then per level
  `set-level-topics --proj <level> --topics ...`. The tree top's topics are decided by the
  executing session from the list (the topics nearly every session uses: the design names git,
  ssh and subagents as examples), logged with reasons, and set with
  `set-top-topics --proj $TREE --topics ...`.
- [ ] **Step 3: The facts.** Tree-top facts only, pinned ones left out: `python3 $TAG items
  --facts-at $TREE`, the tagger, `decide` into `$RUN3/report/facts.batch.jsonl` plus the unsure
  file; opus subagents tag the unsure rows; then
  `python3 $ENG set-topics --proj $TREE --batch $RUN3/report/facts.batch.jsonl --dry-run` and
  the same without `--dry-run`.
- [ ] **Step 4: Render.** `python3 $ENG render-topics --proj $TREE --scope tree --dry-run`, read
  it, then without `--dry-run`, timing it (`date` before and after). Then
  `python3 $REC --check-tree $TREE` -> `TOTAL tree problems: 0`.
- [ ] **Step 5: The report.** A scratch script compares the live tree with `$TREE` and writes
  `$RUN3/report/report.md`: per level, pointer-block bytes and pointer count before and after;
  per LEAF level, the bytes its whole chain loads before and after (this is what a session
  there reads); which rules went where (slug, topics, levels); which stayed at the top and why
  (pinned, universal, a topic no directory has, the top declares its topic); the render time.
- [ ] **Step 6: Reachability, by construction and by count.** The script asserts: every slug of
  the live tree has at least one pointer in `$TREE`; no pinned line moved; for every leaf level,
  the set of slugs its chain loads AFTER is a subset of BEFORE (placement only removes); and it
  lists, per leaf level, the rules the chain LOST. Twenty of those lost (level, rule) pairs,
  drawn at random with a seed, are read by an opus reviewer against the directory: "would a
  session here need this rule?" A yes is a wrong tag or a wrong descriptor: fix it in `$TREE`
  (`set-topics`, `set-level-topics`), re-render, re-report, and draw another twenty. More than 2
  yes in a draw of 20 after two rounds is a STOP: the tagging is not good enough to apply.
- [ ] **Step 7: CHECKPOINT B.** The executing session reads the report and decides go or no-go
  for the paid arm, on these pre-set grounds: the median leaf chain shrinks; no leaf chain
  grows; Step 6 passed; the render took under ten minutes. It appends the decision, the four
  figures and the report path to `<repo>/EXECUTION-USER-REVIEW.md` and to backlog item [35],
  re-reads Tasks 25-27 against the released code, and under VOID_NOISE at G1 stops here.

### Task 25: P2-arm R6 - the generated index as a firing-test arm (paid; CHECKPOINT C)

The phase 1 tool is reused with one change. There an arm was ONE file bound over the tree-top
file and the rest of the chain was live. Here an arm is a directory holding one file per level
of the session's chain, each bound read-only over its live file, so both today arms and the
generated arm are frozen whole.

**Files:** `RUN4=~/.claude/self-improve-audit/p2b-<UTC stamp>` with `tool/` (copied from the
phase 1 run's committed tool: `git -C ~/.claude/self-improve-audit/p1b-20261110T143224Z archive
HEAD tool | tar -x -C "$RUN4"`, a read of that repo, after its grid finished), `inputs/`,
`arms/`, `PREREG.md`.

**Interfaces (the change to the tool, test-first, with its battery re-run):**
- `firing.with_top_bind(prefix, arm_file, top_target)` becomes
  `with_binds(prefix, binds: list[tuple[Path, Path]])`: every `(arm file, live file)` pair
  bound read-only, all placed last before `--chdir`, in a fixed order.
- `config.json`: `top_target` becomes `targets`, the chain's level files from the session
  worktree's repo up to `$ANCHOR` (five files for this repo's chain).
- `firecore.build_arm_text` is used per level: `T1`/`T2` are byte copies of today's files, `G`
  the files of `$TREE` for the same levels, `N-<rule>` today's files with one pointer removed
  wherever it stands, `CAN` today's files with the canary line added to the top file.
- The dry-run probe hashes EVERY bound target inside the sandbox and compares each with its arm
  file.
- `firecore.verdict` is unchanged, with `G` in the place of `S`: the phase 1 pass rule.

**STOP if:** G1 was VOID_NOISE; CHECKPOINT B was no-go; fewer than 20 candidate rules exist that
are managed in `$TREE` and placed, for this repo's chain, at a level BELOW the top (then the arm
cannot test what it is for: say so and stop); the canary fails; the measured cost of Step 4
exceeds what the phase 1 firing test actually spent.

- [ ] **Step 1: Run dir, tool, tests.** Create `$RUN4`, copy the tool, make the change above
  with its tests first (the bind order test, a two-target probe test, the battery arm
  `bind-before-mounts` adapted), run the tool's whole test suite and its mutation battery:
  all green, every arm killed. Commit in `$RUN4`.
- [ ] **Step 2: Frozen inputs.** A detached worktree of `<repo>` at `origin/master` as the
  frozen plugin (`$RUN4/frozen`); today's chain files copied byte for byte with their sha256;
  the same levels' files from `$TREE`; `FROZEN.txt` as in phase 1.
- [ ] **Step 3: Rules and pre-registration.** Candidates are drawn from facts that are managed
  in `$TREE` and whose rendered line, for this chain, stands below the top (at least 16 of 20),
  plus up to 4 that stay at the top (they must not change). Authoring and adversarial review as
  in phase 1's Task 23 (26 proposed, 20 kept; no network, sudo, remote host or push; at most 15
  turns). `PREREG.md`: the question ("does a rule whose pointer is rendered at the level its
  topic places it fire as often as with every pointer at the top?"), the arms, the phase 1 pass
  rule verbatim, the screening rule, and per verdict what follows (PASS: Task 26; FAIL: no
  apply, the scratch tree and report are kept, the failing rules are read for a common cause;
  VOID_NOISE: no apply, the instrument is reported; INCOMPLETE: resume). Commit: sealed.
- [ ] **Step 4: Build arms, dry-run every phase, canary, cost.** As phase 1's Tasks 24-25. The
  canary's measured new tokens and USD per run times the runs left (338 at the phase 1 sizes:
  canary 2, screening 120, grid 216) is compared with the phase 1 test's recorded spend: at or
  below it, go on and log the figure; above it, STOP (a larger paid run than the one the user
  approved is not this session's to start).
- [ ] **Step 5: Screening and grid, unattended.** Each phase is launched from a script in `$RUN4`
  with `setsid nohup`, the script appending its own `RC=<n>` line to its log (a background task
  of the session is reaped when the session ends); the session polls the log's `RC=` line.
  Exit 4 (usage limit): wait for the reset and launch the same line again. Exit 3 (the login
  expires): this is the one step that needs a person (`/login`); say so as the first sentence
  of the reply and stop until it is done. Screening must keep 12 rules (`enough: true`); fewer
  is a STOP with the table.
- [ ] **Step 6: CHECKPOINT C.** `score --phase grid`; adjudicate every `guard_changes` row; record
  the verdict, totals, bound, per-rule fires per arm, spend and every invalid run in
  `<repo>/EXECUTION-USER-REVIEW.md` and backlog item [35]. PASS opens Task 26. Remove
  `$RUN4/frozen` by its exact path when nothing runs on it.

### Task 26: P2-apply R7 - apply to the live store in one run

**Files:** the live store, through the engine only. Artifacts in `$RUN3/apply/`.

**STOP if:** G2 does not hold; the live tree changed since `$TREE` was built in a way that
changes a placement (Step 2); a verify difference cannot be attributed.

- [ ] **Step 1: Backup.** `python3 $REC --check-tree $ANCHOR` -> 0; `python3 $SM backup --from
  $ANCHOR --scope tree --out $RUN3/apply/backup`; record the store's dirty paths.
- [ ] **Step 2: Drift since the scratch run.** A scratch script lists facts added to or removed
  from the tree top, descriptors changed, and levels added since `$TREE` was built. New top
  facts are tagged now (the tagger, then appended to the batch); a changed descriptor is
  re-tagged; anything else is named in the report. Facts whose body changed keep their tags
  unless the hook's trigger changed (read those).
- [ ] **Step 3: Apply, in the scratch run's order.** `topics-set-list --proj $ANCHOR --from-file
  $RUN3/topics-list.json`; `set-level-topics` per level from the scratch tree's values;
  `set-top-topics --proj $ANCHOR --topics <the logged decision>` (the migration's one use of that
  verb); `set-topics --proj $ANCHOR --batch ... --dry-run`, then for real;
  `render-topics --proj $ANCHOR --scope tree --dry-run`, read it against the scratch report,
  then for real. Require each verb's success line; a `! refused:` stops the run where it is
  (adds precede removes, so a stopped render leaves surplus lines, never a missing rule).
- [ ] **Step 4: Verify.** `python3 $SM verify --out $RUN3/apply/backup --json > $RUN3/apply/verify.json`
  and the text form: the cost lines must show the top block's bytes DOWN and bytes arriving only
  at levels the scratch report named. A scratch script compares, level by level, the live
  pointer sets with `$TREE`'s (after Step 2's additions): equal, both ways, every difference
  adjudicated (a peer's capture is named and left). Bodies: only a `topics:` line added
  (`changed` with `what == ["body"]`; diff 5 random ones). Then
  `python3 $REC --check-tree $ANCHOR` -> `TOTAL tree problems: 0`.
- [ ] **Step 5: Undo, if Step 4 fails and cannot be explained.** Restoring the backup undoes the
  run: each level's `CLAUDE.local.md` from `$RUN3/apply/backup/levels/`, the bodies and
  `topics.json` from its store copy, written by a scratch script that first checks no file
  changed since the apply other than by this run, then `--check-tree` -> 0. Say what was
  restored.
- [ ] **Step 6: Commit the store.** Stage exactly the paths this run wrote (bodies from the
  batch, `topics.json`; level files are outside the store repo), compare
  `git diff --cached --name-only` with that list both ways, commit with a message file, push to
  the store's backup remote.

### Task 27: P2-apply R8 - first use, report, backlog

- [ ] **Step 1: A nap in two directories**, one whose chain lost rules and one that gained a
  level's worth (a new or untagged project if there is one): run `bitranox:meta-dream-nap`
  there, and check its report lists the chain render, that sibling files are byte-identical
  (hash them before and after), and `reconcile --check` over the chain prints `TOTAL problems: 0`.
- [ ] **Step 2: Report**: the verify cost lines as printed; per-directory before and after for
  the ten largest changes; the rules that stayed at the top by reason; the tagger and its pilot
  figures (model labels, said as such); the firing arm's verdict and spend; every decision the
  session took in the user's place, by its `EXECUTION-USER-REVIEW.md` entry; what was cut
  (facts at levels below the top are not topic-placed yet).
- [ ] **Step 3:** Record the result and artifact paths in backlog item [35] at once; delete
  `$TREE` by its exact path; keep `$RUN3` and `$RUN4`.

## Self-review record

- Spec coverage: `topics:` and `TOPICS:` through the engine (Tasks 2-4); topic list, open tags
  then closed (Tasks 3, 4, 21); assignment by Jev with a pilot and an opus fallback (M5, Task
  23); generation with roll-up, fallback and no repeat below an ancestor (Task 1, M3); the
  reconcile check (M4); scope "only facts at an inner level" (cut to the tree top for this
  migration, stated in HIGH); the dream tags and re-renders (M6); the nap (M3 chain scope, M6);
  the four safeguards (fallback: Task 1; keyword recall: unchanged code; pinned: Task 4 and M3;
  the top's topics: Task 4 `set-top-topics`, M6); migration steps 1-7 (Tasks 21-26).
- Code run: Tasks 1-4 extracted and run in a scratch copy as stated under Conventions. Tasks 5
  and 6 carry no code. Tasks 7-19 were written at CHECKPOINT A (entry below).
- Observable pass criteria were checked against what the code prints: `topic list updated:`,
  `set topics on N fact(s); M unchanged`, `topics updated:`, `fresh` / `stale: <why>`,
  `scope updated:`, `TOTAL tree problems: 0`, the phase 1 `score.json` field `verdict`. The
  `render-topics` output lines are defined at CHECKPOINT A; Tasks 24 and 26 name its exit code
  and `--check-tree` instead of a line it does not print yet.
- Platforms: the new tests use `tmp_path` and `pathlib`, set `USERPROFILE` with `HOME`, and
  compare level keys as path parts or POSIX-relative strings the code itself builds.
- CHECKPOINT A, 2026-11-12. The consumer sweep ran every reader and writer of a pointer block
  on a planted tree with one topic-bound fact at two sibling levels (114 grep lines, 12 files,
  26 probes; the table is at the head of the Tasks 7-19 section). Against M4's list the scope
  changed in five places: `add` from a level that holds no line of a placed fact ADOPTED it (M4
  assumed a `SlugCollision`), now refused as `PlacedElsewhere` (Task 12); `add --pin` on a
  placed fact, now refused (Task 12); a `[[ref]]` to a placed fact was a hard sideways ref or
  chain orphan, now exempt (Task 11); `ref_map.py` and `mem_levels.py` read a second line as a
  duplicate or dropped it silently, now reported as placed by topic (Task 11); and `set-topics`
  bound a fact whose pointer line is not what its body renders, now refused, because the
  renderer builds lines from the body alone (Task 8). M4's "a cross-tree `relocate` clears the
  `topics:` line" became "refuses a placed fact; un-bind first" (P2a already drops the line for
  an unbound copy). M4's per-slug drift listing became per-level counts with examples, to keep
  the check's memory flat. Everything else M4 named was confirmed and needs what M4 said;
  `store_manifest`, `dedup_scan`, `statusrot`, `versionrot`, `recall-memory`,
  `migrate_to_slug_store`, `gather_scan` and `uuid_store.resolve` need nothing.
- Code run at CHECKPOINT A: Tasks 8-14 applied in order to a scratch copy of the released
  `plugins/`, each task's tests RED before its edits and GREEN after (95 tests), the hooks and
  skill suites clean in the final state apart from tests that need the real checkout, 56 hand
  mutation arms killed, and the design's example rendered and checked end to end through the
  CLI (`render-topics (tree): 1 managed fact(s); changed 3 level(s)`, `TOTAL tree problems: 0`).
  Tasks 17-18 are text: their passages were checked against the released verbs and messages,
  their probes run at execution. The `render-topics` output lines Tasks 24 and 26 wait for are
  the ones Task 9's Interfaces name.
