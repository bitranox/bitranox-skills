# Performance Skills (generic, Python, Rust) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use bitranox:process-agents-subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a generic `coding-performance-review` skill and a `coding-rust-performance-review`
skill, and slim `coding-python-performance-review` to point at the generic one for method.

**Architecture:** Three skills, one per trigger domain. The generic skill holds the measurement
method, a language-neutral review checklist, the router table and the language-neutral claim
checker `validate_perf_claims.py` (moved from the Python skill). The Python skill keeps its
pipeline and seven Python-only scripts. The Rust skill is a checklist plus tool recipes and ships
no scripts. Design: `docs/plans/2026-11-06-performance-skills-design.md` (commit cd0abf67).

**Tech Stack:** Markdown SKILL.md files, the per-skill decision ledger
(`plugins/bitranox/hooks/skill_decisions.py`), Python 3 stdlib script plus pytest tests, clippy
0.1.95 and cargo 1.95.0 on the dev host for the one executed Rust recipe.

## Global Constraints

- ASCII only in every file; no em-dashes, curly quotes or other typographic tells.
- No Claude/AI attribution anywhere: no Co-Authored-By, no "Generated with" footer, no mention in
  a commit message, changelog or doc.
- Commit with `git commit -F <file> -- <paths>`, the message file written in an EARLIER Bash call;
  never `-m`. In this worktree-isolated session, run git as plain separate commands from the
  worktree root (`/media/srv-main-softdev/projects/public/KI/bitranox-skills/.claude/worktrees/perf-skills`).
- `$SCRATCH` below means the session's scratchpad directory (its absolute path is in the
  session's environment block); never `/tmp`, and never a `$TMPDIR` path (it is empty here).
- Never edit anything under `.github/`.
- History is append-only: no force-push, no rewrite.
- Public-repo docs state what a skill does and when to use it, never private provenance
  (no private hosts, paths, project names or "integrated from" history).
- Every SKILL.md change goes through `bitranox:meta-skill-writer` (receipt, Step 0b ledger read,
  RED/GREEN probes, a `.skillwriter/checklist-<date>-<topic>.md` carrying a `Decisions:` line).
- Every shipped `.py` has sibling tests; run them with CI's dependency set:
  `env -u VIRTUAL_ENV uv run --with pytest --with PyYAML --with lxml --with defusedxml --with ruamel.yaml --with httpx2 python -m pytest <paths> -q`
- Executions (implementers, fixers, reviewers) run on opus; reviews at effort medium. The user
  chose on 2026-11-06 to author this plan and the skill texts on opus as a one-off exception to
  the fable-authoring directive.
- Release: one minor bump of `plugins/bitranox/.claude-plugin/plugin.json`, `pyproject.toml` and a
  `CHANGELOG.md` heading, made with `bump_version.py` from the version origin holds AT RELEASE
  TIME. A peer session plans 10.20.0 for the skill-decision-ledger M3 branch; message it before
  pushing, and take whatever minor number follows origin then.
- Skill names, verbatim (user decision 2026-11-06): `coding-performance-review` (generic),
  `coding-rust-performance-review` (Rust); `coding-python-performance-review` keeps its name.

## User decisions this plan delivers (2026-11-06)

| Decision (chosen option)                    | Delivered by         |
|---------------------------------------------|----------------------|
| Three skills (Recommended)                  | Tasks 1, 2, 3        |
| Method + neutral checklist (Recommended)    | Task 1               |
| Checklist + tool recipes (Recommended)      | Task 3               |
| coding-performance-review + coding-rust-... | Tasks 1, 3           |
| Write it here on opus                       | this plan, Tasks 1-3 |

---

### Task 1: The generic skill `coding-performance-review`, with the claim checker moved in

**Files:**
- Create: `plugins/bitranox/skills/coding-performance-review/SKILL.md`
- Move: `plugins/bitranox/skills/coding-python-performance-review/validate_perf_claims.py` ->
  `plugins/bitranox/skills/coding-performance-review/validate_perf_claims.py`
- Move: `plugins/bitranox/skills/coding-python-performance-review/tests/test_validate_perf_claims.py` ->
  `plugins/bitranox/skills/coding-performance-review/tests/test_validate_perf_claims.py`
- Create: `plugins/bitranox/skills/coding-performance-review/tests/conftest.py`
- Modify: `plugins/bitranox/skills/coding-python-performance-review/tests/test_perf_scripts.py`
  (drop the `vpc` import and the `# --- validate_perf_claims ---` section, three tests)
- Modify: `plugins/bitranox/skills/coding-python-performance-review/SKILL.md` (two path mentions
  only: the Reference Files row and the review-pipeline bullet)
- Create: `plugins/bitranox/skills/coding-python-performance-review/tests/test_claim_checker_location.py`
- Create: `plugins/bitranox/skills/coding-performance-review/.skillwriter/decisions.jsonl` (via `skill_decisions.py add`)
- Create: `plugins/bitranox/skills/coding-performance-review/.skillwriter/checklist-20261106-new-skill.md`
- Create: `plugins/bitranox/skills/coding-python-performance-review/.skillwriter/checklist-20261106-claim-checker-moved.md`
- Regenerate: `plugins/bitranox/hooks/skill_triggers.json`, `docs/skills.md`; Modify: `README.md`
  (skill count 83 -> 84, 3 places). A new skill directory fails the hook suite's catalogue,
  trigger-map and README-count tests, which the commit gate runs, so the commit that adds a skill
  carries its regenerated artifacts.

