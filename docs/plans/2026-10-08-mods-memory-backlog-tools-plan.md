# Memory and backlog tools (Claude Code mod) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use bitranox:process-agents-subagent-driven-development (recommended) or bitranox:process-plan-executor to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Register five model-callable tools (`backlog_list`, `backlog_add`, `backlog_close`, `memory_add`, `contrib_add`) from a Claude Code mod shipped inside the bitranox plugin, with every rule they obey in tested Python.

**Architecture:** `plugins/bitranox/hooks/hooks.json` gains `"modules": ["./mods/register.ts"]`. That TypeScript module registers the tools at `session.start` and answers each `tool.call` by running `hooks/mod_bridge.py` through `hooks/run-python.sh` with one JSON request on stdin; the bridge dispatches in-process to `hooks/open_work.py` (new), `memory_engine.add_with_advice` (extracted from the CLI) and `self_improve_signals.add_contribution`, and prints one JSON envelope. Design: `docs/plans/2026-10-08-mods-memory-backlog-tools-design.md`.

**Tech Stack:** Python >= 3.11 (stdlib only), pytest, TypeScript mod on the Claude Code 2.1.290 mods API (`claude plugin validate`, `claude plugin test`), bash shim `run-python.sh`.

## Global Constraints

- Python floor: `requires-python = ">=3.11"`; CI matrix 3.11-3.14 on Linux, macOS, Windows.
- Hook-side Python matches the surrounding files: no type annotations, `%`-formatting is fine, every file opened with `encoding="utf-8"`, no `str.splitlines()` on file text (it also splits on U+2028 and form feed) - use `text.split("\n")`.
- ASCII only in every file and message: no em or en dashes, no curly quotes.
- Every new shipped `.py` gets a sibling test in `plugins/bitranox/hooks/tests/` in the same task.
- Run pytest with CI's dependency set, never bare: `env -u VIRTUAL_ENV uv run --with pytest --with PyYAML --with lxml --with defusedxml --with ruamel.yaml --with httpx2 python -m pytest <paths> -q` from the repo root.
- Subprocess in tests: `sys.executable`, never `"python3"`; pass `env={**os.environ, ...}`, never a fresh dict.
- Never monkeypatch our own modules; the only patched seam is `HOME`/`USERPROFILE` (the machine-local audit dir).
- Commits: message from a file (`git commit -F <file>`), written in an EARLIER command; no AI attribution of any kind; pathspec commits.
- `.github/` is off-limits.
- The tool prefix is `mcp__bitranox__` (plugin name `bitranox`).
- Rank rule (measured on the live backlog 2026-10-08): a rank is a positive integer free over every line, closed included; tens are a convention the tool suggests, never enforces; the file is not sorted, so a new line goes directly after the item with the largest smaller rank, or before the first item.

---

### Task 1: `open_work.py` - read side (parse, list, locate)

**Files:**
- Create: `plugins/bitranox/hooks/open_work.py`
- Test: `plugins/bitranox/hooks/tests/test_open_work.py`

**Interfaces:**
- Produces: `HEADER` (str), `FILENAME = "OPEN-WORK.md"`, `ORIGINS = ("USER", "FOUND")`; errors `BacklogError(ValueError)` and subclasses `NotARepo`, `RankTaken`, `UnknownRank`, `AlreadyClosed`, `AmbiguousRank`, `MalformedField`; `parse_line(line) -> dict | None`; `iter_items(lines) -> iterator of (index, item)`; `list_items(path, state="open") -> list[dict]`; `backlog_path(cwd) -> Path`. An item dict has keys `rank` (int), `raised` (str), `state` (`"open"`/`"closed"`), `origin` (str or None), `what` (str), `size`, `open`, `next`, `closed` (str or None each).

**Out of scope** - do NOT touch:
- `plugins/bitranox/hooks/session-start.py` (`_parse_open_work`) - it keeps its own parser for now; folding it onto `open_work.py` is a follow-up item, not this change (it orders by age and has its own budget rules).

**STOP conditions:**
- the live `OPEN-WORK.md` has an item line `parse_line` cannot read (the count test fails) - report the line, do not loosen the regex blindly;
- a step's verification fails twice after one reasonable fix attempt.

- [ ] **Step 1: Write the failing tests**

```python
"""open_work: OPEN-WORK.md as data. ASCII only.

Driven against real files in tmp_path and the repo's own live backlog; nothing of ours is patched.
"""
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

import open_work as ow

REPO = Path(__file__).resolve().parents[4]
LIVE = REPO / "OPEN-WORK.md"
_ANY_ITEM = re.compile(r"-\s*\[[ xX]\]\s*\([^)]*\)\s*\[\d+\]")


def _item(rank, state=" ", origin="USER", what="x"):
    return "- [%s] (2026-10-01) [%d] %s: %s | size: 1 | open: o | next: n" % (state, rank, origin, what)


def _backlog(tmp_path, *lines):
    p = tmp_path / "OPEN-WORK.md"
    p.write_text(ow.HEADER + "\n".join(lines) + "\n", encoding="utf-8")
    return p


def test_every_item_line_of_the_live_backlog_parses():
    lines = LIVE.read_text(encoding="utf-8").split("\n")
    raw = [ln for ln in lines if _ANY_ITEM.match(ln.strip())]
    items = [it for _, it in ow.iter_items(lines)]
    assert len(raw) > 50                      # the live file, not an empty stand-in
    assert len(items) == len(raw)
    assert all(it["what"] for it in items)


def test_a_full_line_parses_into_its_fields():
    it = ow.parse_line("- [ ] (2026-10-05) [17] USER: build it | size: 3 | open: why | next: do")
    assert it == {"rank": 17, "raised": "2026-10-05", "state": "open", "origin": "USER",
                  "what": "build it", "size": "3", "open": "why", "next": "do", "closed": None}


def test_a_closed_line_carries_its_reason():
    it = ow.parse_line(_item(10, "x") + " | closed: done in 8.5.0")
    assert it["state"] == "closed" and it["closed"] == "done in 8.5.0"


def test_a_label_repeated_inside_a_field_stays_in_that_field():
    it = ow.parse_line("- [ ] (2026-10-05) [3] FOUND: a | size: 1 | open: see | next: x | next: y")
    assert it["next"] == "x | next: y"


def test_prose_and_the_fenced_template_are_not_items(tmp_path):
    p = _backlog(tmp_path, "```", "- [ ] (2026-01-01) [40] USER: inside a fence", "```", _item(10))
    assert [it["rank"] for it in ow.list_items(p, state="all")] == [10]


def test_list_filters_by_state(tmp_path):
    p = _backlog(tmp_path, _item(10), _item(20, "x"), _item(30))
    assert [it["rank"] for it in ow.list_items(p)] == [10, 30]
    assert [it["rank"] for it in ow.list_items(p, state="closed")] == [20]
    assert [it["rank"] for it in ow.list_items(p, state="all")] == [10, 20, 30]


def test_a_missing_backlog_lists_nothing(tmp_path):
    assert ow.list_items(tmp_path / "OPEN-WORK.md") == []


def test_an_unknown_state_is_refused(tmp_path):
    with pytest.raises(ow.MalformedField):
        ow.list_items(_backlog(tmp_path, _item(10)), state="done")


def _git_init(path):
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    subprocess.run(["git", "init", "-q", str(path)], check=True, env=env)


def test_backlog_path_is_the_git_top_level(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    deep = repo / "a" / "b"
    deep.mkdir(parents=True)
    _git_init(repo)
    # a push from a linked worktree exports GIT_DIR; it must not steer the answer
    monkeypatch.setenv("GIT_DIR", str(tmp_path / "nowhere"))
    assert ow.backlog_path(deep).resolve() == (repo / "OPEN-WORK.md").resolve()


def test_backlog_path_outside_a_repo_is_refused(tmp_path):
    with pytest.raises(ow.NotARepo):
        ow.backlog_path(tmp_path)
```

