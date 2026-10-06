# Scratch-collision jigs Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use bitranox:process-agents-subagent-driven-development (recommended) or bitranox:process-plan-executor to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the two recorded scratch-collision mechanisms a jig each - `mutation_arm --revert FILE REV` for "run this test against the committed version of a file", `fanout_crosscheck` for "did an agent write into a sibling's target" - and wire both in so the rule stops living in prose.

**Architecture:** A revert is one more entry in mutation_arm's existing arm, so it inherits the copy-first restore, the byte comparison, the bytecode purge and the timeout; no second restore path. `fanout_crosscheck` is a new compuse-toolbox script that scans only ADDED lines per target for the other targets' identifiers. The spec is `docs/plans/2026-10-05-scratch-collision-jigs-design.md`.

**Tech Stack:** Python 3.10+, stdlib only (subprocess to git), pytest against real temporary git repos, the shared `_cli_envelope` helper.

## Global Constraints

- Exit codes 0/1/2 as the rest of compuse-toolbox: for mutation_arm 0 KILLED, 1 SURVIVED, 2 everything that is not a verdict; a refusal writes nothing.
- `--json` prints the house envelope `{ok, command, data, skipped}` on every exit, `ok` false exactly on exit 2 (`envelope_for_exit` / `emit` from `scripts/_cli_envelope.py`).
- Sources are read and written UTF-8 with `newline=""` (`_read_source` / `_write_source`), so CRLF is kept.
- Subprocesses get `env={**os.environ, ...}`, never a fresh dict (Windows loses SystemRoot).
- Every change under `plugins/bitranox/` bumps `plugins/bitranox/.claude-plugin/plugin.json` AND `pyproject.toml` (the gate checks they agree), re-read from origin/master before bumping, plus a CHANGELOG entry.
- Tests run with CI's set: `env -u VIRTUAL_ENV uv run --with pytest --with PyYAML --with lxml --with defusedxml --with ruamel.yaml --with httpx2 python -m pytest ...`.
- Order: `--revert`, then `fanout_crosscheck`, then the wiring; each its own commit and version bump.

---

### Task 1: `mutation_arm --revert FILE REV`

**Files:**
- Modify: `plugins/bitranox/skills/compuse-toolbox/scripts/mutation_arm.py` (module docstring; `_plan`; `run_arm`; `_parse`; `main`; `_main_single`; new `RevertError`, `resolve_revert`, `plan_reverts`)
- Test: `plugins/bitranox/skills/compuse-toolbox/tests/test_mutation_arm.py` (new section `--revert`)
- Modify: `CHANGELOG.md`, `plugins/bitranox/.claude-plugin/plugin.json`, `pyproject.toml`

**Interfaces:**
- Produces: `resolve_revert(path_arg: str, rev: str) -> tuple[Path, str, str]` returning (path, text at REV as checkout would write it, resolved 40-char sha); `plan_reverts(specs: list[list[str]]) -> tuple[list[tuple[Path, None, str]], list[dict]]` returning planned whole-file entries and one report dict `{"path", "rev", "sha"}` per revert; `plan_mutations(specs, *, after=None)` where `after` maps a resolved path to the text the arm will see after the reverts. A planned entry whose `old` is `None` replaces the whole file.
- Produces for Task 3: the CLI line `mutation_arm.py --revert FILE REV --test NODEID` and `data.reverts` in the envelope.

**Out of scope** - do NOT touch:
- `--battery` arms carrying reverts: the battery spec has no revert field; `--battery` with `--revert` is refused as separate modes, like `--mutate`.
- `anchor_edit.py`: a whole-file replacement never goes through `replace_exact`, so no anchor semantics change.

**STOP conditions:**
- `git cat-file --filters <sha>:<path>` does not apply the checkout eol conversion on this git (the CRLF test fails twice);
- the restore path needs changing to support a revert (it must not: copies are taken before the first write);
- a step's verification fails twice after one reasonable fix attempt.

- [ ] **Step 1: Write the failing tests** (append to `tests/test_mutation_arm.py`)

