# Top Index Phase 1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use bitranox:process-agents-subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give every dream and nap a cost side for the always-loaded pointer blocks, remove the
rule texts that push facts to the tree top, keep pointer titles as data, and compact the tree-top
block; then test and ship shortened hooks.

**Architecture:** The cost report extends `store_manifest.py verify`, which already diffs a
pre-dream backup against the live tree, with per-level state counts. Rule texts change through
`bitranox:meta-skill-writer`. Titles are copied into body frontmatter by the engine. The
compaction is an operational run against the store through `factedit.py`, `memory_engine.py` and
`reconcile_memory_index.py`. The firing test (P1b) adapts the A/B harness in
`skills/meta-skill-ab-test/scripts/`.

**Tech Stack:** Python 3.14 stdlib scripts with pytest tests, Markdown SKILL.md files, the
per-skill decision ledger (`plugins/bitranox/hooks/skill_decisions.py`), headless Claude Code CLI
for P1b.

**Design:** `docs/plans/2026-11-09-top-index-cost-side-design.md` (first commit c211f336,
amended after review). Frozen inputs: the main checkout's gitignored
`.plan/top-index-phase1-inputs/`.

## Global Constraints

- ASCII only in every file; no em-dashes, curly quotes or other typographic tells.
- No Claude/AI attribution anywhere: no Co-Authored-By, no "Generated with" footer, no mention in
  a commit message, changelog or doc.
- Commit with `git commit -F <file> -- <paths>`, the message file written in an EARLIER Bash call;
  never `-m`. Work in the worktree
  `<repo>/.claude/worktrees/top-index-design`
  (branch `design/top-index-topics`); push as `git push origin design/top-index-topics:master`.
- `$ANCHOR` means the knowledge tree's anchor (the topmost dir holding a `CLAUDE.md` and a
  `.claude-memory/`); `export ANCHOR=<that dir>` before any run step, since some steps read it
  inside `bash -c`. `<repo>` means this repo's main checkout.
- `$SCRATCH` means the session's scratchpad directory; never `/tmp`, never `$TMPDIR` (empty here).
- Never edit anything under `.github/`. History is append-only: no force-push, no rewrite.
- Public-repo docs state what a skill or tool does, never private provenance (no private hosts,
  paths, project names).
- Every SKILL.md or reference change goes through `bitranox:meta-skill-writer` (receipt, Step 0b
  ledger read, RED/GREEN probes, a `.skillwriter/checklist-<date>-<topic>.md` with a
  `Decisions:` line).
- Every shipped `.py` has sibling tests; run them with CI's dependency set:
  `env -u VIRTUAL_ENV uv run --with pytest --with PyYAML --with lxml --with defusedxml --with ruamel.yaml --with httpx2 python -m pytest <paths> -q`
- The store (`$ANCHOR/.claude-memory/` and every `CLAUDE.local.md` pointer block)
  is written only through the engine tools, never by Write/Edit, and only after a
  `store_manifest.py backup`.
- Executions (implementers, fixers, reviewers) run on opus; reviews at effort medium. The user
  decided on 2026-11-09 ("go aheat with opus") that this work is authored on opus.
- Release: one minor bump with `uv run plugins/bitranox/hooks/bump_version.py --part minor
  --changelog <notes>` from the version origin holds at release time.
- User decisions this plan implements (verbatim option labels, 2026-11-09): "Keep as data, decide
  in phase 2 (Recommended)" (titles); "Today twice + shortened, 6 runs (Recommended)" (firing
  test); "Over 350, to 350 (Recommended)" (hook scope).

---

## HIGH: milestones

| Milestone | Delivers                                                                                                                                   | Ships as      | Decision after it                    |
|-----------|--------------------------------------------------------------------------------------------------------------------------------------------|---------------|--------------------------------------|
| P1a       | cost report in `verify`; crosstree dreams use backup+verify; rule-text fixes; reconcile warning; titles copied into frontmatter; release   | plugin minor  | none                                 |
| P1a-run   | the compaction run on the store (merges, moves off the top, trims, renamed-skill names), verified with the new cost report                 | store commit  | none                                 |
| P1b       | 213 hooks over 350 rewritten in scratch, loss-checked; harness adapted from the A/B scripts; canary; screening; 3 arms x 12 rules x 6 runs | evidence only | CHECKPOINT: do shortened hooks pass? |
| P1c       | the rewrites applied with `factedit.py apply --batch`, verified                                                                            | store commit  | none                                 |

MVP slice: P1a plus P1a-run. Cut from phase 1: dropping titles, the 300-character cap, all phase 2
work. Risks, ranked: (1) a dream between the plan and the run changes the store, so every
reviewer draft is re-checked against the live store at apply time; (2) rule-text fixes change
dream behaviour that other sessions rely on, so each lands with its RED/GREEN probe; (3) P1b's
harness measures the wrong thing, so the canary pair and the today-versus-today arm come first.

**P1b and P1c get their detailed tasks only after P1a-run is verified.** P1c's tasks are written
only once the P1b checkpoint is decided.

## MID: components and verification

**M1 cost report (`skills/meta-dream-tree/store_manifest.py`).** `verify` already re-derives the
live tree. New: a per-level summary read from the backup's `levels/<rel>/CLAUDE.local.md` and the
live file: block bytes (the managed block only, as the engine parses it), pointer count, slugs
arrived and slugs left, before and after. JSON: `data.levels[]` with `level`, `bytes_before`,
`bytes_after`, `pointers_before`, `pointers_after`, `arrived`, `left`; text: one line per level
whose block changed, top first. Exit codes unchanged. Verified by tests on a planted tree: a lift
that merges two sibling copies into one top copy shows `arrived` at the top and `left` at both
siblings; an unchanged level is omitted from the text; a manifest from before this change (no
level copies readable) reports `skipped`, never zeros.

**M2 crosstree backup (`skills/meta-dream-crosstree/SKILL.md`, `-deep/SKILL.md`).** Replace the
hand-rolled per-run backup with `store_manifest.py backup --scope tree` per tree and `verify` at
the end, printing the cost lines in the report. Verified by the skill-writer probes.

**M3 rule-text fixes.** `skills/meta-dream-tree/SKILL.md` (the soft-cap sentence; the
rationalization row re-homing a misplacement "whatever the verdict"), `references/dream-core.md`
(the report contract names the cost lines), `skills/meta-dream-nap/SKILL.md` (never move a fact to
the tree top; propose it; print the cost lines), `skills/meta-self-improve/reconcile_memory_index.py`
(the large-index warning stops recommending "lift"). Verified by probes and, for reconcile, a test
on the warning text.

**M4 titles as data (`hooks/memory_engine.py`).** A body's frontmatter gains `title:`, written by
`add` and kept by every engine path that rewrites a body (the engine's `upsert_entry`, which
`factedit.py apply` and `amend-pinned` go through, and `retitle`; `move` never touches a body).
An opt-in `heal --backfill-titles` fills titles into older bodies from the pointer line; plain
`heal`, which runs at every SessionStart, still never opens a body. Pointer lines unchanged.
Verified by tests: add writes it; an amend that passes no title keeps it; the back-fill fills it
from the pointer; a body that already has a title is not rewritten; plain heal opens no body.

**M5 release.** The version bump is the FIRST commit (Task 1), because the commit gate refuses a
`plugins/` commit whose version equals origin's; M5 re-bumps with `bump_version.py --merge` only if
origin moved meanwhile, then gate, review, push, CI watched to green.