- [ ] **Step 2: Run them to verify they fail**

Run: `env -u VIRTUAL_ENV uv run --with pytest --with PyYAML --with lxml --with defusedxml --with ruamel.yaml --with httpx2 python -m pytest plugins/bitranox/hooks/tests/test_open_work.py -q`
Expected: collection error `ModuleNotFoundError: No module named 'open_work'`.

- [ ] **Step 3: Write the read side**

```python
"""OPEN-WORK.md as data: list, add and close backlog items without hand-editing the file.

The backlog's own header states its rules: one item per line, a rank no other line holds, a closed
item kept with its reason. This module enforces the mechanical ones, so a tool call cannot split a
bullet, reuse a closed item's number or delete a line. Which item outranks which stays the
caller's judgment - nothing here chooses a rank.
"""
import datetime
import os
import re
import subprocess
from pathlib import Path

import self_improve_signals as sig

FILENAME = "OPEN-WORK.md"
ORIGINS = ("USER", "FOUND")
STATES = ("open", "closed", "all")
#: the labelled fields of a line, in the order a written line carries them
LABELS = ("size", "open", "next", "closed")

HEADER = (
    "# Open work\n\n"
    "The standing backlog: everything that outlives a single session. Items leave it by being\n"
    "CLOSED, never by being dropped.\n\n"
    "One item per line:\n\n"
    "```\n"
    "- [ ] (YYYY-MM-DD) [rank] ORIGIN: what it is | size: how much is left | open: why it is "
    "still open | next: the concrete next action\n"
    "```\n\n"
    "Closing an item means `- [x]` plus `| closed: <reason>`. The line stays.\n\n"
)

_ITEM_RX = re.compile(r"-\s*\[([ xX])\]\s*\(([^)]*)\)\s*\[(\d+)\]\s*(.*)$")
_ORIGIN_RX = re.compile(r"(USER|FOUND):\s*(.*)$")
_FIELD_RX = re.compile(r"\s+\|\s+(size|open|next|closed):\s*")
_FENCE_RX = re.compile(r" {0,3}(`{3,}|~{3,})")


class BacklogError(ValueError):
    """A request the backlog refuses; the class name is the `kind` a caller sees."""


class NotARepo(BacklogError):
    pass


class RankTaken(BacklogError):
    pass


class UnknownRank(BacklogError):
    pass


class AlreadyClosed(BacklogError):
    pass


class AmbiguousRank(BacklogError):
    pass


class MalformedField(BacklogError):
    pass


def parse_line(line):
    """The item a line holds, or None for anything that is not an item line."""
    m = _ITEM_RX.match(line.strip())
    if not m:
        return None
    box, raised, rank, rest = m.groups()
    parts = _FIELD_RX.split(rest)
    fields, current = {}, None
    for label, text in zip(parts[1::2], parts[2::2]):
        if label in fields:
            # the label's own words inside an earlier field: keep them there, never drop them
            fields[current] += " | %s: %s" % (label, text)
            continue
        fields[label] = text.strip()
        current = label
    head = parts[0].strip()
    om = _ORIGIN_RX.match(head)
    item = {"rank": int(rank), "raised": raised.strip(),
            "state": "open" if box == " " else "closed",
            "origin": om.group(1) if om else None,
            "what": (om.group(2) if om else head).strip()}
    for label in LABELS:
        item[label] = fields.get(label)
    return item


def iter_items(lines):
    """(index, item) for every item line outside a fenced code block."""
    fence = None
    for i, line in enumerate(lines):
        if fence is not None:
            bare = line.strip()
            # a closer is the opener's character only, at least as long, nothing else on the line
            if bare and set(bare) == {fence[0]} and len(bare) >= len(fence):
                fence = None
            continue
        m = _FENCE_RX.match(line)
        if m:
            fence = m.group(1)
            continue
        item = parse_line(line)
        if item is not None:
            yield i, item


def list_items(path, state="open"):
    """The items of the backlog at `path` in file order; [] when the file does not exist."""
    if state not in STATES:
        raise MalformedField("state must be one of %s, got %r" % (", ".join(STATES), state))
    path = Path(path)
    if not path.is_file():
        return []
    lines = path.read_text(encoding="utf-8").split("\n")
    return [it for _, it in iter_items(lines) if state == "all" or it["state"] == state]