```python
# --------------------------------------------------------------------------
# --revert FILE REV: run the arm against the committed version of a file
# --------------------------------------------------------------------------

FIXED = SOURCE  # the work tree: test_zero passes
BUGGY = SOURCE.replace('return "zero"', 'return "ZERO"')  # what HEAD holds


def _git(cwd, *args):
    return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True,
                          encoding="utf-8", errors="replace", check=True).stdout.strip()


def make_git_project(tmp_path, committed=BUGGY, worktree=FIXED):
    """HEAD holds `committed`, the work tree `worktree`: the shape of an uncommitted fix."""
    p = make_project(tmp_path)
    (p / "src.py").write_text(committed, encoding="utf-8")
    _git(p, "init", "-q")
    _git(p, "config", "user.name", "t")
    _git(p, "config", "user.email", "t@example.com")
    _git(p, "add", "src.py", "test_src.py")
    _git(p, "commit", "-q", "-m", "c1")
    (p / "src.py").write_text(worktree, encoding="utf-8")
    return p


def test_a_revert_the_test_notices_is_killed(tmp_path):
    p = make_git_project(tmp_path)
    proc = run(p, "--revert", "src.py", "HEAD", "--test", "test_src.py::test_zero", "--json")
    assert proc.returncode == 0, (proc.stdout, proc.stderr)
    data = json.loads(proc.stdout)["data"]
    assert data["verdict"] == "killed"
    assert data["reverts"] == [{"path": "src.py", "rev": "HEAD", "sha": _git(p, "rev-parse", "HEAD")}]


def test_a_revert_the_test_cannot_see_survives(tmp_path):
    p = make_git_project(tmp_path, committed=SOURCE.replace('"negative"', '"NEGATIVE"'))
    proc = run(p, "--revert", "src.py", "HEAD", "--test", "test_src.py::test_zero", "--json")
    assert proc.returncode == 1, (proc.stdout, proc.stderr)
    assert json.loads(proc.stdout)["data"]["verdict"] == "survived"


def test_a_revert_restores_the_uncommitted_work_byte_for_byte(tmp_path):
    p = make_git_project(tmp_path)
    before = (p / "src.py").read_bytes()
    run(p, "--revert", "src.py", "HEAD", "--test", "test_src.py::test_zero")
    assert (p / "src.py").read_bytes() == before


def test_a_revert_restores_after_a_timeout(tmp_path):
    p = make_git_project(tmp_path)
    before = (p / "src.py").read_bytes()
    planned, _ = M.plan_reverts([[str(p / "src.py"), "HEAD"]])
    report = M.run_arm(planned, "test_src.py::test_zero", timeout=1,
                       runner=[sys.executable, "-c", "import time; time.sleep(30)"])
    assert report["verdict"] == "timeout"
    assert (p / "src.py").read_bytes() == before


@pytest.mark.parametrize("case", ["untracked", "not_a_repo", "bad_rev", "identical"])
def test_a_revert_that_cannot_mean_anything_is_refused_and_writes_nothing(tmp_path, case):
    p = make_git_project(tmp_path) if case != "not_a_repo" else make_project(tmp_path)
    target, rev = "src.py", "HEAD"
    if case == "untracked":
        (p / "extra.py").write_text("x = 1\n", encoding="utf-8")
        target = "extra.py"
    elif case == "bad_rev":
        rev = "no-such-rev"
    elif case == "identical":
        (p / "src.py").write_text(BUGGY, encoding="utf-8")
    before = (p / target).read_bytes()
    proc = run(p, "--revert", target, rev, "--test", "test_src.py::test_zero", "--json")
    assert proc.returncode == 2, (case, proc.stdout, proc.stderr)
    assert json.loads(proc.stdout)["ok"] is False
    assert (p / target).read_bytes() == before


def test_a_revert_and_a_mutation_apply_together_as_one_arm(tmp_path):
    """Alone, either one is KILLED; together the test passes - which only happens when both
    were applied."""
    p = make_git_project(tmp_path)
    (p / "old.txt").write_text('assert classify(0) == "zero"', encoding="utf-8")
    (p / "new.txt").write_text('assert classify(0) == "ZERO"', encoding="utf-8")
    proc = run(p, "--revert", "src.py", "HEAD", "--mutate", "test_src.py", "old.txt", "new.txt",
               "--test", "test_src.py::test_zero", "--json")
    assert proc.returncode == 1, (proc.stdout, proc.stderr)


def test_a_mutation_anchor_is_checked_against_the_reverted_text(tmp_path):
    """'return "ZERO"' exists only at HEAD, so the anchor must be looked up after the revert."""
    p = make_git_project(tmp_path)
    (p / "old.txt").write_text('return "ZERO"', encoding="utf-8")
    (p / "new.txt").write_text('return "zero"', encoding="utf-8")
    proc = run(p, "--revert", "src.py", "HEAD", "--mutate", "src.py", "old.txt", "new.txt",
               "--test", "test_src.py::test_zero", "--json")
    assert proc.returncode == 1, (proc.stdout, proc.stderr)


def test_a_reverted_crlf_checkout_keeps_its_line_endings_during_the_arm(tmp_path):
    p = make_git_project(tmp_path)
    _git(p, "config", "core.autocrlf", "true")
    (p / "src.py").write_bytes(FIXED.replace("\n", "\r\n").encode("utf-8"))
    before = (p / "src.py").read_bytes()
    seen = p / "seen.bin"
    probe = (f"import pathlib; pathlib.Path({str(seen)!r}).write_bytes("
             f"pathlib.Path({str(p / 'src.py')!r}).read_bytes()); raise SystemExit(0)")
    planned, _ = M.plan_reverts([[str(p / "src.py"), "HEAD"]])
    M.run_arm(planned, "test_src.py::test_zero", runner=[sys.executable, "-c", probe])
    during = seen.read_bytes()
    assert b'return "ZERO"\r\n' in during
    assert during.count(b"\n") == during.count(b"\r\n")
    assert (p / "src.py").read_bytes() == before


def test_revert_and_battery_together_are_refused(tmp_path):
    p = make_git_project(tmp_path)
    (p / "spec.json").write_text('{"tests": ["test_src.py"], "arms": []}', encoding="utf-8")
    proc = run(p, "--battery", "spec.json", "--revert", "src.py", "HEAD")
    assert proc.returncode == 2
    assert "separate modes" in proc.stderr
```

