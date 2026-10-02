"""Read the Jev shadow log back: agreement between the agent and Jev, per site and question.

`jev_shadow.py run` appends one record per judged item to a monthly
`jev-skill-shadow-YYYY-MM.jsonl`. This module turns those records into, per site and question:
how many items, how many were PAIRED (both the agent and Jev answered), the agreement among the
paired, the agent-by-Jev confusion counts, the share of Jev answers inside the uncertainty band,
agreement with that band excluded, and a FLAT flag. A constant answer is a broken instrument, not
consensus, so FLAT is a finding about the question, never about the items.

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

__all__ = [
    "BAND",
    "FLAT_MIN_ANSWERS",
    "FLAT_SHARE",
    "FLAT_STDEV",
    "MIN_CONFIDENCE",
    "LogRead",
    "answer_label",
    "disagreements",
    "jev_index",
    "jev_label",
    "read_records",
    "render",
    "summarize",
]

BAND = (0.2, 0.8)
MIN_CONFIDENCE = 0.6
# Below this many Jev answers a question is too small to call flat: two equal answers are noise.
FLAT_MIN_ANSWERS = 5
FLAT_STDEV = 0.05
FLAT_SHARE = 0.95


@dataclass
class LogRead:
    """Records read from the log files, and the lines that could not be read (`file:line`)."""

    records: list[dict[str, Any]] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)


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
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        out.skipped.append(path.name)
        return
    for number, line in enumerate(lines, start=1):
        rec = _parse(line)
        if rec is not None:
            out.records.append(rec)
        elif line.strip():
            out.skipped.append(f"{path.name}:{number}")


def _keep(rec: dict[str, Any], *, site: str | None, since: str | None) -> bool:
    if site is not None and rec.get("site") != site:
        return False
    return since is None or str(rec.get("ts") or "")[:10] >= since


def _parse(line: str) -> dict[str, Any] | None:
    try:
        rec = json.loads(line)
    except ValueError:
        return None
    return rec if isinstance(rec, dict) else None


def jev_index(value: float, levels: int | None = None) -> int:
    """A score's position rounded half up to the nearest level index, clamped to the levels."""
    idx = int(value + 0.5)
    return max(0, min(idx, levels - 1)) if levels else max(0, idx)


def jev_label(qtype: str, answer: dict[str, Any]) -> Any:
    """The comparable form of one Jev answer: a bool, a choice key or a score index."""
    value = answer.get("value")
    if qtype == "noul":
        return float(value) >= 0.5
    if qtype == "score":
        return jev_index(float(value))
    return value


def answer_label(value: Any) -> str:
    """A confusion-table label: `true`/`false` for a bool, the plain value otherwise."""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _in_band(qtype: str, answer: dict[str, Any]) -> bool:
    if qtype == "noul":
        return BAND[0] < float(answer.get("value") or 0.0) < BAND[1]
    confidence = answer.get("confidence")
    return isinstance(confidence, (int, float)) and confidence < MIN_CONFIDENCE


def _is_flat(qtype: str, answers: list[dict[str, Any]]) -> bool:
    if len(answers) < FLAT_MIN_ANSWERS:
        return False
    if qtype == "choice":
        top = Counter(str(a.get("value")) for a in answers).most_common(1)[0][1]
        return top / len(answers) >= FLAT_SHARE
    return statistics.pstdev(float(a.get("value") or 0.0) for a in answers) < FLAT_STDEV


def _infer_type(answer: dict[str, Any]) -> str:
    if isinstance(answer.get("value"), str):
        return "choice"
    return "score" if answer.get("probabilities") else "noul"


def _pct(part: int, whole: int) -> float | None:
    return round(100.0 * part / whole, 1) if whole else None


