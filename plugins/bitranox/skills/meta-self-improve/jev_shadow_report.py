"""Read the Jev shadow log back: agreement between the agent and Jev, per site and question.

`jev_shadow.py run` appends one record per judged item to a monthly
`jev-skill-shadow-YYYY-MM.jsonl`. This module turns those records into, per site and question:
how many items, how many were PAIRED (both the agent and Jev answered), the agreement among the
paired, the agent-by-Jev confusion counts, the share of Jev answers inside the uncertainty band,
agreement with that band excluded, and a FLAT flag. A constant answer is a broken instrument, not
consensus, so FLAT is a finding about the question, never about the items.

Records are never pooled across question wordings: every figure is reported per `questions_sha`,
the hash of the exact questions the records were asked. The current site file decides question
types and score level counts only for the records carrying ITS sha; records from an older wording
have their types read from their own answers, so a question that changed type (a choice that
became a noul) is reported as what it was when it was asked.

The band is the one the jev-judge skill reads by hand: a noul strictly between 0.2 and 0.8, a
choice or score with confidence below 0.6. Standard library only.
"""

from __future__ import annotations

import json
import statistics
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from jev_shadow_sites import as_number, as_record, jev_index, jsonl_lines

__all__ = [
    "BAND",
    "FLAT_MIN_ANSWERS",
    "FLAT_SHARE",
    "FLAT_STDEV",
    "MIN_CONFIDENCE",
    "LogRead",
    "SiteSpec",
    "answer_label",
    "disagreements",
    "jev_label",
    "read_records",
    "render",
    "summarize",
]

Record = dict[str, Any]

BAND = (0.2, 0.8)
MIN_CONFIDENCE = 0.6
# Below this many Jev answers a question is too small to call flat: two equal answers are noise.
FLAT_MIN_ANSWERS = 5
FLAT_STDEV = 0.05
FLAT_SHARE = 0.95


@dataclass(frozen=True)
class SiteSpec:
    """What a site file says today: its questions hash, question types and score level counts."""

    sha: str
    types: dict[str, str]
    levels: dict[str, int]


@dataclass
class LogRead:
    """Records read from the log files, and the lines that could not be read (`file:line`)."""

    records: list[Record] = field(default_factory=list[Record])
    skipped: list[str] = field(default_factory=list[str])


def read_records(
    files: Iterable[Path], *, site: str | None, since: str | None
) -> LogRead:
    """Every record in `files`, oldest first, filtered by site and by the date its `ts` carries.

    Args:
        files: The monthly log files, oldest first.
        site: Keep only this site, or every site when None.
        since: Keep only records whose `ts` date (YYYY-MM-DD) is on or after this one.

    Returns:
        The kept records and the `file:line` of each line that was not a JSON object.
    """
    out = LogRead()
    for path in files:
        _read_file(path, out)
    out.records = [r for r in out.records if _keep(r, site=site, since=since)]
    return out


def _read_file(path: Path, out: LogRead) -> None:
    """Add a file's records to `out`; an unreadable file or line goes to `out.skipped`."""
    try:
        lines = jsonl_lines(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError):
        out.skipped.append(path.name)
        return
    for number, line in enumerate(lines, start=1):
        rec = _parse(line)
        if rec is None:
            out.skipped.append(f"{path.name}:{number}")
        else:
            out.records.append(rec)


def _keep(rec: Record, *, site: str | None, since: str | None) -> bool:
    if site is not None and rec.get("site") != site:
        return False
    return since is None or str(rec.get("ts") or "")[:10] >= since


def _parse(line: str) -> Record | None:
    try:
        rec: object = json.loads(line)
    except ValueError:
        return None
    return as_record(rec)


def jev_label(
    qtype: str, answer: Record, levels: int | None = None
) -> bool | int | str | None:
    """The comparable form of one Jev answer: a bool, a choice key or a score index.

    The score index is clamped to `levels` exactly as the record's `agree` was, so the confusion
    table and the agreement figure count the same thing. None for an answer of the wrong shape.
    """
    value: object = answer.get("value")
    if qtype == "choice":
        return None if value is None else str(value)
    number = as_number(value)
    if number is None:
        return None
    return number >= 0.5 if qtype == "noul" else jev_index(number, levels)