- [ ] **Step 2: Run them, expect FAIL** (`--revert` is an unknown argument: exit 2 from argparse, so the KILLED/SURVIVED/combined tests fail and the refusal tests may pass for the wrong reason - that is why they assert on the envelope too)

Run: `env -u VIRTUAL_ENV uv run --with pytest python -m pytest -q -p no:cacheprovider plugins/bitranox/skills/compuse-toolbox/tests/test_mutation_arm.py -k revert`

- [ ] **Step 3: Implement** in `scripts/mutation_arm.py`

```python
class RevertError(ValueError):
    """A --revert that cannot mean anything; refused before anything is written."""


def _git(args, cwd) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True,
                          env={**os.environ, "LC_ALL": "C"})


def resolve_revert(path_arg, rev):
    """(path, the file's text at REV as a checkout would write it, REV's 40-char sha).

    `git cat-file --filters` applies the same eol and smudge conversion a checkout does, so a CRLF
    work tree gets CRLF text back rather than the LF blob. Refused: a path outside a git work
    tree, a REV that is not a commit, a file absent at REV, and a work tree already identical to
    REV - that arm would change nothing, so its SURVIVED would be vacuous.
    """
    path = Path(path_arg)
    if not path.is_file():
        raise RevertError(f"not a file: {path}")
    real = path.resolve()
    top = _git(["rev-parse", "--show-toplevel"], real.parent)
    if top.returncode != 0:
        raise RevertError(f"{path} is not inside a git work tree")
    sha = _git(["rev-parse", "--verify", "-q", f"{rev}^{{commit}}"], real.parent)
    if sha.returncode != 0:
        raise RevertError(f"{rev!r} does not resolve to a commit")
    sha_text = sha.stdout.decode("ascii").strip()
    rel = real.relative_to(Path(top.stdout.decode("utf-8").strip()).resolve()).as_posix()
    blob = _git(["cat-file", "--filters", f"{sha_text}:{rel}"], real.parent)
    if blob.returncode != 0:
        raise RevertError(f"{path} does not exist at {rev}")
    text = blob.stdout.decode("utf-8")
    if text == _read_source(path):
        raise RevertError(f"{path} already matches {rev}: the arm would change nothing")
    return path, text, sha_text


def plan_reverts(specs):
    """Planned whole-file entries (path, None, text at REV) and one report dict per revert."""
    planned, reports, seen = [], [], set()
    for path_arg, rev in specs:
        path, text, sha = resolve_revert(path_arg, rev)
        if path.resolve() in seen:
            raise RevertError(f"{path} is reverted twice in one arm")
        seen.add(path.resolve())
        planned.append((path, None, text))
        reports.append({"path": str(path_arg), "rev": rev, "sha": sha})
    return planned, reports
```

