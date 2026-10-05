#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["orjson"]
# ///
"""How much of real working time goes to the INSTRUMENTATION - memory upkeep, handovers, and
detours into the tooling itself - and what started each stretch of it?

Why: a hook that nudges ("capture this", "write a handover", "review your decisions") costs the
time of whatever the session does next, and that cost lands in someone else's project. Measuring
it meant rebuilding the same classifier by hand each time, and the one that produced a release's
baseline numbers lived in a session scratchpad and was lost, so the promised re-measurement could
not be compared like for like.

What it does, over the Claude Code transcript corpus (`~/.claude/projects`, main session files;
subagent transcripts run in parallel with their parent, so counting them would double the clock):

  * Every tool call is CLASSIFIED by its tool and input as `work` or one of three instrumentation
    kinds - `memory` (the memory store, the engine, the contribution queue, a dream or self-improve
    skill), `handover` (handover.md, OPEN-WORK.md, the context watcher) or `skills-detour` (an
    edit or a shell command in the plugin's own source or cache, a skill-writing skill). RUNNING a
    shipped jig or reading a skill is using the tooling and counts as work. The rules are the
    `RULES` table below; first match wins, and anything unmatched is work. The figures are only as
    good as those patterns, so compare two periods with the same version of this tool.
  * Each call is CHARGED the time until the next event of its session (call or prompt), capped at
    `--max-gap` minutes, so an idle night is not charged to whatever ran last. Work and
    instrumentation are charged the same way, which is what makes the share comparable.
  * Consecutive instrumentation calls form an EPISODE, attributed to the TRIGGER in effect when it
    began: the latest Stop-hook block (`stop:<its first words>`), SessionStart hook context
    (`session-start`) or typed prompt (`prompt`) before the episode's first call. A Skill call
    that opens an episode is part of the episode, so the Stop hook that led to it keeps the blame.
  * Sessions whose working directory matches `--exclude-cwd` are skipped and counted - by default
    the plugin's own repository, where tooling work IS the work.

A tool call repeated in a resumed or forked transcript is counted once, by its tool_use id.

Run:
  uv run scripts/instrument_share.py --since 2026-09-13
  uv run scripts/instrument_share.py --since 2026-09-13 --until 2026-10-04 --json
  uv run scripts/instrument_share.py --root DIR --max-gap 5 --top 15

Exit codes: 0 = measured, 1 = the corpus was read but no tool call fell in the range (nothing to
measure), 2 = could not measure: a --root that does not exist, a bad date or option, a transcript
or directory that could not be read (the figures then cover only what was read, and the unread
paths are listed), or a crash. `--json` prints `{ok, command, data, skipped}` on every exit, 2
included; `ok` is false exactly on exit 2.
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from _cli_envelope import EXIT_ERROR, EXIT_NO, EXIT_YES, EnvelopeArgumentParser, emit, guarded

try:                                                     # pragma: no cover - speed, not behaviour
    import orjson

    def _loads(raw: str) -> Any:
        return orjson.loads(raw)
except ImportError:                                      # a bare interpreter provisions no deps
    def _loads(raw: str) -> Any:
        return json.loads(raw)

__all__ = [
    "CATEGORIES", "Event", "RULES", "UsageError", "classify", "events_of", "main", "measure",
    "stop_signature",
]

DEFAULT_ROOT = "~/.claude/projects"
DEFAULT_EXCLUDE_CWD = r"[/\\]bitranox-skills(?:[/\\]|$)"
WORK = "work"
CATEGORIES = ("memory", "handover", "skills-detour")

_WRITES = frozenset({"Edit", "Write", "MultiEdit", "NotebookEdit"})
_SHELL_OR_WRITES = _WRITES | {"Bash", "PowerShell"}

#: (category, the tools the row applies to or None for any, regex over the call's input as JSON).
#: First match wins; a call matching none is work. Handover precedes memory because a handover
#: step also names the memory files it points at, and the reverse is rare. A row may name `work`
#: explicitly: RUNNING a shipped jig or tool from a skill directory is using the tooling, not a
#: detour into it, and without that row every toolbox call would read as one.
RULES: list[tuple[str, frozenset[str] | None, re.Pattern[str]]] = [
    ("handover", frozenset({"Skill"}), re.compile(r"meta-context-watcher")),
    ("memory", frozenset({"Skill"}),
     re.compile(r"meta-(?:self-improve|dream|collect-knowledge|memory-settings)"
                r"|process-review-uncertain-decisions")),
    ("skills-detour", frozenset({"Skill"}),
     re.compile(r"meta-(?:skill-writer|skill-audit|claude-hooks|adopting-external-skills"
                r"|audit-local)")),
    ("handover", None, re.compile(r"handover\.md|OPEN-WORK\.md")),
    ("memory", None, re.compile(r"\.claude-memory|CLAUDE\.local\.md|memory_engine|contrib_queue"
                                r"|dream_state|self-improve-audit|reconcile_memory_index"
                                r"|factedit|statusrot|[/\\]memory[/\\]MEMORY\.md")),
    (WORK, frozenset({"Bash", "PowerShell"}),
     re.compile(r"(?:uv\s+run|python3?|py\s+-3|run-python\.sh)\s+(?:--\S+\s+)*\S*"
                r"(?:skills[/\\][\w-]+[/\\](?:scripts[/\\])?|toolbox[/\\]tools[/\\])\w+\.py")),
    ("skills-detour", _SHELL_OR_WRITES,
     re.compile(r"bitranox-skills|\.claude[/\\]plugins[/\\]|plugins[/\\]bitranox[/\\]"
                r"|\.skillwriter|skill_receipt")),
]

_STOP_PREFIX = "Stop hook feedback:"


class UsageError(Exception):
    """A bad option or an unusable --root: exit 2, never a traceback."""


@dataclass
class Event:
    """One moment in a session: a tool call, a typed prompt, or a hook trigger."""

    when: datetime
    kind: str                       # "call" | "prompt" | "trigger"
    label: str = ""                 # category for a call, trigger name for a trigger
    call_id: str | None = None


@dataclass
class Tally:
    """Minutes per category, and episode counts."""

    minutes: dict[str, float] = field(default_factory=lambda: defaultdict(float))
    episodes: int = 0

    def add(self, category: str, mins: float) -> None:
        self.minutes[category] += mins

    def as_dict(self) -> dict[str, Any]:
        total = sum(self.minutes.values())
        instr = sum(v for k, v in self.minutes.items() if k != WORK)
        return {"minutes": {k: round(v, 1) for k, v in sorted(self.minutes.items())},
                "total_minutes": round(total, 1), "instrumentation_minutes": round(instr, 1),
                "instrumentation_share_pct": round(100 * instr / total, 1) if total else None,
                "episodes": self.episodes}


def classify(tool: str, tool_input: Any) -> str:
    """The category of one tool call: `work` unless a RULES row matches. PURE."""
    text = json.dumps(tool_input, ensure_ascii=False) if not isinstance(tool_input, str) \
        else tool_input
    for category, only, rx in RULES:
        if only is not None and tool not in only:
            continue
        if rx.search(text):
            return category
    return WORK


def stop_signature(text: str, words: int = 6) -> str:
    """A stable short name for a Stop-hook block: its first words, digits folded to `#`. PURE.

    The block text names the situation ("This session is carrying 404,715 tokens ...") while the
    record names only the event, so the words are the one handle that tells two Stop hooks apart.
    """
    body = text[len(_STOP_PREFIX):] if text.startswith(_STOP_PREFIX) else text
    body = re.sub(r"\b[0-9a-f]{7,40}\b", "#", body)      # a commit sha, before digits fold
    body = re.sub(r"\d[\d,.]*", "#", body)
    return "stop:" + " ".join(re.findall(r"[A-Za-z#'-]+", body)[:words]).lower()


def _when(raw: Any) -> datetime | None:
    if not isinstance(raw, str):
        return None
    try:
        stamp = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    return stamp if stamp.tzinfo else stamp.replace(tzinfo=timezone.utc)


def _user_text(message: Any) -> str | None:
    if not isinstance(message, dict):
        return None
    content = message.get("content")
    if isinstance(content, str):
        return content
    if not isinstance(content, list) or any(
            isinstance(b, dict) and b.get("type") == "tool_result" for b in content):
        return None
    texts = [b.get("text") for b in content if isinstance(b, dict) and b.get("type") == "text"]
    return "\n".join(t for t in texts if isinstance(t, str)) or None


def _record_events(rec: dict[str, Any], when: datetime) -> Iterable[Event]:
    kind = rec.get("type")
    if kind == "assistant":
        for block in (rec.get("message") or {}).get("content") or []:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                yield Event(when, "call", classify(str(block.get("name")), block.get("input")),
                            block.get("id"))
    elif kind == "user":
        text = _user_text(rec.get("message"))
        if text is None:
            return
        if rec.get("isMeta"):
            if text.startswith(_STOP_PREFIX):
                yield Event(when, "trigger", stop_signature(text))
            return
        yield Event(when, "prompt", "prompt")
    elif kind == "attachment":
        att = rec.get("attachment") or {}
        if att.get("hookEvent") == "SessionStart" and att.get("type") == "hook_additional_context":
            yield Event(when, "trigger", "session-start")


def events_of(text: str) -> tuple[list[Event], str | None]:
    """The events of one transcript in time order, and its working directory. PURE."""
    events: list[Event] = []
    cwd = None
    for line in text.split("\n"):
        if not line.strip():
            continue
        try:
            rec = _loads(line)
        except Exception:                                # noqa: BLE001 - a half-written line
            continue
        if not isinstance(rec, dict) or rec.get("isSidechain"):
            continue
        cwd = cwd or rec.get("cwd")
        when = _when(rec.get("timestamp"))
        if when is not None:
            events.extend(_record_events(rec, when))
    events.sort(key=lambda e: e.when)
    return events, cwd


def _iso_week(when: datetime) -> str:
    year, week, _ = when.isocalendar()
    return f"{year}-W{week:02d}"


@dataclass
class Report:
    """Everything one measurement accumulates."""

    total: Tally = field(default_factory=Tally)
    weeks: dict[str, Tally] = field(default_factory=lambda: defaultdict(Tally))
    triggers: dict[str, Tally] = field(default_factory=lambda: defaultdict(Tally))
    sessions: int = 0
    sessions_excluded: int = 0
    calls: int = 0
    duplicates_skipped: int = 0


def _charge_session(events: list[Event], report: Report, seen: set[str], max_gap: float,
                    window: tuple[datetime | None, datetime | None]) -> None:
    trigger = "session-start"
    episode_trigger: str | None = None
    for i, ev in enumerate(events):
        if ev.kind != "call":
            if ev.kind in ("trigger", "prompt"):
                trigger = ev.label
            continue
        if ev.call_id and ev.call_id in seen:
            report.duplicates_skipped += 1
            continue
        if ev.call_id:
            seen.add(ev.call_id)
        nxt = events[i + 1].when if i + 1 < len(events) else ev.when
        mins = min(max((nxt - ev.when).total_seconds() / 60.0, 0.0), max_gap)
        in_window = not ((window[0] and ev.when < window[0]) or (window[1] and ev.when >= window[1]))
        if ev.label == WORK:
            episode_trigger = None
        elif episode_trigger is None:
            # The episode state advances outside the window too, so one that began before
            # --since is not recounted as a new episode at the boundary.
            episode_trigger = trigger
            if in_window:
                report.triggers[trigger].episodes += 1
                report.total.episodes += 1
                report.weeks[_iso_week(ev.when)].episodes += 1
        if not in_window:
            continue
        report.calls += 1
        report.total.add(ev.label, mins)
        report.weeks[_iso_week(ev.when)].add(ev.label, mins)
        if episode_trigger is not None:
            report.triggers[episode_trigger].add(ev.label, mins)


def _transcripts(base: Path, skipped: list[str]) -> list[Path]:
    """Main session transcripts below `base`; subagent transcripts are left out on purpose."""
    def record(err: OSError) -> None:
        skipped.append(f"{err.filename}: {err}")

    found = []
    for dirpath, dirs, names in os.walk(base, onerror=record):
        dirs[:] = [d for d in dirs if d != "subagents"]
        found.extend(Path(dirpath) / n for n in names if n.endswith(".jsonl"))
    return sorted(found)


def measure(root: Path, *, since: date | None = None, until: date | None = None,
            max_gap: float = 5.0, exclude_cwd: str | None = DEFAULT_EXCLUDE_CWD
            ) -> tuple[Report, list[str], int]:
    """Measure the corpus below `root`. Returns (report, unread paths, files read)."""
    skipped: list[str] = []
    files = _transcripts(root, skipped) if root.is_dir() else [root]
    window = (datetime(since.year, since.month, since.day, tzinfo=timezone.utc) if since else None,
              datetime(until.year, until.month, until.day, tzinfo=timezone.utc) if until else None)
    exclude = re.compile(exclude_cwd) if exclude_cwd else None
    report, seen, read = Report(), set(), 0
    for path in files:
        try:
            text = path.read_bytes().decode("utf-8-sig", errors="replace")
        except OSError as exc:
            skipped.append(f"{path}: {exc}")
            continue
        read += 1
        events, cwd = events_of(text)
        if not any(e.kind == "call" for e in events):
            continue
        if exclude is not None and cwd and exclude.search(cwd):
            report.sessions_excluded += 1
            continue
        report.sessions += 1
        _charge_session(events, report, seen, max_gap, window)
    return report, skipped, read


def _data(report: Report, top: int, read: int, args: Any) -> dict[str, Any]:
    triggers = sorted(report.triggers.items(),
                      key=lambda kv: -sum(v for k, v in kv[1].minutes.items() if k != WORK))
    return {"total": report.total.as_dict(),
            "weeks": {w: t.as_dict() for w, t in sorted(report.weeks.items())
                      if sum(t.minutes.values())},
            "triggers": {name: t.as_dict() for name, t in triggers[:top]},
            "sessions": report.sessions, "sessions_excluded": report.sessions_excluded,
            "calls": report.calls, "duplicates_skipped": report.duplicates_skipped,
            "files_read": read, "max_gap_minutes": args.max_gap,
            "since": args.since, "until": args.until, "exclude_cwd": args.exclude_cwd}


def _print(data: dict[str, Any]) -> None:
    t = data["total"]
    print(f"{data['sessions']} sessions ({data['sessions_excluded']} excluded by --exclude-cwd), "
          f"{data['calls']} calls, {data['files_read']} files read")
    print(f"total {t['total_minutes']} min, instrumentation {t['instrumentation_minutes']} min "
          f"({t['instrumentation_share_pct']}%), {t['episodes']} episodes")
    print("\nper ISO week:")
    for week, w in data["weeks"].items():
        cats = ", ".join(f"{k} {v}" for k, v in w["minutes"].items() if k != WORK)
        print(f"  {week}  {w['instrumentation_share_pct']}% of {w['total_minutes']} min  [{cats}]")
    print("\nper trigger (instrumentation minutes):")
    for name, tr in data["triggers"].items():
        cats = ", ".join(f"{k} {v}" for k, v in tr["minutes"].items() if k != WORK)
        print(f"  {tr['instrumentation_minutes']:8} min  {tr['episodes']:4} episodes  {name}  "
              f"[{cats}]")


def _date(raw: str | None, flag: str) -> date | None:
    if raw is None:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise UsageError(f"{flag} {raw!r}: not a YYYY-MM-DD date") from exc


@guarded("instrument_share")
def main(argv: Sequence[str] | None = None) -> int:
    ap = EnvelopeArgumentParser(prog="instrument_share", envelope_command="instrument_share",
                                description="Share of session time spent on instrumentation, per "
                                            "ISO week and per trigger.")
    ap.add_argument("--root", default=DEFAULT_ROOT, help="transcript corpus [%(default)s]")
    ap.add_argument("--since", help="first day counted, YYYY-MM-DD (UTC)")
    ap.add_argument("--until", help="first day NOT counted, YYYY-MM-DD (UTC)")
    ap.add_argument("--max-gap", type=float, default=5.0,
                    help="cap, in minutes, on the time charged to one call [5]")
    ap.add_argument("--exclude-cwd", default=DEFAULT_EXCLUDE_CWD,
                    help="regex; sessions whose cwd matches are skipped ('' skips none) "
                         "[the plugin's own repository]")
    ap.add_argument("--top", type=int, default=20, help="triggers to list [20]")
    ap.add_argument("--json", action="store_true", help="print the {ok,command,data,skipped} envelope")
    args = ap.parse_args(argv)
    try:
        since, until = _date(args.since, "--since"), _date(args.until, "--until")
        if args.max_gap <= 0 or args.top < 1:
            raise UsageError("--max-gap must be positive and --top at least 1")
        root = Path(args.root).expanduser()
        if not root.exists():
            raise UsageError(f"--root {args.root}: no such file or directory")
        exclude = args.exclude_cwd or None
        if exclude:
            re.compile(exclude)
    except (UsageError, re.error) as exc:
        if args.json:
            return emit(EXIT_ERROR, "instrument_share", error=str(exc))
        print(f"instrument_share: {exc}", file=sys.stderr)
        return EXIT_ERROR
    report, skipped, read = measure(root, since=since, until=until, max_gap=args.max_gap,
                                    exclude_cwd=exclude)
    data = _data(report, args.top, read, args)
    code = EXIT_ERROR if skipped else (EXIT_YES if report.calls else EXIT_NO)
    for note in skipped:
        print(f"instrument_share: not read: {note}", file=sys.stderr)
    if args.json:
        return emit(code, "instrument_share", data, skipped=skipped,
                    error=f"{len(skipped)} paths could not be read" if skipped else None)
    _print(data)
    if not report.calls:
        print("no tool call fell in the range", file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())