@dataclass
class _Tally:
    qtype: str
    n: int = 0
    paired: int = 0
    agreed: int = 0
    answers: list[dict[str, Any]] = field(default_factory=list)
    in_band: int = 0
    paired_out: int = 0
    agreed_out: int = 0
    confusion: Counter[str] = field(default_factory=Counter)

    def add(self, rec: dict[str, Any], qid: str) -> None:
        self.n += 1
        answer = ((rec.get("jev") or {}).get(qid)) or None
        band = False
        if answer is not None:
            self.answers.append(answer)
            band = _in_band(self.qtype, answer)
            self.in_band += band
        agree = (rec.get("agree") or {}).get(qid)
        if agree is None or answer is None:
            return
        self._pair(rec, qid, answer, bool(agree), band)

    def _pair(
        self,
        rec: dict[str, Any],
        qid: str,
        answer: dict[str, Any],
        agree: bool,
        band: bool,
    ) -> None:
        self.paired += 1
        self.agreed += agree
        if not band:
            self.paired_out += 1
            self.agreed_out += agree
        agent = (rec.get("agent") or {}).get(qid)
        key = f"agent={answer_label(agent)}/jev={answer_label(jev_label(self.qtype, answer))}"
        self.confusion[key] += 1

    def result(self) -> dict[str, Any]:
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


def _qids(rec: dict[str, Any]) -> list[str]:
    return list((rec.get("agree") or {}).keys())


def _qtype(qid: str, types: dict[str, str], recs: list[dict[str, Any]]) -> str:
    if qid in types:
        return types[qid]
    for rec in recs:
        answer = (rec.get("jev") or {}).get(qid)
        if answer:
            return _infer_type(answer)
    return "noul"


def _tally(
    tallies: dict[str, _Tally],
    qid: str,
    types: dict[str, str],
    recs: list[dict[str, Any]],
) -> _Tally:
    if qid not in tallies:
        tallies[qid] = _Tally(_qtype(qid, types, recs))
    return tallies[qid]


def _site_summary(recs: list[dict[str, Any]], types: dict[str, str]) -> dict[str, Any]:
    tallies: dict[str, _Tally] = {}
    for rec in recs:
        for qid in _qids(rec):
            _tally(tallies, qid, types, recs).add(rec, qid)
    cost = sum(float(r.get("cost_usd") or 0.0) for r in recs)
    return {
        "records": len(recs),
        "cost_usd": round(cost, 6),
        "questions": {qid: t.result() for qid, t in tallies.items()},
    }


def summarize(
    records: list[dict[str, Any]], types_by_site: dict[str, dict[str, str]]
) -> dict[str, Any]:
    """Per site, per question: the agreement figures described in the module docstring.

    Args:
        records: The log records to summarize.
        types_by_site: Question id -> type per site, from the current site files; a question no
            longer in its site file has its type inferred from Jev's answer.

    Returns:
        `{"records": n, "sites": {site: {"records", "cost_usd", "questions": {qid: {...}}}}}`.
    """
    by_site: dict[str, list[dict[str, Any]]] = {}
    for rec in records:
        by_site.setdefault(str(rec.get("site") or ""), []).append(rec)
    return {
        "records": len(records),
        "sites": {
            s: _site_summary(r, types_by_site.get(s, {}))
            for s, r in sorted(by_site.items())
        },
    }


def disagreements(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The paired records where any question disagrees, with their state, for reading by hand."""
    keep = (
        "ts",
        "run_id",
        "site",
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
        if any(v is False for v in (rec.get("agree") or {}).values())
    ]


def _question_line(qid: str, q: dict[str, Any]) -> str:
    flat = "  FLAT - a constant answer, check the question" if q["flat"] else ""
    return (
        f"  {qid} ({q['type']}): {q['n']} items, {q['paired']} paired, "
        f"agreement {q['agreement_pct']}%, band {q['band_pct']}%, "
        f"outside band {q['agreement_outside_band_pct']}% ({q['paired_outside_band']} paired)"
        f"{flat}"
    )


def render(summary: dict[str, Any]) -> str:
    """The human form of `summarize`'s result: one line per site, two per question."""
    lines = [f"{summary['records']} records"]
    for name, s in summary["sites"].items():
        lines.append(f"{name}: {s['records']} records, cost ${s['cost_usd']:.6f}")
        for qid, q in s["questions"].items():
            lines.append(_question_line(qid, q))
            if q["confusion"]:
                lines.append(
                    "    " + ", ".join(f"{k} {n}" for k, n in q["confusion"].items())
                )
    return "\n".join(lines)