`_plan(specs, load, after=None)`: seed `texts` from `after` (`texts = dict(after or {})`) so a mutation anchor is checked against the reverted text; `plan_mutations(specs, *, after=None)` passes it through. In `run_arm`, the apply loop becomes
`_write_source(path, new if old is None else replace_exact(_read_source(path), old, new))`.
`_parse` gains `--revert` (`nargs=2, action="append", metavar=("FILE", "REV")`). `main` refuses `--battery` with `--revert` ("--battery and --revert are separate modes; give one"). `_main_single`: refuse when neither `--mutate` nor `--revert` ("no --mutate or --revert given"); plan reverts first, then `plan_mutations(args.mutate or [], after={p.resolve(): t for p, _, t in reverts})`; catch `RevertError` beside `AnchorError` as "refused, nothing written"; set `report["reverts"]`; the text output prints `reverted <path> to <rev> (<sha>)` per revert. Module docstring: one bullet naming the job and why it is safe (copy-first restore, never `git checkout --`).

- [ ] **Step 4: Run the whole file, expect PASS**

Run: `env -u VIRTUAL_ENV uv run --with pytest python -m pytest -q -p no:cacheprovider plugins/bitranox/skills/compuse-toolbox/tests/test_mutation_arm.py`

- [ ] **Step 5: RED-verify the anchor-ordering test** with `mutation_arm.py --mutate` itself: drop the `after=` seeding and require `test_a_mutation_anchor_is_checked_against_the_reverted_text` to fail.

- [ ] **Step 6: Bump, CHANGELOG, commit, push, watch CI** (version re-read from origin/master; minor bump: a new capability).

### Task 2: `fanout_crosscheck` (detailed after Task 1 lands)

Per the design's Part 2: `scripts/fanout_crosscheck.py --target NAME=PATH ... [--since REV] [--ident NAME=TOKEN ...] [--allow NAME=TOKEN ...] [--json]`; added lines only (`git diff -U0`, default work tree plus index; a plain-file target counts every line as added); identifiers are each target NAME's snake/kebab/space spellings case-insensitive plus `--ident`; a declared `pyproject.toml` dependency of the scanned target and `--allow` are not findings; exit 0 clean, 1 findings, 2 usage/IO or zero added lines examined; the examined counts always reported. Tests: the 2026-10-05 three-repo fixture, declared-dependency negative, pre-existing-line negative, plain-file targets, zero-lines exit 2, planted positive and negative.

### Task 3: wiring (detailed after Task 2 lands)

SKILL.md rows for both jigs (each registered only after an isolated retrieval test picks it, NONE acceptable); one Verification line in `process-agents-dispatching-parallel`; a toolbox-nudge signature pointing a hand-rolled `git show HEAD:<file> > <file>` during a test run at `--revert` (nudge, never block, firing rate replayed over the corpus first); the memory fact `feedback-a-parallel-write-agent-can-clobber-a-sibling-target-and-report-success` pointed at both jigs.