def backlog_path(cwd):
    """OPEN-WORK.md at the git top level of `cwd`.

    Every GIT_ variable is dropped first: git reads GIT_DIR before the cwd, and a push from a
    linked worktree exports it, which would answer for some other repository."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env["LC_ALL"] = "C"
    r = subprocess.run(["git", "-C", str(cwd), "rev-parse", "--show-toplevel"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
    if r.returncode != 0 or not r.stdout.strip():
        raise NotARepo("%s is not inside a git repository, so it has no OPEN-WORK.md" % cwd)
    return Path(r.stdout.strip()) / FILENAME
```

(`datetime` and `sig` are imported here because Task 2 uses them in this same file.)

- [ ] **Step 4: Run the tests to verify they pass**

Run: the Step 2 command. Expected: `10 passed`.

- [ ] **Step 5: Commit**

```bash
git add plugins/bitranox/hooks/open_work.py plugins/bitranox/hooks/tests/test_open_work.py
git commit -F <msg-file> -- plugins/bitranox/hooks/open_work.py plugins/bitranox/hooks/tests/test_open_work.py
```
Message: `open_work: read OPEN-WORK.md as data (parse, list, locate)`.

---

### Task 2: `open_work.py` - write side (add, close)

**Files:**
- Modify: `plugins/bitranox/hooks/open_work.py` (append)
- Test: `plugins/bitranox/hooks/tests/test_open_work.py` (append)

**Interfaces:**
- Consumes: Task 1's `parse_line`, `iter_items`, `HEADER`, `ORIGINS`, the error classes; `sig.memory_lock(path)` (context manager, raises `TimeoutError` on contention).
- Produces: `add_item(path, rank, origin, what, size, open_, next_, raised=None, today=None) -> {"rank": int, "line": str}`; `close_item(path, rank, reason) -> {"rank": int, "line": str}`; `require_line(value, name) -> str`.

**Out of scope:**
- Re-ranking or reordering existing lines - the tool only inserts and closes.

**STOP conditions:**
- `sig.memory_lock` does not exist or is not a context manager taking a path.

- [ ] **Step 1: Append the failing tests** (add `import datetime` to the file's top import block,
not mid-file)

```python
def _lines(p):
    return p.read_text(encoding="utf-8").split("\n")


def _add(p, rank, **kw):
    args = dict(origin="USER", what="w", size="1", open_="o", next_="n",
                today=datetime.date(2026, 10, 8))
    args.update(kw)
    return ow.add_item(p, rank, **args)


def test_a_rank_held_by_a_closed_line_is_refused_with_free_tens(tmp_path):
    p = _backlog(tmp_path, _item(10, "x"))
    with pytest.raises(ow.RankTaken, match="20"):
        _add(p, 10)


def test_a_new_line_goes_after_the_largest_smaller_rank(tmp_path):
    p = _backlog(tmp_path, _item(10), _item(30), _item(20))      # unsorted, as the live file is
    _add(p, 25)
    ranks = [it["rank"] for _, it in ow.iter_items(_lines(p))]
    assert ranks == [10, 30, 20, 25]


def test_a_rank_below_every_item_goes_before_the_first(tmp_path):
    p = _backlog(tmp_path, _item(10), _item(20))
    _add(p, 5)
    assert [it["rank"] for _, it in ow.iter_items(_lines(p))] == [5, 10, 20]
    assert p.read_text(encoding="utf-8").startswith(ow.HEADER)


def test_an_add_grows_the_file_by_exactly_one_line(tmp_path):
    p = _backlog(tmp_path, _item(10), _item(20))
    before = len(_lines(p))
    _add(p, 15)
    assert len(_lines(p)) == before + 1


def test_a_missing_raised_is_today_with_a_question_mark(tmp_path):
    p = _backlog(tmp_path, _item(10))
    out = _add(p, 20)
    assert out["line"].startswith("- [ ] (2026-10-08?) [20] USER: w | size: 1")


def test_a_written_line_parses_back_to_what_was_given(tmp_path):
    p = _backlog(tmp_path)
    _add(p, 40, origin="FOUND", what="a thing", size="2 files", open_="why", next_="do it",
         raised="2026-09-30")
    assert ow.list_items(p) == [{"rank": 40, "raised": "2026-09-30", "state": "open",
                                 "origin": "FOUND", "what": "a thing", "size": "2 files",
                                 "open": "why", "next": "do it", "closed": None}]


def test_a_missing_file_is_created_with_the_header(tmp_path):
    p = tmp_path / "OPEN-WORK.md"
    _add(p, 10)
    text = p.read_text(encoding="utf-8")
    assert text.startswith(ow.HEADER) and text.endswith("\n")
    assert [it["rank"] for it in ow.list_items(p)] == [10]


@pytest.mark.parametrize("field,value", [
    ("what", "two\nlines"),
    ("what", ""),
    ("size", "1 | next: smuggled"),
    ("next_", "   "),
])
def test_a_malformed_field_is_refused_and_nothing_is_written(tmp_path, field, value):
    p = _backlog(tmp_path, _item(10))
    before = p.read_bytes()
    with pytest.raises(ow.MalformedField):
        _add(p, 20, **{field: value})
    assert p.read_bytes() == before


@pytest.mark.parametrize("kw", [{"origin": "ME"}, {"raised": "yesterday"},
                                {"raised": "2026-02-30"}])
def test_a_bad_origin_or_date_is_refused(tmp_path, kw):
    with pytest.raises(ow.MalformedField):
        _add(_backlog(tmp_path), 10, **kw)


@pytest.mark.parametrize("rank", [0, -10, "10", True, 2.5])
def test_a_rank_that_is_not_a_positive_integer_is_refused(tmp_path, rank):
    with pytest.raises(ow.MalformedField):
        _add(_backlog(tmp_path), rank)


def test_close_keeps_the_line_and_appends_the_reason(tmp_path):
    p = _backlog(tmp_path, _item(10), _item(20))
    before = len(_lines(p))
    out = ow.close_item(p, 10, "shipped in 8.6.0")
    assert out["line"] == _item(10, "x") + " | closed: shipped in 8.6.0"
    assert len(_lines(p)) == before
    assert ow.list_items(p, state="closed")[0]["closed"] == "shipped in 8.6.0"


def test_close_refuses_unknown_closed_and_ambiguous_ranks(tmp_path):
    p = _backlog(tmp_path, _item(10, "x"), _item(20), _item(20))
    with pytest.raises(ow.UnknownRank):
        ow.close_item(p, 30, "r")
    with pytest.raises(ow.AlreadyClosed):
        ow.close_item(p, 10, "r")
    with pytest.raises(ow.AmbiguousRank):
        ow.close_item(p, 20, "r")


def test_close_without_a_reason_is_refused(tmp_path):
    with pytest.raises(ow.MalformedField):
        ow.close_item(_backlog(tmp_path, _item(10)), 10, " ")
```

- [ ] **Step 2: Run them to verify they fail**

Run: the Task 1 Step 2 command. Expected: the new tests fail with `AttributeError: module 'open_work' has no attribute 'add_item'`; Task 1's tests still pass.

- [ ] **Step 3: Append the write side to `open_work.py`**

```python
_RAISED_RX = re.compile(r"(\d{4})-(\d{2})-(\d{2})\??$")


def require_line(value, name):
    """`value` as one non-empty line, or MalformedField naming the field."""
    if not isinstance(value, str) or not value.strip():
        raise MalformedField("%s must be a non-empty string" % name)
    if "\n" in value or "\r" in value:
        raise MalformedField("%s must be one line: the backlog holds one item per line" % name)
    if _FIELD_RX.search(" " + value + " "):
        raise MalformedField("%s contains a ' | <label>: ' separator, which would split the "
                             "line into the wrong fields" % name)
    return value.strip()


def _require_rank(rank):
    # bool is an int subclass: True would otherwise be accepted as rank 1
    if isinstance(rank, bool) or not isinstance(rank, int) or rank < 1:
        raise MalformedField("rank must be a positive integer, got %r" % (rank,))
    return rank


def _require_raised(raised, today):
    if raised is None:
        # never an inferred date: an admitted unknown is today's date with a question mark
        return (today or datetime.date.today()).isoformat() + "?"
    if raised == "unknown":
        return raised
    m = _RAISED_RX.match(raised) if isinstance(raised, str) else None
    if not m:
        raise MalformedField("raised must be YYYY-MM-DD, YYYY-MM-DD? or unknown, got %r" % (raised,))
    try:
        datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        raise MalformedField("raised is not a calendar date: %r" % raised) from None
    return raised


def _free_tens_near(rank, taken):
    base = rank - rank % 10
    below = next((r for r in range(base, 0, -10) if r not in taken and r != rank), None)
    above = next(r for r in range(base + 10, base + 10 ** 6, 10) if r not in taken)
    return [r for r in (below, above) if r is not None]


def _write(path, lines):
    tmp = path.with_name("%s.tmp-%d" % (path.name, os.getpid()))
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines))
    os.replace(tmp, path)


def add_item(path, rank, origin, what, size, open_, next_, raised=None, today=None):
    """Insert one open item; returns {"rank", "line"}. Refuses before writing anything."""
    rank = _require_rank(rank)
    if origin not in ORIGINS:
        raise MalformedField("origin must be USER or FOUND, got %r" % (origin,))
    fields = [require_line(v, n) for v, n in ((what, "what"), (size, "size"),
                                              (open_, "open"), (next_, "next"))]
    line = "- [ ] (%s) [%d] %s: %s | size: %s | open: %s | next: %s" % (
        (_require_raised(raised, today), rank, origin) + tuple(fields))
    path = Path(path)
    with sig.memory_lock(path):
        text = path.read_text(encoding="utf-8") if path.is_file() else HEADER
        lines = text.split("\n")
        items = list(iter_items(lines))
        taken = {it["rank"] for _, it in items}
        if rank in taken:
            raise RankTaken("rank %d is already held by a line (closed lines count); free tens "
                            "nearby: %s" % (rank, ", ".join(map(str, _free_tens_near(rank, taken)))))
        smaller = [(it["rank"], i) for i, it in items if it["rank"] < rank]
        if smaller:
            at = max(smaller)[1] + 1
        elif items:
            at = items[0][0]
        else:
            # no item yet: after the last non-empty line, so the file keeps one trailing newline
            at = len(lines) - 1 if lines and lines[-1] == "" else len(lines)
        new = lines[:at] + [line] + lines[at:]
        if new[-1] != "":
            new.append("")
        if len(new) != len(lines) + 1 + (0 if lines[-1] == "" else 1):
            raise BacklogError("internal: an add must grow the file by exactly one line")
        _write(path, new)
    return {"rank": rank, "line": line}


def close_item(path, rank, reason):
    """Mark one open item closed with its reason; the line stays. Returns {"rank", "line"}."""
    rank = _require_rank(rank)
    reason = require_line(reason, "reason")
    path = Path(path)
    with sig.memory_lock(path):
        if not path.is_file():
            raise UnknownRank("no %s here, so there is no rank %d" % (FILENAME, rank))
        lines = path.read_text(encoding="utf-8").split("\n")
        hits = [(i, it) for i, it in iter_items(lines) if it["rank"] == rank]
        if not hits:
            raise UnknownRank("no line holds rank %d" % rank)
        open_hits = [(i, it) for i, it in hits if it["state"] == "open"]
        if not open_hits:
            raise AlreadyClosed("rank %d is already closed" % rank)
        if len(open_hits) > 1:
            raise AmbiguousRank("rank %d labels %d open lines; give one a free number before "
                                "closing either" % (rank, len(open_hits)))
        i = open_hits[0][0]
        # edit the raw line rather than re-rendering it, so an older line keeps its exact text
        lines[i] = re.sub(r"^(\s*-\s*\[) \]", r"\1x]", lines[i], count=1) + " | closed: " + reason
        _write(path, lines)
    return {"rank": rank, "line": lines[i]}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: the Task 1 Step 2 command. Expected: all pass (10 from Task 1 plus the new ones).

- [ ] **Step 5: RED-check one guard with the mutation_arm jig**

Run (launch the jig with a python that has pytest, per its own help; read the `failure` field, not only the verdict):
`uv run ~/.claude/plugins/cache/bitranox-skills/bitranox/8.5.0/skills/compuse-toolbox/scripts/mutation_arm.py --help`
then mutate `if rank in taken:` to `if False:` in `open_work.py` and require `test_a_rank_held_by_a_closed_line_is_refused_with_free_tens` to FAIL; revert with the jig's `--revert`.

- [ ] **Step 6: Commit** - message `open_work: add and close backlog items, refusing before any write`, pathspec the two files.

---

### Task 3: `memory_engine.add_with_advice` - one write path for the CLI and the bridge

**Files:**
- Modify: `plugins/bitranox/hooks/memory_engine.py` (new `add_with_advice` and `_add_advice` near `add_or_update_entry` at line 265; the CLI `add` branch at lines 1955-2010)
- Test: `plugins/bitranox/hooks/tests/test_memory_engine_add_with_advice.py` (new)

**Interfaces:**
- Produces: `add_with_advice(proj, title, hook, body="", type_=None, pin=False, scope_default="", slug=None) -> (slug: str, created: bool, advice: list[str])`. `advice` holds the exact `~ warning: ...` / `~ note: ...` lines the CLI printed, in the same order. Raises what `add_or_update_entry` raises.

**Out of scope:**
- `amend-pinned` and every other verb - unchanged.
- The advisory texts themselves - moved verbatim, not reworded.

**STOP conditions:**
- an existing memory_engine test changes outcome after the refactor (the CLI output must be byte-identical).

- [ ] **Step 1: Write the failing test**

```python
"""add_with_advice: the CLI add and the mod bridge share one write path. ASCII only."""
import pytest

import memory_engine as ME


@pytest.fixture(autouse=True)
def home(tmp_path, monkeypatch):
    h = tmp_path / "home"
    (h / ".claude").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    return h


def test_first_add_creates_and_a_second_updates(tmp_path):
    level = tmp_path / "proj"
    level.mkdir()
    slug, created, _ = ME.add_with_advice(str(level), "Rule", "When x, do y.", body="Because z.")
    assert created is True
    slug2, created2, _ = ME.add_with_advice(str(level), "Rule", "When x, do y now.", body="Because z.")
    assert (slug2, created2) == (slug, False)


def test_a_trigger_less_hook_comes_back_as_advice_not_output(tmp_path, capsys):
    level = tmp_path / "proj"
    level.mkdir()
    _, _, advice = ME.add_with_advice(str(level), "Plain", "Do y.", body="Because z.")
    assert any("no trigger phrase" in a for a in advice)
    assert capsys.readouterr().out == ""


def test_an_over_cap_hook_raises_before_writing(tmp_path):
    level = tmp_path / "proj"
    level.mkdir()
    with pytest.raises(ME.HookTooLong):
        ME.add_with_advice(str(level), "Long", "When x, " + "y" * 600, body="b")
```

- [ ] **Step 2: Run it to verify it fails**

Run: CI-deps pytest on `plugins/bitranox/hooks/tests/test_memory_engine_add_with_advice.py`. Expected: `AttributeError: module 'memory_engine' has no attribute 'add_with_advice'`.

- [ ] **Step 3: Add the function and route the CLI through it**

Insert after `add_or_update_entry` (the module already has `slugify = us.slugify` at line 45 and `_anchor`):

```python
def add_with_advice(proj, title, hook, body="", type_=None, pin=False, scope_default="",
                    slug=None):
    """`add_or_update_entry` plus the advisories the CLI prints after it, returned as data.

    The CLI `add` and the mod bridge both write a fact through here, so a capture made either way
    gets the same validation and the same warnings. Returns (slug, created, advice): `created` is
    False when the fact already had a body (an update); `advice` holds the '~ warning: ...' and
    '~ note: ...' lines in the order the CLI prints them."""
    hook = (hook or "").strip()
    target = slug or slugify(title, type_)
    created = not us.body_path(_anchor(os.path.abspath(str(proj))), target).is_file()
    slug = add_or_update_entry(proj, title=title, hook=hook, body=body, type_=type_, pin=pin,
                               scope_default=scope_default, slug=slug)
    return slug, created, _add_advice(hook, body)


def _add_advice(hook, body):
    advice = []
    if us.hook_over_budget(hook):
        advice.append("~ warning: hook is %d chars (soft cap %d, advisory - fine up to the %d-char "
                      "hard cap; keep it self-sufficient, do not trim load-bearing detail to "
                      "silence this)" % (len(hook), us.HOOK_SOFT_MAX, us.HOOK_HARD_MAX))
    if us.hook_missing_trigger(hook):
        advice.append("~ warning: hook has no trigger phrase - lead with WHEN it applies "
                      "('When <situation>, <directive>'), or it will not fire during reasoning")
    for _advice in capture_constraints.advise(hook, body):
        advice.append(f"~ warning: {_advice}")
    # The recurrence count is the one durable "this was already written and did not hold" signal.
    # Naming BOTH ladders is deliberate: the body cannot say whether a repeat is a rule being
    # skipped or work being re-done.
    seen = us.recurrence_count(body)
    if seen is not None and seen >= us.RECURRENCE_ESCALATE_AT and _user_decided_escalation(body):
        advice.append("~ note: this body records recurrence %d and the user's escalation decision "
                      "- not re-proposing a guard or jig" % seen)
    elif seen is not None and seen >= us.RECURRENCE_ESCALATE_AT:
        advice.append("~ warning: this body records recurrence %d - prose has already failed %d "
                      "times, so do NOT just reword it. Escalate and PROPOSE it to the user in "
                      "THIS turn: a deterministic GUARD if a rule keeps being skipped, a JIG "
                      "(toolbox tool) if the same multi-step work keeps being re-done by hand - "
                      "and BOTH when it is both." % (seen, seen))
    return advice
```

IMPORTANT: copy each advisory string from the CURRENT CLI branch character for character (the
literals above must match what lines ~1985-2010 print today; where they differ, the CLI's text
wins). Then replace the CLI branch from `try:` through the last advisory `print` with:

```python
        try:
            slug, _created, advice = add_with_advice(args.proj, title=args.title, hook=hook,
                                                     body=body, type_=args.type_, pin=args.pin,
                                                     scope_default=scope_default, slug=args.slug)
        except (SlugCollision, HookTooLong, EmptyBody, PinnedEntry, InvalidSlug) as c:
            return _refused(c)
        print(slug)
        for line in advice:
            print(line)
        return 0
```

Keep the `# hook, never args.hook` comment's point: `_add_advice` receives the resolved `hook`.

- [ ] **Step 4: Run the new test and every memory_engine test**

Run: CI-deps pytest on `plugins/bitranox/hooks/tests/ -k "memory_engine or e2e_memory"`. Expected: all pass, same count as before the change plus 3.

- [ ] **Step 5: Commit** - message `memory_engine: add_with_advice, the one write path the CLI and the mod share`.

---

### Task 4: `self_improve_signals.why_not_queued` - the refusal reason, shared

**Files:**
- Modify: `plugins/bitranox/hooks/self_improve_signals.py` (add `why_not_queued` after `read_closed`, line ~794)
- Modify: `plugins/bitranox/skills/meta-self-improve/contrib_queue.py:92-105` (delete `_why_not_queued`), `:290` (call `sig.why_not_queued`)
- Test: `plugins/bitranox/hooks/tests/test_self_improve_signals.py` (append)

**Interfaces:**
- Produces: `sig.why_not_queued(proj, what, target) -> str`: `"shipped earlier"`, `"rejected earlier"`, `"already queued"`, or the could-not-read text.

**STOP conditions:**
- `contrib_queue.py` has a caller of `_why_not_queued` other than line 290 (grep with `command grep -rn`).

- [ ] **Step 1: Append the failing test**

```python
def test_why_not_queued_names_the_outcome_that_closed_it(tmp_path, monkeypatch):
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    proj = str(tmp_path / "proj")
    assert S.add_contribution(proj, {"what": "fix x", "target": "hook"}, strict=True)
    assert S.why_not_queued(proj, "fix x", "hook") == "already queued"
    S.drain_contributions(proj, note="shipped", strict=True)
    assert S.why_not_queued(proj, "fix x", "hook") == "shipped earlier"
```

(The test module imports the signals module as `S`; `drain_contributions(proj, note="",
strict=False, max_items=200)` at `self_improve_signals.py:746` closes the whole queue as SHIPPED.)

- [ ] **Step 2: Run it to verify it fails** - `AttributeError: ... has no attribute 'why_not_queued'`.

- [ ] **Step 3: Move the function**

In `self_improve_signals.py`:

```python
def why_not_queued(proj, what, target):
    """Why an add was refused: "shipped earlier", "rejected earlier" or "already queued".

    The add itself already read the closed set through the raising loader, so an unreadable one
    failed it before this runs; a read failure here is a change in between, and says so rather
    than guessing "already queued"."""
    try:
        closed = {(r.get("what"), r.get("target") or ""): r.get("outcome")
                  for r in read_closed(proj)}
    except OSError as exc:
        return "already queued or closed - the closed set could not be read: %s" % exc
    return {SHIPPED: "shipped earlier", REJECTED: "rejected earlier"}.get(
        closed.get((what, target or "")), "already queued")
```

In `contrib_queue.py`: delete `_why_not_queued` and change line 290 to
`print("not queued (%s): %s" % (sig.why_not_queued(proj, args.what, args.target), args.what))`.

- [ ] **Step 4: Run** the new test plus `plugins/bitranox/skills/meta-self-improve/tests/test_contrib_queue.py`. Expected: all pass.

- [ ] **Step 5: Commit** - message `contrib queue: why_not_queued moves into self_improve_signals for a second caller`.

---

### Task 5: `mod_bridge.py` - one JSON request in, one envelope out

**Files:**
- Create: `plugins/bitranox/hooks/mod_bridge.py`
- Test: `plugins/bitranox/hooks/tests/test_mod_bridge.py`

**Interfaces:**
- Consumes: Tasks 1-4 (`open_work.*`, `ME.add_with_advice`, `sig.add_contribution`, `sig.why_not_queued`).
- Produces: the stdin/stdout contract the TS module relies on. stdin: `{"tool": "<name>", "input": {...}}` (UTF-8 JSON). stdout: one ASCII JSON line, `{"ok": true, "tool": ..., "data": ...}` or `{"ok": false, "tool": ..., "error": {"kind": ..., "message": ...}}`. Exit 0 success, 1 refusal, 2 could not run (bad JSON, unknown tool). The working directory is the session's (the TS module passes none, so `$.process.run` uses the session's).

**STOP conditions:**
- running the bridge as a script cannot import `memory_engine` (it must, from `hooks/` as `sys.path[0]`).

- [ ] **Step 1: Write the failing tests**

```python
"""mod_bridge: driven as the mod drives it - a real subprocess, JSON on stdin. ASCII only."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

