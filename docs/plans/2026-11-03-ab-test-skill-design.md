# meta-skill-ab-test: A/B test skill variants on real work (design)

Backlog [27]. Compare the shipped version of a skill (the control) against one or more modified
versions (variants, each carrying one or more tagged changes) by letting each one do the same real
task in the real repository, then judging the resulting code, its exact cost and whether it met an
executed floor. The work is not thrown away: every arm's commits stay on a branch, and the winner's
branch is reviewed and merged like any other.

Built from an earlier prototype harness (a two-stage A/B of a plan-executor skill), whose lessons
are folded in below. Approved section by section with the user on 2026-11-03. Chosen over
extending skill-creator's evals (no real repository, no cost accounting) and over waiting for the
prototype's remaining stages (their lessons arrive later and revise this design).

## 1. Inputs and the run loop

A run directory per experiment holds:

- **Control**: the shipped skill at a pinned bitranox-skills commit.
- **Variants**: each a directory holding a modified copy of the skill, with a list of tagged
  changes and the marker words that would unblind a judge.
- **Workpiece**: the real repository, a base commit, and the task text (a plan, an issue, or any
  task). The workpiece language is not fixed: Rust, Python or anything with a runnable gate.
- **Profile** (`abtest.toml`, section 3): gate command, optional sealed acceptance suite and its
  command, build-cache paths, model, n, deadline and token cap per arm.

**Pre-registration**, committed before the first arm: hypothesis per variant, the decision rule,
and the acceptance suite's hash. `run` refuses to start if the suite's hash differs.

**Schedule: serial, interleaved**, start order rotated per round (round 1: C, V1, V2; round 2: V1,
V2, C; ...). Chosen over parallel rounds for the cleanest isolation: no shared CPU, no quota burst,
no cache interaction between concurrent arms. In the prototype, back-to-back serial opus arms all
started equally warm (first message: 11,491 to 11,607 tokens read from cache, 20,322 to 20,505
written, over 11 arms), so serial arms need no cold-start correction; the per-arm check stays.

**Each arm**:

- a git worktree of the real workpiece repository at the base commit, on branch
  `abx/<run>/<arm>`, so the real CLAUDE.md cascade and memory index load exactly as in normal work;
- its own HOME and config directory, with the arm's skill version installed from a frozen detached
  checkout, verified byte for byte against the plugin cache before launch;
- `BITRANOX_MEMORY_WRITES=off` (section 3) plus a snapshot guard over the memory store and the
  ancestor `CLAUDE.local.md` files that records any change for adjudication;
- a headless `claude -p --model opus` run. The main model is asserted from the transcript's init
  record; delegation to haiku inside the arm (subagents, side calls) is allowed and its cost is
  counted per model.

**Per-arm scoring**: exact cost from the result's `modelUsage`, per model, split into new tokens
and cache reads; the first-message cache read compared with the other arms; the floor (gate and
suite); a git bundle of `base..HEAD`; then the worktree and its build cache are removed (in the
prototype one arm's worktree was 47.8 GB, 47.7 GB of it build cache, while its bundle was 48 KB).
The branch stays. The arm's config directory, which holds a credentials copy, is deleted when the
arm ends.

## 2. Judging and the verdict

**What the judge sees**: an opus session with no tools, never a transcript. It gets the task text
and, labelled A and B, the control's and one variant's commits and diffs (`base..HEAD`, workpiece
paths only, variant artifacts and the plan file excluded). Every line naming one of the profile's
marker words is removed from subjects, bodies and diffs before judging.

**One call, two outputs**:

1. a per-criterion verdict, A, B or tie, each backed by a quoted line: correctness, task coverage,
   tests, readability, scope creep, and beyond-plan fixes (classed REAL-BEYOND-PLAN,
   PLAN-REQUIRED, NOT-A-FIX or UNCLEAR; a real fix needs a test that fails before it and passes at
   HEAD);
2. a weighted 0-10 rubric score per criterion for each side.

Each pair is judged twice with A and B swapped; a criterion whose verdict flips with the order is a
tie. An arm's rubric figure is the median of its scores. **The pairwise verdict decides**; the
rubric is reported beside it, and a pair where the two disagree is flagged. The absolute rubric
alone was too flat to decide: in the prototype it gave all 11 arms 7.43 to 8.19, and two ratings of
one arm differed as much as arms did.

**Two phases**: every variant against the control in every round; then the variants that beat the
control and pass every floor against each other, all pairs, ranked by wins. A cycle is reported as
a tie, not resolved.

**Cost is relative.** A variant that does better work is compared against the control's ADJUSTED
cost: the control's measured cost plus a repair charge. For every advantage the judge confirms (a
beyond-plan fix, or a defect the control has and the variant does not), the control is charged the
input-side cost the variant itself spent on that change, read per message from its stream. An
advantage the variant got right first time adds nothing, so the charge is a floor, never an
overestimate. Only the input side is charged: the stream's per-message output token counts are
placeholders, while the input side reproduced the reported totals to within 5.1% under, never
over. Cost bands come from the control's own spread across rounds.