**Interfaces:**
- Produces: `validate_perf_claims.py` at its new path, unchanged in content and CLI
  (`python3 validate_perf_claims.py [diff_file]`, exit 0 scanned, 2 unreadable; function
  `find_performance_claims(diff_file) -> list[dict]` with keys `claim`, `where`; `main(argv) -> int`).
- Produces: the skill name `bitranox:coding-performance-review`, which Tasks 2-4 cite.

**Out of scope** - do NOT touch, though they look related:
- The other seven scripts in `coding-python-performance-review/` - they need Python ASTs,
  cProfile or pytest and stay where they are.
- `coding-python-performance-review/tests/test_perf_scripts_floor.py` - it globs `*.py` in that
  skill dir; with the script moved out it simply checks one file fewer, which is correct.
- Any other Python SKILL.md text: slimming is Task 2.

**STOP conditions** - stop and report rather than improvise, if:
- `validate_perf_claims.py` imports anything outside the standard library, or another script in
  the Python skill imports it (it must be self-contained to move);
- a step's verification fails twice after one reasonable fix attempt;
- the change needs a file not listed in **Files:**;
- `skill_decisions.py add` refuses an anchor as not occurring exactly once.

- [ ] **Step 1: Write the failing location test** (drives the real files on disk)

`plugins/bitranox/skills/coding-python-performance-review/tests/test_claim_checker_location.py`:

```python
"""The diff claim checker lives in the generic performance skill; this skill names it there."""
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
GENERIC = SKILL.parent / "coding-performance-review"
REL = "../coding-performance-review/validate_perf_claims.py"


def test_skill_md_names_the_claim_checker_at_its_real_path():
    text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    assert REL in text
    assert (SKILL / REL).resolve().is_file()


def test_no_copy_of_the_claim_checker_is_left_here():
    assert not (SKILL / "validate_perf_claims.py").exists()
    assert (GENERIC / "validate_perf_claims.py").is_file()
```

- [ ] **Step 2: Run it to verify it fails**

Run: `env -u VIRTUAL_ENV uv run --with pytest python -m pytest plugins/bitranox/skills/coding-python-performance-review/tests/test_claim_checker_location.py -q`
Expected: 2 failed (SKILL.md lacks the relative path; the script is still in the Python skill).

- [ ] **Step 3: Check the move precondition**

Run: `grep -n '^import\|^from' plugins/bitranox/skills/coding-python-performance-review/validate_perf_claims.py`
Expected: only `argparse`, `re`, `sys`. Run:
`grep -rln 'import validate_perf_claims\|from validate_perf_claims' plugins/bitranox/skills/coding-python-performance-review --include=*.py`
Expected: only the two test files `tests/test_perf_scripts.py` and `tests/test_validate_perf_claims.py`.

- [ ] **Step 4: Move the script and its test with git**

```bash
mkdir -p plugins/bitranox/skills/coding-performance-review/tests
git mv plugins/bitranox/skills/coding-python-performance-review/validate_perf_claims.py plugins/bitranox/skills/coding-performance-review/validate_perf_claims.py
git mv plugins/bitranox/skills/coding-python-performance-review/tests/test_validate_perf_claims.py plugins/bitranox/skills/coding-performance-review/tests/test_validate_perf_claims.py
```

- [ ] **Step 5: Create the generic skill's conftest**

`plugins/bitranox/skills/coding-performance-review/tests/conftest.py`:

```python
"""Put the skill directory on sys.path so tests import its scripts by module name."""
import os
import sys

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SKILL_DIR)
```

Then check the moved test file uses no fixture from the old conftest:
`grep -n 'run_script\|clean_env' plugins/bitranox/skills/coding-performance-review/tests/test_validate_perf_claims.py`.
If it prints anything, copy the `_clean_env`, `clean_env` and `run_script` definitions verbatim
from `plugins/bitranox/skills/coding-python-performance-review/tests/conftest.py` into the new
conftest (with their imports `site`, `subprocess`, `pytest`).

- [ ] **Step 6: Move the three claim tests out of the shared Python test file**

In `plugins/bitranox/skills/coding-python-performance-review/tests/test_perf_scripts.py` delete the
line `import validate_perf_claims as vpc` and the whole block from
`# --- validate_perf_claims ---...` up to (not including) `# --- compare_performance ---...`.
Append to `plugins/bitranox/skills/coding-performance-review/tests/test_validate_perf_claims.py`:

```python
# --- phrasings and the CLI's missing-file contract ------------------------------------------

def _diff(tmp_path, name, body):
    p = tmp_path / name
    p.write_text(textwrap.dedent(body), encoding="utf-8")
    return str(p)


def test_claims_extracts_varied_phrasings(tmp_path):
    diff = _diff(tmp_path, "changes.diff", """
        +This change is 40% faster and gives a 3x speedup.
        +It reduced latency by 30%.
        +Improves the cache hit rate noticeably.
    """)
    claims = " | ".join(c["claim"] for c in vpc.find_performance_claims(diff)).lower()
    assert "40% faster" in claims
    assert "3x speedup" in claims
    assert ("latency by 30%" in claims) or ("30%" in claims)
    assert "cache hit rate" in claims


def test_claims_empty_when_none(tmp_path):
    diff = _diff(tmp_path, "d.diff", "+just a normal refactor, no numbers here.\n")
    assert vpc.find_performance_claims(diff) == []


def test_validate_main_missing_file_returns_2(tmp_path):
    # 2 = could not do the job; 1 would read as an answer
    assert vpc.main([str(tmp_path / "nope.diff")]) == 2
```

and add `import textwrap` beside the file's existing `import validate_perf_claims as vpc`.
`_diff` is a copy of `test_perf_scripts.py`'s `_write` (dedent, write UTF-8, return the path);
leave `_write` where it is, since other tests in that file still call it.

