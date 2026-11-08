"""What an arm's kept files show beyond cost and the void rules: subagent overlap, idea markers, the suite's outcome.

Three readers, each over one file kind the arm dir keeps, each memory-bounded (line by line, only
the current record held), and each answering None when its file is absent, so "nothing found" is
never confused with "nothing to look at":

- subagent_overlap: the subagent transcripts under arms/<label>/transcripts/. A stream's Agent call
  and its tool_result say nothing about parallelism for run_in_background, whose launch returns at
  once; each transcript's own first and last timestamp do.
- idea_markers: the `[abx] idea=N ...` lines an arm writes to .bitranox/sdd/progress.md. That file
  is untracked, so it is in no branch: the writing tool calls in the stream and the subagent
  transcripts are the only record left.
- suite_outcome (and step_outcome, the same reading of any floor step, the gate's included): the
  step split by its log into a missing build prerequisite (a build script that cannot find
  protoc), does-not-compile (rustc E-codes and the symbols they name) and fails-at-run-time (N of
  M tests), where cargo exits 101 for all three.

Stdlib only, like every script here: the repo gate runs this suite in a bare environment.
"""
from __future__ import annotations

import json
import re
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

__all__ = [
    "MISSING_CAP",
    "SUITE_FAILED",
    "SUITE_NOT_FINISHED",
    "SUITE_NO_COMPILE",
    "SUITE_PASSED",
    "SUITE_PREREQ_MISSING",
    "SUITE_TESTS_FAILED",
    "describe_ideas",
    "describe_subagents",
    "describe_suite",
    "idea_markers",
    "step_outcome",
    "subagent_overlap",
    "suite_outcome",
]

# Claude Code names a subagent's transcript agent-<id>.jsonl (beside it agent-<id>.meta.json); the
# main session's transcript is <session-id>.jsonl, so the prefix alone tells them apart.
SUBAGENT_PREFIX = "agent-"
MARKER = re.compile(r"\[abx\] idea=(\d+)[^\n]*")
# The tools whose input IS the text written, and the input fields that carry it.
_WRITE_FIELDS = {"Write": ("content",), "Edit": ("new_string",), "NotebookEdit": ("new_source",)}
# A shell command writes when it appends (>>), tees, or redirects stdout to a file: "2>/dev/null"
# (a digit before >) and ">&2" (a descriptor after it) are not writes of the marker.
_SHELL_WRITE = re.compile(r">>|\btee\b|(?<![0-9&>])>(?![&>])")
# In a shell command the marker line runs on into its quote and redirect; that tail is not the line.
_SHELL_TAIL = re.compile(r"""\s*(?:\\n)?["']?\s*(?:>>?|\|).*$""")

SUITE_PASSED = "passed"
SUITE_NO_COMPILE = "does_not_compile"
SUITE_TESTS_FAILED = "tests_failed"
SUITE_FAILED = "failed"  # a non-zero exit whose log shows neither shape
SUITE_NOT_FINISHED = "did_not_finish"  # timed out, could not start, held open, or the suite was not placed
# A build script failed for want of a tool the arm's worktree does not have (protoc, which a
# gitignored .packages dir holds in the real checkout): the arm's code was never compiled, so
# this is neither its compile error nor its failing test.
SUITE_PREREQ_MISSING = "build_prerequisite_missing"
# At most this many missing symbols are listed; every error code is still counted.
MISSING_CAP = 20
_ERROR_CODE = re.compile(r"^error\[(E\d{4})\]:(.*)$")
_COULD_NOT_COMPILE = re.compile(r"^error: could not compile ")
_TEST_RESULT = re.compile(r"^test result: \w+\. (\d+) passed; (\d+) failed;")
_BACKTICKED = re.compile(r"`([^`]+)`")
_BUILD_SCRIPT_FAILED = re.compile(r"^error: failed to run custom build command for ")
# How a build script says protoc is missing: prost-build 0.12+ ("Could not find `protoc`"), older
# prost-build ("failed to invoke protoc"), and a PROTOC path that does not exist. cargo indents a
# build script's stderr, so these are searched anywhere in the line.
_PROTOC_MISSING = re.compile(r"Could not find `?protoc|failed to invoke protoc|protoc\S*:? .*No such file or directory")
# The rustc codes that mean a name was not found: unresolved import or path, unknown value, type,
# struct, trait, method or field. Their first backticked name is the symbol the code expected.
_MISSING_CODES = frozenset({"E0405", "E0407", "E0412", "E0422", "E0423", "E0425", "E0432", "E0433",
                            "E0560", "E0599", "E0609"})