def answer_label(value: object) -> str:
    """A confusion-table label: `true`/`false` for a bool, the plain value otherwise."""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _in_band(qtype: str, answer: Record) -> bool:
    if qtype == "noul":
        number = as_number(answer.get("value"))
        return number is not None and BAND[0] < number < BAND[1]
    confidence = as_number(answer.get("confidence"))
    return confidence is not None and confidence < MIN_CONFIDENCE


def _is_flat(qtype: str, answers: list[Record]) -> bool:
    if len(answers) < FLAT_MIN_ANSWERS:
        return False
    if qtype == "choice":
        top = Counter(str(a.get("value")) for a in answers).most_common(1)[0][1]
        return top / len(answers) >= FLAT_SHARE
    numbers = [n for n in (as_number(a.get("value")) for a in answers) if n is not None]
    return len(numbers) >= FLAT_MIN_ANSWERS and statistics.pstdev(numbers) < FLAT_STDEV


def _pct(part: int, whole: int) -> float | None:
    return round(100.0 * part / whole, 1) if whole else None


def _answer(rec: Record, qid: str) -> Record | None:
    jev = as_record(rec.get("jev"))
    return None if jev is None else as_record(jev.get(qid))


def _agent(rec: Record, qid: str) -> object:
    agent = as_record(rec.get("agent"))
    return None if agent is None else agent.get(qid)


def _agree(rec: Record) -> Record:
    return as_record(rec.get("agree")) or {}


@dataclass
class _Tally:
    qtype: str
    levels: int | None
    n: int = 0
    paired: int = 0
    agreed: int = 0
    answers: list[Record] = field(default_factory=list[Record])
    in_band: int = 0
    paired_out: int = 0
    agreed_out: int = 0
    confusion: Counter[str] = field(default_factory=Counter[str])

    def add(self, rec: Record, qid: str) -> None:
        self.n += 1
        answer = _answer(rec, qid)
        label = None if answer is None else jev_label(self.qtype, answer, self.levels)
        if answer is None or label is None:
            return
        self.answers.append(answer)
        band = _in_band(self.qtype, answer)
        self.in_band += band
        agree: object = _agree(rec).get(qid)
        if isinstance(agree, bool):
            self._pair(_agent(rec, qid), label, agree, band)

    def _pair(self, agent: object, label: object, agree: bool, band: bool) -> None:
        self.paired += 1
        self.agreed += agree
        if not band:
            self.paired_out += 1
            self.agreed_out += agree
        self.confusion[f"agent={answer_label(agent)}/jev={answer_label(label)}"] += 1

    def result(self) -> dict[str, object]:
        return {
            "type": self.qtype,
            "n": self.n,
            "paired": self.paired,
            "agreement_pct": _pct(self.agreed, self.paired),
            "confusion": dict(sorted(self.confusion.items())),
            "jev_answers": len(self.answers),
            "band_pct": _pct(self.in_band, len(self.answers)),
            "agreement_outside_band_pct": _pct(self.agreed_out, self.paired_out),
            "paired_outside_band": self.paired_out,
            "flat": _is_flat(self.qtype, self.answers),
        }


def _qids(rec: Record) -> list[str]:
    return list(_agree(rec))


_TYPES = frozenset({"noul", "choice", "score"})


def _score_levels(answers: list[Record]) -> int | None:
    """The level count a score's probabilities name, or None when no answer carries them."""
    probs = (as_record(a.get("probabilities")) for a in answers)
    levels = [len(p) for p in probs if p is not None]
    return max(levels) if levels else None


def _logged_type(answers: list[Record]) -> str | None:
    """The one question type the answers were logged with, or None when they carry none (a
    record written before answers kept their type) or disagree."""
    logged = {a.get("type") for a in answers} & _TYPES
    return str(next(iter(logged))) if len(logged) == 1 else None


def _inferred(qid: str, recs: list[Record]) -> tuple[str, int | None]:
    """A question's type and score level count for an older wording: the type its answers
    were logged with, else (records from before that) a guess from the answers' shape."""
    answers = [a for a in (_answer(r, qid) for r in recs) if a is not None]
    logged = _logged_type(answers)
    if logged is not None:
        return logged, _score_levels(answers) if logged == "score" else None
    if any(isinstance(a.get("value"), str) for a in answers):
        return "choice", None
    levels = _score_levels(answers)
    if levels is not None:
        return "score", levels
    agents = [_agent(r, qid) for r in recs]
    if any(isinstance(a, str) for a in agents):
        return "choice", None
    if any(isinstance(a, int) and not isinstance(a, bool) for a in agents):
        return "score", None
    return "noul", None