**P1a-run compaction (operational).** First, on its own backup and verify, the title back-fill
(it changes nearly every body's digest, so inside the compaction it would flood the diff). Then:
backup; re-derive each reviewer draft against the live store
(`factedit.py apply --batch --dry-run`); relink `[[slug]]` references to each merged-away fact;
apply merges and trims; `reconcile_memory_index.py --archive` the merged-away facts; `memory_engine
move` the 11 facts off the top; rename the renamed skill in hooks;
`verify` (the cost lines must show the top block shrinking); `reconcile --check-tree` with 0
problems; commit the store. Verified by the cost lines and the manifest diff matching the plan's
list of slugs, both ways.

---

## DETAILED: P1a tasks

Conventions for every task below.

- `W` is the worktree root,
  `<repo>/.claude/worktrees/top-index-design`.
  Every command starts with `cd <W> &&` (written out in full; a bare `cd` does not carry between
  calls in a subagent). `P` is `<W>/plugins/bitranox`.
- `TEST <paths>` stands for the CI command written out in full:
  `env -u VIRTUAL_ENV uv run --with pytest --with PyYAML --with lxml --with defusedxml --with ruamel.yaml --with httpx2 python -m pytest <paths> -q`.
  If a worktree-isolation guard refuses the `env -u` form, run the same command after `unset
  VIRTUAL_ENV;` in the same call. Run it in the foreground and read pytest's own last line
  (`N passed` / `N failed`), never through a pipe.
- Commit: write the message file with the Write tool in an EARLIER call, then `git status
  --porcelain`, then `git commit -F <msgfile> -- <paths>` (a NEW file is `git add`ed first). The
  PreToolUse commit gate runs the hooks suite (4-8 minutes) and refuses a commit whose
  `plugins/` change ships a version equal to the fork point's: that is why Task 1 bumps the version
  and every later commit rides that bump. A refusal is read and fixed at its cause; never
  `--no-verify`. No Co-Authored-By or any other attribution line.
- Python: 3.14 floor, ASCII only, every new public name of `store_manifest.py` in `__all__`.
  `memory_engine.py` and `uuid_store.py` declare no `__all__` today; adding one for a single name
  would misdeclare their surface, so none is added (recorded in the report as a decision).
- Skill text (Tasks 6-10) goes through `bitranox:meta-skill-writer`: invoke it with the Skill tool
  first, then open a receipt with `python3 <P>/hooks/skill_receipt.py start meta-skill-writer` and
  close it with `python3 <P>/hooks/skill_receipt.py end meta-skill-writer`. Text-only probes run as
  `bitranox:baseline-probe` agents on opus, once with the OLD passage (RED) and once with the NEW
  one (GREEN); paste the passage into the prompt, never a path. Ledger entries are written only
  with `python3 <P>/hooks/skill_decisions.py add --from-file <file>`, AFTER the text edit (an
  anchor must already be in the skill's text). Each touched skill directory gets its own
  `.skillwriter/checklist-20261110-<topic>.md` with a `Decisions:` line.
- After editing a Markdown table, run
  `python3 <P>/skills/docs-md-table-formatting/reformat_tables.py <file>` and read `git diff` for
  that file before committing.

### Task 1: M1a - backup copies every in-scope level and records them; open the release

**Files:**
- Modify: `plugins/bitranox/hooks/uuid_store.py` (add `pointer_region` after `_pointer_region`,
  lines 419-422)
- Modify: `plugins/bitranox/skills/meta-dream-tree/store_manifest.py` (line 71 `__all__`; insert
  `scope_levels` before `derive` at line 284; lines 295-296 in `derive`; lines 375-384
  `_write_manifest`; lines 427-436 in `backup`; lines 451-453 in `_manifest_shape_error`)
- Modify: `plugins/bitranox/.claude-plugin/plugin.json`, `pyproject.toml`, `CHANGELOG.md` (via
  `bump_version.py`)
- Test: `plugins/bitranox/skills/meta-dream-tree/tests/test_store_manifest.py` (append after line
  545)

**Interfaces:**
- Produces: `store_manifest.scope_levels(anchor: Path, *, scope: str, start: Path, exclude:
  tuple[Path, ...] = (), unreadable: list[str] | None = None) -> list[Path]`;
  `uuid_store.pointer_region(text: str | None) -> str`; manifest key `"levels": list[str]` (every
  level dir the backup copied, as `str(Path)`).
- Consumes: `levels_under`, `levels_on_chain`, `LEVEL_FILE`, `_write_manifest`, `load_manifest`
  (existing, same module).

**Out of scope:** the cost report itself (Task 2); any change to `verify`'s exit codes or to the
existing manifest keys.

**STOP if:** `git fetch origin` shows `origin/master` has moved past `c211f336` with a change to
`store_manifest.py` or `uuid_store.py` (re-read both before editing); or the bump jig reports a
version origin already holds.

- [ ] **Step 1: Write the failing tests** - append to `test_store_manifest.py`:

```python


# ---- the cost report: per-level block state, backup copy against the live file ----------------

def make_siblings(root: Path) -> tuple[Path, Path]:
    """An anchor with an empty top block and two sibling levels that each hold a copy of one slug:
    the shape a dream lift merges into one top copy."""
    (root / "CLAUDE.md").write_text("anchor\n", encoding="utf-8")
    (root / ".claude-memory" / "facts").mkdir(parents=True)
    (root / ".claude-memory" / "facts" / "shared.md").write_text("body\n", encoding="utf-8")
    (root / ".claude-memory" / "facts" / "own-a.md").write_text("body a\n", encoding="utf-8")
    (root / "CLAUDE.local.md").write_text("# Memory index\n", encoding="utf-8")
    sib_a, sib_b = root / "a", root / "b"
    for sib, extra in ((sib_a, "- [Own](mem:own-a) - When own, do own.\n"), (sib_b, "")):
        sib.mkdir()
        (sib / "CLAUDE.local.md").write_text(
            "# Memory index\n- [Shared](mem:shared) - When shared, do shared.\n" + extra,
            encoding="utf-8")
    return sib_a, sib_b


def test_backup_copies_a_level_whose_block_holds_no_pointer(tmp_path):
    """Its bytes before are what the cost report subtracts from when the run adds a pointer."""
    make_siblings(tmp_path)
    out = outside(tmp_path)
    assert run_cli(["backup", "--from", str(tmp_path), "--out", str(out)], tmp_path).returncode == 0
    assert (out / "levels" / "CLAUDE.local.md").is_file()
    data = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert str(tmp_path) in data["levels"]


def test_a_manifest_whose_levels_is_not_a_list_of_strings_is_refused(tmp_path):
    make_siblings(tmp_path)
    out = outside(tmp_path)
    assert run_cli(["backup", "--from", str(tmp_path), "--out", str(out)], tmp_path).returncode == 0
    manifest = out / "manifest.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data["levels"] = "not a list"
    manifest.write_text(json.dumps(data), encoding="utf-8")
    r = run_cli(["verify", "--out", str(out)], tmp_path)
    assert r.returncode == 2, r.stdout + r.stderr
    assert "'levels' is not a list of strings" in r.stdout + r.stderr


def test_scope_levels_is_the_set_derive_walks(tmp_path):
    sib_a, sib_b = make_siblings(tmp_path)
    tree = SM.scope_levels(tmp_path, scope="tree", start=tmp_path)
    chain = SM.scope_levels(tmp_path, scope="chain", start=sib_a)
    assert sorted(tree) == sorted([tmp_path, sib_a, sib_b])
    assert sorted(chain) == sorted([tmp_path, sib_a])
```

- [ ] **Step 2: Run them, expect FAIL**

`cd <W> && TEST plugins/bitranox/skills/meta-dream-tree/tests/test_store_manifest.py`
Expected: 3 failed - `KeyError: 'levels'`, `assert False` on `.../levels/CLAUDE.local.md).is_file`,
and `AttributeError: module 'store_manifest' has no attribute 'scope_levels'`; the 47 existing
tests pass.

- [ ] **Step 3: Implement**

In `uuid_store.py`, directly after `_pointer_region` (ends line 422):

```python


def pointer_region(text):
    """The text pointers are read from (see `_pointer_region`), for a caller outside this module
    that measures the always-loaded block exactly as the parser bounds it."""
    return _pointer_region(text or "")
```

In `store_manifest.py`:

1. Line 71 becomes (Task 2 adds its three names; an `__all__` naming a missing name breaks
   `import *`, so they are not listed yet):

```python
__all__ = ["Entry", "Diff", "NoAnchor", "Unreadable", "derive", "diff", "manifest_key",
           "scope_levels", "main"]
```

2. Insert before `def derive(` (line 284):

```python
def scope_levels(anchor: Path, *, scope: str, start: Path, exclude: tuple[Path, ...] = (),
                 unreadable: list[str] | None = None) -> list[Path]:
    """Every level dir a manifest of `scope` covers: the tree under `anchor`, or the chain from
    `start` up to it. One definition for derive, backup and the cost report, so the three can never
    disagree about which levels exist."""
    if scope == "tree":
        return levels_under(anchor, exclude, unreadable)
    return levels_on_chain(start, anchor)


```

3. In `derive`, replace lines 295-296

```python
    levels = (levels_under(anchor, exclude, unreadable) if scope == "tree"
              else levels_on_chain(begin, anchor))
```

   with

```python
    levels = scope_levels(anchor, scope=scope, start=begin, exclude=exclude,
                          unreadable=unreadable)
```

4. `_write_manifest` signature (lines 375-376) gains `levels: list[Path]`:

```python
def _write_manifest(out: Path, *, anchor: Path, scope: str, start: Path,
                    entries: list[Entry], levels: list[Path]) -> Path:
```

   and in its dict, between the `"generated"` line (381) and the `"entries"` line, insert:

```python
               # Every level the backup COPIED, pointers or not: the cost report reads a level
               # absent from this list as "did not exist", which only this list can prove.
               "levels": [str(lvl) for lvl in levels],
```

5. In `backup`, replace the block from the `# Every in-scope level sits under the anchor` comment
   through the `return` (lines 429-436) with:

```python
    # EVERY in-scope level, not only those holding a pointer: a level whose block is empty now
    # can gain pointers in the run, and the cost report needs its bytes before. Every in-scope
    # level sits under the anchor (the tree walk starts there, the chain walk stops there), so
    # relative_to cannot fail.
    levels = scope_levels(anchor, scope=scope, start=start, exclude=(Path(out).expanduser(),))
    for lvl in levels:
        dst = out / "levels" / lvl.relative_to(anchor)
        dst.mkdir(parents=True, exist_ok=True)
        shutil.copy2(lvl / LEVEL_FILE, dst / LEVEL_FILE)
    return entries, _write_manifest(out, anchor=anchor, scope=scope, start=start,
                                    entries=entries, levels=levels)
```

6. In `_manifest_shape_error`, replace lines 451-453

```python
    exclude = data.get("exclude", [])
    if not (isinstance(exclude, list) and all(isinstance(p, str) for p in exclude)):
        return "its 'exclude' is not a list of strings"
```

   with

```python
    for key in ("exclude", "levels"):
        value = data.get(key, [])
        if not (isinstance(value, list) and all(isinstance(p, str) for p in value)):
            return f"its '{key}' is not a list of strings"
```

- [ ] **Step 4: Run, expect PASS**

`cd <W> && TEST plugins/bitranox/skills/meta-dream-tree/tests/ plugins/bitranox/hooks/tests/test_uuid_store.py`
Expected: all pass (the store_manifest file alone: 50 passed).

- [ ] **Step 5: Open the release.** `cd <W> && git fetch origin`, then write
  `$SCRATCH/notes-p1a.md` with the Write tool:

```text
### Added

- `store_manifest.py backup` copies every in-scope level, pointers or not, and records them in
  the manifest's `levels` list.
```

  then `cd <W> && uv run plugins/bitranox/hooks/bump_version.py --part minor --changelog
  $SCRATCH/notes-p1a.md`. Expected: plugin.json, pyproject.toml and a new `## [11.1.0]` section
  (or the next minor above origin's version). Read `git diff --stat`: exactly those three files
  beside this task's.

- [ ] **Step 6: Commit.** Message file `$SCRATCH/msg-t1.txt`:

```text
store_manifest: back up every in-scope level and record the list

backup copied only the levels holding a pointer, so a level whose block was empty
had no copy, and nothing recorded which levels existed. It now copies every level
the scope covers and writes them to the manifest's `levels` key; verify refuses a
manifest whose `levels` is not a list of strings. scope_levels is the one
definition derive and backup share. uuid_store gains a public pointer_region.

Opens the next minor release's changelog section.
```

  `cd <W> && git commit -F $SCRATCH/msg-t1.txt -- plugins/bitranox/hooks/uuid_store.py plugins/bitranox/skills/meta-dream-tree/store_manifest.py plugins/bitranox/skills/meta-dream-tree/tests/test_store_manifest.py plugins/bitranox/.claude-plugin/plugin.json pyproject.toml CHANGELOG.md`

### Task 2: M1b - verify prints the cost of every level's pointer block

**Files:**
- Modify: `plugins/bitranox/skills/meta-dream-tree/store_manifest.py` (`__all__`; new section
  before `# ---- CLI` at line 492 as it stands after Task 1; the `verify` branch of `main`, lines
  552-562 before Task 1)
- Modify: `CHANGELOG.md` (one bullet under the new version's `### Added`)
- Test: `plugins/bitranox/skills/meta-dream-tree/tests/test_store_manifest.py` (append)

**Interfaces:**
- Produces: `LevelCost` (frozen dataclass: `level: str`, `bytes_before: int | None`,
  `bytes_after: int`, `pointers_before: int`, `pointers_after: int`, `arrived: tuple[str, ...]`,
  `left: tuple[str, ...]`, property `changed: bool`, `as_dict() -> dict`);
  `block_bytes(text: str) -> int`; `cost_report(out: Path) -> tuple[list[LevelCost], list[str]]`;
  `verify --json` gains `data.levels` (list of `LevelCost.as_dict()`), and `skipped` gains one line
  when bytes before are unknown. Text output gains the `pointer blocks` lines.
- Consumes: `scope_levels`, `load_manifest`, `parse_level`, `read_level_text`, `Unreadable`,
  `uuid_store.pointer_region` (Task 1).

**Out of scope:** exit codes (0 identical, 1 differs, 2 refused) stay exactly as they are; the
cost lines never change them.

**STOP if:** any existing `test_store_manifest.py` test needs an edit to pass (the change is
additive; an existing failure means the text output was broken).

- [ ] **Step 1: Write the failing tests** - append:

```python


def cost_rows(stdout: str) -> dict[str, dict]:
    return {row["level"]: row for row in json.loads(stdout)["data"]["levels"]}


def test_a_merge_lift_arrives_at_the_top_and_leaves_both_siblings(tmp_path):
    """Two sibling copies of one slug merged into one top copy is an add plus two removes to the
    diff; the cost report must show it as state: ARRIVED at the top, LEFT at each sibling."""
    sib_a, sib_b = make_siblings(tmp_path)
    out = outside(tmp_path)
    assert run_cli(["backup", "--from", str(tmp_path), "--out", str(out)], tmp_path).returncode == 0
    (tmp_path / "CLAUDE.local.md").write_text(
        "# Memory index\n- [Shared](mem:shared) - When shared, do shared.\n", encoding="utf-8")
    sib_a.joinpath("CLAUDE.local.md").write_text(
        "# Memory index\n- [Own](mem:own-a) - When own, do own.\n", encoding="utf-8")
    sib_b.joinpath("CLAUDE.local.md").write_text("# Memory index\n", encoding="utf-8")
    r = run_cli(["verify", "--out", str(out), "--json"], tmp_path)
    assert r.returncode == 1, r.stdout + r.stderr
    rows = cost_rows(r.stdout)
    top, a, b = rows[str(tmp_path)], rows[str(sib_a)], rows[str(sib_b)]
    assert (top["arrived"], top["left"]) == (["shared"], [])
    assert (top["pointers_before"], top["pointers_after"]) == (0, 1)
    assert top["bytes_after"] > top["bytes_before"]
    assert (a["arrived"], a["left"], a["pointers_after"]) == ([], ["shared"], 1)
    assert (b["arrived"], b["left"], b["pointers_after"]) == ([], ["shared"], 0)
    assert b["bytes_after"] < b["bytes_before"]


def test_the_levels_are_listed_top_first(tmp_path):
    make_siblings(tmp_path)
    out = outside(tmp_path)
    assert run_cli(["backup", "--from", str(tmp_path), "--out", str(out)], tmp_path).returncode == 0
    r = run_cli(["verify", "--out", str(out), "--json"], tmp_path)
    levels = [row["level"] for row in json.loads(r.stdout)["data"]["levels"]]
    assert levels[0] == str(tmp_path)
    assert sorted(levels[1:]) == levels[1:] and len(levels) == 3


def test_an_unchanged_level_is_omitted_from_the_text_but_kept_in_the_json(tmp_path):
    sib_a, sib_b = make_siblings(tmp_path)
    out = outside(tmp_path)
    assert run_cli(["backup", "--from", str(tmp_path), "--out", str(out)], tmp_path).returncode == 0
    sib_b.joinpath("CLAUDE.local.md").write_text("# Memory index\n", encoding="utf-8")
    text = run_cli(["verify", "--out", str(out)], tmp_path).stdout
    cost_lines = [ln for ln in text.splitlines() if "  bytes " in ln]
    assert len(cost_lines) == 1 and cost_lines[0].lstrip().startswith(str(sib_b))
    assert str(sib_a) in cost_rows(run_cli(["verify", "--out", str(out), "--json"],
                                           tmp_path).stdout)


def test_an_untouched_tree_reports_no_changed_level_and_still_exits_0(tmp_path):
    make_siblings(tmp_path)
    out = outside(tmp_path)
    assert run_cli(["backup", "--from", str(tmp_path), "--out", str(out)], tmp_path).returncode == 0
    r = run_cli(["verify", "--out", str(out)], tmp_path)
    assert r.returncode == 0
    assert r.stdout.startswith("IDENTICAL") and "pointer blocks: no level changed" in r.stdout


def test_a_backup_without_level_copies_reports_skipped_never_zero_bytes(tmp_path):
    """A backup whose levels/ copies are gone (or that never had them) cannot know the bytes
    before. A 0 there would read as a block that grew from nothing."""
    make_siblings(tmp_path)
    out = outside(tmp_path)
    assert run_cli(["backup", "--from", str(tmp_path), "--out", str(out)], tmp_path).returncode == 0
    shutil.rmtree(out / "levels")
    r = run_cli(["verify", "--out", str(out), "--json"], tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr     # the exit code still answers "differs?"
    env = json.loads(r.stdout)
    assert all(row["bytes_before"] is None for row in env["data"]["levels"])
    assert [row["pointers_before"] for row in env["data"]["levels"]] == [0, 2, 1]
    assert any("block bytes before not known for 3 level(s)" in s for s in env["skipped"])
    text = run_cli(["verify", "--out", str(out)], tmp_path).stdout
    assert "block bytes before not known" in text


def test_a_manifest_without_a_levels_list_cannot_prove_a_new_level_was_absent(tmp_path):
    """A manifest written before the `levels` list existed knows only the levels it saw pointers
    at; a level that has pointers now may have existed then with an empty block."""
    make_siblings(tmp_path)
    out = outside(tmp_path)
    assert run_cli(["backup", "--from", str(tmp_path), "--out", str(out)], tmp_path).returncode == 0
    manifest = out / "manifest.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    del data["levels"]
    manifest.write_text(json.dumps(data), encoding="utf-8")
    new = tmp_path / "c"
    new.mkdir()
    (new / "CLAUDE.local.md").write_text("# Memory index\n- [N](mem:n-slug) - When n, do n.\n",
                                         encoding="utf-8")
    env = json.loads(run_cli(["verify", "--out", str(out), "--json"], tmp_path).stdout)
    row = {r["level"]: r for r in env["data"]["levels"]}[str(new)]
    assert row["bytes_before"] is None and row["arrived"] == ["n-slug"]
    assert any(str(new) in s for s in env["skipped"])


def test_a_level_created_after_a_backup_with_a_levels_list_starts_from_zero(tmp_path):
    """The recorded `levels` list proves the level did not exist, so 0 bytes before is a fact."""
    make_siblings(tmp_path)
    out = outside(tmp_path)
    assert run_cli(["backup", "--from", str(tmp_path), "--out", str(out)], tmp_path).returncode == 0
    new = tmp_path / "c"
    new.mkdir()
    (new / "CLAUDE.local.md").write_text("# Memory index\n- [N](mem:n-slug) - When n, do n.\n",
                                         encoding="utf-8")
    env = json.loads(run_cli(["verify", "--out", str(out), "--json"], tmp_path).stdout)
    row = {r["level"]: r for r in env["data"]["levels"]}[str(new)]
    assert row["bytes_before"] == 0 and row["bytes_after"] > 0
    assert env["skipped"] == []


def test_block_bytes_counts_the_managed_block_only():
    block = ("<!-- BITRANOX-MEMORY-INDEX:BEGIN managed by bitranox self-improve; do not hand-edit."
             " -->\n# Memory index\n<!-- BITRANOX-MEMORY-INDEX:END -->")
    assert SM.block_bytes("hand-written prose\n\n" + block + "\n\nmore prose\n") == len(block)
    assert SM.block_bytes("# Memory index\n") == len("# Memory index\n")   # no fences: whole text
```

  Before running, confirm the two fence strings in the last test equal `uuid_store.INDEX_BEGIN` and
  `uuid_store.INDEX_END` (`python3 -c` printing both); if they differ, build the block from those
  constants instead of literals.

- [ ] **Step 2: Run, expect FAIL**

`cd <W> && TEST plugins/bitranox/skills/meta-dream-tree/tests/test_store_manifest.py`
Expected: 8 failed - `KeyError: 'levels'` (the JSON tests: `data` has no `levels`), the text test
`assert (0 == 1)` on `len([])`, `'pointer blocks: no level changed' in 'IDENTICAL: ...'` false,
and `AttributeError: module 'store_manifest' has no attribute 'block_bytes'`.

- [ ] **Step 3: Implement.** `__all__` becomes the full list:

```python
__all__ = ["Entry", "Diff", "LevelCost", "NoAnchor", "Unreadable", "block_bytes", "cost_report",
           "derive", "diff", "manifest_key", "scope_levels", "main"]
```

  Insert directly before the `# ---- CLI ----` comment line:

```python
# ---- the cost report: what each level's always-loaded block weighs, before and after -----------

@dataclass(frozen=True)
class LevelCost:
    """One level's pointer block before the run and now. `bytes_before` is None when the backup
    holds no readable copy of the level, so an unknown is never printed as a zero."""

    level: str
    bytes_before: int | None
    bytes_after: int
    pointers_before: int
    pointers_after: int
    arrived: tuple[str, ...] = ()
    left: tuple[str, ...] = ()

    @property
    def changed(self) -> bool:
        return (self.bytes_before != self.bytes_after
                or self.pointers_before != self.pointers_after or bool(self.arrived or self.left))

    def as_dict(self) -> dict:
        return {"level": self.level, "bytes_before": self.bytes_before,
                "bytes_after": self.bytes_after, "pointers_before": self.pointers_before,
                "pointers_after": self.pointers_after, "arrived": list(self.arrived),
                "left": list(self.left)}


def block_bytes(text: str) -> int:
    """UTF-8 bytes of the pointer block as the engine bounds it (the managed fences when present,
    else the whole text). PURE. Prose around the block is not counted: the cost this reports is
    the index a dream changes, not hand-written text beside it."""
    return len(uuid_store.pointer_region(text).encode("utf-8"))


def _copy_text(out: Path, anchor: Path, level: str) -> str | None:
    """The backup's copy of one level, or None when it is missing or cannot be read."""
    try:
        rel = Path(level).relative_to(anchor)
        return (Path(out) / "levels" / rel / LEVEL_FILE).read_text(encoding="utf-8-sig")
    except (ValueError, OSError, UnicodeDecodeError):
        return None


def _live_texts(anchor: Path, data: dict) -> dict[str, str]:
    """Every in-scope live level's text, read with the manifest's own scope. Raises Unreadable."""
    unreadable: list[str] = []
    levels = scope_levels(anchor, scope=data.get("scope", "tree"),
                          start=Path(data.get("start", str(anchor))),
                          exclude=tuple(Path(p) for p in data.get("exclude", [])),
                          unreadable=unreadable)
    texts: dict[str, str] = {}
    for lvl in levels:
        text = read_level_text(lvl / LEVEL_FILE, unreadable)
        if text is not None:
            texts[str(lvl)] = text
    if unreadable:
        raise Unreadable(sorted(unreadable))
    return texts


def _depth_key(level: str) -> tuple[int, str]:
    return (len(Path(level).parts), level)


def cost_report(out: Path) -> tuple[list[LevelCost], list[str]]:
    """Per-level block state, backup copy against the live file, top first; plus `skipped` lines.

    State, not move events: a lift that merges two sibling copies into one top copy is an add and
    two removes to the diff, while here it is one slug ARRIVED at the top and LEFT at both
    siblings. Pointer counts and slugs before come from the manifest entries, which every manifest
    has; only the bytes need the level copy. A level with no readable copy reports
    `bytes_before` None and is named in `skipped`. A level absent from a manifest's recorded
    `levels` list did not exist at backup time, so its bytes before are a true 0; a manifest
    written before that list existed cannot prove it, so there it is None too."""
    data = load_manifest(out)
    anchor = Path(data["anchor"])
    slugs_before: dict[str, set[str]] = {}
    for e in data["entries"]:
        slugs_before.setdefault(e["level"], set()).add(e["slug"])
    recorded = data.get("levels")
    copied = set(recorded) if recorded is not None else set(slugs_before)
    live = _live_texts(anchor, data)
    costs: list[LevelCost] = []
    unknown: list[str] = []
    for level in sorted(copied | set(slugs_before) | set(live), key=_depth_key):
        if level in copied:
            text = _copy_text(out, anchor, level)
            before_bytes = None if text is None else block_bytes(text)
        else:
            before_bytes = 0 if recorded is not None else None
        if before_bytes is None:
            unknown.append(level)
        after_text = live.get(level, "")
        after = {e.slug for e in parse_level(after_text, level)}
        before = slugs_before.get(level, set())
        costs.append(LevelCost(level=level, bytes_before=before_bytes,
                               bytes_after=block_bytes(after_text) if level in live else 0,
                               pointers_before=len(before), pointers_after=len(after),
                               arrived=tuple(sorted(after - before)),
                               left=tuple(sorted(before - after))))
    skipped = [] if not unknown else [
        f"block bytes before not known for {len(unknown)} level(s): the backup holds no readable "
        "copy of them, so their bytes_before is null rather than 0: " + "; ".join(unknown)]
    return costs, skipped


def _render_costs(costs: list[LevelCost]) -> str:
    changed = [c for c in costs if c.changed]
    if not changed:
        return "pointer blocks: no level changed"
    lines = ["pointer blocks (changed levels, top first):"]
    for c in changed:
        before = "?" if c.bytes_before is None else str(c.bytes_before)
        delta = "" if c.bytes_before is None else f" ({c.bytes_after - c.bytes_before:+d})"
        lines.append(f"  {c.level}  bytes {before} -> {c.bytes_after}{delta}  pointers "
                     f"{c.pointers_before} -> {c.pointers_after}  arrived {len(c.arrived)}  "
                     f"left {len(c.left)}")
    return "\n".join(lines)


```

  In `main`, the `verify` branch: replace

```python
        out = Path(args.out).expanduser()
        d = verify(out)
        compared = content_compared(load_manifest(out))
        skipped = [] if compared else [
            "hooks and bodies not compared: the manifest predates their digests, so only level, "
            "slug, title and pin were checked"]
        data = dict(d.as_dict(), content_compared=compared)
        text = _render_diff(d) + ("" if compared else "\n(" + skipped[0] + ")")
```

  with

```python
        out = Path(args.out).expanduser()
        d = verify(out)
        compared = content_compared(load_manifest(out))
        costs, cost_skipped = cost_report(out)
        skipped = [] if compared else [
            "hooks and bodies not compared: the manifest predates their digests, so only level, "
            "slug, title and pin were checked"]
        data = dict(d.as_dict(), content_compared=compared,
                    levels=[c.as_dict() for c in costs])
        text = (_render_diff(d) + ("" if compared else "\n(" + skipped[0] + ")")
                + "\n" + _render_costs(costs)
                + "".join("\n(" + line + ")" for line in cost_skipped))
        skipped += cost_skipped
```

  leaving every line after it (the envelope print and `return 0 if d.identical else 1`) as it is.
  Read the module's existing imports first: `dataclass`, `parse_level` and `read_level_text` must
  already be imported (they were in the prototype); add any that are not.

- [ ] **Step 4: Run, expect PASS.** `cd <W> && TEST plugins/bitranox/skills/meta-dream-tree/tests/`
  Expected: all pass (store_manifest file: 58 passed). Then the mutation check with the toolbox
  jig `mutation_arm.py` (bitranox:compuse-toolbox): arm 1 changes `sorted(after - before)` to
  `sorted(before - after)` in `cost_report`, arm 2 changes `0 if recorded is not None else None`
  to `0`; each must turn at least one of the new tests RED, and the jig restores the file.

- [ ] **Step 5: CHANGELOG.** Add under the new version's `### Added`:

```text
- `store_manifest.py verify` reports the cost of every level's always-loaded pointer block:
  bytes and pointer count before and after, and the slugs that arrived and left, one line per
  changed level, top first (`data.levels[]` under `--json`). A level the backup holds no copy of
  reports its bytes before as unknown, never as 0. The exit codes are unchanged.
```

- [ ] **Step 6: Commit.** `$SCRATCH/msg-t2.txt`:

```text
store_manifest verify: report the cost of each level's pointer block

verify diffed facts, which cannot show where the always-loaded cost moved: a lift
that merges two sibling copies into one top copy is an add and two removes. It now
also compares each level's block, backup copy against the live file, and prints
one line per changed level with bytes and pointers before and after and the slugs
that arrived and left, top first; --json carries every level in data.levels.
Unknown bytes before are null and named in skipped. Exit codes are unchanged.
```

  `cd <W> && git commit -F $SCRATCH/msg-t2.txt -- plugins/bitranox/skills/meta-dream-tree/store_manifest.py plugins/bitranox/skills/meta-dream-tree/tests/test_store_manifest.py CHANGELOG.md`

### Task 3: M3a - the large-index warning stops recommending a lift

**Files:**
- Modify: `plugins/bitranox/skills/meta-self-improve/reconcile_memory_index.py` (docstring lines
  273-277, warning lines 1162-1164)
- Modify: `CHANGELOG.md` (`### Changed`)
- Test: `plugins/bitranox/skills/meta-self-improve/tests/test_reconcile_memory_index.py` (append
  after line 877)

**Interfaces:** none new; the warning line's text changes, its count (`warnings += 1`) and the exit
code do not.

**Out of scope:** the 50,000-byte threshold `_WARN_BYTES`; any other reconcile output.

**STOP if:** a test anywhere asserts the old phrase (`grep -rn "lift/dedup" plugins/` finds more
than the two source lines).

- [ ] **Step 1: Write the failing test** - append:

```python


def test_the_large_index_warning_never_recommends_lifting_facts(proj, capsys):
    """A lift moves a fact to a level more sessions load, so a size warning that recommends one
    grows the always-loaded cost it is warning about."""
    local = ME.sig.claude_local_md_path(proj)
    lines = "\n".join("- [T%d](uuid:0000000%d-0000-5000-8000-000000000000) - a hook <!-- bx:slug=t%d -->"
                      % (i, i % 10, i) for i in range(3000))
    local.write_text("%s\n# Memory index\n\n%s\n%s\n" % (us.INDEX_BEGIN, lines, us.INDEX_END),
                     encoding="utf-8")
    assert R.main(["--check", proj]) == 0
    warning = [ln for ln in capsys.readouterr().out.splitlines() if "~ warning:" in ln]
    assert len(warning) == 1
    assert "lift/" not in warning[0] and "promote" not in warning[0]
    assert "fold near-duplicates, trim long hooks" in warning[0]
```

- [ ] **Step 2: Run, expect FAIL.**
  `cd <W> && TEST plugins/bitranox/skills/meta-self-improve/tests/test_reconcile_memory_index.py -k lifting`
  Expected: 1 failed, `'lift/' is contained here: the dream lift/dedup/promote, else it loads only
  for this project`.

- [ ] **Step 3: Implement.** Docstring of `over_cap`, replace
  `block grows large; the remedy is to let the dream lift/dedup/promote. Bodies are central (not in
  the block), so only the pointer lines count toward the always-loaded budget."""` with:

```python
    block grows large; the remedy is to shrink the block where it is (fold near-duplicates, trim
    long hooks), never to lift its facts to a broader level, which loads them in more sessions.
    Bodies are central (not in the block), so only the pointer lines count toward the always-loaded
    budget."""
```

  and the print, replace the line
  `"index; let the dream lift/dedup/promote, else it loads only for this project"` with:

```python
                          "index; shrink it in place (fold near-duplicates, trim long hooks) - lifting "
                          "a fact to a broader level loads it in more sessions, not fewer"
```

- [ ] **Step 4: Run, expect PASS.** `cd <W> && TEST plugins/bitranox/skills/meta-self-improve/tests/test_reconcile_memory_index.py`
  Expected: all pass (78 passed in the prototype).

- [ ] **Step 5: CHANGELOG** under `### Changed`:

```text
- `reconcile_memory_index.py --check`: the large-index warning says to shrink the block in
  place (fold near-duplicates, trim long hooks) and no longer recommends lifting facts to a
  broader level, which loads them in more sessions.
```

- [ ] **Step 6: Commit.** `$SCRATCH/msg-t3.txt`:

```text
reconcile: the large-index warning no longer recommends a lift

The warning told the reader to let the dream lift/dedup/promote, and a lift moves a
fact to a level more sessions load, which grows the cost being warned about. It now
says to shrink the block in place.
```

  `cd <W> && git commit -F $SCRATCH/msg-t3.txt -- plugins/bitranox/skills/meta-self-improve/reconcile_memory_index.py plugins/bitranox/skills/meta-self-improve/tests/test_reconcile_memory_index.py CHANGELOG.md`

### Task 4: M4a - every engine write keeps the title in the body's frontmatter

**Files:**
- Modify: `plugins/bitranox/hooks/memory_engine.py` (insert `_body_title`, `_with_title` before
  `_retype_body` at line 667; one statement before `bodies[slug] = e.body` at line 465 in
  `upsert_entry`; `retitle_entry` docstring lines 1609-1611 and one statement after line 1653)
- Modify: `plugins/bitranox/skills/meta-self-improve/migrate_memory.py` (line 272 in
  `_is_own_placement`)
- Modify: `plugins/bitranox/hooks/tests/test_memory_engine_retitle.py` (module docstring line 10;
  test at lines 71-79; lines 258 and 268)
- Modify: `plugins/bitranox/skills/meta-dream-tree/tests/test_factedit.py` (`make_tree` body,
  line 120)
- Create: `plugins/bitranox/hooks/tests/test_memory_engine_title_field.py`
- Test: also append to `plugins/bitranox/skills/meta-dream-tree/tests/test_factedit_round_trip.py`
  (after line 209)

**Interfaces:**
- Produces: `memory_engine._body_title(text: str) -> str`;
  `memory_engine._with_title(text: str, title: str) -> str`. A framed body now reads
  `---\nname: <slug>\ndescription: <hook>\ntitle: <title>\nmetadata:\n  type: <t>\n---\n\n<prose>`.
- Consumes: `_frontmatter`, `_with_frame`, `_normalised_title`, `us.put_body` (existing).

**Out of scope:** the pointer line (unchanged); `move_entry` and `relocate_entry` (they never
touch bodies); `factedit.py` (it writes through the engine's `add`/`amend-pinned`, so it is
covered without a change - the round-trip test proves it); the back-fill (Task 5).

**STOP if:** any test outside the three named test files fails after Step 3 (that is a consumer
that rebuilds the engine's frame itself, as `migrate_memory._is_own_placement` did - find it with
`grep -rn "_framed_body" plugins/` and report it before patching it).

- [ ] **Step 1: Write the failing tests.** Create `test_memory_engine_title_field.py`:

```python
"""Tests for the body frontmatter `title:` - a fact's title kept as data beside its pointer line.

The title lives in the always-loaded pointer line `- [Title](mem:slug) - hook`, and otherwise
nowhere. Kept in the body's frontmatter as well, a pointer line can be rebuilt from the body
alone: every write through the engine copies the title there and keeps it equal to the pointer,
and `heal --backfill-titles` fills it into bodies written before. Pointer lines are unchanged by
all of this. All content ASCII.
"""

from pathlib import Path

import pytest

import memory_engine as E
import uuid_store as us


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch):
    h = tmp_path / "home"
    h.mkdir(exist_ok=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    return h


def _tree(tmp_path):
    """anchor -> proj, each a CLAUDE.md-bearing rung; central store at the anchor."""
    anchor = tmp_path / "tree"
    proj = anchor / "proj"
    proj.mkdir(parents=True)
    for d in (anchor, proj):
        (d / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (anchor / us.STORE_DIRNAME).mkdir()
    return str(anchor), str(proj)


def _body(anchor, slug):
    return us.body_path(anchor, slug).read_text(encoding="utf-8")


def _pointer_title(level, slug):
    text = (Path(level) / "CLAUDE.local.md").read_text(encoding="utf-8")
    return next(p.title for p in us.parse_pointer_index(text)[1] if p.slug == slug)


# ---- every write keeps the body's title equal to the pointer's ------------------------------

def test_add_writes_the_title_into_the_frontmatter_after_the_description(tmp_path):
    anchor, proj = _tree(tmp_path)
    slug = E.add_or_update_entry(proj, "Use the jig", "When counting, use the jig.", body="B")
    body = _body(anchor, slug)
    assert body.startswith("---\nname: %s\ndescription: When counting, use the jig.\n"
                           "title: Use the jig\nmetadata:\n" % slug), body
    assert _pointer_title(proj, slug) == "Use the jig"


def test_an_update_with_a_new_title_rewrites_the_body_title(tmp_path):
    anchor, proj = _tree(tmp_path)
    slug = E.add_or_update_entry(proj, "Old title", "When x, do y.", body="B")
    E.add_or_update_entry(proj, "New title", "When x, do y.", slug=slug)
    assert E._body_title(_body(anchor, slug)) == "New title"


def test_an_amend_that_passes_no_title_keeps_it(tmp_path, capsys):
    anchor, proj = _tree(tmp_path)
    slug = E.add_or_update_entry(proj, "Iron rule", "When x, do y.", body="B", pin=True)
    assert E.main(["amend-pinned", "--proj", proj, "--slug", slug, "--hook", "When x, do z."]) == 0
    capsys.readouterr()
    assert E._body_title(_body(anchor, slug)) == "Iron rule"


def test_a_body_handed_back_with_a_stale_title_takes_the_pointer_title(tmp_path):
    """A body read with `show --body` before a retitle carries the old `title:`; writing it back
    must not resurrect it, as the description already does not."""
    anchor, proj = _tree(tmp_path)
    slug = E.add_or_update_entry(proj, "Old title", "When x, do y.", body="B")
    stale = _body(anchor, slug)
    E.add_or_update_entry(proj, "New title", "When x, do y.", body=stale, slug=slug)
    assert E._body_title(_body(anchor, slug)) == "New title"


def test_a_title_with_a_backslash_and_a_colon_is_stored_literally(tmp_path):
    anchor, proj = _tree(tmp_path)
    slug = E.add_or_update_entry(proj, r"Paths: C:\temp\x", "When x, do y.", body="B",
                                 slug="paths-fact")
    assert E._body_title(_body(anchor, slug)) == r"Paths: C:\temp\x"


def test_a_retitle_changes_the_body_title_and_nothing_else_in_the_body(tmp_path):
    anchor, proj = _tree(tmp_path)
    slug = E.add_or_update_entry(proj, "Stale title", "When x, do y.", body="the body")
    before = _body(anchor, slug)
    assert E.retitle_entry(proj, slug, "Accurate title")["retitled"] is True
    after = _body(anchor, slug)
    assert E._body_title(after) == "Accurate title"
    assert after == before.replace("title: Stale title", "title: Accurate title")


def test_a_move_leaves_the_body_and_its_title_byte_identical(tmp_path):
    anchor, proj = _tree(tmp_path)
    slug = E.add_or_update_entry(proj, "Moving fact", "When x, do y.", body="B")
    before = us.body_path(anchor, slug).read_bytes()
    assert E.move_entry(proj, anchor, slug)["moved"] is True
    assert us.body_path(anchor, slug).read_bytes() == before
    assert E._body_title(before.decode("utf-8")) == "Moving fact"


def test_the_pointer_line_is_unchanged_by_the_title_field(tmp_path):
    anchor, proj = _tree(tmp_path)
    slug = E.add_or_update_entry(proj, "Use the jig", "When counting, use the jig.", body="B")
    text = (Path(proj) / "CLAUDE.local.md").read_text(encoding="utf-8")
    assert "- [Use the jig](mem:%s) - When counting, use the jig.\n" % slug in text
```

  (Task 5 appends the back-fill tests to this file and adds the `import os` they need.)

  Append to `test_factedit_round_trip.py`:

```python


def test_apply_writes_the_pointer_title_into_a_body_that_predates_titles(tmp_path):
    """A body stored before titles were kept as data gains `title:` on its next apply, taken from
    the pointer: factedit re-sends the stored title, and the engine's write path copies it."""
    level = make_tree(tmp_path)
    body = _body_file(level)
    body.write_text(body.read_text(encoding="utf-8").replace("title: A Title\n", ""),
                    encoding="utf-8")
    f = tmp_path / "body.md"
    f.write_text("The body prose, extended.\n", encoding="utf-8")
    r = _real(["apply", "--slug", "feedback-demo", "--from", str(level), "--body-file", str(f)],
              tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "\ntitle: A Title\n" in body.read_text(encoding="utf-8")
```

  In `test_factedit.py` `make_tree`, after the line
  `        "description: When something happens, do the thing.\n"` (line 120) insert
  `        "title: A Title\n"` - the fixture body now looks like what the engine writes, which keeps
  `test_show_body_then_apply_body_file_leaves_the_stored_body_byte_identical` meaningful. Confirm
  first that the fixture's pointer title is `A Title` (read `make_tree`); use the title it really
  writes.

  In `test_memory_engine_retitle.py`:
  - module docstring line 10: replace `The body must come back byte-identical, which is` and the
    rest of that sentence with `The body changes in its `title:` line only, which is the promise
    the `add` workaround could not make.` (rewrap to the docstring's width);
  - replace `test_the_body_file_is_byte_identical_after_a_retitle` (lines 71-79) with:

```python
def test_a_retitle_changes_only_the_title_line_of_the_body(tmp_path):
    """The invariant the `add` workaround cannot promise: a title fix touches nothing in the body
    but the `title:` line that carries the title as data."""
    anchor, _mid, proj = _three_levels(tmp_path)
    E.add_or_update_entry(proj, "Stale title", "When testing, do the thing.", body="the body")
    before = us.body_path(anchor, "stale-title").read_text(encoding="utf-8")

    E.retitle_entry(proj, "stale-title", "Accurate title")

    assert us.body_path(anchor, "stale-title").read_text(encoding="utf-8") == before.replace(
        "title: Stale title", "title: Accurate title")
```

  - line 258: `before = us.body_path(anchor, slug).read_bytes()` becomes
    `before = us.body_path(anchor, slug).read_text(encoding="utf-8")`;
  - line 268: `assert us.body_path(anchor, slug).read_bytes() == before` becomes

```python
    assert us.body_path(anchor, slug).read_text(encoding="utf-8") == before.replace(
        "title: Stale iron rule", "title: Accurate iron rule")
```

- [ ] **Step 2: Run, expect FAIL.**
  `cd <W> && TEST plugins/bitranox/hooks/tests/test_memory_engine_title_field.py plugins/bitranox/hooks/tests/test_memory_engine_retitle.py plugins/bitranox/skills/meta-dream-tree/tests/test_factedit_round_trip.py`
  Expected: 8 failed - the add test (`assert False` on `startswith(... title: Use the jig ...)`),
  every title-field test that calls `_body_title` with `AttributeError: module 'memory_engine' has
  no attribute '_body_title'` (six, the move test included: it reaches that call only after the
  move left the body byte-identical), and the round-trip test (`'\ntitle: A Title\n' in
  '---\nname: feedback-demo\n...'` is false). The pointer-line test passes: it pins what must NOT
  change. The two rewritten tests in
  `test_memory_engine_retitle.py` also pass here, vacuously: the old body has no `title:` line, so
  `.replace` changes nothing and the old engine leaves the body alone. That is why the title-field
  retitle test asserts `_body_title(after)` as well; the retitle-file tests start to bite once
  the engine writes the line.

- [ ] **Step 3: Implement.** In `memory_engine.py`, insert before `def _retype_body(`:

```python
def _body_title(text):
    """The `title:` value from a framed body's frontmatter, or '' if absent. Scoped to the leading
    frontmatter block (see `_frontmatter`), like `_body_description`."""
    _head, m = _frontmatter(text)
    if m is None:
        return ""
    t = re.search(r"(?m)^title:[ \t]*([^\r\n]*)", m.group(1))
    return t.group(1).strip() if t else ""


def _with_title(text, title):
    """Return framed `text` with its frontmatter `title:` set to `title` (one line), prose untouched.

    The pointer line is the title's only other home, so the title is kept in the body as data and a
    pointer line can be rebuilt from the body alone. A frame without the key gains it after
    `description:` (or after `name:` when there is no description). An unframed `text`, or an empty
    title, is returned unchanged: every write path frames first, and a title is never invented.
    The replacement is a lambda, as in `_reframe_description`: a title can carry backslashes."""
    head, m = _frontmatter(text)
    title = _normalised_title(title)
    if m is None or not title:
        return text
    inner = m.group(1)
    nl = "\r\n" if inner.endswith("\r\n") else "\n"
    new_inner, n = re.subn(r"(?m)^(title:)[ \t]*[^\r\n]*", lambda t: "%s %s" % (t.group(1), title),
                           inner, count=1)
    for key in ("description", "name"):
        if n:
            break
        new_inner, n = re.subn(r"(?m)^(%s:[^\r\n]*)(?=\r?$)" % key,
                               lambda t: "%s%stitle: %s" % (t.group(1), nl, title), inner, count=1)
    return _with_frame(head, m, new_inner) if n else text


```

  In `upsert_entry`, directly before `        bodies[slug] = e.body` (line 465):

```python
        # The body carries the pointer's title as data (`title:`); every write through here,
        # amend-pinned and factedit's apply included, keeps the two equal.
        e.body = _with_title(e.body, e.title)
```

  In `retitle_entry`'s docstring, replace the three lines starting
  `    Same slug, same body, same hook: only the label changes. The body is not opened at all - a title`
  with:

```python
    Same slug, same hook, same prose: only the label changes - in the pointer line and in the
    body's frontmatter `title:`, which carries it as data. A body with no frame is left as it is.
```

  and directly after `    rep["levels"].append(str(lvl))` (line 1653) add:

```python
    us.put_body(str(anchor), slug, _with_title(entry.body, title))
```

  Read `retitle_entry` first: `anchor` and `entry` must be the names in scope at that line (they
  were in the prototype); if the function names them differently, use its names.

  In `migrate_memory.py`, `_is_own_placement`, replace line 272 with:

```python
    # The engine's frame plus the `title:` its write path adds: what upsert really stores.
    framed = ME._framed_body(slug, hook, entry["type"], entry["body"])  # noqa: SLF001 - the engine's frame
    written = ME._with_title(framed, entry["title"])  # noqa: SLF001 - the engine's title field
```

  Confirm `entry` carries a `"title"` key there (read the function's callers in the same module);
  if it does not, STOP and report.

- [ ] **Step 4: Run, expect PASS.**
  `cd <W> && TEST plugins/bitranox/hooks/tests/ plugins/bitranox/skills/meta-dream-tree/tests/ plugins/bitranox/skills/meta-self-improve/tests/`
  Expected: all pass. In particular
  `test_migrate_memory.py::test_a_resumed_run_reuses_its_own_placement_and_places_no_duplicate`
  (it fails if the migrate fix is missing: a resumed run places `notes-3`). Then
  `mutation_arm.py` arm: delete the `e.body = _with_title(...)` line; the add, update, amend and
  round-trip tests must go RED.

- [ ] **Step 5: CHANGELOG** under `### Added`:

```text
- A fact's body frontmatter carries its title (`title:`, after `description:`), written by
  `add` and kept equal to the pointer's title by every engine write: `amend-pinned`, `retitle`
  and `factedit.py apply` included. Pointer lines are unchanged.
```

- [ ] **Step 6: Commit.** `$SCRATCH/msg-t4.txt`:

```text
memory_engine: keep each fact's title in its body frontmatter

A title existed only in the pointer line, so a pointer could not be rebuilt from
the store. upsert_entry now sets `title:` in the frame (after `description:`) on
every write, and retitle rewrites it beside the pointer; the pointer line is
unchanged. migrate_memory's own-placement check rebuilds the frame the engine
writes, so it adds the title too, or a resumed migration places a duplicate. Two
retitle tests asserted a byte-identical body and now assert that only the title
line changed; the factedit fixture body carries the line the engine writes.
```

  `cd <W> && git add plugins/bitranox/hooks/tests/test_memory_engine_title_field.py && git commit -F $SCRATCH/msg-t4.txt -- plugins/bitranox/hooks/memory_engine.py plugins/bitranox/skills/meta-self-improve/migrate_memory.py plugins/bitranox/hooks/tests/test_memory_engine_title_field.py plugins/bitranox/hooks/tests/test_memory_engine_retitle.py plugins/bitranox/skills/meta-dream-tree/tests/test_factedit.py plugins/bitranox/skills/meta-dream-tree/tests/test_factedit_round_trip.py CHANGELOG.md`

### Task 5: M4b - `heal --backfill-titles` fills titles into bodies written before

**Files:**
- Modify: `plugins/bitranox/hooks/memory_engine.py` (new `backfill_titles` before
  `_heal_one_level`; heal parser after line 1988; CLI handler before `if args.cmd == "heal":` at
  line 2163 - line numbers before Task 4's inserts, about +40 after them)
- Modify: `plugins/bitranox/hooks/tests/test_memory_engine_title_field.py` (append; add
  `import os`)
- Modify: `CHANGELOG.md`

**Interfaces:**
- Produces: `memory_engine.backfill_titles(proj: str) -> dict` returning
  `{"filled": list[str], "kept": int, "unframed": list[str], "missing": list[str]}`; CLI
  `memory_engine.py heal --proj D --backfill-titles`, printing
  `back-filled N title(s); M body(ies) already had one`, then `    ~ body has no frontmatter, left
  as it is: <slug>` and `    ! missing central body (not fabricated): <slug>` lines; exit 0, exit 2
  on a refusal (memory writes off) or an unreadable level/body (`TreeWalkError`, which `main`
  already maps to 2).
- Consumes: `curated_levels_under`, `read_store_text`, `us.parse_pointer_index`, `us.body_path`,
  `us.put_body`, `sig.memory_lock`, `sig.claude_local_md_path`, `sig.refuse_if_memory_writes_off`,
  `_anchor`, `_body_title`, `_with_title`.

**Out of scope:** plain `heal`, which SessionStart runs on every start and which must still never
open a body (the deviation from the MID wording "heal back-fills" is deliberate: a back-fill reads
every body of the tree; recorded as a user decision in the report).

**STOP if:** `curated_levels_under(anchor)` with no `unreadable` list does not raise
`TreeWalkError` on an unreadable level (read its docstring) - the back-fill must never report done
over a tree it could not fully read.

- [ ] **Step 1: Write the failing tests** - add `import os` to the imports and append:

```python


# ---- the back-fill: bodies written before titles were kept ---------------------------------

def _pre_title_fact(level, title, slug, extra=""):
    """A fact as every engine before this change left it: written through the engine, then its
    body reset to the frame those engines wrote, which has no `title:` (or `extra` in its place)."""
    E.add_or_update_entry(level, title, "When x, do y.", body="P.", slug=slug, type_="feedback")
    anchor = E._anchor(level)
    us.body_path(anchor, slug).write_text(
        "---\nname: %s\ndescription: When x, do y.\n%smetadata:\n  type: feedback\n---\n\nP.\n"
        % (slug, extra), encoding="utf-8")
    return us.body_path(anchor, slug)


def test_backfill_copies_the_pointer_title_into_a_body_without_one(tmp_path, capsys):
    anchor, proj = _tree(tmp_path)
    _pre_title_fact(proj, "Old fact title", "old-fact")
    assert E.main(["heal", "--proj", proj, "--backfill-titles"]) == 0
    assert "back-filled 1 title(s)" in capsys.readouterr().out
    assert E._body_title(_body(anchor, "old-fact")) == "Old fact title"
    assert _body(anchor, "old-fact").endswith("---\n\nP.\n")


def test_backfill_never_rewrites_a_body_that_already_has_a_title(tmp_path):
    anchor, proj = _tree(tmp_path)
    path = _pre_title_fact(proj, "A different pointer title", "kept-fact",
                           extra="title: Its own title\n")
    os.utime(path, (1_000_000, 1_000_000))
    before = path.read_bytes()
    rep = E.backfill_titles(proj)
    assert rep["filled"] == [] and rep["kept"] == 1
    assert path.read_bytes() == before and path.stat().st_mtime == 1_000_000


def test_backfill_covers_every_level_of_the_tree_not_only_the_chain(tmp_path):
    anchor, proj = _tree(tmp_path)
    sibling = Path(anchor) / "sibling"
    sibling.mkdir()
    (sibling / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    _pre_title_fact(str(sibling), "Sibling fact", "sib-fact")
    assert E.backfill_titles(proj)["filled"] == ["sib-fact"]


def test_backfill_leaves_an_unframed_body_and_reports_a_missing_one(tmp_path):
    anchor, proj = _tree(tmp_path)
    bare = _pre_title_fact(proj, "Bare", "bare")
    bare.write_text("just prose\n", encoding="utf-8")
    _pre_title_fact(proj, "Gone", "gone").unlink()
    rep = E.backfill_titles(proj)
    assert rep["unframed"] == ["bare"] and rep["missing"] == ["gone"]
    assert _body(anchor, "bare") == "just prose\n"


def test_plain_heal_still_never_opens_a_body(tmp_path):
    """SessionStart runs `heal` on every start; the back-fill must not ride along with it."""
    anchor, proj = _tree(tmp_path)
    path = _pre_title_fact(proj, "Old fact title", "old-fact")
    before = path.read_bytes()
    E.heal(proj)
    assert path.read_bytes() == before


def test_backfill_is_refused_under_memory_writes_off(tmp_path, monkeypatch, capsys):
    anchor, proj = _tree(tmp_path)
    _pre_title_fact(proj, "Old fact title", "old-fact")
    monkeypatch.setenv("BITRANOX_MEMORY_WRITES", "off")
    assert E.main(["heal", "--proj", proj, "--backfill-titles"]) == 2
    capsys.readouterr()
    assert E._body_title(_body(anchor, "old-fact")) == ""
```

  (`monkeypatch.setenv` here sets the process environment, the real external edge the engine
  reads; nothing in the module under test is patched.)

- [ ] **Step 2: Run, expect FAIL.**
  `cd <W> && TEST plugins/bitranox/hooks/tests/test_memory_engine_title_field.py`
  Expected: 6 failed - `SystemExit: 2` (argparse: unrecognized `--backfill-titles`) and
  `AttributeError: module 'memory_engine' has no attribute 'backfill_titles'`;
  `test_plain_heal_still_never_opens_a_body` passes (it pins the current behaviour).

- [ ] **Step 3: Implement.** Insert before `def _heal_one_level(`:

```python
def backfill_titles(proj):
    """Copy each pointer's title into its body's frontmatter where the body has none, across the
    WHOLE tree of `proj`'s anchor. A body that already has a `title:` is never rewritten, an
    unframed body is left alone and counted, and a missing body is counted, never fabricated.

    Separate from `heal`, which SessionStart runs on every start and which never opens a body: a
    back-fill reads every body of the tree and writes most of them once, a one-off for stores
    written before titles were kept as data. Returns {'filled': [slugs], 'kept': n, 'unframed':
    [slugs], 'missing': [slugs]}; a slug pointed at from two levels is filled from the first level
    the walk meets. Raises TreeWalkError (exit 2 on the CLI) when a level or a body cannot be read:
    a back-fill that skipped part of the tree would read as done."""
    sig.refuse_if_memory_writes_off()
    anchor = _anchor(proj)
    rep = {"filled": [], "kept": 0, "unframed": [], "missing": []}
    seen = set()
    for level in curated_levels_under(anchor):
        with sig.memory_lock(sig.claude_local_md_path(level)):
            text = read_store_text(sig.claude_local_md_path(level))
            for ptr in us.parse_pointer_index(text)[1]:
                if ptr.legacy or ptr.slug in seen:
                    continue
                seen.add(ptr.slug)
                path = us.body_path(anchor, ptr.slug)
                if not path.is_file():
                    rep["missing"].append(ptr.slug)
                    continue
                body = read_store_text(path).rstrip("\n")
                if _body_title(body):
                    rep["kept"] += 1
                    continue
                filled = _with_title(body, ptr.title)
                if filled == body:
                    rep["unframed"].append(ptr.slug)
                    continue
                us.put_body(str(anchor), ptr.slug, filled)
                rep["filled"].append(ptr.slug)
    return rep


```

  In `build_parser`, after the heal parser's `--proj` argument:

```python
    h.add_argument("--backfill-titles", action="store_true", dest="backfill_titles",
                   help="instead of healing the chain, copy each pointer's title into its body's "
                        "frontmatter where the body has none, across the WHOLE tree (a one-off for "
                        "stores written before titles were kept as data; reads every body)")
```

  In `main`, directly before `    if args.cmd == "heal":`:

```python
    if args.cmd == "heal" and args.backfill_titles:
        rep = backfill_titles(args.proj)
        print("back-filled %d title(s); %d body(ies) already had one"
              % (len(rep["filled"]), rep["kept"]))
        for slug in rep["unframed"]:
            print("    ~ body has no frontmatter, left as it is: %s" % slug)
        for slug in rep["missing"]:
            print("    ! missing central body (not fabricated): %s" % slug)
        return 0

```

  Confirm `put_body` writes with a trailing newline (the `endswith("---\n\nP.\n")` assertion
  depends on it; read `us.put_body`).

- [ ] **Step 4: Run, expect PASS.** `cd <W> && TEST plugins/bitranox/hooks/tests/ plugins/bitranox/skills/meta-self-improve/tests/`
  Expected: all pass (the title-field file: 14 passed).

- [ ] **Step 5: CHANGELOG** under `### Added`:

```text
- `memory_engine.py heal --backfill-titles` copies each pointer's title into its body's
  frontmatter where the body has none, across the whole tree; a body that has one is never
  rewritten. Plain `heal` still never opens a body.
```

- [ ] **Step 6: Commit.** `$SCRATCH/msg-t5.txt`:

```text
memory_engine heal: --backfill-titles for bodies written before titles

A one-off, tree-wide pass that copies each pointer's title into a body that has no
`title:`; a body that has one is left byte-identical, an unframed body is reported
and left, a missing body is reported, never fabricated. Plain heal, which
SessionStart runs, still never opens a body. An unreadable level or body exits 2.
```

  `cd <W> && git commit -F $SCRATCH/msg-t5.txt -- plugins/bitranox/hooks/memory_engine.py plugins/bitranox/hooks/tests/test_memory_engine_title_field.py CHANGELOG.md`

### Task 6: M4c - the backend reference documents the title field and the back-fill

**Files:**
- Modify: `plugins/bitranox/skills/meta-self-improve/references/memory-backend.md` (frame block
  lines 71-82; verb table rows at lines 185 and 190)
- Create: `plugins/bitranox/skills/meta-self-improve/.skillwriter/checklist-20261110-title-field.md`

**Interfaces:** documentation only. **Out of scope:** any other row of the verb table.

**STOP if:** `repo-gate.py --mirrors` lists `meta-self-improve` as a mirrored pair (then the twin
needs the same edit in the same change).

- [ ] **Step 1: Skill-writer start.** Invoke `bitranox:meta-skill-writer`; open the receipt; run
  `python3 <P>/hooks/skill_decisions.py show meta-self-improve --kind rejected,removed --full` and
  `python3 <P>/hooks/skill_decisions.py show meta-self-improve`; nothing there may forbid a frame
  key (if one does, STOP and report).
- [ ] **Step 2: RED (text).** `cd <W> && grep -c "title:" plugins/bitranox/skills/meta-self-improve/references/memory-backend.md`
  and `grep -c "backfill-titles" ...`: record both counts (expected: no `title:` inside the frame
  block, `backfill-titles` 0).
- [ ] **Step 3: Edit.** In the frame block, between `      description: <the hook>` and
  `      metadata:` insert `      title: <the pointer's title>`. After the sentence
  `The engine writes that frame automatically.` insert:
  `The `title:` line carries the pointer's title as data: every engine write keeps the two equal,
  and `heal --backfill-titles` fills it into bodies written before it existed.`
  In the verb table, after the `heal --proj D` row add the row
  `| `heal --proj D --backfill-titles` (tree-wide, a one-off: copies each pointer's title into a body that has no `title:`; never rewrites one that has; plain `heal` never opens a body) | `back-filled N title(s); M body(ies) already had one` |`,
  and in the `retitle` row replace `leaving slug, hook and body untouched` with
  `leaving slug, hook and prose untouched; the body's `title:` line follows the new title`.
  Run `reformat_tables.py` on the file.
- [ ] **Step 4: GREEN (text).** Same greps: `title: <the pointer's title>` 1, `backfill-titles` 2;
  quote the three changed passages in the checklist. Then a `bitranox:baseline-probe` (opus) with
  the frame block and the two rows pasted, asking: "A body file you read with show --body has
  `title: Old` and the pointer now says `New`. You write the file back with factedit apply. What
  title does the body carry afterwards, and which command fills a title into an old body with
  none?" Expected: `New` (the engine syncs it), `heal --proj D --backfill-titles`.
- [ ] **Step 5: Ledger.** Write `$SCRATCH/dec-t6.json`:

```json
[{"skill": "meta-self-improve", "kind": "rule", "topic": "body-title-field",
  "decision": "A fact body's frontmatter carries its title as data; every engine write keeps it equal to the pointer, and heal --backfill-titles fills it into older bodies.",
  "why": "A title existed only in the always-loaded pointer line, so the pointer could not be rebuilt from the store; the user chose to keep titles as data in phase 1.",
  "evidence": {"tier": "user", "text": "User decision 2026-11-09: Keep as data, decide in phase 2 (Recommended). Engine tests in hooks/tests/test_memory_engine_title_field.py."},
  "reopen_if": "Pointer lines are rendered from body data and the title is dropped from them, or the engine stops writing the title line.",
  "origin": "authored", "anchors": ["The `title:` line carries the pointer's title as data"],
  "supersedes": [], "refs": []}]
```

  `cd <W> && python3 plugins/bitranox/hooks/skill_decisions.py add --from-file $SCRATCH/dec-t6.json`
  (note the printed id).
- [ ] **Step 6: Checklist** `checklist-20261110-title-field.md`: what changed, the Step 0b result,
  RED and GREEN counts and quotes, the probe answer, `Decisions: <the id>`, ASCII check
  (`git diff -U0 | grep '^+' | grep -P '[^\x00-\x7F]'` prints nothing). Close the receipt.
- [ ] **Step 7: Commit.** `$SCRATCH/msg-t6.txt`:

```text
meta-self-improve: document the body title field and heal --backfill-titles

The memory-backend reference's frame block gains the `title:` line the engine now
writes, the verb table a heal --backfill-titles row, and the retitle row says the
body's title line follows the new title.
```

  `cd <W> && git add plugins/bitranox/skills/meta-self-improve/.skillwriter/checklist-20261110-title-field.md && git commit -F $SCRATCH/msg-t6.txt -- plugins/bitranox/skills/meta-self-improve/references/memory-backend.md plugins/bitranox/skills/meta-self-improve/.skillwriter/`

### Task 7: M2 - the crosstree dreams back up and verify with store_manifest

Order: run Tasks 8 and 9 before this one (its GREEN probe and its contract test need Task 9's
report contract); the numbering follows the MID milestones, not the run order.

**Files:**
- Modify: `plugins/bitranox/skills/meta-dream-crosstree/SKILL.md` (step 1, lines 58-62; step 8,
  line 179)
- Modify: `plugins/bitranox/skills/meta-dream-crosstree-deep/SKILL.md` (line 24)
- Modify: `plugins/bitranox/hooks/tests/test_dream_skill_contracts.py` (append after line 113)
- Create: `.skillwriter/checklist-20261110-store-manifest-backup.md` in BOTH skill dirs
- Modify: `CHANGELOG.md`

**Interfaces:** consumes the `store_manifest.py backup`/`verify` CLI (Tasks 1-2) and the report
contract of Task 9 (`pointer blocks` lines); do Task 9 before this task's GREEN probe, or paste
Task 9's new report-contract sentence into the probe.

**Out of scope:** every other crosstree step; the native `memory/` dirs, which store_manifest does
not cover (the new text says so).

**STOP if:** Step 0b shows a rejected or removed decision about the crosstree backup.

- [ ] **Step 1: Write the failing contract test** - append to `test_dream_skill_contracts.py`:

```python


@pytest.mark.parametrize("name", sorted(FAMILY))
def test_every_dream_backs_up_and_verifies_with_store_manifest(name):
    """A hand-rolled snapshot records no manifest, so the run can never be verified against it
    and its cost lines cannot be printed."""
    text = _read(FAMILY[name])
    assert "store_manifest.py backup" in text, "%s hand-rolls its backup" % name
    assert "store_manifest.py verify" in text, "%s never verifies against its backup" % name
```

- [ ] **Step 2: Run, expect FAIL.** `cd <W> && TEST plugins/bitranox/hooks/tests/test_dream_skill_contracts.py`
  Expected: 2 failed - `meta-dream-crosstree hand-rolls its backup` and
  `meta-dream-crosstree-deep hand-rolls its backup`; the nap and tree cases pass.
- [ ] **Step 3: Skill-writer start** (receipt; Step 0b `show` for `meta-dream-crosstree` and
  `meta-dream-crosstree-deep`, both `--kind rejected,removed --full` and plain).
- [ ] **Step 4: RED probe.** `bitranox:baseline-probe` (opus), prompt: the OLD crosstree step 1 and
  the OLD step 8 first sentence pasted, then: "You are about to run this crosstree dream over two
  knowledge trees, /work and /lab. Give the exact commands you run to take the per-run backup, and
  say what your report states about how each tree top's always-loaded pointer block changed."
  Expected RED: copies made by hand (cp/rsync or similar), no manifest, nothing about block bytes.
- [ ] **Step 5: Edit.** Crosstree step 1: replace the five lines from
  `1. **Back up first.** Snapshot every store this run may touch` through
  `hand-edit. The one-time whole-store backup is the safety net; this is the per-run one.` with:

```text
1. **Back up first, with `store_manifest.py backup`** (home: `<plugin>/skills/meta-dream-tree/`,
   launch via `hooks/run-python.sh`), once per tree this run may write, before any edit:
   `store_manifest.py backup --from <that tree's anchor> --scope tree --out
   ~/.claude/self-improve-audit/backups/<key>-<ts>` (outside every tree, so a backup is never
   re-discovered as live memory). It copies the tree's store and every in-scope `CLAUDE.local.md`
   and records the manifest step 8 verifies against; never hand-roll the snapshot (meta-dream-tree
   step 2 says why). A native `memory/` dir you will write is not covered: copy it beside the
   backup by hand. Curated writes go through the engine, not a hand-edit. The one-time whole-store
   backup is the safety net; this is the per-run one.
```

  Crosstree step 8: replace `output is what the report states, never a silent gap. Counts: stores
  scanned,` with:

```text
   output is what the report states, never a silent gap. Then run `store_manifest.py verify --out
   <each step 1 dir>`, once per tree: exit 0 is identical, exit 1 names each difference, and every
   one is a decided merge, move, prune or reword, or a loss to explain (meta-dream-tree step 8).
   Its `pointer blocks` lines go into the report as printed, per tree (dream-core.md, report
   contract); a promotion to a common ancestor shows there as slugs arriving at that level.
   Counts: stores scanned,
```

  rejoining the rest of the original line after `stores scanned,`. Deep line 24: replace
  `1. **Back up first** (per-run snapshot of each affected tree's TOP store + any store you will write) - unchanged.`
  with:

```text
1. **Back up first** with `store_manifest.py backup --scope tree`, once per tree you will write,
   and verify against each backup with `store_manifest.py verify` before the report - unchanged
   from meta-dream-crosstree steps 1 and 8.
```

- [ ] **Step 6: Run the contract test, expect PASS** (all cases).
- [ ] **Step 7: GREEN probe** - the same prompt with the NEW passages (and Task 9's report
  sentence). Expected: `store_manifest.py backup --from /work --scope tree --out ...` and the same
  for `/lab`, `verify --out` per tree, the `pointer blocks` lines in the report, and native
  `memory/` copied by hand. A control question in the same probe: "Does a nap use --scope tree?"
  must answer no (chain).
- [ ] **Step 8: Ledger.** `$SCRATCH/dec-t7.json`:

```json
[{"skill": "meta-dream-crosstree", "kind": "rule", "topic": "store-manifest-backup",
  "decision": "The crosstree dream backs up each tree it writes with store_manifest.py backup --scope tree and verifies against it before the report, printing the pointer-block cost lines.",
  "why": "A hand-rolled snapshot has no manifest, so the run that adds the most pointers to tree tops could not be verified or costed.",
  "evidence": {"tier": "measured", "text": "grep: neither crosstree skill named store_manifest before this change; contract test test_every_dream_backs_up_and_verifies_with_store_manifest."},
  "reopen_if": "store_manifest.py is replaced, or stops copying every in-scope CLAUDE.local.md.",
  "origin": "authored", "anchors": ["Back up first, with `store_manifest.py backup`"],
  "supersedes": [], "refs": []},
 {"skill": "meta-dream-crosstree-deep", "kind": "rule", "topic": "store-manifest-backup",
  "decision": "The deep crosstree dream backs up and verifies exactly as meta-dream-crosstree steps 1 and 8 say.",
  "why": "It shares crosstree's backup and report steps; a restated hand-rolled snapshot would drift.",
  "evidence": {"tier": "argued", "text": "The deep skill defers every unchanged step to meta-dream-crosstree."},
  "reopen_if": "The deep dream gets a backup step of its own.",
  "origin": "authored", "anchors": ["with `store_manifest.py backup --scope tree`, once per tree you will write"],
  "supersedes": [], "refs": []}]
```

  `cd <W> && python3 plugins/bitranox/hooks/skill_decisions.py add --from-file $SCRATCH/dec-t7.json`
- [ ] **Step 9: Checklists** in both skill dirs (each with its own `Decisions:` id), receipt end.
- [ ] **Step 10: CHANGELOG** under `### Changed`:

```text
- meta-dream-crosstree and meta-dream-crosstree-deep back up each tree they write with
  `store_manifest.py backup --scope tree` and verify against it before the report, printing the
  pointer-block cost lines, instead of a hand-rolled snapshot.
```

- [ ] **Step 11: Commit.** `$SCRATCH/msg-t7.txt`:

```text
crosstree dreams: back up and verify with store_manifest

Both crosstree skills hand-rolled their per-run snapshot, so the dream that adds
the most pointers to tree tops recorded no manifest and could neither verify nor
cost its run. They now take store_manifest.py backup --scope tree per tree and
verify against it before the report. A contract test pins that every dream skill
names both commands.
```

  `cd <W> && git add plugins/bitranox/skills/meta-dream-crosstree/.skillwriter plugins/bitranox/skills/meta-dream-crosstree-deep/.skillwriter && git commit -F $SCRATCH/msg-t7.txt -- plugins/bitranox/skills/meta-dream-crosstree plugins/bitranox/skills/meta-dream-crosstree-deep plugins/bitranox/hooks/tests/test_dream_skill_contracts.py CHANGELOG.md`

### Task 8: M3b - meta-dream-tree: no applied re-home to the top, length is a cost question

**Files:**
- Modify: `plugins/bitranox/skills/meta-dream-tree/SKILL.md` (misplacement bullet lines 275-278;
  soft-cap sentence lines 344-346; step 8 after line 426; rationalization row line 561)
- Create: `plugins/bitranox/skills/meta-dream-tree/.skillwriter/checklist-20261110-cost-side.md`
- Modify: `CHANGELOG.md`

**Interfaces:** points at Task 9's dream-core text (the misplacement row and the report contract);
land Task 9 in the same commit or first.

**Out of scope:** the corroboration gate itself; the 350/500 constants; P1b's question whether
shortened hooks fire (this text never shortens a hook unasked).

**STOP if:** Step 0b shows a decision that a misplacement is re-homed to the top (a `rule` whose
anchor is the old bullet): supersede it in the ledger with the reason, never edit the ledger.

- [ ] **Step 1: Skill-writer start** (receipt; `show meta-dream-tree --kind rejected,removed
  --full`; `show meta-dream-tree`).
- [ ] **Step 2: RED probes** (opus, old passages pasted):
  - A: "Tree dream. Fact F sits at /t/proj; its hook is written generally and /t/proj's PLACE-HERE
    excludes it. The routing prompt's narrowest covering level is the tree top /t. should-promote
    printed hold. What do you do with F, and what does the report say?" Expected RED: re-home F to
    /t whatever the verdict.
  - B: "The firing check finds a complete, trigger-first hook of 430 characters at the tree top.
    Rewrite it? Report anything?" Expected RED: leave it, report nothing.
- [ ] **Step 3: Edit.** Bullet: replace

```text
   - a hook written generally, at a level whose PLACE-HERE EXCLUDES it, is a MISPLACEMENT:
     re-home it to the level the routing prompt picks, whatever `should-promote` says (a `hold`
     answers the promotion question, not this one), and still record the sighting with
     `saw-promotable`;
```

  with

```text
   - a hook written generally, at a level whose PLACE-HERE EXCLUDES it, is a MISPLACEMENT:
     re-home it to the level the routing prompt picks, whatever `should-promote` says (a `hold`
     answers the promotion question, not this one), and still record the sighting with
     `saw-promotable` - unless that level is the tree top: a re-home to the top is PROPOSED in
     the report with its cost and never applied by this rule (references/dream-core.md, the
     misplacement row);
```

  Soft-cap sentence: replace

```text
   check - would this line catch your attention at the right moment?). Do
   NOT rewrite a hook merely for exceeding the 350 SOFT cap - a complete trigger-first hook may run up
   to the hard cap, which the engine enforces by refusal. Queue offenders to an opus
```

  with

```text
   check - would this line catch your attention at the right moment?). Length alone is not a
   FIRING defect: a complete trigger-first hook may run up to the 500 hard cap, which the engine
   enforces by refusal, so the firing check never rewrites a hook for exceeding the 350 SOFT cap.
   Length is a COST question, met by representation (references/dream-passes.md, removal
   policy): a hook over the soft cap at a broad level goes into the report with its length and
   its level's block bytes as a shortening proposal, never shortened unasked. Queue offenders to an opus
```

  Step 8: after the sentence ending `and checks` / `level, slug, title and pin only.` (it wraps
  across two lines) insert:

```text
   Under the diff, verify prints the `pointer blocks` lines (one per level whose block changed:
   bytes and pointers before and after, slugs arrived and left, top first; `data.levels[]` under
   `--json`); they go into the report as printed (references/dream-core.md, report contract). A
   backup without level copies prints `block bytes before not known` and null bytes, never 0.
```

  Rationalization row: replace its right cell with
  `A `hold` answers the promotion question only. Classify first: a general hook at a level whose PLACE-HERE excludes it is a MISPLACEMENT and is re-homed whatever the verdict says - to any level but the tree top, where the re-home is proposed with its cost, not applied.`
  and run `reformat_tables.py` on the file.
- [ ] **Step 4: GREEN probes** A and B with the new passages (and Task 9's row). Expected: A -
  F stays at /t/proj, the report proposes the move with F's hook length and /t's block bytes,
  the sighting is recorded; B - not rewritten by the firing check, listed as a shortening proposal.
  Control C in the same probe: "F's routing picks /t/team (not the top), same facts" - expected: F
  is re-homed to /t/team (the rule still re-homes below the top).
- [ ] **Step 5: Contract and gate.** `cd <W> && TEST plugins/bitranox/hooks/tests/test_dream_skill_contracts.py`
  must pass (no family literal duplicated).
- [ ] **Step 6: Ledger** `$SCRATCH/dec-t8.json`:

```json
[{"skill": "meta-dream-tree", "kind": "rule", "topic": "no-applied-rehome-to-top",
  "decision": "A misplacement whose routed level is the tree top is proposed in the report with its cost, never re-homed there by the misplacement rule; below the top it is re-homed whatever should-promote says.",
  "why": "The top's block loads in every session of the tree and the misplacement test passes for nearly any general lesson, so the ungated re-home was the main route facts took to the top.",
  "evidence": {"tier": "measured", "text": "Store history 2026-11-09: 159 of 163 pointers arriving at the top in a day were moves up; moves up outnumbered moves down about 35 to 1."},
  "reopen_if": "Pointer placement is generated from topics (phase 2), or the top's block stops loading in every session.",
  "origin": "authored", "anchors": ["a re-home to the top is PROPOSED in the report with its cost and never applied by this rule"],
  "supersedes": [], "refs": []},
 {"skill": "meta-dream-tree", "kind": "rule", "topic": "hook-length-is-a-cost",
  "decision": "The firing check never rewrites a hook for its length; a hook over the soft cap at a broad level is reported as a shortening proposal with its block bytes.",
  "why": "The old sentence forbade any length rewrite while the passes note met size by representation; shortening unasked waits on a firing test.",
  "evidence": {"tier": "user", "text": "User decisions 2026-11-09: Over 350, to 350 (Recommended); Today twice + shortened, 6 runs (Recommended)."},
  "reopen_if": "A firing test shows hooks shortened to the soft cap fire as often as today's, and shortening becomes a pass of its own.",
  "origin": "authored", "anchors": ["Length is a COST question, met by representation"],
  "supersedes": [], "refs": []}]
```

  Any superseded id from Step 1 goes into `supersedes`.
- [ ] **Step 7: Checklist** (with `Decisions:` both ids), receipt end, CHANGELOG under
  `### Changed`:

```text
- meta-dream-tree: a misplacement whose routed level is the tree top is proposed with its
  cost instead of re-homed; the firing check no longer rewrites a hook for its length, and a
  long hook at a broad level is reported as a shortening proposal; step 8 copies verify's
  pointer-block lines into the report.
```

- [ ] **Step 8: Commit** together with Task 9 (same message file `$SCRATCH/msg-t8-9.txt`, below in
  Task 9).

### Task 9: M3c - dream-core: the misplacement row and the report contract name the cost

**Files:**
- Modify: `plugins/bitranox/skills/meta-dream-tree/references/dream-core.md` (table row line 315
  and the paragraph after it, lines 317-318; report contract lines 367-372)

- Modify: `plugins/bitranox/hooks/tests/test_dream_skill_contracts.py` (append after line 113)

**Interfaces:** the literal `pointer blocks` lives here, in the report contract.

**Out of scope:** the corroboration-gate paragraph's reasoning (kept), every other contract line.

- [ ] **Step 0: Failing contract test** - append to `test_dream_skill_contracts.py`:

```python


def test_the_report_contract_names_the_cost_lines():
    assert "pointer blocks" in _read(CORE), "dream-core.md's report contract lost the cost lines"
```

  `cd <W> && TEST plugins/bitranox/hooks/tests/test_dream_skill_contracts.py -k cost_lines` -
  expected: 1 failed, `dream-core.md's report contract lost the cost lines`.

- [ ] **Step 1: RED probe** (opus, old table + old report sentence): "What does a dream do with a
  misplacement whose only covering level is the tree top, and what does its report say about the
  pointer blocks?" Expected RED: re-homes it; counts only.
- [ ] **Step 2: Edit.** In the table's misplacement row (padded cells `no`, `no`,
  `a misplacement`, `re-home it, and record the sighting anyway`), the last cell becomes
  `re-home it, and record the sighting anyway; to the tree top only as a proposal`; then
  `reformat_tables.py`. After the paragraph `Record the sighting in the re-home case too - it
  costs nothing, and the fact may still be a genuine promotion candidate later.` add:

```text
A re-home to the tree top is the one re-home this table does not apply. The top's block loads in
every session of the tree, and the misplacement test passes for nearly any lesson written
generally, so the move is PROPOSED in the report with its cost (the fact, its hook length, the
top block's bytes) and the fact stays where it is until the user decides.
```

  Report contract: replace `Report counts (merges, placements with direction, prunes,` and the
  next line's `pinned untouched) and, when the run covered what the nudge asked for, run` with:

```text
Report counts (merges, placements with direction, prunes, pinned untouched), then the `pointer
blocks` lines `store_manifest.py verify` prints, as printed: one per level whose block changed,
with bytes and pointers before and after and the slugs that arrived and left, top first, and every
slug that arrived at the tree top named. Any proposed move to the top is listed beside them. When
the run covered what the nudge asked for, run
```

  keeping the rest of that paragraph (`dream_state.py done --kind nap` ...) unchanged.
- [ ] **Step 3: GREEN probe**, same question, new text: proposes, does not move; report carries the
  pointer-blocks lines with the top's arrivals named.
- [ ] **Step 4: Run** `cd <W> && TEST plugins/bitranox/hooks/tests/test_dream_skill_contracts.py`
  - expected all pass, the Step 0 test included.
- [ ] **Step 5: Ledger and checklist.** The dream-core edit belongs to the `meta-dream-tree` skill
  dir: add one more entry to `$SCRATCH/dec-t8.json` before running `add` (or a second file):

```json
{"skill": "meta-dream-tree", "kind": "rule", "topic": "report-cost-lines",
 "decision": "Every dream report carries the pointer-block lines store_manifest.py verify prints, the tree top's arrivals named, beside any proposed move to the top.",
 "why": "The store-growth rule counted facts, and a move to the top keeps the count while every session pays for the line; the cost has to be visible where the run is judged.",
 "evidence": {"tier": "argued", "text": "Design 2026-11-09, cost side; verify's cost lines tested in test_store_manifest.py."},
 "reopen_if": "verify stops printing per-level block lines, or placement is generated from topics.",
 "origin": "authored", "anchors": ["lines `store_manifest.py verify` prints, as printed"],
 "supersedes": [], "refs": []}
```

  (`add` refuses an anchor the skill's text does not contain after whitespace normalisation, so a
  refusal here means the edit and the anchor differ). The Task 8 checklist covers both files and lists all three ids.
- [ ] **Step 6: Commit Tasks 8 and 9.** `$SCRATCH/msg-t8-9.txt`:

```text
meta-dream-tree: give placement a cost side

A misplacement routed to the tree top is proposed with its cost instead of
re-homed: the top's block loads in every session, and the ungated re-home was the
main route facts took there. The firing check no longer rewrites a hook for its
length; a long hook at a broad level is reported as a shortening proposal. The
report contract in dream-core.md carries verify's pointer-block lines, the top's
arrivals named.
```

  `cd <W> && git add plugins/bitranox/skills/meta-dream-tree/.skillwriter/checklist-20261110-cost-side.md && git commit -F $SCRATCH/msg-t8-9.txt -- plugins/bitranox/skills/meta-dream-tree/SKILL.md plugins/bitranox/skills/meta-dream-tree/references/dream-core.md plugins/bitranox/skills/meta-dream-tree/.skillwriter plugins/bitranox/hooks/tests/test_dream_skill_contracts.py CHANGELOG.md`
  Task 7 follows.

### Task 10: M3d - a nap never moves a fact to the tree top, and prints the cost lines

**Files:**
- Modify: `plugins/bitranox/skills/meta-dream-nap/SKILL.md` (step 4 lines 131-134; step 6 lines
  142-144; deliverables after line 166; rationalizations table after line 179)
- Create: `plugins/bitranox/skills/meta-dream-nap/.skillwriter/checklist-20261110-no-move-to-top.md`
- Modify: `CHANGELOG.md`

**Interfaces:** the report contract of Task 9.

**Out of scope:** moves DOWN from the anchor (still allowed on the chain), and moves between
non-anchor chain levels.

**STOP if:** Step 0b shows a decision that chain-internal placement includes moves to the anchor
(supersede it with the reason; do not edit the ledger).

- [ ] **Step 1: Skill-writer start** (receipt; `show meta-dream-nap --kind rejected,removed --full`;
  `show meta-dream-nap`).
- [ ] **Step 2: RED probe** (opus, old step 4 and step 6): "Nap at /t/a/proj, chain /t/a/proj ->
  /t/a -> /t (the anchor). Routing sends fact G from /t/a to /t, confidence high, evidence clear.
  Apply? What does the report say about pointer blocks?" Expected RED: applies the move; nothing
  about block bytes.
- [ ] **Step 3: Edit.** Step 4: replace `   (up or down). Low/UNSURE and anything involving a sibling
  stays put. A pinned fact re-levels` with:

```text
   (up or down), except a move TO the tree top (the anchor): a nap never applies one. It lists the
   fact, its hook length and the top block's bytes in the report as a proposal for the full
   dream, because the top's block loads in every session of the tree. Low/UNSURE and anything
   involving a sibling stays put. A pinned fact re-levels
```

  Step 6: replace `   manifest file), and `TOTAL problems: 0` from ONE` with:

```text
   manifest file; its `pointer blocks` lines go into the report as printed, per the core's report
   contract), and `TOTAL problems: 0` from ONE
```

  Deliverables: after `- [ ] Manifest diff clean; reconcile `TOTAL problems: 0` over the chain.`
  add `- [ ] No fact moved to the tree top (each such move listed as a proposal), and the `pointer blocks` lines in the report.`
  Rationalizations: add the row
  `| "The anchor is on the chain, so moving a fact there is chain-internal" | It is, and it is the one chain move a nap never applies: the anchor's block loads in every session of the tree. List it as a proposal for the full dream. |`
  and run `reformat_tables.py`.
- [ ] **Step 4: GREEN probe**, same prompt, new text: G stays at /t/a, the report proposes it with
  its hook length and /t's bytes, the pointer-blocks lines are in the report. Control in the same
  probe: "routing sends fact H from /t to /t/a" - expected: applied (down-moves are unchanged).
- [ ] **Step 5: Contract test** `cd <W> && TEST plugins/bitranox/hooks/tests/test_dream_skill_contracts.py` passes.
- [ ] **Step 6: Ledger** `$SCRATCH/dec-t10.json`:

```json
[{"skill": "meta-dream-nap", "kind": "rule", "topic": "no-move-to-top",
  "decision": "A nap never applies a move to the tree top (the anchor); it proposes it in the report for the full dream. Moves down from the anchor and between other chain levels are unchanged.",
  "why": "The anchor's block loads in every session of the tree, and naps, run many times a day, moved the second most pointers to the top.",
  "evidence": {"tier": "measured", "text": "Store backups 2026-11-09: nap intervals added 140 top pointers against 71 removed over 85 intervals."},
  "reopen_if": "Pointer placement is generated from topics (phase 2), or naps stop running on the anchor's chain.",
  "origin": "authored", "anchors": ["except a move TO the tree top (the anchor): a nap never applies one"],
  "supersedes": [], "refs": []}]
```

- [ ] **Step 7: Checklist, receipt end, CHANGELOG** under `### Changed`:

```text
- meta-dream-nap: a nap never moves a fact to the tree top; it lists such a move as a
  proposal for the full dream, and its report carries verify's pointer-block lines.
```

- [ ] **Step 8: Commit.** `$SCRATCH/msg-t10.txt`:

```text
meta-dream-nap: never move a fact to the tree top

The anchor is on every chain, so chain-internal placement let a nap move a fact to
the block every session loads. A nap now lists such a move as a proposal for the
full dream, and copies verify's pointer-block lines into its report.
```

  `cd <W> && git add plugins/bitranox/skills/meta-dream-nap/.skillwriter/checklist-20261110-no-move-to-top.md && git commit -F $SCRATCH/msg-t10.txt -- plugins/bitranox/skills/meta-dream-nap CHANGELOG.md`

### Task 11: M5 - release

**Files:** none new; `plugin.json`, `pyproject.toml`, `CHANGELOG.md` only if origin moved.

**STOP if:** the full gate fails on anything this plan did not touch (report it; fix it in its
own worktree per the pathfinder rule, never inside this branch); or a peer session is pushing
bitranox-skills (ListAgents; message it to hold).

- [ ] **Step 1:** `cd <W> && git fetch origin && git log --oneline HEAD..origin/master`. If
  origin's `plugin.json` version moved past the fork point's, run
  `cd <W> && uv run plugins/bitranox/hooks/bump_version.py --merge` and re-read the CHANGELOG
  section it produced (both sections present, ours renumbered).
- [ ] **Step 2: Full gate.** `cd <W> && python3 plugins/bitranox/hooks/repo-gate.py --ci` -
  expected exit 0 and pytest's `N passed` line. Then `cd <W> && python3
  plugins/bitranox/hooks/skill_decisions.py check` - exit 0.
- [ ] **Step 3: Review.** Dispatch an opus code reviewer (effort medium) with `git diff
  origin/master...HEAD` for Tasks 1-10 and the authority to contradict this plan; each finding
  needs a concrete failing input. Fix confirmed findings, re-run Step 2.
- [ ] **Step 4: Push.** `cd <W> && git push origin design/top-index-topics:master` (the pre-push
  hook runs the suite, 4-8 minutes). Verify: `cd <W> && git fetch origin && git rev-list --count
  origin/master..HEAD` prints 0.
- [ ] **Step 5: Watch CI** with the toolbox jig: `cd <W> && python3
  ~/.claude/skills/toolbox/tools/ci_wait.py --ref HEAD` (expect 18-35 minutes; a background run
  polls its own log). Every workflow terminal and green, or fix and repeat.

### Task 12: P1a-run R1 - preflight and the title back-fill

The store is shared and naps run in other sessions all day. Every R-task records what it wrote,
and every verify difference not on this plan's lists is a peer's until shown otherwise.

**Files:** store only (`$ANCHOR/.claude-memory/facts/*.md`, pointer blocks
untouched by the back-fill). Run dir `RUN=~/.claude/self-improve-audit/p1a-run-<ts>` (outside the
tree; created with `mkdir -p`, the timestamp from `date +%Y%m%d-%H%M%S` in the same command).

**Interfaces:** `ENG=<P>/hooks/memory_engine.py`, `SM=<P>/skills/meta-dream-tree/store_manifest.py`,
`FE=<P>/skills/meta-dream-tree/factedit.py`, `REC=<P>/skills/meta-self-improve/reconcile_memory_index.py`,
all from the worktree at the released commit (Task 11). Launch each with `python3`.

**STOP if:** the worktree HEAD is not the released commit (`git -C <W> rev-parse HEAD` against
`git -C <W> rev-parse origin/master`); or `reconcile --check-tree` is not 0 BEFORE the run (a
pre-existing problem is fixed or reported first, never mixed into this run).

- [ ] **Step 1: Preflight.** `python3 $REC --check-tree $ANCHOR` -> `TOTAL tree
  problems: 0`. `git -C $ANCHOR/.claude-memory status --porcelain` - record the
  dirty paths (peers' uncommitted work) in `$RUN/dirty-before.txt`; this run never stages them.
- [ ] **Step 2: Backup.** `python3 $SM backup --from $ANCHOR --scope tree --out
  $RUN/backup-titles` - expect the entries count and the out path.
- [ ] **Step 3: Back-fill.** `python3 $ENG heal --proj $ANCHOR --backfill-titles`
  - expect `back-filled N title(s); M body(ies) already had one`, N about the number of bodies
  (every body predates the field). Any `!` line is read: a missing body is a pre-existing
  dangling pointer (Step 1 should have caught it - STOP).
- [ ] **Step 4: Verify.** `python3 $SM verify --out $RUN/backup-titles --json > $RUN/verify-titles.json`
  then check with a scratch script that every `changed` entry has `what == ["body"]`, `added`,
  `removed` and `moved` are empty, and every `data.levels` row is unchanged (pointer lines are
  untouched): print the counts, and list any entry that breaks the rule. A `changed` body that is
  not a title-only change (diff the backup body against the live one for 5 random slugs: the only
  added line is `title: ...`) is a STOP.
- [ ] **Step 5: Commit the store.** `git -C $ANCHOR/.claude-memory status
  --porcelain`, then stage exactly the filled slugs' bodies (from Step 3's report, not a glob):
  write their paths to `$RUN/titles-paths.txt` and `git -C $ANCHOR/.claude-memory
  add --pathspec-from-file=$RUN/titles-paths.txt`; check `git diff --cached --name-only` equals the
  list (both ways); message file `$RUN/msg-titles.txt` ("facts: back-fill each body's title from
  its pointer"), `git -C ... commit -F $RUN/msg-titles.txt`; push to its approved backup remote
  `git -C $ANCHOR/.claude-memory push`. A path that a peer also has dirty (Step 1
  list) is left out and named in the report.

### Task 13: P1a-run R2 - compaction backup and the live re-check of every draft

**Files:** `$RUN/drafts/` (hook and body files), `$RUN/batch.jsonl`; no store write.

**STOP if:** a planned slug is no longer at the tree top, or no longer exists - drop it from the
lists and say so; never re-target it unasked.

- [ ] **Step 1: Backup.** `python3 $SM backup --from $ANCHOR --scope tree --out $RUN/backup-compaction`.
- [ ] **Step 2: The lists.** Copy `FEEDBACK`, `REF_T1`, `REF_T2`, `REF_T3`, `MOVES` and `TRIMS` out
  of the frozen `.plan/top-index-phase1-inputs/analysis/final_numbers.py` (main checkout) into
  `$RUN/lists.json` (survivor first in each merge group). `REF_T3` is applied only if the user
  approves it (the weakest tier: four groups the reviewer called possible, not worth doing); ask
  once, before Step 3, with both options' cost and saving (3,104 bytes, 1.2%).
- [ ] **Step 3: Live state.** For every slug in the lists: `python3 $FE show --slug <s> --level
  $ANCHOR --body --json > $RUN/show/<s>.json`. A non-zero exit means the slug left
  the top: record and drop it. Then for each, `git -C $ANCHOR/.claude-memory log
  --since=2026-11-09T19:00 --format=%h -- facts/<s>.md` plus `git status --porcelain facts/<s>.md`:
  any output means the body changed after the review.
- [ ] **Step 4: Drafts.** Merges: the hook is the `Hook:` line of the matching group in
  `review-feedback-joins.md` / `review-reference-joins.md` (match by the member slugs, not by the
  group number - the files number their groups differently from `final_numbers.py`). The merged
  body is written by an opus subagent from both live bodies (Step 3) and the group's `Keep:` list:
  every kept item present, the survivor's frame and `**Why:**`/`**How to apply:**` kept, the other
  member's measurements added as its own paragraph, each `[[ref]]` of either body kept once, and
  a `[[ref]]` to a member of the same group dropped (it would point at an archived fact). A draft
  body that cites ANY merged-away slug of another group gets that ref rewritten to its survivor
  here, in the draft: Task 14 relinks only bodies that are not in this batch.
  Trims: the draft hook column of the table in `review-skill-pointers.md`; body unchanged. A slug
  whose body changed after the review (Step 3) gets its draft re-reviewed by a second opus pass
  against the live body before use. Every hook: `python3 $FE check --hook-file <f> --body-file <b>`
  - accepted, at most 500 characters (the merged hooks were drafted to at most 350).
- [ ] **Step 5: The renamed skill.** `bash -c 'grep -rlF "coding-python-enforce-data-architecture-strict" $ANCHOR/.claude-memory/facts'`
  and the same over every `CLAUDE.local.md` the backup's `levels` list names. For each slug
  carrying the old name in its hook or body, draft the hook/body with `coding-python-data-architecture`
  (the installed skill name; confirm it with the plugin's `skills/` listing first). Pointers at
  levels below the top are included (the name is wrong everywhere); their `level` in the batch is
  their owning level from `show`.
- [ ] **Step 6: Batch file.** One JSON object per line, written with Python (`json.dumps`), never
  by hand:

```text
{"slug": "<survivor or trimmed slug>", "level": "$ANCHOR", "hook_file": "drafts/<slug>.hook", "body_file": "drafts/<slug>.body.md"}
```

  `body_file` only for merges and renamed-skill bodies; `title` only where the review drafted one.
  Relative paths resolve against the batch file's dir.
- [ ] **Step 7: Dry run.** `python3 $FE apply --batch $RUN/batch.jsonl --dry-run` - every entry
  validated, the engine command printed per line, nothing written. A pinned slug in the batch is a
  STOP (the run never passes `--allow-pinned`; a pinned fact's change is the user's).

### Task 14: P1a-run R3 - relink every reference to a merged-away or moved fact

**Files:** citer bodies, through `$FE apply`.

**STOP if:** a CLAUDE.md (not a fact) names a merged-away slug - list it; a CLAUDE.md edit is not
this run's.

- [ ] **Step 1: Inventory.** For every merged-away slug M: `python3 $REC --archive M
  $ANCHOR --dry-run` - it lists every fact that links `[[M]]` or names M and every
  CLAUDE.md that names it, and writes nothing. Write the list to `$RUN/citers.json`.
- [ ] **Step 2: Rewrite.** For each citer body that is NOT in `$RUN/batch.jsonl` (a batch entry
  already carries its relinked body, Task 13 Step 4): `python3 $FE show --slug <c> --level <its level>
  --body > $RUN/citers/<c>.body.md` (the frame stays in the file), replace `[[M]]` with `[[<M's
  survivor>]]` with a Python script asserting each replacement count, drop a duplicate
  `[[survivor]]` the replacement created, and add the citers to a second batch
  `$RUN/relink.jsonl` (`slug`, `level`, `body_file`). Dry run, then
  `python3 $FE apply --batch $RUN/relink.jsonl`.
- [ ] **Step 3: Moves' inbound refs.** For each slug in `MOVES`, list its citers the same way. A
  fact moved DOWN may not be cited from above (refs are upward-only, and `move` refuses). For each
  citer: if it belongs at the target level too, it moves with the fact as one set (Task 16); if
  not, the fact STAYS at the top and is dropped from `MOVES`, named in the report. Never rewrite a
  citer's reference away to make a move pass, and never `--force`.

### Task 15: P1a-run R4 - apply the merges, trims and renamed-skill hooks

- [ ] **Step 1:** `python3 $FE apply --batch $RUN/batch.jsonl --json > $RUN/apply.json` - expect
  one engine success (the printed slug) per line. `apply` stops at the first failure, with the
  entries before it already written: read it, fix that entry's file, re-run the dry run, then
  apply the whole batch again (an entry already applied is rewritten with the same content).
- [ ] **Step 2:** for 5 applied slugs, `python3 $FE show --slug <s> --level <level>` - the stored
  hook equals the draft file byte for byte, and the body carries `title:`.

### Task 16: P1a-run R5 - archive the merged-away facts

- [ ] **Step 1:** for each merged-away slug M (Task 14 relinked every citer):
  `python3 $REC --archive M $ANCHOR` - expect `archived M ...`, exit 0. Exit 1
  means something still names M: read the list, relink it (Task 14 Step 2), retry. Never
  `--force`.

### Task 17: P1a-run R6 - move the facts off the top

Targets (from the review; each confirmed against the target level's PLACE-HERE descriptor before
moving - read its `CLAUDE.local.md` head):

```text
feedback-public-push-review-and-humanize                                   -> bitranox-systems/provmm-umbrella
feedback-iterate-before-you-cap-datamax-dpl-builds-labels-one-by-one       -> projects/public/apps/utils/datamax-dpl
feedback-forward-the-caller-s-identity-across-an-ssh-re-run-of-the-harness -> bitranox-systems/provmm-umbrella
feedback-measure-a-queueing-change-never-predict-it                        -> bitranox-systems/provmm-umbrella
feedback-key-a-violation-detector-on-state-at-the-instant-never-on-whether-an-event-ever-happened -> projects/public/KI
feedback-an-unused-feature-its-users-understood-needs-a-trigger-not-more-wording -> projects/public/KI
reference-two-concurrent-rustup-installs-of-one-toolchain-both-roll-back   -> bitranox-systems/provmm-umbrella
project-rebasing-onto-a-new-upstream-test-module-diff-test-names-before-keeping-both -> bitranox-systems/provmm-umbrella
reference-socket-recv-fds-ignores-its-flags-received-fds-arrive-inheritable -> bitranox-systems/provmm-umbrella
reference-wsl-exe-prints-utf-16-over-ssh-set-wsl-utf8-1                   -> bitranox-systems/provmm-umbrella
reference-judge-windows-domain-membership-by-partofdomain-never-by-the-domain-name -> projects  (medium confidence: ask)
```

(paths relative to `$ANCHOR`).

- [ ] **Step 1:** for each (or each set, Task 14 Step 3): `python3 $ENG move --from-level
  $ANCHOR --to-level <target> --slug <s> [--slug <citer> ...]` - expect
  `moved <slug>: A -> B (down)`. A refusal is read; a dangling-ref refusal means Task 14 Step 3
  missed a citer: drop the move, never `--force`.

### Task 18: P1a-run R7 - verify the whole run

- [ ] **Step 1:** `python3 $SM verify --out $RUN/backup-compaction --json > $RUN/verify.json` and
  the text form to `$RUN/verify.txt`. Exit 1 expected.
- [ ] **Step 2: Both ways.** A scratch script reads `verify.json` and `$RUN/lists.json` (after
  Task 13-17's drops) and prints, for each class, the expected and the observed set and both
  differences: `removed` = the merged-away slugs; `moved` = the applied moves (and their set
  members); `changed` = survivors (`hook`, `body`), trims (`hook`), renamed-skill facts and relinked
  citers (`body`); `added` = none. Every slug in a difference is adjudicated: a peer's write
  (store `git log`, the live sessions in `~/.claude/sessions/`) is named and left; anything else is
  a loss and a STOP.
- [ ] **Step 3: Cost.** The top's `pointer blocks` line must show bytes DOWN and `arrived 0`
  (this run moves nothing up). Compare the drop with the planned saving (23,512 bytes with tier 3,
  20,408 without, minus dropped items); a drop below half of that is explained before finishing.
- [ ] **Step 4:** `python3 $REC --check-tree $ANCHOR` -> `TOTAL tree problems: 0`,
  and `python3 $REC --check <each changed level> ... $ANCHOR` (narrowest first) ->
  `TOTAL problems: 0`.

### Task 19: P1a-run R8 - commit the store and report

- [ ] **Step 1:** stage exactly the bodies this run wrote, from `apply.json`, `relink` and the
  archive moves (`facts/<M>.md` removed, `.archive/<M>.md` added) - never `git add -A`; check
  `git diff --cached --name-only` against that list both ways; message file in `$RUN`; commit;
  push to the store's approved backup remote.
- [ ] **Step 2: Report** to the user: the verify cost lines as printed, the counts per class, every
  dropped item with its reason, every peer write adjudicated, the tier-3 and domain-membership
  answers, and the check-tree result. Record the result and its artifact paths in the backlog line
  [35] at once.
- [ ] **Step 3:** P1b's detailed tasks are written next, against the store this run left.