- [ ] **Step 7: Point the Python SKILL.md at the new path (two places)**

In `plugins/bitranox/skills/coding-python-performance-review/SKILL.md`:
- the Reference Files row: replace `validate_perf_claims.py` in the File column with
  `../coding-performance-review/validate_perf_claims.py`;
- the review-pipeline bullet: replace "- `validate_perf_claims.py <diff_file>` - EXTRACTS" with
  "- `python3 ../coding-performance-review/validate_perf_claims.py <diff_file>` (path relative to
  this skill's directory) - EXTRACTS".
Let the table hook realign the table; do not hand-pad it.

- [ ] **Step 8: Run the tests to verify they pass**

Run: `env -u VIRTUAL_ENV uv run --with pytest --with PyYAML --with lxml --with defusedxml --with ruamel.yaml --with httpx2 python -m pytest plugins/bitranox/skills/coding-performance-review/tests plugins/bitranox/skills/coding-python-performance-review/tests -q`
Expected: all pass, and `grep -c '^def test_' plugins/bitranox/skills/coding-performance-review/tests/test_validate_perf_claims.py`
prints 22 (19 moved with the file plus the 3 moved out of `test_perf_scripts.py`).

- [ ] **Step 9: Write the generic SKILL.md through meta-skill-writer**

REQUIRED SUB-SKILL: bitranox:meta-skill-writer (receipt, Step 0b, RED/GREEN). RED probes run
BEFORE the file exists, on `bitranox:baseline-probe` (opus), each given the scenario text only:
- G1: "A bash script loops over 5,000 hostnames and runs `ssh host uptime` once per host. A
  colleague's commit adds a cache file and its message says 'now 3x faster'. Review the script
  and the claim for performance."
- G2: "You timed build A five times, then build B five times, on a laptop with performance and
  efficiency cores. B's median is 12 percent lower. Write the conclusion for the release notes."
RED records whether each answer (G1) proposes batching or parallelising the per-host calls AND
asks for a measured before/after instead of accepting "3x", and (G2) refuses to attribute the 12
percent until the arms are interleaved and the cores pinned. GREEN repeats both with the SKILL.md
text below pasted into the prompt; pass = every one of those points present in both answers.
Record RED and GREEN answers verbatim in the checklist.

The SKILL.md text (write exactly this, then let the table hook align the tables):

````markdown
---
name: coding-performance-review
description: Use when measuring, comparing or reviewing performance in any language - before optimising, when a change or commit message claims a speedup, when timing two versions, builds or configurations against each other, when an A/B timing reads as a clear win or a clear null, when reviewing code for algorithmic cost, N+1 queries or calls, per-item I/O, repeated work, blocking calls, or unbounded memory and input, or when the language has no performance skill of its own (bash, JavaScript, Go, SQL). Routes Python to coding-python-performance-review and Rust to coding-rust-performance-review.
---

# Performance review and measurement (any language)

Two halves: how to measure so that a number means what you think it means, and what to look for
in code. The language skills add their own tools on top of this one; the method is shared.

## Route by language

| Code under review | Load as well                                                                  |
|-------------------|-------------------------------------------------------------------------------|
| Python            | `bitranox:coding-python-performance-review` (profiling pipeline, AST finders) |
| Rust              | `bitranox:coding-rust-performance-review` (clippy, criterion, profilers)      |
| anything else     | nothing: this skill alone                                                     |

## Method: a number you can believe

1. **Profile before optimising.** Find where the time goes on a real workload (the project's own
   test suite, a recorded production input, the real request), not on a hand-made
   micro-benchmark. An optimisation outside the hot path is cost without benefit.
2. **Reproduce the recorded BEFORE figure first.** When the defect already has a measured before
   number (an issue, a backlog line, a saved profile), run your probe on the unfixed code and
   require it to land within an order of magnitude of that figure before you trust your after
   number. A probe that hits an early return is fast in both arms, so the fix looks enormous
   while the slow path never ran.
3. **Identical settings on both sides.** Same build mode and flags, input, data size, warm or cold
   state, host and concurrency. Diff what each side RESOLVED, defaults included, not its config
   file.
4. **Interleave the arms: A, B, A, B, at least three runs each.** All-A-then-all-B confounds the
   arm with the clock (thermal state, other load, caches). Report the median and the spread per
   arm; a difference smaller than the spread within one arm is noise.
5. **Pin the core on a hybrid CPU.** On a CPU with performance and efficiency cores (on Linux,
   compare `cpuinfo_max_freq` across `/sys/devices/system/cpu/cpu*/cpufreq/`), identical code
   spreads widely by core placement alone. Pin each run (`taskset -c N`, `sched_setaffinity`) or
   record which core type it ran on.
6. **Prove the change took effect.** Before believing an A/B, above all a null one, show that the
   variable moved inside the system under test (the cache was hit, the flag was read, the new
   build is the one that ran) and that nothing else moved.
7. **Do not write off an approach measured with your own constraint still on it.** List every
   constraint you added to make a variant correct (a lock, serialisation, a cap) and measure it
   without the incidental ones before calling the approach slow.
8. **Measure a concurrency or queueing change; never predict it** from the architecture. The
   cost often sits somewhere the design diagram does not show.
9. **Read current load from two samples, not from a lifetime average.** `ps -o pcpu` averages
   over the whole life of the process; use the second sample of `top -b -n2`, `pidstat`, or two
   reads of `/proc/<pid>/stat`.
