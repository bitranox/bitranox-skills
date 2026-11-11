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

**Tasks 7-19 (P2b, P2c) get their detailed tasks at CHECKPOINT A; Tasks 20-27 (the migration) are
written below in operational form against the MID interfaces and are re-read against the
released code at CHECKPOINT B before anything runs.**

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
  `python3 ~/.claude/skills/toolbox/tools/ci_wait.py --ref HEAD` (18-35 minutes) to green.

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

Written at CHECKPOINT A (Task 6, Step 5).

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
  and 6 carry no code. Tasks 7-19 are deliberately not written before CHECKPOINT A.
- Observable pass criteria were checked against what the code prints: `topic list updated:`,
  `set topics on N fact(s); M unchanged`, `topics updated:`, `fresh` / `stale: <why>`,
  `scope updated:`, `TOTAL tree problems: 0`, the phase 1 `score.json` field `verdict`. The
  `render-topics` output lines are defined at CHECKPOINT A; Tasks 24 and 26 name its exit code
  and `--check-tree` instead of a line it does not print yet.
- Platforms: the new tests use `tmp_path` and `pathlib`, set `USERPROFILE` with `HOME`, and
  compare level keys as path parts or POSIX-relative strings the code itself builds.