BRIDGE = Path(__file__).resolve().parents[1] / "mod_bridge.py"


@pytest.fixture
def env(tmp_path):
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    return {**{k: v for k, v in os.environ.items() if not k.startswith("GIT_")},
            "HOME": str(home), "USERPROFILE": str(home)}


@pytest.fixture
def repo(tmp_path, env):
    r = tmp_path / "repo"
    r.mkdir()
    subprocess.run(["git", "init", "-q", str(r)], check=True, env=env)
    return r


def call(cwd, env, tool, payload=None, raw=None):
    data = raw if raw is not None else json.dumps({"tool": tool, "input": payload or {}})
    p = subprocess.run([sys.executable, str(BRIDGE)], input=data.encode("utf-8"),
                       capture_output=True, cwd=cwd, env=env)
    return p.returncode, json.loads(p.stdout.decode("ascii"))


ITEM = {"rank": 20, "origin": "USER", "what": "w", "size": "1", "open": "o", "next": "n"}


def test_backlog_add_then_list(repo, env):
    rc, out = call(repo, env, "backlog_add", ITEM)
    assert (rc, out["ok"], out["data"]["rank"]) == (0, True, 20)
    rc, out = call(repo, env, "backlog_list")
    assert rc == 0 and [it["rank"] for it in out["data"]["items"]] == [20]
    assert (repo / "OPEN-WORK.md").is_file()