def _tally(
    tallies: dict[str, _Tally], qid: str, spec: SiteSpec | None, recs: list[Record]
) -> _Tally:
    """The tally for `qid`, created on first use. `spec` is the current site file only when it
    was written for these very records; otherwise the shape comes from the records."""
    if qid not in tallies:
        if spec is not None and qid in spec.types:
            tallies[qid] = _Tally(spec.types[qid], spec.levels.get(qid))
        else:
            tallies[qid] = _Tally(*_inferred(qid, recs))
    return tallies[qid]


def _sha_summary(
    recs: list[Record], spec: SiteSpec | None, sha: str
) -> dict[str, object]:
    current = spec is not None and spec.sha == sha
    own_spec = spec if current else None
    tallies: dict[str, _Tally] = {}
    for rec in recs:
        for qid in _qids(rec):
            _tally(tallies, qid, own_spec, recs).add(rec, qid)
    return {
        "site_version": recs[0].get("site_version"),
        "current": current,
        "records": len(recs),
        "cost_usd": _cost(recs),
        "questions": {qid: t.result() for qid, t in tallies.items()},
    }


def _cost(recs: list[Record]) -> float:
    return round(sum(as_number(r.get("cost_usd")) or 0.0 for r in recs), 6)


def summarize(records: list[Record], specs: dict[str, SiteSpec]) -> dict[str, object]:
    """Per site, per questions sha, per question: the figures described in the module docstring.

    Args:
        records: The log records to summarize.
        specs: The current site files, by site; each applies only to records of its own sha.

    Returns:
        `{"records": n, "sites": {site: {"records", "cost_usd", "shas": {sha: {"site_version",
        "current", "records", "cost_usd", "questions": {qid: {...}}}}}}}`; shas in the order
        their first record was logged.
    """
    grouped: dict[str, dict[str, list[Record]]] = {}
    for rec in records:
        site, sha = str(rec.get("site") or ""), str(rec.get("questions_sha") or "")
        grouped.setdefault(site, {}).setdefault(sha, []).append(rec)
    sites: dict[str, object] = {}
    for site, by_sha in sorted(grouped.items()):
        recs = [r for group in by_sha.values() for r in group]
        shas = {sha: _sha_summary(g, specs.get(site), sha) for sha, g in by_sha.items()}
        sites[site] = {"records": len(recs), "cost_usd": _cost(recs), "shas": shas}
    return {"records": len(records), "sites": sites}


def disagreements(records: list[Record]) -> list[Record]:
    """The paired records where any question disagrees, with their state, for reading by hand."""
    keep = (
        "ts",
        "run_id",
        "site",
        "questions_sha",
        "item_id",
        "state",
        "agent",
        "agent_note",
        "jev",
        "agree",
    )
    return [
        {k: rec.get(k) for k in keep}
        for rec in records
        if any(v is False for v in _agree(rec).values())
    ]


def _question_line(qid: str, q: dict[str, Any]) -> str:
    flat = "  FLAT - a constant answer, check the question" if q["flat"] else ""
    return (
        f"    {qid} ({q['type']}): {q['n']} items, {q['paired']} paired, "
        f"agreement {q['agreement_pct']}%, band {q['band_pct']}%, "
        f"outside band {q['agreement_outside_band_pct']}% ({q['paired_outside_band']} paired)"
        f"{flat}"
    )


def _sha_lines(sha: str, s: dict[str, Any]) -> list[str]:
    age = "current" if s["current"] else "older wording"
    head = f"  questions {sha} (site version {s['site_version']}, {age}): "
    lines = [head + f"{s['records']} records, cost ${s['cost_usd']:.6f}"]
    for qid, q in s["questions"].items():
        lines.append(_question_line(qid, q))
        if q["confusion"]:
            lines.append(
                "      " + ", ".join(f"{k} {n}" for k, n in q["confusion"].items())
            )
    return lines


def render(summary: dict[str, Any]) -> str:
    """The human form of `summarize`'s result: per site, per questions sha, per question."""
    lines = [f"{summary['records']} records"]
    for name, s in summary["sites"].items():
        lines.append(f"{name}: {s['records']} records, cost ${s['cost_usd']:.6f}")
        for sha, by_sha in s["shas"].items():
            lines.extend(_sha_lines(sha, by_sha))
    return "\n".join(lines)
