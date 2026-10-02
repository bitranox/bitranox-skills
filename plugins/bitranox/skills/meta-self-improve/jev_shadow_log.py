"""The Jev shadow log: one record per judged item, monthly files, and their retention.

`jev_shadow.py run` builds one record per item with `build_record` and appends the batch with
`append_records`, under the memory lock (a bare append is not safe when several sessions log at
once). Files are `~/.claude/self-improve-audit/jev-skill-shadow-YYYY-MM.jsonl`; every append then
deletes the months whose last day is more than LOG_KEEP_DAYS ago, and after that the oldest months
while the rest exceed LOG_MAX_BYTES. The current month is never deleted. Skill sites fire weekly at
most, which is why this keeps 400 days where the hook shadow keeps 30.

A record keeps the item's state, redacted and capped exactly as it was sent, so a later and better
question can be replayed over logged items without re-running the skill. Standard library only.
"""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

# The hooks dir holds classifier and self_improve_signals; put it on sys.path before importing
# them, the same setup classifier_eval.py uses, so this module imports on its own too.
_HERE = Path(__file__).resolve().parent
_HOOKS = _HERE.parent.parent / "hooks"
for _d in (str(_HOOKS), str(_HERE)):
    if _d not in sys.path:
        sys.path.insert(0, _d)

import classifier as cl
import self_improve_signals as sig

import jev_shadow_report as rpt
import jev_shadow_sites as sites

__all__ = [
    "LOG_KEEP_DAYS",
    "LOG_MAX_BYTES",
    "LOG_PREFIX",
    "JevRun",
    "LogLocked",
    "RunContext",
    "Verdict",
    "agrees",
    "append_records",
    "audit_dir",
    "build_record",
    "log_files",
    "log_path",
    "prune_logs",
    "short_reason",
]

LOG_PREFIX = "jev-skill-shadow-"
_LOG_RE = re.compile(r"^jev-skill-shadow-(\d{4})-(\d{2})\.jsonl$")
LOG_KEEP_DAYS = 400
LOG_MAX_BYTES = 100 * 1024 * 1024
_REASON_CAP = 200


class LogLocked(OSError):
    """Another writer held the log's lock past the wait."""


@dataclass(frozen=True)
class Verdict:
    """The agent's answers for one item, and its optional one-line reason."""

    answers: dict[str, Any]
    note: str | None


@dataclass(frozen=True)
class JevRun:
    """What one jev-judge run returned: rows by item id, the run's totals, and why it failed."""

    rows: dict[str, dict[str, Any]]
    cost_usd: float | None
    input_tokens: int
    reason: str | None


@dataclass(frozen=True)
class RunContext:
    """What every record of one run shares."""

    ts: str
    run_id: str
    site: sites.Site
    jev_judge_version: str | None
    cwd: str
    git_head: str | None
    plugin_version: str
    jev: JevRun


def audit_dir() -> Path:
    """The directory the hooks log into, resolved per call so a changed HOME is honoured."""
    return Path.home() / ".claude" / "self-improve-audit"


def short_reason(text: str) -> str:
    """A failure reason fit for the log: one line, redacted, capped."""
    state, _n = cl.prepare_state({"t": " ".join(text.split())}, cap=_REASON_CAP)
    return state["t"]


# ---- one record -----------------------------------------------------------------------------