def test_a_taken_rank_is_a_refusal_with_its_kind(repo, env):
    call(repo, env, "backlog_add", ITEM)
    rc, out = call(repo, env, "backlog_add", ITEM)
    assert (rc, out["ok"], out["error"]["kind"]) == (1, False, "RankTaken")


def test_backlog_close(repo, env):
    call(repo, env, "backlog_add", ITEM)
    rc, out = call(repo, env, "backlog_close", {"rank": 20, "reason": "done"})
    assert rc == 0 and out["data"]["line"].endswith("| closed: done")


def test_list_without_a_backlog_says_so(repo, env):
    rc, out = call(repo, env, "backlog_list")
    assert rc == 0 and out["data"]["items"] == [] and "no OPEN-WORK.md" in out["data"]["note"]


def test_memory_add_creates_then_updates_with_advice(tmp_path, env):
    level = tmp_path / "proj"
    level.mkdir()
    fact = {"title": "Rule", "hook": "Do y.", "body": "Because z.", "level": str(level)}
    rc, out = call(tmp_path, env, "memory_add", fact)
    assert rc == 0 and out["data"]["action"] == "created"
    assert any("no trigger phrase" in w for w in out["data"]["warnings"])
    rc, out = call(tmp_path, env, "memory_add", fact)
    assert rc == 0 and out["data"]["action"] == "updated"


def test_memory_add_over_cap_hook_is_refused(tmp_path, env):
    level = tmp_path / "proj"
    level.mkdir()
    rc, out = call(tmp_path, env, "memory_add",
                   {"title": "L", "hook": "When x, " + "y" * 600, "body": "b", "level": str(level)})
    assert (rc, out["error"]["kind"]) == (1, "HookTooLong")