**Labels per variant**, pre-registered:

| Label     | When                                                                                                      |
|-----------|-----------------------------------------------------------------------------------------------------------|
| HARMFUL   | any run below the floor, OR a majority of rounds lost to the control, OR higher cost with no quality gain |
| KEPT      | majority of rounds won, every run at or above the floor, cost no higher than the control's adjusted cost  |
| TRADE-OFF | quality won, but cost above the control's adjusted cost; both numbers shown                               |
| NEUTRAL   | everything else                                                                                           |

Higher cost alone is never HARMFUL. Judge cost is recorded separately and never charged to an arm.

**Report**: one row per variant with floor, exact cost per model, wins/ties/losses against the
control, median rubric, finalist rank, label, and branch name, plus the void list with reasons.

## 3. Components

**Skill**: `meta-skill-ab-test` in bitranox-skills; scripts in `skills/meta-skill-ab-test/scripts/`
with sibling tests. Linux first; Windows untested and stated as such.

**Profile** (`abtest.toml`, validated with Pydantic at load):

```toml
[workpiece]
repo = "/path/to/repo"
base = "<40-char sha>"
task_file = "task.md"

[control]
skills_ref = "<bitranox-skills sha>"
skill = "process-agents-subagent-driven-development"

[[variant]]
name = "V1"
dir = "variants/V1"
changes = ["parallel dispatch", "code node"]
markers = ["Graph Execution"]

[floor]
gate = "make test"
suite = "acceptance/test_task.py"     # optional; gate-only when absent
suite_cmd = "pytest {suite} -q"
cache_paths = [".venv", "target"]

[run]
model = "opus"
n = 3
deadline_s = 14400
max_tokens = 6000000
```