def _records(path: Path) -> Iterator[dict[str, Any]]:
    """Every JSON-object line of a JSONL file; a torn or non-object line is skipped."""
    with path.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try:
                record = json.loads(line)
            except (ValueError, RecursionError):
                continue
            if isinstance(record, dict):
                yield record


# --- subagent overlap ----------------------------------------------------------------------------

def _instant(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return stamp if stamp.tzinfo else stamp.replace(tzinfo=timezone.utc)


def _span(path: Path) -> tuple[datetime, datetime] | None:
    """(earliest, latest) timestamp of one transcript, whatever the line order; None without one."""
    first: datetime | None = None
    last: datetime | None = None
    for record in _records(path):
        stamp = _instant(record.get("timestamp"))
        if stamp is None:
            continue
        first = stamp if first is None or stamp < first else first
        last = stamp if last is None or stamp > last else last
    return None if first is None or last is None else (first, last)


def _max_concurrent(spans: list[tuple[datetime, datetime]]) -> int:
    # An end sorts before a start at the same instant: one agent ending as the next begins is a
    # hand-over, not two running at once.
    events = sorted([(start, 1) for start, _ in spans] + [(end, -1) for _, end in spans])
    running = peak = 0
    for _, delta in events:
        running += delta
        peak = max(peak, running)
    return peak


def subagent_overlap(transcripts: Path) -> dict[str, int] | None:
    """How many subagent transcripts an arm left, and the most of them running at once.

    Args:
        transcripts: the arm's transcripts dir (arms/<label>/transcripts), searched recursively for
            agent-*.jsonl; the main session's transcript and the .meta.json files are not counted.

    Returns:
        None when the dir does not exist (no transcripts were kept, so nothing can be said), else
        {"transcripts": files found, "max_concurrent": the peak number whose [first, last]
        timestamp spans overlap, "untimed": files with no parsable timestamp, left out of the peak}.
    """
    if not transcripts.is_dir():
        return None
    spans: list[tuple[datetime, datetime]] = []
    files = untimed = 0
    for path in sorted(transcripts.rglob(f"{SUBAGENT_PREFIX}*.jsonl")):
        if not path.is_file():
            continue
        files += 1
        span = _span(path)
        if span is None:
            untimed += 1
        else:
            spans.append(span)
    return {"transcripts": files, "max_concurrent": _max_concurrent(spans), "untimed": untimed}


# --- idea markers --------------------------------------------------------------------------------

def _shell_marker_text(command: str) -> list[str]:
    if not _SHELL_WRITE.search(command):
        return []
    return [_SHELL_TAIL.sub("", m.group(0)) for m in MARKER.finditer(command)]


def _written_texts(name: str, tool_input: dict[str, Any]) -> list[str]:
    """The text a writing tool call puts into a file; [] for a call that writes nothing."""
    if name == "Bash":
        command = tool_input.get("command")
        return ["\n".join(_shell_marker_text(command))] if isinstance(command, str) else []
    if name == "MultiEdit":
        edits = tool_input.get("edits")
        edits = edits if isinstance(edits, list) else []
        return [e["new_string"] for e in edits if isinstance(e, dict) and isinstance(e.get("new_string"), str)]
    return [v for f in _WRITE_FIELDS.get(name, ()) if isinstance(v := tool_input.get(f), str)]


def _tool_uses(record: dict[str, Any]) -> Iterator[dict[str, Any]]:
    """The tool_use blocks of an assistant record (what the arm DID, never what it was told)."""
    if record.get("type") != "assistant":
        return
    message = record.get("message")
    content = message.get("content") if isinstance(message, dict) else None
    for block in content if isinstance(content, list) else []:
        if isinstance(block, dict) and block.get("type") == "tool_use" and isinstance(block.get("input"), dict):
            yield block


class _IdeaTally:
    """Distinct marker lines per idea number, the first seen of each, and the writing calls."""

    def __init__(self) -> None:
        self.lines: dict[int, list[str]] = {}
        self.writes = 0
        self.seen_ids: set[str] = set()

    def add_call(self, block: dict[str, Any]) -> None:
        tid = block.get("id")
        if isinstance(tid, str):
            if tid in self.seen_ids:
                return
            self.seen_ids.add(tid)
        markers = [m for text in _written_texts(str(block.get("name")), block["input"]) for m in MARKER.finditer(text)]
        if markers:
            self.writes += 1
        for m in markers:
            line = m.group(0).strip()
            known = self.lines.setdefault(int(m.group(1)), [])
            if line not in known:
                known.append(line)

    def result(self) -> dict[str, Any]:
        ideas = {str(n): {"count": len(lines), "first": lines[0]} for n, lines in sorted(self.lines.items())}
        return {"writes": self.writes, "ideas": ideas}


def _subagent_transcripts(transcripts: Path | None) -> list[Path]:
    if transcripts is None or not transcripts.is_dir():
        return []
    return [p for p in sorted(transcripts.rglob(f"{SUBAGENT_PREFIX}*.jsonl")) if p.is_file()]


def idea_markers(stream: Path, transcripts: Path | None = None) -> dict[str, Any] | None:
    """The `[abx] idea=N ...` lines the arm wrote, read from the writing tool calls it made.

    The calls are read from the stream and from every subagent transcript (agent-*.jsonl) under
    transcripts: a background subagent's calls need not reach the stream, and a call seen in both
    is one call (deduplicated by its tool_use id). A marker counts only inside a call that writes
    or appends: Write content, Edit/MultiEdit new_string, NotebookEdit new_source, or a Bash
    command that redirects, appends or tees. The same marker in the prompt, in the arm's own
    prose, in a subagent's brief, in a read-back tool_result or in a non-writing command (grep) is
    not a marker written; a write by any other route (sed -i, a script) is not seen.

    Args:
        stream: the arm's stream.jsonl.
        transcripts: the arm's transcripts dir, or None to read the stream alone.

    Returns:
        None when neither the stream nor a subagent transcript exists, else {"writes": writing
        calls that carried a marker, "ideas": {"<N>": {"count": distinct marker lines for idea N,
        "first": the first of them}}}, ordered by N. A line rewritten by a later Write or Edit is
        counted once.
    """
    sources = ([stream] if stream.is_file() else []) + _subagent_transcripts(transcripts)
    if not sources:
        return None
    tally = _IdeaTally()
    for source in sources:
        for record in _records(source):
            for block in _tool_uses(record):
                tally.add_call(block)
    return tally.result()


# --- the suite's outcome -------------------------------------------------------------------------

class _SuiteLog:
    """What a cargo suite log says: error codes, missing symbols, and the summed test results."""

    def __init__(self) -> None:
        self.codes: dict[str, int] = {}
        self.missing: list[str] = []
        self.could_not_compile = False
        self.passed: int | None = None
        self.failed: int | None = None
        self.build_script_failed = False
        self.protoc_missing = False

    def feed(self, line: str) -> None:
        # Read beside the classification below, never instead of it: the line still counts there.
        self.build_script_failed = self.build_script_failed or _BUILD_SCRIPT_FAILED.match(line) is not None
        self.protoc_missing = self.protoc_missing or _PROTOC_MISSING.search(line) is not None
        if (m := _ERROR_CODE.match(line)) is not None:
            self._note_error(m.group(1), m.group(2))
        elif _COULD_NOT_COMPILE.match(line):
            self.could_not_compile = True
        elif (t := _TEST_RESULT.match(line)) is not None:
            self.passed = (self.passed or 0) + int(t.group(1))
            self.failed = (self.failed or 0) + int(t.group(2))

    def _note_error(self, code: str, message: str) -> None:
        self.codes[code] = self.codes.get(code, 0) + 1
        name = _BACKTICKED.search(message)
        if code in _MISSING_CODES and name and name.group(1) not in self.missing and len(self.missing) < MISSING_CAP:
            self.missing.append(name.group(1))

    def does_not_compile(self) -> bool:
        return bool(self.codes) or self.could_not_compile

    def prerequisite(self) -> str | None:
        """The tool a failed build script could not find; only both lines together name one.

        A protoc line alone is not enough: a test may print one, and a tool found is still named.
        """
        return "protoc" if self.build_script_failed and self.protoc_missing else None


def _read_log(log: Path) -> _SuiteLog:
    parsed = _SuiteLog()
    try:
        with log.open(encoding="utf-8", errors="replace") as fh:
            for line in fh:
                parsed.feed(line.rstrip("\r\n"))
    except OSError:
        pass  # a missing or unreadable log classifies by the exit code alone
    return parsed


def _outcome(step: dict[str, Any], parsed: _SuiteLog) -> str:
    if step.get("error"):
        return SUITE_NOT_FINISHED
    if step.get("rc") == 0:
        return SUITE_PASSED
    if parsed.prerequisite() is not None:
        return SUITE_PREREQ_MISSING
    if parsed.does_not_compile():
        return SUITE_NO_COMPILE
    return SUITE_TESTS_FAILED if parsed.failed else SUITE_FAILED


def step_outcome(step: dict[str, Any] | None, log: Path) -> dict[str, Any] | None:
    """A floor step (the gate or the suite), classified by its log rather than by one exit code.

    Args:
        step: the step as run_floor recorded it ({"name", "rc", "error", ...}); None when the
            floor attempted no such step.
        log: the step's log (floor-gate.log or floor-suite.log in the arm dir).

    Returns:
        None for no step, else {"outcome": SUITE_PASSED, SUITE_PREREQ_MISSING (a "failed to run
        custom build command" line and a line saying protoc is missing), SUITE_NO_COMPILE (a rustc
        error[Exxxx] or "could not compile" line), SUITE_TESTS_FAILED (the "test result:" lines
        count a failed test), SUITE_FAILED (a non-zero exit the log does not explain) or
        SUITE_NOT_FINISHED (the step recorded an error), "rc", "error_codes" ({code: count}),
        "missing" (the names the not-found codes expected, at most MISSING_CAP, in log order),
        "tests_failed" and "tests_total" (passed plus failed over every "test result:" line; None
        when the log has none), "prerequisite" (the missing tool, "protoc", when the outcome is
        SUITE_PREREQ_MISSING; else None)}.
    """
    if step is None:
        return None
    parsed = _read_log(log)
    total = None if parsed.passed is None or parsed.failed is None else parsed.passed + parsed.failed
    outcome = _outcome(step, parsed)
    prerequisite = parsed.prerequisite() if outcome == SUITE_PREREQ_MISSING else None
    return {"outcome": outcome, "rc": step.get("rc"), "error_codes": dict(sorted(parsed.codes.items())),
            "missing": parsed.missing, "tests_failed": parsed.failed, "tests_total": total,
            "prerequisite": prerequisite}


def suite_outcome(step: dict[str, Any] | None, log: Path) -> dict[str, Any] | None:
    """The floor's suite step, classified by its log (step_outcome of the suite step and floor-suite.log)."""
    return step_outcome(step, log)


# --- the text line -------------------------------------------------------------------------------

def describe_subagents(subagents: dict[str, int] | None) -> str:
    """'-' (no transcripts kept), '0', or '<files>(max <peak> at once[, <n> untimed])'."""
    if subagents is None:
        return "-"
    if not subagents["transcripts"]:
        return "0"
    untimed = f", {subagents['untimed']} untimed" if subagents["untimed"] else ""
    return f"{subagents['transcripts']}(max {subagents['max_concurrent']} at once{untimed})"


def describe_ideas(markers: dict[str, Any] | None) -> str:
    """'-' (no stream), 'none' (a stream with no marker written), or '<N>x<count>,...'."""
    if markers is None:
        return "-"
    ideas = markers["ideas"]
    return ",".join(f"{n}x{v['count']}" for n, v in ideas.items()) if ideas else "none"


def describe_suite(suite: dict[str, Any] | None) -> str:
    """The outcome, with its codes and missing symbols, its failed-of-total count, or the missing tool.

    Reads any step_outcome, the gate's as well as the suite's.
    """
    if suite is None:
        return "-"
    outcome = suite["outcome"]
    if outcome == SUITE_PREREQ_MISSING:
        return f"{outcome}({suite.get('prerequisite') or '?'})"
    if outcome == SUITE_NO_COMPILE:
        codes = ",".join(f"{c}x{n}" for c, n in suite["error_codes"].items())
        missing = f"; missing {','.join(suite['missing'])}" if suite["missing"] else ""
        return f"{outcome}({codes}{missing})"
    if outcome == SUITE_TESTS_FAILED:
        return f"{outcome}({suite['tests_failed']} of {suite['tests_total']})"
    return str(outcome)