def test_memory_add_bad_type_is_refused(tmp_path, env):
    rc, out = call(tmp_path, env, "memory_add",
                   {"title": "T", "hook": "When x, y.", "body": "b", "type": "note"})
    assert (rc, out["error"]["kind"]) == (1, "BadInput")


def test_contrib_add_queues_once(tmp_path, env):
    req = {"what": "fix x", "target": "hook", "why": "seen twice"}
    rc, out = call(tmp_path, env, "contrib_add", req)
    assert (rc, out["data"]) == (0, {"queued": True})
    rc, out = call(tmp_path, env, "contrib_add", req)
    assert rc == 0 and out["data"] == {"queued": False, "reason": "already queued"}


def test_a_missing_required_field_is_a_refusal(repo, env):
    rc, out = call(repo, env, "backlog_add", {k: v for k, v in ITEM.items() if k != "what"})
    assert (rc, out["error"]["kind"]) == (1, "MalformedField")


@pytest.mark.parametrize("raw", ["not json", "[]", '{"tool": "nope", "input": {}}',
                                 '{"tool": "backlog_list", "input": []}'])
def test_a_request_the_bridge_cannot_run_exits_2(tmp_path, env, raw):
    rc, out = call(tmp_path, env, None, raw=raw)
    assert (rc, out["ok"], out["error"]["kind"]) == (2, False, "BadRequest")
```

- [ ] **Step 2: Run them to verify they fail** - every test errors on the missing `mod_bridge.py` (`json.loads` of empty stdout).

- [ ] **Step 3: Write `mod_bridge.py`**

```python
"""One JSON request in on stdin, one JSON envelope out on stdout: the Claude Code mod's way in.

hooks/mods/register.ts registers the model-callable tools and hands each call here, so every rule
those tools obey lives in tested Python and the TypeScript only relays. Exit 0 on success, 1 when
the request was refused (the envelope names the kind), 2 when the bridge could not run it at all.
Output is ASCII-escaped JSON, so no console code page can mangle it.
"""
import json
import os
import sys
from pathlib import Path

import memory_engine as ME
import open_work as ow
import self_improve_signals as sig

MEMORY_TYPES = (None, "user", "feedback", "project", "reference")


class BadInput(ValueError):
    """A tool input the bridge refuses before calling anything."""


class BadRequest(ValueError):
    """A request the bridge cannot run: not JSON, not an object, an unknown tool."""


REFUSALS = (ow.BacklogError, BadInput, ME.SlugCollision, ME.HookTooLong, ME.EmptyBody,
            ME.PinnedEntry, ME.InvalidSlug, OSError)


def _backlog_list(inp, cwd):
    path = ow.backlog_path(cwd)
    data = {"path": str(path), "items": ow.list_items(path, state=inp.get("state", "open"))}
    if not path.is_file():
        data["note"] = "no OPEN-WORK.md at %s yet; backlog_add creates it" % path.parent
    return data


def _backlog_add(inp, cwd):
    return ow.add_item(ow.backlog_path(cwd), inp.get("rank"), inp.get("origin"), inp.get("what"),
                       inp.get("size"), inp.get("open"), inp.get("next"), raised=inp.get("raised"))


def _backlog_close(inp, cwd):
    return ow.close_item(ow.backlog_path(cwd), inp.get("rank"), inp.get("reason"))


def _text(inp, name):
    value = inp.get(name)
    if not isinstance(value, str) or not value.strip():
        raise BadInput("%s must be a non-empty string" % name)
    return value


def _memory_add(inp, cwd):
    level = Path(inp.get("level") or cwd)
    if not level.is_dir():
        raise BadInput("level is not a directory: %s" % level)
    type_ = inp.get("type")
    if type_ not in MEMORY_TYPES:
        raise BadInput("type must be one of user, feedback, project, reference, got %r" % (type_,))
    slug, created, advice = ME.add_with_advice(
        str(level), title=_text(inp, "title"), hook=_text(inp, "hook"), body=_text(inp, "body"),
        type_=type_, slug=inp.get("slug"))
    return {"slug": slug, "level": str(level.resolve()),
            "action": "created" if created else "updated", "warnings": advice}


def _contrib_add(inp, cwd):
    what = ow.require_line(_text(inp, "what"), "what")
    target = ow.require_line(_text(inp, "target"), "target")
    proj = str(cwd)
    queued = sig.add_contribution(proj, {"what": what, "target": target,
                                         "why": _text(inp, "why"), "source": "mod:contrib_add"},
                                  strict=True)
    if queued:
        return {"queued": True}
    return {"queued": False, "reason": sig.why_not_queued(proj, what, target)}


TOOLS = {"backlog_list": _backlog_list, "backlog_add": _backlog_add,
         "backlog_close": _backlog_close, "memory_add": _memory_add, "contrib_add": _contrib_add}


def _request(raw):
    try:
        req = json.loads(raw)
    except ValueError as exc:
        raise BadRequest("stdin is not JSON: %s" % exc) from None
    if not isinstance(req, dict) or not isinstance(req.get("input", {}), dict):
        raise BadRequest("the request must be {\"tool\": <name>, \"input\": {...}}")
    if req.get("tool") not in TOOLS:
        raise BadRequest("unknown tool %r; known: %s" % (req.get("tool"), ", ".join(sorted(TOOLS))))
    return req["tool"], req.get("input", {})


def _emit(envelope, rc):
    sys.stdout.write(json.dumps(envelope, ensure_ascii=True) + "\n")
    sys.stdout.flush()
    return rc


def main():
    tool = None
    try:
        tool, inp = _request(sys.stdin.buffer.read().decode("utf-8", errors="replace"))
    except BadRequest as exc:
        return _emit({"ok": False, "tool": tool,
                      "error": {"kind": "BadRequest", "message": str(exc)}}, 2)
    try:
        data = TOOLS[tool](inp, Path(os.getcwd()))
    except REFUSALS as exc:
        return _emit({"ok": False, "tool": tool,
                      "error": {"kind": type(exc).__name__, "message": str(exc)}}, 1)
    return _emit({"ok": True, "tool": tool, "data": data}, 0)


if __name__ == "__main__":
    sys.exit(main())
```

Note `"input": []` must be refused: `isinstance(req.get("input", {}), dict)` is False for a list.

- [ ] **Step 4: Run** `test_mod_bridge.py` with CI deps. Expected: all pass.

- [ ] **Step 5: RED-check** with the mutation_arm jig: make `_emit(..., 1)` return 0 in the refusal branch and require `test_a_taken_rank_is_a_refusal_with_its_kind` to fail; revert.

- [ ] **Step 6: Commit** - message `mod_bridge: the JSON entry point the Claude Code mod relays tool calls through`.

---

### Task 6: the TypeScript mod and its registration

**Files:**
- Create: `plugins/bitranox/hooks/mods/register.ts`
- Create: `plugins/bitranox/hooks/mods/register.test.ts`
- Modify: `plugins/bitranox/hooks/hooks.json` (add a top-level `"modules": ["./mods/register.ts"]`, through a JSON round-trip, never a hand edit)

**Interfaces:**
- Consumes: Task 5's stdin/stdout/exit contract.
- Produces: tools `mcp__bitranox__backlog_list`, `..._backlog_add`, `..._backlog_close`, `..._memory_add`, `..._contrib_add`.

**Out of scope:**
- Every classic entry in `hooks.json` - unchanged, order kept.

**STOP conditions:**
- `claude plugin validate plugins/bitranox` reports an error (warnings are fine);
- a repo test that iterates `hooks.json` (registration tests) fails on the new `modules` key - report it rather than special-casing the key;
- `claude plugin test` cannot run in this plugin folder.

- [ ] **Step 1: Write the failing plugin test** (`register.test.ts`). Findings from the 2026-10-08 probe that shape it: the test kit has NO engine beneath the plugin, so the test answers every `$` call the plugin makes (`tool.register`, `session.start`, `process.run`, `env.get` via `mock.env`); an op hook (`tool.register`, `process.run`) answers `{ value: ... }`; `session.start` answers `{ cwd }`.

```ts
import type { On } from "claude-code";
import { test, expect, mock } from "claude-code/testing";