**CLI** `abtest.py`, `--json` envelope, exit 0 yes / 1 no / 2 could not run: `init` (profile and
pre-registration skeletons), `seal`, `run`, `score`, `judge`, `report`, `prune-run <id>` (deletes
a run's branches in the workpiece repository).

**Ported from the prototype** with every language-specific literal moved into the profile: the arm
runner (worktree in the real repository), the scorer (floor commands from the profile), the
beyond-plan fix extraction, adjudication, proof and cost scripts, the SDK guard (tools bounded by a
PreToolUse deny hook, never `allowed_tools`; a minimal environment built from scratch, never a copy
of the parent's), and the prune step. **New**: the pairwise judge with the rubric in the same call,
the finalists phase, the label verdict, the memory snapshot guard. **Dropped**: the prototype's
idea-marker variant builder; variants are plain directories.

**Memory-writes switch**, a separate plugin change with its own version bump: with
`BITRANOX_MEMORY_WRITES=off` the memory engine's write commands, `factedit apply`, the
`memory_add` tool and `contrib_queue add` refuse with one line and exit 2, and the self-improve and
dream nudges stay quiet; recall, the skill router and every guard stay on. In the prototype, 5 of
12 arms made at least one memory or contribution write.

**Run directory**: `~/.abtest/<run-id>/` by default, outside every repository, itself a git
repository so the pre-registration and its amendments are append-only commits.

## 4. Failure handling, testing, build order

**Void rules apply to every arm**, never to one: main model not opus, no result record, deadline
or token cap hit, first-message cache read out of line. A void arm counts as nothing, never as the
null result. The store guard does not void: it records each change in the arm's scores for
adjudication against the arm's transcripts (user decision 2026-11-04: concurrent sessions share
the store, so a change it sees may not be the arm's).

**"Not logged in" is checked out of band**: one request to `/v1/messages` with the arm's
credential; 401 is a real login failure, 429 an exhausted quota (the CLI reports both the same
way), which pauses the run instead of voiding arms.

**Resume**: the run directory journals each completed step; `run` resumes after the last finished
arm and never repeats a paid step.

**Waiting**: end on the launcher's own exit-code line; "stalled" needs a flat stream AND no file of
any arm changed in the window; deadline about 2x the measured arm duration.

**Tests**: through real seams (a fake `claude` binary replaying recorded `stream.jsonl` fixtures, a
scratch git repository as workpiece, an injected git runner); one test per memory write path
expecting the refusal; a dry run of the scorer on the base commit before the first paid arm; one
liveness pair on a small Python workpiece, where a variant with a planted defect must lose and a
variant identical to the control must tie.

**Build order**: (1) this design; (2) the memory-writes switch; (3) the scripts, ported test-first;
(4) the skill text, authored on fable; (5) the liveness pair, run on opus; (6) the first real
experiment. Authoring (skill text, pre-registration, acceptance suite) happens in a fable session;
every arm and judge runs on opus.

## 5. Amendments (fable review, 2026-11-03, before the implementation plan)

Section-by-section re-read on the authoring tier, against the plugin's code and the prototype's.
Each item names the section it changes; the text above stays as approved.

- **(1) The cascade in a nested worktree is an assumption, not a given.** A worktree under
  `<repo>/.claude/worktrees/` loads its own CLAUDE.md and the levels above the repo; whether the
  repo-level `CLAUDE.local.md` pointer block (untracked, so absent from the checkout) reaches the
  arm, and what the plugin's SessionStart writes into the worktree (`session-start.py` runs
  `memory_engine.heal()` on every start, and heal writes pointer blocks), is MEASURED by the
  build's first task, with one short headless run, before any task rests on it. If the project
  level's index does not load, the runner copies the repo's `CLAUDE.local.md` into the worktree
  as an untracked file; the memory-writes switch keeps the engine from writing there.
- **(2) A priced advantage names its commit.** The judge's beyond-plan verdict carries the sha(s)
  of the variant commit(s) that deliver each advantage. The repair charge is the input-side cost of
  the stream span attributed to those commits (the prototype's method: from the message after the
  previous commit's call through the commit's result). An advantage whose named commit is the arm's
  only commit, or that the judge cannot tie to a commit, is charged 0 and listed as "unpriced".
- **(3) The control must carry the switch.** `skills_ref` must be at or after the release that
  ships `BITRANOX_MEMORY_WRITES`; `run` checks the frozen checkout's `hooks/self_improve_signals.py`
  for that name and refuses otherwise, because an arm on an older plugin would honour nothing.
  The switch covers every engine verb that writes (add, amend-pinned, move, relocate, rename,
  retitle, set-scope, heal, ensure-memory-structure, ensure-all-trees) and the hooks that call them,
  not only the four paths section 3 names.
- **(4) Exact arithmetic for the labels.** Per variant V with runs r = 1..n and control C:
  `cost(V)` = median over V's valid runs of the result record's total cost (all models);
  `repair(r)` = the sum of priced advantages of V's run r; `adjusted(C)` = median over r of
  `cost(C, r) + repair(r)`; the control band is `[min_r cost(C, r), max_r cost(C, r)]`. A round is
  WON by V when the weighted criterion sum (A = +1, B = -1, tie = 0, after the order-swap tie rule)
  is above 0. KEPT needs `cost(V) <= adjusted(C) + 0.10 USD` (the prototype's cost resolution);
  "higher cost with no quality gain" is `cost(V) > max_r cost(C, r) + 0.10` without a majority of
  rounds won. Default weights, fixed at `seal`: correctness 0.30, task coverage 0.25, tests 0.20,
  beyond-plan fixes 0.10, readability 0.10, scope creep 0.05.
- **(5) The warmth check has a knob.** An arm is void when its first assistant message's cache
  read differs by more than `warmth_tolerance` (default 0.25) from the median of the run's other
  finished arms. The prototype's spread was 1 percent; the default is a guess until measured.
- **(6) Profile validation is stdlib.** `tomllib` plus frozen dataclasses with explicit checks,
  not Pydantic: the repo's gate runs every skill's tests in a bare environment with no PEP 723
  dependency provisioned, so a third-party import fails the gate. Gate and suite commands are argv
  lists run without a shell.
- **(7) Dropped with the prototype:** the absolute quality judge and the mutation battery. Both
  depended on an external checkout and Rust-specific scoring; the rubric now lives inside the
  pairwise call (section 2), and the mutation battery's job is not part of any label.