10. **Check every speed claim in a diff.** `validate_perf_claims.py` (in this skill's directory)
    extracts phrases like "40% faster", "3x speedup" or "reduced latency by 30%" from a unified
    diff's added lines and prints each with its `path:line`. It reaches no verdict: check each
    claim against a measured run and report the ones that are unproven or contradicted.

```bash
git diff origin/main...HEAD > changes.diff
python3 "<this skill's directory>/validate_perf_claims.py" changes.diff   # 0 scanned, 2 unreadable
```

Report every finding with the measured number, the spread, the runs per arm and the command that
produced it. A figure you did not run yourself is labelled as read or estimated, never as
measured.

## What to flag in code (any language)

Severity: SEVERE can exhaust memory or time on real input; MEDIUM costs measurably on a hot
path; MINOR is cheap to fix but not shown to be hot. Each finding names the input size at which
it starts to hurt.

- **Unbounded memory (usually SEVERE).** Reading a big file, a huge query result or a huge log
  fully into memory, or accumulating an unbounded list, map or string, instead of streaming,
  iterating, chunking or paginating. Only a provably small, fixed-size input may be materialised.
- **Unbounded or unsafe input.** Input with no length bound, unvalidated types, or unhandled
  encodings and characters (non-ASCII, emoji, CJK, control characters, binary). Adversarial input
  must not blow up time or memory (catastrophic regex backtracking, quadratic blow-ups,
  out-of-memory); the bound is validated and tested.
- **Untrusted structured input.** A map, JSON document or deserialised payload used without
  parsing or validating its shape at the boundary.
- **Quadratic work.** A nested loop over the same collection, a membership test against a list
  inside a loop, a repeated sort or search inside a loop, or string building by repeated
  concatenation where the language copies on every step.
- **N+1 calls.** A query, HTTP request, subprocess or RPC per item where one batched call would
  do.
- **Per-item I/O.** An open, close, flush, fsync or system call per record; unbuffered writes.
- **Repeated pure work.** The same parse, compile (a regex, a template) or lookup redone on every
  call with the same input. Hoist or cache it after confirming the work is pure and the hit rate
  is real.
- **Blocking calls on a hot or async path.** A sleep, synchronous network or disk I/O inside an
  event loop, or a lock held while waiting.
- **Eager work that is mostly thrown away.** Building a full list to take its first element, or
  loading every column to use one.

## Common mistakes

| Mistake                                          | Fix                                                      |
|--------------------------------------------------|----------------------------------------------------------|
| Optimising before profiling                      | Profile the real workload first; fix only the hot path   |
| Timing all A runs, then all B runs               | Interleave A, B, A, B, at least three each               |
| Trusting an after figure on its own              | Reproduce the recorded before figure with the same probe |
| Accepting "N times faster" from a commit message | Run `validate_perf_claims.py` and measure each claim     |
| Reading a null A/B as "no effect"                | Prove the variable moved and its mechanism fired         |
| Quoting `ps` %CPU as current load                | Take two samples                                         |
````

- [ ] **Step 10: Record the ledger entries**

Write `$SCRATCH/perf-generic-decisions.json` (the session scratchpad, not `/tmp`):

```json
[
  {"skill": "coding-performance-review", "kind": "rule", "topic": "three-skill-shape",
   "decision": "Performance is covered by three skills: this generic one, coding-python-performance-review and coding-rust-performance-review; this one routes by language.",
   "why": "Each description triggers on its own language, and an invoked SKILL.md loads whole, so a Rust task must not load the 610-line Python body.",
   "evidence": {"tier": "user", "text": "user decision 2026-11-06: Three skills (Recommended)"},
   "reopen_if": "Claude Code loads skill bodies partially, or a language skill shrinks to a few lines.",
   "anchors": ["The language skills add their own tools on top of this one; the method is shared."],
   "supersedes": [], "refs": ["docs/plans/2026-11-06-performance-skills-design.md"], "origin": "authored"},
  {"skill": "coding-performance-review", "kind": "rejected", "topic": "one-skill-per-language-refs",
   "decision": "One renamed performance skill with references/python.md and references/rust.md.",
   "why": "Its description would list every language and trigger less precisely, and every task would load the router first.",
   "evidence": {"tier": "user", "text": "user decision 2026-11-06"},
   "reopen_if": "Skill triggering stops depending on the description text.",
   "supersedes": [], "refs": [], "origin": "authored"},
  {"skill": "coding-performance-review", "kind": "rule", "topic": "method-and-checklist",
   "decision": "This skill holds both the measurement method and a language-neutral review checklist.",
   "why": "A language with no skill of its own needs a list of what to look for, and the method must live in one place instead of being copied into each language skill.",
   "evidence": {"tier": "user", "text": "user decision 2026-11-06: Method + neutral checklist (Recommended)"},
   "reopen_if": "The checklist grows language-specific entries a language skill should own.",
   "anchors": ["Two halves: how to measure so that a number means what you think it means"],
   "supersedes": [], "refs": [], "origin": "authored"}
]
```

Then (SKILL.md must be tracked before anchors count):

```bash
git add plugins/bitranox/skills/coding-performance-review/SKILL.md
python3 plugins/bitranox/hooks/skill_decisions.py add --from-file "$SCRATCH/perf-generic-decisions.json"
python3 plugins/bitranox/hooks/skill_decisions.py check
```
Expected: `add` prints three ids; `check` exits 0.

- [ ] **Step 11: Write both checklists**

`coding-performance-review/.skillwriter/checklist-20261106-new-skill.md`: the meta-skill-writer
checklist with RED and GREEN answers for G1 and G2 quoted, the receipt line, and
`Decisions: <the three ids from Step 10>`.
`coding-python-performance-review/.skillwriter/checklist-20261106-claim-checker-moved.md`: the
change is two path mentions; `Decisions: none - the claim checker moved to the generic skill; no rule changed`.

- [ ] **Step 12: Commit**

First regenerate the derived artifacts:

```bash
python3 plugins/bitranox/hooks/build_skill_triggers.py
python3 plugins/bitranox/hooks/build_skill_docs.py
```
and change the three README mentions of `83` skills to `84` (`ls plugins/bitranox/skills | wc -l`
must print 84). Then, message file (earlier call):
`feat(skills): coding-performance-review, the generic performance skill` with a body naming the move.
```bash
git add plugins/bitranox/skills/coding-performance-review plugins/bitranox/skills/coding-python-performance-review plugins/bitranox/hooks/skill_triggers.json docs/skills.md README.md
git commit -F "$SCRATCH/msg-task1.txt" -- plugins/bitranox/skills/coding-performance-review plugins/bitranox/skills/coding-python-performance-review plugins/bitranox/hooks/skill_triggers.json docs/skills.md README.md
```
The commit gate runs the suite. No version bump in this commit (Task 4 releases).

---

### Task 2: Slim `coding-python-performance-review` to point at the generic skill

**Files:**
- Modify: `plugins/bitranox/skills/coding-python-performance-review/SKILL.md`
- Create: `plugins/bitranox/skills/coding-python-performance-review/.skillwriter/checklist-20261106-method-to-generic.md`
- Ledger: `plugins/bitranox/skills/coding-python-performance-review/.skillwriter/decisions.jsonl` (via `add`)

**Interfaces:**
- Consumes: `bitranox:coding-performance-review` and its sections "Method: a number you can
  believe" and "What to flag in code (any language)" from Task 1.

**Out of scope:**
- Step 4f ("Detect Unbounded Memory Patterns") and `find_unbounded_memory.py`: the Python scanner
  for the first checklist item stays here.
- The description: it already triggers on Python performance review.

**STOP conditions:**
- `python3 plugins/bitranox/hooks/skill_decisions.py show coding-python-performance-review --kind rejected,removed --full`
  prints an entry this change would contradict;
- any of the three replaced passages below is not found verbatim.

- [ ] **Step 1: Step 0b ledger read** (as in STOP conditions; record the output in the checklist).

- [ ] **Step 2: RED probe** on `bitranox:baseline-probe` (opus) with the CURRENT Python SKILL.md
text and the generic SKILL.md both pasted: "Review a Python ETL step that reads a 4 GB CSV with
`f.read().splitlines()` and calls `requests.get` once per row. Name the skills' sections you rely
on." Record whether it reports the unbounded read and the N+1 calls. The Python skill duplicates
the "Always flag" text today, so RED is expected to pass; the probe's job is the GREEN comparison.

- [ ] **Step 3: Replace the "Always Flag" section**

Replace the whole section from `## Always Flag: Unbounded Memory and Unsafe Input` up to (not
including) `## Purpose` with:

```markdown
## Always Flag: Unbounded Memory and Unsafe Input

The language-neutral checklist (unbounded memory, unbounded or unsafe input, untrusted structured
input, quadratic work, N+1 calls, per-item I/O) and the measurement method live in
`bitranox:coding-performance-review`: load it alongside this skill. Step 4f below is this
skill's Python scanner for the unbounded-memory item.
```

- [ ] **Step 4: Replace the BEFORE-figure paragraph**

Replace the paragraph beginning `When the defect you are fixing already has a recorded BEFORE figure`
(ending `...saying why its input has that shape.`) with:

```markdown
Before trusting an AFTER figure, follow the method in `bitranox:coding-performance-review`:
reproduce the recorded BEFORE figure with the same probe, interleave the arms and pin the core.
```

- [ ] **Step 5: Adjust the two Key Behaviors lines**

Replace
`- **ALWAYS flag unbounded memory**  -  big files / huge DB results / huge logfiles must stream, not load whole`
and
`- **ALWAYS flag unsafe input**  -  bound length, sanitize types/encoding (non-ASCII/emoji/CJK/binary), test it`
with one line:
`- **ALWAYS walk the generic checklist**  -  unbounded memory and unsafe input first (bitranox:coding-performance-review)`

- [ ] **Step 6: GREEN probe** with the edited Python SKILL.md plus the generic SKILL.md: same
scenario. Pass = the answer still reports the unbounded read AND the per-row calls, and names the
generic skill's checklist as the source.

- [ ] **Step 7: Ledger entry and checklist**

`$SCRATCH/perf-python-decisions.json`:

```json
[
  {"skill": "coding-python-performance-review", "kind": "rule", "topic": "method-lives-in-generic",
   "decision": "The measurement method and the language-neutral checklist live in coding-performance-review; this skill points there and keeps only Python tooling.",
   "why": "One place for the method; a copy here would drift from the generic text.",
   "evidence": {"tier": "user", "text": "user decision 2026-11-06: Three skills (Recommended)"},
   "reopen_if": "The generic skill is removed or stops covering unbounded memory and input.",
   "anchors": ["load it alongside this skill. Step 4f below is this"],
   "supersedes": [], "refs": ["docs/plans/2026-11-06-performance-skills-design.md"], "origin": "authored"}
]
```

The anchor sits on one line of the Step 3 replacement text. `git add` the SKILL.md, then `add`,
then `check`. Checklist `checklist-20261106-method-to-generic.md` with RED/GREEN answers and
`Decisions: <id>`.

- [ ] **Step 8: Run the skill's tests, then commit**

Run the Task 1 Step 8 command. Expected: all pass. Commit with `-F` and the pathspec
`plugins/bitranox/skills/coding-python-performance-review`.

---

### Task 3: The Rust skill `coding-rust-performance-review`

**Files:**
- Create: `plugins/bitranox/skills/coding-rust-performance-review/SKILL.md`
- Create: `plugins/bitranox/skills/coding-rust-performance-review/.skillwriter/checklist-20261106-new-skill.md`
- Ledger: `plugins/bitranox/skills/coding-rust-performance-review/.skillwriter/decisions.jsonl`
- Modify: `plugins/bitranox/skills/coding-rust/SKILL.md` (the "See also" section, one bullet)
- Create: `plugins/bitranox/skills/coding-rust/.skillwriter/checklist-20261106-see-also-perf.md`

**Interfaces:**
- Consumes: `bitranox:coding-performance-review` (Task 1).

**Out of scope:**
- Any bundled script: the user chose no scripts for the Rust skill.
- The rest of `coding-rust/SKILL.md`.

**STOP conditions:**
- the clippy command in Step 3 does not run as written on the scratch crate (an unknown lint name,
  a flag cargo refuses) after one fix attempt: report it, never ship an unexecuted command;
- `cargo` cannot build a scratch crate offline here (no registry access): report it.

- [ ] **Step 1: RED probes** on `bitranox:baseline-probe` (opus), scenario only:
- R1: a function that builds `let mut v = Vec::new();` then pushes in a `for i in 0..n` loop,
  does `let name = item.name.clone();` per iteration, calls `Regex::new(r"\d+")` inside the loop
  and builds output with `out = out + &format!(...)`. "You timed `cargo run` before and after your
  fix and it got 20 percent faster. Review the code and the measurement."
- R2: an axum handler holding a `std::sync::Mutex` guard across `.await` and calling
  `std::fs::read_to_string` on a 2 GB file. "Review it for performance."
RED records, for R1: release build or criterion, `with_capacity`, the clone, the regex in the loop,
clippy's perf lints; for R2: the guard across `.await`, blocking I/O in async
(`spawn_blocking` or `tokio::fs`), the unbounded read.

- [ ] **Step 2: Write the SKILL.md** (exactly this text):

````markdown
---
name: coding-rust-performance-review
description: Use when reviewing or improving the performance of Rust code - a slow hot loop, needless clones or allocations, a Vec or String grown without capacity, Regex::new or format! inside a loop, async code that blocks or holds a lock across .await, unbuffered I/O, a benchmark (criterion, cargo bench), a profiler or flamegraph run, release-profile settings (lto, codegen-units, debug symbols), or timing a change between two builds. Keywords - clippy perf, criterion, flamegraph, samply, heaptrack, DHAT, with_capacity, spawn_blocking.
---

# Rust performance review

Rust-specific checks and tools. The measurement method (profile first, reproduce the before
figure, interleave the arms, pin the core, prove the change took effect) and the language-neutral
checklist live in `bitranox:coding-performance-review`: load it alongside this skill. This skill
ships no scripts, because clippy and criterion already do the mechanical part.

## Measure the build you ship

- **Never time a debug build.** `cargo run` and `cargo test` without `--release` build the dev
  profile, which is unoptimised, so its timings say nothing about the release binary and an
  optimisation can vanish or invert there. Time the `cargo build --release` binary, or use
  `cargo bench` (the bench profile inherits from release).
- **Keep symbols without changing code generation:** `debug = "line-tables-only"` under
  `[profile.release]`, or `CARGO_PROFILE_RELEASE_DEBUG=line-tables-only cargo build --release`
  for one build. Debug info does not change the optimisation level.
- **Profile settings are A/B arms, not defaults:** `lto = "thin"` or `"fat"`,
  `codegen-units = 1`, `panic = "abort"`, and `RUSTFLAGS="-C target-cpu=native"` (that binary may
  not run on an older CPU). Record which ones each arm used.

## Lint first: clippy

```bash
cargo clippy --all-targets -- -D clippy::perf \
  -W clippy::redundant_clone -W clippy::needless_collect -W clippy::inefficient_to_string \
  -W clippy::large_types_passed_by_value -W clippy::trivially_copy_pass_by_ref \
  -W clippy::format_collect -W clippy::rc_buffer -W clippy::large_stack_arrays
```

The `perf` group warns by default (36 lints in clippy 0.1.95, among them
`regex_creation_in_loops`, `manual_memcpy`, `large_enum_variant`); `-D` makes them errors. The
`-W` lints are off by default because they have false positives: treat each hit as a candidate
to measure, not a verdict.

## Benchmarks: criterion

Add criterion as a dev-dependency (`cargo add --dev criterion`) and a bench target with the
default harness turned off:

```toml
[[bench]]
name = "hot_path"
harness = false
```

```rust
use criterion::{criterion_group, criterion_main, Criterion};
use std::hint::black_box;

fn bench(c: &mut Criterion) {
    let input = load_input();
    c.bench_function("parse", |b| b.iter(|| parse(black_box(&input))));
}

criterion_group!(benches, bench);
criterion_main!(benches);
```

Before and after: on the old code `cargo bench --bench hot_path -- --save-baseline before`, then
on the new code `cargo bench --bench hot_path -- --baseline before`. Criterion reports the change
with a confidence interval; "No change in performance detected" or "Change within noise
threshold" is not a win. `black_box` keeps the compiler from deleting the work being timed. A
criterion run is a micro-benchmark: confirm a win on the real workload too.

For whole programs, `hyperfine --warmup 3 ./old ./new` compares two binaries, but it runs all of
one command's runs before the other's, so repeat the comparison with the order swapped before
believing a small difference.

## Profilers and allocations

These recipes are unverified on this skill's test host (the tools were not installed there):
- `cargo flamegraph --bin app -- <args>` (`cargo install flamegraph`; builds release by default,
  uses perf on Linux and dtrace on macOS).
- `samply record ./target/release/app <args>` (`cargo install samply`), viewed in the Firefox
  Profiler.
- `perf record --call-graph dwarf ./target/release/app <args>`, then `perf report`. Inside a
  container perf can be refused by `kernel.perf_event_paranoid` or a missing capability; profile
  on the host or in a VM then.
- Allocations: `heaptrack ./target/release/app <args>`, or the `dhat` crate:
  `#[global_allocator] static ALLOC: dhat::Alloc = dhat::Alloc;` and
  `let _profiler = dhat::Profiler::new_heap();` at the top of `main`, which writes
  `dhat-heap.json` for the DHAT viewer.

## What to flag in Rust code

| Pattern                                                                             | Fix                                                                                                       |
|-------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------|
| `.clone()`, `.to_string()`, `.to_vec()` in a loop to please the borrow checker      | Borrow, use `Cow`, or restructure; `redundant_clone` finds some                                           |
| `Vec::new()` or `String::new()` then a push per iteration of known length           | `with_capacity(n)`, or `collect()` from an iterator with a size hint                                      |
| String built with `+` or `format!` per iteration                                    | One `String`, `push_str` or `write!` into it                                                              |
| `collect()` into a `Vec` only to iterate once or take `len()`                       | Keep the iterator (`needless_collect`)                                                                    |
| `Regex::new`, a parser or a client built inside a loop or per call                  | Build once: a `std::sync::LazyLock` static, or pass it in                                                 |
| `dyn Trait` or `Box<dyn Fn>` called per element on a hot path                       | Generics for static dispatch; measure the speed against the code-size cost                                |
| Default-hashed `HashMap` with integer keys on a profiled hot path                   | `rustc-hash` or `ahash`, only if the keys are not attacker-controlled (SipHash resists HashDoS)           |
| A `std::sync::Mutex` or `RwLock` guard alive across `.await`                        | End the guard's scope before the await, or `tokio::sync::Mutex` if it must be held (`await_holding_lock`) |
| Blocking calls in async code (`std::fs`, `std::thread::sleep`, heavy CPU)           | `tokio::fs`, `spawn_blocking`, or a thread pool such as rayon                                             |
| Small reads or writes on a `File`; `println!` in a hot loop                         | `BufReader`/`BufWriter`; lock stdout once (`let mut out = std::io::stdout().lock();`)                     |
| `read_to_string`/`read_to_end` on a large input; `collect()` of an unbounded stream | Stream with `BufRead::lines` or fixed-size chunks (generic checklist: unbounded memory)                   |
| `Arc<Mutex<_>>` updated from every task of a parallel loop                          | Per-thread accumulation, merged once at the end                                                           |
| A large value moved by value; one enum variant far larger than the rest             | Pass a reference; box the large variant (`large_enum_variant`)                                            |
````

- [ ] **Step 3: Execute the clippy recipe once on a scratch crate**

```bash
D=$(mktemp -d "$SCRATCH/rustperf.XXXXXX")
cargo new --vcs none --lib "$D/probe"
```

Write `$D/probe/src/lib.rs` (with the Write tool):

```rust
pub fn digits(lines: &[String]) -> Vec<String> {
    let mut out = Vec::new();
    for line in lines {
        let re = regex_lite_stand_in(line);
        out.push(re.clone());
    }
    out
}

fn regex_lite_stand_in(s: &str) -> String {
    s.chars().filter(|c| c.is_ascii_digit()).collect::<Vec<char>>().iter().collect()
}
```

Run (from `$D/probe`): the exact clippy command from the SKILL.md.
Expected: exit non-zero OR warnings, and at least one lint from the command's list reported
(`redundant_clone` on `re.clone()` or `needless_collect` on the `Vec<char>`); no "unknown lint"
error. Record the command, its exit code and the lint names it printed in the checklist. If a lint
name is unknown, fix the SKILL.md command and re-run. The crate uses no external dependency, so
it builds offline.

- [ ] **Step 4: Ledger entries**

`$SCRATCH/perf-rust-decisions.json`:

```json
[
  {"skill": "coding-rust-performance-review", "kind": "rule", "topic": "no-bundled-scripts",
   "decision": "The Rust skill is a checklist plus tool recipes and ships no scripts.",
   "why": "clippy's perf group and criterion already do statically and by benchmark what the Python skill's scanners do by hand.",
   "evidence": {"tier": "user", "text": "user decision 2026-11-06: Checklist + tool recipes (Recommended); clippy 0.1.95 perf group measured at 36 lints"},
   "reopen_if": "A recurring Rust review step is done by hand that clippy and criterion cannot do.",
   "anchors": ["ships no scripts, because clippy and criterion already do the mechanical part."],
   "supersedes": [], "refs": ["docs/plans/2026-11-06-performance-skills-design.md"], "origin": "authored"},
  {"skill": "coding-rust-performance-review", "kind": "rejected", "topic": "scripted-pipeline",
   "decision": "A scripted pipeline like the Python skill's (setup, profile, scanners, prioritise).",
   "why": "Much of it would duplicate clippy, and with the profilers absent on the authoring host its parsers would ship untested against real output.",
   "evidence": {"tier": "user", "text": "user decision 2026-11-06"},
   "reopen_if": "Profilers are available on a test host and a repeated manual step appears.",
   "supersedes": [], "refs": [], "origin": "authored"}
]
```

The anchor sits on one line of the Step 2 text. `git add` the SKILL.md, then `add`, then `check`.

- [ ] **Step 5: GREEN probes** R1 and R2 with the SKILL.md text pasted (plus the generic
SKILL.md). Pass = every point listed in Step 1 present in both answers. Write the checklist with
RED/GREEN answers, the Step 3 clippy record, and `Decisions: <the two ids>`.

- [ ] **Step 6: Point `coding-rust` at it**

Step 0b for `coding-rust` first (`skill_decisions.py show coding-rust --kind rejected,removed --full`).
In `plugins/bitranox/skills/coding-rust/SKILL.md`, section `## See also`, add the bullet:

```markdown
- `bitranox:coding-rust-performance-review` - performance: clippy's perf lints, criterion,
  profilers, release-profile settings and a Rust hot-path checklist.
```

Checklist `coding-rust/.skillwriter/checklist-20261106-see-also-perf.md` with
`Decisions: none - a cross-reference to the new skill; no rule changed`.

- [ ] **Step 7: Regenerate, then commit**

Run `python3 plugins/bitranox/hooks/build_skill_triggers.py` and
`python3 plugins/bitranox/hooks/build_skill_docs.py`, and change the three README mentions of `84`
skills and the one in `docs/installation.md` ("all 84 skills") to `85`
(`ls plugins/bitranox/skills | wc -l` must print 85): the commit gate's hook suite refuses a new
skill directory without them. Commit with `-F` and the pathspecs
`plugins/bitranox/skills/coding-rust-performance-review plugins/bitranox/skills/coding-rust plugins/bitranox/hooks/skill_triggers.json docs/skills.md README.md docs/installation.md`.

---

### Task 4: Cross-reference, generated artifacts, release

**Files:**
- Modify: `plugins/bitranox/skills/process-review-enhance-code-quality/SKILL.md` (the paragraph
  "**The cost rows are read, never measured.**")
- Create: `plugins/bitranox/skills/process-review-enhance-code-quality/.skillwriter/checklist-20261106-perf-skills-routing.md`
- Regenerate (check only, Tasks 1 and 3 already regenerated): `plugins/bitranox/hooks/skill_triggers.json`, `docs/skills.md`
- Bump: `plugins/bitranox/.claude-plugin/plugin.json`, `pyproject.toml`, `CHANGELOG.md`

**Out of scope:**
- `plugins/bitranox/skills/web-frontend-responsive-ux/analysis.py` line 7: its comment describes
  the Python skill's analyzer split, which is still true.
- `plugins/bitranox/skill-taxonomy.json`: the `coding` prefix already exists; confirm with
  `build_skill_docs.py --check` after regeneration rather than editing it.

**STOP conditions:**
- origin/master holds a version with the same minor as the one you are about to take (a peer
  released meanwhile): fetch, rebase, re-run `bump_version.py` from origin's number;
- `repo-gate.py --ci` fails on something this branch did not touch: report it with the output.

- [ ] **Step 1: Route the quality skill's performance pass**

Step 0b for `process-review-enhance-code-quality`. Replace the sentence
"run `bitranox:coding-python-performance-review` on a Python project as a pass of its own."
with
"run it as a pass of its own: `bitranox:coding-python-performance-review` on a Python project,
`bitranox:coding-rust-performance-review` on a Rust one, and `bitranox:coding-performance-review`
for the method and for any other language."
Checklist with `Decisions: none - routing extended to the new performance skills; no rule changed`.

- [ ] **Step 2: Confirm the generated artifacts are in sync**

```bash
python3 plugins/bitranox/hooks/build_skill_triggers.py --check
python3 plugins/bitranox/hooks/build_skill_docs.py --check
```
Expected: both exit 0 (Tasks 1 and 3 regenerated them; Step 1 changes no description). If either
fails, run it without `--check` and include the result in this task's commit.

- [ ] **Step 3: Bump (already made: commit 3395c79e, 10.20.0 -> 10.21.0)**

The commit gate refuses any commit touching `plugins/` while plugin.json equals origin's version,
so the controller made the bump commit before Task 1's commit, with the notes below. In this task:
`git fetch origin`; if origin's plugin.json is still 10.20.0, keep the bump and only correct the
CHANGELOG section if the shipped content differs from these notes. If origin moved past 10.20.0,
rebase onto it and re-bump from origin's number. The notes used for 3395c79e,
`$SCRATCH/notes.md`:

```markdown
### Added

- `coding-performance-review`: the measurement method (profile first, reproduce the before
  figure, interleave A/B runs, pin cores on hybrid CPUs, prove the change took effect) and a
  language-neutral review checklist, with a router to the language skills. It now holds
  `validate_perf_claims.py`.
- `coding-rust-performance-review`: a Rust hot-path checklist plus recipes for clippy's perf
  lints, criterion, profilers and release-profile settings.

### Changed

- `coding-python-performance-review` points at the generic skill for the method and the
  language-neutral checklist, and runs the claim checker from its new place.
```

```bash
# only when origin moved past 10.20.0, after the rebase:
uv run plugins/bitranox/hooks/bump_version.py --part minor --changelog "$SCRATCH/notes.md"
```

- [ ] **Step 4: Full gate**

```bash
python3 plugins/bitranox/hooks/repo-gate.py --ci
```
Expected: exit 0. Then commit everything from Steps 1-3 with `-F` and explicit pathspecs.

- [ ] **Step 5: Push and watch CI**

Message the peer session working on the skill-decision ledger before pushing. Then
`git fetch origin`, and if origin moved, `git rebase origin/master` and re-check the version.
Push `git push origin HEAD:master` (the pre-push hook runs the gate, about 11 minutes). Watch CI:
`python3 plugins/bitranox/skills/compuse-toolbox/scripts/ci_wait.py --ref HEAD`
run in the foreground or alone in the background. Done = every run on the pushed sha green, and
`git log origin/master -1` shows the bump commit.