type RunInit = { stdin?: string; timeoutMs?: number };
type Run = { argv: readonly string[]; init?: RunInit };

const NAMES = ["backlog_list", "backlog_add", "backlog_close", "memory_add", "contrib_add"];

// The kit has no engine beneath the plugin: every $ call the plugin makes is answered here.
function stubs(on: On, stdout: string, exitCode = 0) {
  const runs: Run[] = [];
  const registered: string[] = [];
  on("tool.register", async (_$, e) => {
    const name = String((e as { name: string }).name);
    registered.push(name);
    return { value: { tool: `mcp__bitranox__${name}` } };
  });
  on("session.start", async (_$, e) => ({ cwd: String((e as { cwd: string }).cwd) }));
  on("process.run", async (_$, e) => {
    runs.push(e as unknown as Run);
    return { value: { exitCode, stdout, stderr: "boom", isStdoutTruncated: false, isStderrTruncated: false } };
  });
  return { runs, registered };
}

test("registers all five tools at session start", async ($, on) => {
  mock.env(on, {});
  const s = stubs(on as never, "{}");
  await $.session.start({ source: "startup", cwd: "/tmp" } as never);
  expect([...s.registered].sort()).toEqual([...NAMES].sort());
});

test("a call sends the input without the reserved keys and relays the envelope", async ($, on) => {
  mock.env(on, {});
  const env = JSON.stringify({ ok: true, tool: "backlog_add", data: { rank: 20, line: "L" } });
  const s = stubs(on as never, env);
  await $.session.start({ source: "startup", cwd: "/tmp" } as never);
  const r = await $.tool.call({ tool: "mcp__bitranox__backlog_add", rank: 20, what: "w" } as never);
  expect(JSON.stringify(r)).toContain('"line":"L"');
  const sent = JSON.parse(String(s.runs[0].init?.stdin));
  expect(sent).toEqual({ tool: "backlog_add", input: { rank: 20, what: "w" } });
  expect(String(s.runs[0].argv[s.runs[0].argv.length - 1])).toContain("mod_bridge.py");
  expect(s.runs[0].argv[0]).toBe("bash");
});

test("output that is not an envelope comes back as BridgeFailed with the exit code", async ($, on) => {
  mock.env(on, {});
  stubs(on as never, "Traceback ...", 2);
  await $.session.start({ source: "startup", cwd: "/tmp" } as never);
  const r = await $.tool.call({ tool: "mcp__bitranox__backlog_list" } as never);
  expect(JSON.stringify(r)).toContain("BridgeFailed");
  expect(JSON.stringify(r)).toContain("exit 2");
});

test("Windows: CLAUDE_CODE_GIT_BASH_PATH is the interpreter when set", async ($, on) => {
  mock.env(on, { CLAUDE_CODE_GIT_BASH_PATH: "C:\\Git\\bin\\bash.exe" });
  const s = stubs(on as never, JSON.stringify({ ok: true, tool: "backlog_list", data: {} }));
  await $.session.start({ source: "startup", cwd: "/tmp" } as never);
  await $.tool.call({ tool: "mcp__bitranox__backlog_list" } as never);
  expect(s.runs[0].argv[0]).toBe("C:\\Git\\bin\\bash.exe");
});
```

If `toEqual` on the sent input fails because the engine stamps a key beyond `tool` and `tool_use_id` onto `e`, check the `McpToolCallInputFallback` type in the bundled `claude-code.d.ts`: add the key to `RESERVED` only if the types mark it reserved; otherwise STOP and report.

- [ ] **Step 2: Run it to verify it fails**

Run: `claude plugin test plugins/bitranox`. Expected: FAIL (no module registered: `tool.register` never called).

- [ ] **Step 3: Write `register.ts`**

```ts
import type { Register } from "claude-code";

// The tools' rules live in hooks/mod_bridge.py and the Python it calls; this module only relays.
const TIMEOUT_MS = 60_000;
const RESERVED = new Set(["tool", "tool_use_id"]);

const str = (description: string) => ({ type: "string", description });

const TOOLS = [
  {
    name: "backlog_list",
    description:
      "List this repo's OPEN-WORK.md backlog items (open by default). Read it before backlog_add to choose a rank.",
    inputSchema: { type: "object", properties: { state: { type: "string", enum: ["open", "closed", "all"] } } },
  },
  {
    name: "backlog_add",
    description:
      "Add one item to this repo's OPEN-WORK.md backlog. YOU choose the rank: USER items above FOUND ones, a USER item the user deferred below the live USER items but above every FOUND one, bigger size first within an origin. The tool refuses a rank any line already holds (closed lines included) and suggests free tens. Omit `raised` unless you know when it was first raised: the tool then writes today's date with '?', never a guessed one.",
    inputSchema: {
      type: "object",
      required: ["rank", "origin", "what", "size", "open", "next"],
      properties: {
        rank: { type: "integer", minimum: 1 },
        origin: { type: "string", enum: ["USER", "FOUND"] },
        what: str("what it is, one line (the user's own words for a USER item)"),
        size: str("how much is left; 'unknown' is honest, an invented count is not"),
        open: str("why it is still open"),
        next: str("the concrete next action"),
        raised: str("YYYY-MM-DD, YYYY-MM-DD? or unknown; omit for today with '?'"),
      },
    },
  },
  {
    name: "backlog_close",
    description: "Close one open OPEN-WORK.md item by rank with a reason. The line stays, marked [x].",
    inputSchema: {
      type: "object",
      required: ["rank", "reason"],
      properties: { rank: { type: "integer", minimum: 1 }, reason: str("why it is closed, one line") },
    },
  },
  {
    name: "memory_add",
    description:
      "Capture or update one curated bitranox memory fact (the memory engine's add). `level` is the directory whose subtree the fact concerns (default: the session cwd); an update must target the level that owns the fact, or it is refused as SlugCollision. The hook is trigger-first ('When <situation>, <directive>'), at most 500 chars; warnings come back in the result.",
    inputSchema: {
      type: "object",
      required: ["title", "hook", "body"],
      properties: {
        title: str("short title"),
        hook: str("one line, trigger-first"),
        body: str("the fact body (multi-line allowed)"),
        level: str("directory to capture at; default the session cwd"),
        type: { type: "string", enum: ["user", "feedback", "project", "reference"] },
        slug: str("target an existing fact explicitly"),
      },
    },
  },
  {
    name: "contrib_add",
    description:
      "Queue one bitranox hook or skill contribution (contrib_queue add) instead of fixing the tool in place during unrelated work. A duplicate or an already closed intent is not re-queued; the result says why.",
    inputSchema: {
      type: "object",
      required: ["what", "target", "why"],
      properties: {
        what: str("the change, one line"),
        target: str("where it goes, e.g. hook or skill:<name>"),
        why: str("the evidence it is needed"),
      },
    },
  },
] as const;

function failure(tool: string, kind: string, message: string) {
  return { ok: false, tool, error: { kind, message } };
}