def _jev_answers(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row or not row.get("ok"):
        return None
    answers = row.get("answers") or {}
    return {
        qid: {k: a.get(k) for k in ("value", "probabilities", "confidence")}
        for qid, a in answers.items()
        if isinstance(a, dict)
    }


def agrees(
    question: dict[str, Any], agent: Any, answer: dict[str, Any] | None
) -> bool | None:
    """Agent against Jev: a noul at 0.5, a choice by key, a score by index.

    Args:
        question: The site's question object.
        agent: The agent's answer, or None when it left the question out.
        answer: Jev's answer, or None when Jev gave none.

    Returns:
        Whether they agree, or None when either side is absent.
    """
    if agent is None or answer is None or answer.get("value") is None:
        return None
    value = answer["value"]
    if question["type"] == "noul":
        return agent == (float(value) >= 0.5)
    if question["type"] == "score":
        return agent == rpt.jev_index(float(value), len(question["criteria"]))
    return agent == value


def _item_cost(ctx: RunContext, tokens: int) -> float | None:
    """This item's share of the run's cost, by its share of the input tokens."""
    if ctx.jev.cost_usd is None or not ctx.jev.input_tokens:
        return None
    return round(ctx.jev.cost_usd * tokens / ctx.jev.input_tokens, 9)


def _jev_reason(ctx: RunContext, row: dict[str, Any] | None) -> str | None:
    if row is None:
        return ctx.jev.reason or "jev-judge wrote no row for this item"
    if row.get("ok"):
        return None
    return short_reason(str(row.get("reason") or "failed"))


def build_record(
    ctx: RunContext,
    item: sites.ShadowItem,
    redactions: int,
    verdict: Verdict | None,
) -> dict[str, Any]:
    """The one log record for one item.

    Args:
        ctx: What the run's records share, including Jev's rows.
        item: The item as it was sent: its state already redacted and capped.
        redactions: How many secrets the redaction replaced in this item.
        verdict: The agent's verdict, or None when it did not judge this item.

    Returns:
        The record, with every field the reference doc lists.
    """
    row = ctx.jev.rows.get(item.id)
    jev = _jev_answers(row)
    agent = verdict.answers if verdict else None
    agree = {
        q["id"]: agrees(q, (agent or {}).get(q["id"]), (jev or {}).get(q["id"]))
        for q in ctx.site.questions
    }
    tokens = int((row or {}).get("input_tokens") or 0)
    return {
        "ts": ctx.ts,
        "run_id": ctx.run_id,
        "site": ctx.site.name,
        "site_version": ctx.site.version,
        "questions_sha": ctx.site.questions_sha,
        "plugin_version": ctx.plugin_version,
        "jev_judge_version": ctx.jev_judge_version,
        "model": (row or {}).get("model") or None,
        "cwd": ctx.cwd,
        "git_head": ctx.git_head,
        "item_id": item.id,
        "state": item.state,
        "redactions": redactions,
        "jev": jev,
        "jev_reason": _jev_reason(ctx, row),
        "agent": agent,
        "agent_note": verdict.note if verdict else None,
        "agree": agree,
        "latency_ms": (row or {}).get("latency_ms"),
        "input_tokens": tokens,
        "cost_usd": _item_cost(ctx, tokens),
    }


# ---- the files and their retention ------------------------------------------------------------


def log_path(audit: Path, now: datetime) -> Path:
    """The monthly file a record logged at `now` (an aware UTC datetime) goes to."""
    return audit / f"{LOG_PREFIX}{now:%Y-%m}.jsonl"


def log_files(audit: Path) -> list[Path]:
    """Every monthly shadow log in `audit`, oldest first (the fixed-width name sorts by month)."""
    try:
        names = os.listdir(audit)
    except OSError:
        return []
    return [audit / n for n in sorted(names) if _LOG_RE.match(n)]


def _month_end(path: Path) -> date:
    """The last day of the month a log file is named for: the date of its newest possible row."""
    m = _LOG_RE.match(path.name)
    if m is None:
        raise ValueError(f"not a shadow log name: {path.name}")
    year, month = int(m.group(1)), int(m.group(2))
    return date(year + month // 12, month % 12 + 1, 1) - timedelta(days=1)


def _unlink(path: Path) -> bool:
    """True when `path` is gone afterwards; a file another process holds open may refuse."""
    try:
        path.unlink()
    except FileNotFoundError:
        return True
    except OSError:
        return False
    return True


def _drop_expired(
    audit: Path, now: datetime
) -> tuple[list[Path], list[tuple[Path, int]]]:
    """Delete months past LOG_KEEP_DAYS; return the removed paths and the survivors' sizes."""
    current = log_path(audit, now)
    cutoff = now.date() - timedelta(days=LOG_KEEP_DAYS)
    removed, sized = [], []
    for path in log_files(audit):
        if path != current and _month_end(path) < cutoff:
            if _unlink(path):
                removed.append(path)
            continue
        try:
            sized.append((path, path.stat().st_size))
        except OSError:
            continue
    return removed, sized


def prune_logs(audit: Path, now: datetime) -> list[Path]:
    """Drop months whose last day is over LOG_KEEP_DAYS ago, then the oldest past LOG_MAX_BYTES.

    Args:
        audit: The audit directory.
        now: The current aware UTC time; its month is never dropped, even alone over the cap.

    Returns:
        The paths removed.
    """
    current = log_path(audit, now)
    removed, sized = _drop_expired(audit, now)
    total = sum(size for _p, size in sized)
    for path, size in sized:
        if total <= LOG_MAX_BYTES:
            break
        if path != current and _unlink(path):
            removed.append(path)
            total -= size
    return removed


def append_records(records: list[dict[str, Any]], now: datetime) -> None:
    """Append the records to the current month under the memory lock, then prune.

    Raises:
        LogLocked: Another writer held the lock past the wait.
    """
    audit = audit_dir()
    audit.mkdir(parents=True, exist_ok=True)
    path = log_path(audit, now)
    try:
        with sig.memory_lock(path):
            with path.open("a", encoding="utf-8") as fh:
                fh.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in records)
            prune_logs(audit, now)
    except TimeoutError as exc:
        raise LogLocked(f"the shadow log is locked by another writer: {exc}") from exc