function envelopeFrom(tool: string, run: { exitCode: number; stdout: string; stderr: string }) {
  try {
    const parsed: unknown = JSON.parse(run.stdout);
    if (parsed !== null && typeof parsed === "object" && "ok" in parsed) return parsed;
  } catch {
    // not an envelope: report what the bridge printed instead
  }
  const said = (run.stderr || run.stdout).slice(0, 2000);
  return failure(tool, "BridgeFailed", `exit ${run.exitCode}: ${said}`);
}

export const register: Register = (on) => {
  on("session.start", async ($, e, next) => {
    for (const spec of TOOLS) await $.tool.register(spec as never);
    return next(e);
  });

  for (const spec of TOOLS) {
    on("tool.call", { tool: `mcp__bitranox__${spec.name}` }, async ($, e) => {
      const input = Object.fromEntries(
        Object.entries(e as Record<string, unknown>).filter(([k]) => !RESERVED.has(k)),
      );
      // On Windows a bare "bash" can resolve to the WSL stub; Claude Code's own Git Bash setting wins.
      const bash = (await $.env.get("CLAUDE_CODE_GIT_BASH_PATH")) ?? "bash";
      const root = $.plugin.root;
      try {
        const run = await $.process.run(
          [bash, `${root}/hooks/run-python.sh`, `${root}/hooks/mod_bridge.py`],
          { stdin: JSON.stringify({ tool: spec.name, input }), timeoutMs: TIMEOUT_MS },
        );
        return { result: envelopeFrom(spec.name, run) as never };
      } catch (err) {
        return { result: failure(spec.name, "BridgeFailed", String(err)) as never };
      }
    }).catch(($, e, next) =>
      next.called ? next(e) : { deny: `bitranox: the ${spec.name} tool failed before it ran.` },
    );
  }
};
```

- [ ] **Step 4: Register the module in `hooks.json` through a round-trip**

Write a short round-trip script to the scratchpad and run it with `python3` (never sed, never a hand edit): load `plugins/bitranox/hooks/hooks.json` with `json`, assert `"modules" not in d`, set `d["modules"] = ["./mods/register.ts"]`, dump with `indent=2` and a trailing newline, re-load and assert both `d["hooks"]` is unchanged and `d["modules"]` is set. Then `git diff --stat plugins/bitranox/hooks/hooks.json` must show only added lines.

- [ ] **Step 5: Validate and run**

Run: `claude plugin validate plugins/bitranox` - expected `Validation passed` (warnings allowed), listing `tool.call{tool=mcp__bitranox__...}` five times and `$.tool.register`, `$.process.run`, `$.env.get`.
Run: `claude plugin test plugins/bitranox` - expected `4 pass, 0 fail`.
RED-check: change `?? "bash"` to `?? "sh"` and require the reserved-keys test to fail; revert.

- [ ] **Step 6: Run the whole Python suite** (CI deps, `plugins/bitranox/hooks/tests/` and `plugins/bitranox/skills/`) - any registration test that iterates `hooks.json` must still pass (STOP if not).

- [ ] **Step 7: Commit** - message `mods: register the backlog and memory tools from a hooks module`.

---

### Task 7: live end-to-end through a real session

**Files:** none (verification).

- [ ] **Step 1:** In the scratchpad, `git init` a throwaway repo `e2e-repo`.
- [ ] **Step 2:** From inside it run (prompt right after `-p`; stdin from `/dev/null`):
  `claude -p "Use mcp__bitranox__backlog_add to add rank 10, origin FOUND, what 'e2e probe', size '1', open 'probe', next 'none'; then call mcp__bitranox__backlog_list and print the ranks it returns." --plugin-dir <abs path>/plugins/bitranox --allowedTools mcp__bitranox__backlog_add mcp__bitranox__backlog_list --model haiku < /dev/null > out.txt 2> err.txt`
- [ ] **Step 3:** Pass = `e2e-repo/OPEN-WORK.md` contains `[10] FOUND: e2e probe`, and `err.txt` names no skipped hook. Judge by the FILE, not by the model's reply.
- [ ] **Step 4:** Record the measured wall time of one tool call (from `--debug-file` timestamps or `time`) in the CHANGELOG draft; it replaces the design's UNMEASURED Python-start estimate.

---

### Task 8: release gate 1 - an older Claude Code without mods

**Files:** none (verification). If it FAILS, stop and take it to the user; do not ship.

- [ ] **Step 1:** Find the first Claude Code release that loads `modules` (the lowest version where `claude plugin validate` accepts it); pick the release just before it, and one well before (e.g. a 2.0.x). Install each into the scratchpad: `npm install --prefix <scratch>/cc-old @anthropic-ai/claude-code@<version>` (verify the download progresses within a minute).
- [ ] **Step 2:** Control first: with the UNCHANGED plugin (a separate checkout of origin/master: `git worktree add <scratch>/base origin/master`, removed afterwards) run `<scratch>/cc-old/node_modules/.bin/claude -p "say ok" --plugin-dir <scratch>/base/plugins/bitranox --debug-file <scratch>/old-base.log < /dev/null` and confirm the classic SessionStart hook ran (the debug log names `session-start.py`).
- [ ] **Step 3:** Same with this branch's `plugins/bitranox`. Pass = the classic hooks run exactly as in the control and the log shows no plugin-load error. Fail = any classic hook missing, or the plugin refused.
- [ ] **Step 4:** Write the result (versions, pass/fail, log lines) into the CHANGELOG draft and the [17] line.

---

### Task 9: release gate 2 - Windows

**Files:** none (verification). If it FAILS, stop and take it to the user.

- [ ] **Step 1:** Copy the branch's `plugins/bitranox` to the Windows dev VM (tar + scp; the host, user and key are in the machine-local memory fact about testing Windows-only code; scp destination with backslashes).
- [ ] **Step 2:** On the VM, in a git repo, pipe `{"tool": "backlog_add", "input": {...}}` into `bash run-python.sh mod_bridge.py` from Git Bash and confirm exit 0 and the line in `OPEN-WORK.md`; then run Task 7's headless `claude -p` there (with `--plugin-dir`), and confirm the file again.
- [ ] **Step 3:** Confirm which `bash` the mod resolved (set `CLAUDE_CODE_GIT_BASH_PATH` if the VM's Claude Code uses one; a WSL `bash.exe` resolution is a FAIL).

---

### Task 10: ship

**Files:**
- Modify: `plugins/bitranox/.claude-plugin/plugin.json` and `pyproject.toml` (version), `CHANGELOG.md`, `docs/reference.md` (a short "Model-callable tools" section: the five tools, what each refuses, that they need Claude Code with mods support), `OPEN-WORK.md` ([17] closed with the gate results; a new FOUND item for folding `session-start.py`'s parser onto `open_work.py`).

- [ ] **Step 1:** `git fetch origin` and re-read `plugin.json`'s version on `origin/master`; the next minor above it is this release (8.6.0 if origin is still 8.5.0). Assert the current value before writing it (`assert doc["version"] == "<read value>"`), in both `plugin.json` and `pyproject.toml`, through a JSON/TOML round-trip.
- [ ] **Step 2:** CHANGELOG `Added` entry (ASCII, describes the current behaviour, no history narrative).
- [ ] **Step 3:** `python3 plugins/bitranox/hooks/repo-gate.py --ci` - expected exit 0. Also regenerate any derived artifact the gate names.
- [ ] **Step 4:** Rebase onto `origin/master`, merge to `master` fast-forward, push (the pre-push gate runs the suite; a lost race means fetch, rebase, re-bump above origin, push again).
- [ ] **Step 5:** Watch CI with the toolbox `ci_wait.py --sha <full sha derived in the same command>`; every workflow green, windows-latest included.
- [ ] **Step 6:** Close [17] via the new `backlog_close` itself only if the session has the mod loaded; otherwise by a pathspec edit of that one line.
