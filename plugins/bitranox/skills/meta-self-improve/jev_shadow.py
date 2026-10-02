#!/usr/bin/env python3
"""Jev shadow for skill judgment sites: the agent keeps judging, Jev answers the same items beside it.

Several skill steps make one bounded judgment over many items (is this guard firing real, is this
memory note a stale negative claim, which level does this fact belong at). In shadow mode the agent
still decides every item itself. It writes its verdicts to a file FIRST, then this tool asks Jev
(TypeSafe, through the published `jev-judge` CLI) the same questions about the same items and logs
both answers per item, so a later report can say whether Jev could take that step over.

Off unless the user set `classifier_backend = jev` AND `classifier_skills = shadow`
(meta-memory-settings); turning it on is the consent to send these items to TypeSafe. With the knob
off, no `uvx`, or no key, `run` prints `shadow: off (<reason>)`, exits 0 and writes nothing, so the
skill step runs exactly as it does without shadow. A non-empty `classifier_model` knob is passed
to jev-judge as `--model`; empty, jev-judge chooses.

BLIND: `run` refuses (exit 2) unless the agent's verdicts file already exists, and it prints only
counts - never which items disagree - so the agent cannot drift toward Jev mid-task. `report` is
for afterwards.

Each item's state is redacted and capped with `classifier.prepare_state` before it is sent, and
the same redacted state is logged (jev_shadow_log.py), so a better question can be replayed over
logged items later. The sites, their questions and the item builders are in jev_shadow_sites.py,
the agreement report in jev_shadow_report.py, and the typed facade over the hook modules in
jev_shadow_ports.py.

Usage:
  jev_shadow.py status [--json]
  jev_shadow.py items  --site S [--anchor DIR | --firings F --hazard TEXT] --out items.jsonl [--json]
  jev_shadow.py run    --site S --items items.jsonl --verdicts verdicts.jsonl [--workdir DIR] [--json]
  jev_shadow.py report [--site S] [--since YYYY-MM-DD] [--disagreements OUT.jsonl] [--json]

Verdicts file, one line per item the agent judged (unjudged items are allowed):
  {"id": "<item id>", "verdict": {"<qid>": true|false|"<choice key>"|<score index>}, "note": "..."}

Exit codes: 0 done (or shadow off, or no items to ask about); 1 no (status: no run would happen;
items: none built; run: Jev answered no item; report: no records); 2 usage, input or IO error,
including a missing verdicts file. Standard library only.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
from collections.abc import Generator, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

# The sibling modules live beside this script; runpy and `python -I` do not put its dir on
# sys.path. jev_shadow_ports adds the hooks dir the same way classifier_eval.py does.
_HERE = str(Path(__file__).resolve().parent)
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import jev_shadow_log as slog
import jev_shadow_ports as ports
import jev_shadow_report as rpt
import jev_shadow_sites as sites

__all__ = [
    "EXIT_ERROR",
    "EXIT_NO",
    "EXIT_OK",
    "JEV_JUDGE_FLOOR",
    "JEV_JUDGE_SPEC",
    "Gate",
    "ShadowError",
    "check_key",
    "main",
    "read_items",
    "read_verdicts",
]

# Pinned by a test to the floor in ai-llm-jev-judge/SKILL.md: a sync that raises it there fails
# until this follows.
JEV_JUDGE_FLOOR = "0.2.4"
JEV_JUDGE_SPEC = "btx-skill-jev-judge>=" + JEV_JUDGE_FLOOR
EXIT_OK, EXIT_NO, EXIT_ERROR = 0, 1, 2
# uvx may download jev-judge and its Python on first use; a run is paced by Jev's rate limit.
_CHECK_TIMEOUT = 300
_RUN_TIMEOUT = 3600


class ShadowError(Exception):
    """A usage, input or IO problem: one line on stderr, exit 2."""


# ---- the gate: knob, uvx, key -------------------------------------------------------------


def knob_off_reason(cfg: Mapping[str, object]) -> str | None:
    """Why the config keeps shadow off, or None when both knobs are on."""
    if cfg.get("classifier_backend") != "jev":
        return "classifier_backend is not jev"
    if cfg.get("classifier_skills") != "shadow":
        return "classifier_skills is not shadow"
    return None


def model_knob(cfg: Mapping[str, object]) -> str | None:
    """The `classifier_model` knob when it holds a non-empty string; None lets jev-judge choose."""
    model = cfg.get("classifier_model")
    return model.strip() if isinstance(model, str) and model.strip() else None


def _jev(
    uvx: str, *args: str, timeout: float
) -> subprocess.CompletedProcess[str] | None:
    """Run `jev-judge <args>` through uvx; None when it could not be started or timed out."""
    argv = [uvx, "--from", JEV_JUDGE_SPEC, "jev-judge", *args]
    try:
        return subprocess.run(
            argv,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None


def check_key(uvx: str) -> tuple[bool | None, str]:
    """Ask `jev-judge check-key`, which reports where a key is and never prints it.

    Returns:
        (True, "") with a key, (False, why) without one, (None, why) when check-key itself failed.
    """
    proc = _jev(uvx, "check-key", timeout=_CHECK_TIMEOUT)
    if proc is None:
        return None, "jev-judge check-key could not run"
    if proc.returncode == 0:
        return True, ""
    if proc.returncode == 1:
        return False, "no Jev key"
    return None, f"jev-judge check-key failed (exit {proc.returncode})"


def jev_judge_version(uvx: str) -> str | None:
    """The jev-judge version uvx resolved, or None."""
    proc = _jev(uvx, "--version", timeout=_CHECK_TIMEOUT)
    if proc is None or proc.returncode != 0:
        return None
    m = re.search(r"version\s+(\S+)", proc.stdout)
    return m.group(1) if m else None


@dataclass(frozen=True)
class Gate:
    """Whether a run would happen, and why not."""

    uvx: str | None
    key: bool | None
    reason: str | None

    @property
    def on(self) -> bool:
        """True when nothing keeps shadow off."""
        return self.reason is None


def gate_without_key(cfg: Mapping[str, object]) -> Gate:
    """The knob and uvx part of the gate: the checks that start no subprocess."""
    reason = knob_off_reason(cfg)
    uvx = shutil.which("uvx")
    if reason is None and uvx is None:
        reason = "uvx not found on PATH"
    return Gate(uvx=uvx, key=None, reason=reason)


def with_key(gate: Gate) -> Gate:
    """Add the key check (one subprocess, spends nothing) to a gate that has uvx."""
    if gate.uvx is None:
        return gate
    present, why = check_key(gate.uvx)
    reason = gate.reason
    if reason is None and present is not True:
        reason = why
    return Gate(uvx=gate.uvx, key=present, reason=reason)


# ---- input files --------------------------------------------------------------------------


def _jsonl(path: Path, what: str) -> Iterator[tuple[int, object]]:
    """(line number, decoded value) per non-blank line, split on "\\n" only (see jsonl_lines)."""
    try:
        lines = sites.jsonl_lines(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ShadowError(f"{what} file {path} does not exist") from exc
    except (OSError, UnicodeError) as exc:
        raise ShadowError(f"cannot read {what} file {path}: {exc}") from exc
    for number, line in enumerate(lines, start=1):
        try:
            yield number, json.loads(line)
        except ValueError as exc:
            raise ShadowError(
                f"{path.name} record {number} is not JSON: {exc}"
            ) from exc


def _state_text(value: object) -> str:
    """A state field as Jev reads it: a JSON null is an empty field, never the text "None"."""
    return "" if value is None else str(value)


def _item(raw: object, site: sites.Site, where: str) -> sites.ShadowItem:
    rec = rpt.as_record(raw)
    state = None if rec is None else rpt.as_record(rec.get("state"))
    if rec is None or state is None or "id" not in rec:
        raise ShadowError(f'{where} is not {{"id": ..., "state": {{...}}}}')
    if set(state) != set(site.state_fields):
        raise ShadowError(
            f"{where}: state fields {sorted(state)}, the site {site.name} needs exactly "
            f"{sorted(site.state_fields)}"
        )
    return sites.ShadowItem(
        str(rec["id"]), {k: _state_text(v) for k, v in state.items()}
    )


def read_items(path: Path, site: sites.Site) -> list[sites.ShadowItem]:
    """The items file, each state checked to carry exactly the site's state fields.

    Raises:
        ShadowError: The file is missing or unreadable, a line is malformed, a state carries
            other fields than the site's, or an id repeats.
    """
    items: list[sites.ShadowItem] = []
    seen: set[str] = set()
    for number, raw in _jsonl(path, "items"):
        item = _item(raw, site, f"{path.name} record {number}")
        if item.id in seen:
            raise ShadowError(f"{path.name} record {number}: duplicate id")
        seen.add(item.id)
        items.append(item)
    return items


def _valid_value(question: Mapping[str, Any], value: object) -> bool:
    """A noul takes a bool, a choice one of its keys, a score an int index into its levels."""
    qtype = question["type"]
    if qtype == "noul":
        return isinstance(value, bool)
    if qtype == "choice":
        return isinstance(value, str) and value in question["criteria"]
    if isinstance(value, bool) or not isinstance(value, int):
        return False
    return 0 <= value < len(question["criteria"])


def _verdict(site: sites.Site, raw: object, where: str) -> tuple[str, slog.Verdict]:
    rec = rpt.as_record(raw)
    answers = None if rec is None else rpt.as_record(rec.get("verdict"))
    if rec is None or answers is None or "id" not in rec:
        raise ShadowError(f'{where} is not {{"id": ..., "verdict": {{...}}}}')
    types = site.types()
    for qid, value in answers.items():
        if qid not in types:
            raise ShadowError(f"{where}: {qid!r} is not a question of {site.name}")
        if not _valid_value(site.question(qid), value):
            raise ShadowError(f"{where}: {qid} is not a valid {types[qid]} answer")
    note: object = rec.get("note")
    return str(rec["id"]), slog.Verdict(
        dict(answers), None if note is None else str(note)
    )


def read_verdicts(
    path: Path, site: sites.Site, item_ids: set[str]
) -> dict[str, slog.Verdict]:
    """The agent's verdicts by item id.

    Raises:
        ShadowError: The file does not exist (that is what keeps the agent blind: it must have
            judged before Jev is asked), or a line is malformed, names an unknown or repeated
            item, an unknown question, or an answer of the wrong type.
    """
    if not path.is_file():
        raise ShadowError(
            f"verdicts file {path} does not exist: write your own verdicts BEFORE asking "
            "Jev (shadow mode is blind)"
        )
    out: dict[str, slog.Verdict] = {}
    for number, raw in _jsonl(path, "verdicts"):
        item_id, verdict = _verdict(site, raw, f"{path.name} record {number}")
        if item_id not in item_ids or item_id in out:
            raise ShadowError(f"{path.name} record {number}: id is unknown or repeated")
        out[item_id] = verdict
    return out


# ---- asking Jev ---------------------------------------------------------------------------


def _decoded(line: str) -> object:
    try:
        return json.loads(line)
    except ValueError:
        return None


def _read_rows(path: Path) -> dict[str, dict[str, Any]]:
    """jev-judge's rows by item id; a missing file or a malformed line reads as no row."""
    try:
        lines = sites.jsonl_lines(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError):
        return {}
    rows: dict[str, dict[str, Any]] = {}
    for line in lines:
        row = rpt.as_record(_decoded(line))
        if row is not None and "id" in row:
            rows[str(row["id"])] = row
    return rows


def _envelope_data(stdout: str) -> dict[str, Any]:
    """The `data` of jev-judge's --json envelope (its last stdout line), or {}."""
    lines = sites.jsonl_lines(stdout)
    env = rpt.as_record(_decoded(lines[-1])) if lines else None
    data = None if env is None else rpt.as_record(env.get("data"))
    return data or {}


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), "utf-8"
    )


def _failure(proc: subprocess.CompletedProcess[str] | None) -> str:
    if proc is None:
        return "jev-judge run could not start or timed out"
    detail = slog.short_reason(proc.stderr or proc.stdout)
    return f"jev-judge run exited {proc.returncode}: {detail}"


@dataclass(frozen=True)
class JevRequest:
    """One jev-judge run: the site, its redacted items, where to work, and the model knob."""

    site: sites.Site
    items: list[sites.ShadowItem]
    workdir: Path
    model: str | None


def ask_jev(uvx: str, req: JevRequest) -> slog.JevRun:
    """Write the redacted items and the site's questions, run jev-judge, read its rows back.

    jev-judge takes `--questions` as a JSON LIST, so the site file's `questions` are written out
    on their own rather than passing the site file.
    """
    items_path, rows_path = req.workdir / "items.jsonl", req.workdir / "rows.jsonl"
    questions_path = req.workdir / "questions.json"
    _write_jsonl(items_path, [{"id": i.id, "state": i.state} for i in req.items])
    questions_path.write_text(json.dumps(req.site.questions), encoding="utf-8")
    argv = ["run", "--items", str(items_path), "--questions", str(questions_path)]
    argv += ["--out", str(rows_path), "--json"]
    if req.model:
        argv += ["--model", req.model]
    proc = _jev(uvx, *argv, timeout=_RUN_TIMEOUT)
    rows = _read_rows(rows_path)
    data = _envelope_data(proc.stdout) if proc is not None else {}
    cost: object = data.get("cost_usd")
    tokens: object = data.get("input_tokens")
    return slog.JevRun(
        rows=rows,
        cost_usd=float(cost) if isinstance(cost, int | float) else None,
        input_tokens=tokens if isinstance(tokens, int) else 0,
        reason=None if rows else _failure(proc),
    )


def _git_head(cwd: str) -> str | None:
    git = shutil.which("git")
    if git is None:
        return None
    try:
        proc = subprocess.run(
            [git, "rev-parse", "HEAD"],
            cwd=cwd,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip() or None


# ---- commands -------------------------------------------------------------------------------


def _emit(
    args: argparse.Namespace,
    command: str,
    ok: bool,
    data: Mapping[str, object],
    human: str,
    skipped: list[str] | None = None,
) -> None:
    if args.json:
        envelope = {
            "ok": ok,
            "command": command,
            "data": data,
            "skipped": skipped or [],
        }
        print(json.dumps(envelope))
    else:
        print(human)


def cmd_status(args: argparse.Namespace) -> int:
    """Would a run happen? Knob, uvx and key; it spends nothing."""
    cfg = ports.load_config()
    gate = with_key(gate_without_key(cfg))
    data = {
        "classifier_backend": cfg.get("classifier_backend"),
        "classifier_skills": cfg.get("classifier_skills"),
        "classifier_model": model_knob(cfg),
        "uvx": gate.uvx,
        "key": gate.key,
        "would_run": gate.on,
        "reason": gate.reason,
    }
    human = "shadow: on" if gate.on else f"shadow: off ({gate.reason})"
    _emit(args, "status", gate.on, data, human)
    return EXIT_OK if gate.on else EXIT_NO


def cmd_items(args: argparse.Namespace) -> int:
    """Build a store-based site's items into --out."""
    site = sites.load_site(args.site)
    req = sites.BuildRequest(
        anchor=Path(args.anchor) if args.anchor else None,
        firings=Path(args.firings) if args.firings else None,
        hazard=args.hazard,
    )
    items = sites.build_items(site, req)
    out = Path(args.out)
    try:
        _write_jsonl(out, [{"id": i.id, "state": i.state} for i in items])
    except OSError as exc:
        raise ShadowError(f"cannot write --out {out}: {exc}") from exc
    data = {"site": site.name, "items": len(items), "out": str(out)}
    human = f"{site.name}: {len(items)} items written to {out}"
    _emit(args, "items", bool(items), data, human)
    return EXIT_OK if items else EXIT_NO


def _quiet(args: argparse.Namespace, data: dict[str, object], human: str) -> int:
    """Exit 0 having asked nothing: shadow is off, or there is nothing to ask about."""
    _emit(args, "run", True, data, human)
    return EXIT_OK


def _off(args: argparse.Namespace, reason: str) -> int:
    return _quiet(args, {"shadow": "off", "reason": reason}, f"shadow: off ({reason})")


@contextmanager
def _workdir(given: str | None) -> Generator[Path, None, None]:
    """--workdir when given (kept), else a temporary directory removed afterwards."""
    if given:
        path = Path(given)
        path.mkdir(parents=True, exist_ok=True)
        yield path
        return
    with tempfile.TemporaryDirectory(prefix="jev-shadow-") as tmp:
        yield Path(tmp)


def _is_paired(record: Mapping[str, Any]) -> bool:
    """Paired: at least one question has both an agent answer and a Jev answer."""
    return any(v is not None for v in record["agree"].values())


def _counts(records: list[dict[str, Any]], jev: slog.JevRun) -> dict[str, object]:
    """Counts only - never an item id, which would let the agent see where Jev disagrees."""
    votes: list[bool] = [
        v for r in records for v in r["agree"].values() if v is not None
    ]
    return {
        "items": len(records),
        "paired": sum(1 for r in records if _is_paired(r)),
        "answers_paired": len(votes),
        "answers_agreed": sum(votes),
        "jev_failed": sum(1 for r in records if r["jev"] is None),
        "cost_usd": jev.cost_usd,
    }


def _human_counts(c: Mapping[str, Any]) -> str:
    cost = "" if c["cost_usd"] is None else f", ~${c['cost_usd']:.6f}"
    return (
        f"shadow: {c['items']} items, {c['paired']} paired, {c['answers_agreed']} of "
        f"{c['answers_paired']} answers agreed, {c['jev_failed']} without a Jev answer{cost}"
    )


def _no_answer_reason(records: list[dict[str, Any]], jev: slog.JevRun) -> str:
    """Why Jev answered no item: the run's failure, else the first row's reason (no item id)."""
    if jev.reason:
        return jev.reason
    first = next(
        (str(r["jev_reason"]) for r in records if r["jev_reason"]), "no reason given"
    )
    return f"Jev answered none of {len(records)} items: {first}"


def _context(
    site: sites.Site, uvx: str, jev: slog.JevRun, now: datetime
) -> slog.RunContext:
    cwd = str(Path.cwd())
    return slog.RunContext(
        ts=now.isoformat(timespec="seconds"),
        run_id=uuid.uuid4().hex,
        site=site,
        jev_judge_version=jev_judge_version(uvx),
        cwd=cwd,
        git_head=_git_head(cwd),
        plugin_version=ports.plugin_version(),
        jev=jev,
    )


def _redacted(items: list[sites.ShadowItem]) -> list[tuple[sites.ShadowItem, int]]:
    """Each item with its state redacted and capped as it will be sent and logged."""
    out: list[tuple[sites.ShadowItem, int]] = []
    for item in items:
        state, n = ports.prepare_state(item.state)
        out.append((sites.ShadowItem(item.id, state), n))
    return out


@dataclass(frozen=True)
class _RunPlan:
    """Everything `run` has checked before asking Jev: the site, items, verdicts and model."""

    site: sites.Site
    items: list[sites.ShadowItem]
    verdicts: dict[str, slog.Verdict]
    model: str | None


def _ask_and_log(args: argparse.Namespace, uvx: str, plan: _RunPlan) -> int:
    prepared = _redacted(plan.items)
    with _workdir(args.workdir) as workdir:
        jev = ask_jev(
            uvx, JevRequest(plan.site, [i for i, _n in prepared], workdir, plan.model)
        )
    now = datetime.now(UTC)
    ctx = _context(plan.site, uvx, jev, now)
    records = [
        slog.build_record(ctx, i, n, plan.verdicts.get(i.id)) for i, n in prepared
    ]
    slog.append_records(records, now)
    counts = _counts(records, jev)
    answered = counts["jev_failed"] != counts["items"]
    if not answered:
        print(f"jev_shadow: {_no_answer_reason(records, jev)}", file=sys.stderr)
    elif jev.reason:
        print(f"jev_shadow: {jev.reason}", file=sys.stderr)
    _emit(args, "run", answered, counts, _human_counts(counts))
    return EXIT_OK if answered else EXIT_NO


def cmd_run(args: argparse.Namespace) -> int:
    """Ask Jev the site's questions about items the agent has already judged, and log both."""
    site = sites.load_site(args.site)
    cfg = ports.load_config()
    gate = gate_without_key(cfg)
    if not gate.on:
        return _off(args, str(gate.reason))
    items = read_items(Path(args.items), site)
    if not items:
        return _quiet(args, {"items": 0}, "shadow: 0 items, nothing asked")
    verdicts = read_verdicts(Path(args.verdicts), site, {i.id for i in items})
    gate = with_key(gate)
    if not gate.on or gate.uvx is None:
        return _off(args, str(gate.reason))
    return _ask_and_log(
        args, gate.uvx, _RunPlan(site, items, verdicts, model_knob(cfg))
    )


def _check_since(since: str | None) -> None:
    if since is None:
        return
    try:
        date.fromisoformat(since)
    except ValueError as exc:
        raise ShadowError(f"--since {since!r} is not YYYY-MM-DD") from exc


def _spec(site: sites.Site) -> rpt.SiteSpec:
    levels = {
        str(q["id"]): len(q["criteria"]) for q in site.questions if q["type"] == "score"
    }
    return rpt.SiteSpec(sha=site.questions_sha, types=site.types(), levels=levels)


def cmd_report(args: argparse.Namespace) -> int:
    """Agreement per site, per questions sha, per question over the shadow log."""
    _check_since(args.since)
    log = rpt.read_records(
        slog.log_files(slog.audit_dir()), site=args.site, since=args.since
    )
    if not log.records:
        print("jev_shadow: no shadow records match", file=sys.stderr)
        _emit(
            args, "report", False, {"records": 0, "sites": {}}, "0 records", log.skipped
        )
        return EXIT_NO
    specs = {name: _spec(sites.load_site(name)) for name in sites.site_names()}
    summary = rpt.summarize(log.records, specs)
    if args.disagreements:
        out = Path(args.disagreements)
        try:
            _write_jsonl(out, rpt.disagreements(log.records))
        except OSError as exc:
            raise ShadowError(f"cannot write --disagreements {out}: {exc}") from exc
    _emit(args, "report", True, summary, rpt.render(summary), log.skipped)
    return EXIT_OK


# ---- argv -----------------------------------------------------------------------------------


def _parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="jev_shadow.py", description=(__doc__ or "").split("\n")[0]
    )
    sub = ap.add_subparsers(dest="command", required=True)
    st = sub.add_parser("status", help="would a run happen: knob, uvx, key")
    it = sub.add_parser("items", help="build a store-based site's items")
    it.add_argument("--site", required=True)
    it.add_argument(
        "--anchor", help="memory tree anchor (dream-* and crosstree-misplaced)"
    )
    it.add_argument("--firings", help="guard_replay.py --firings output (guard-firing)")
    it.add_argument("--hazard", help="what the guard warns about (guard-firing)")
    it.add_argument("--out", required=True)
    rn = sub.add_parser("run", help="ask Jev beside the agent's verdicts and log both")
    rn.add_argument("--site", required=True)
    rn.add_argument("--items", required=True)
    rn.add_argument("--verdicts", required=True)
    rn.add_argument(
        "--workdir", help="keep jev-judge's input and rows here (default: a temp dir)"
    )
    rp = sub.add_parser("report", help="agreement per site and question")
    rp.add_argument("--site")
    rp.add_argument("--since", help="only records on or after YYYY-MM-DD")
    rp.add_argument(
        "--disagreements", help="write the disagreeing paired items here (JSONL)"
    )
    for p in (st, it, rn, rp):
        p.add_argument(
            "--json", action="store_true", help="{ok, command, data, skipped}"
        )
    return ap


_COMMANDS = {
    "status": cmd_status,
    "items": cmd_items,
    "run": cmd_run,
    "report": cmd_report,
}


def main(argv: list[str] | None = None) -> int:
    """Parse argv, run the command, map refusals to exit 2 with one line on stderr.

    An OSError (an unwritable log, workdir or output) is an IO error like any refusal here:
    exit 2 and one line, never a traceback with exit 1, which would read as "Jev answered none".

    Args:
        argv: The arguments after the program name; None reads sys.argv.

    Returns:
        The exit code: 0 done or shadow off, 1 no, 2 usage, input or IO error.
    """
    try:
        args = _parser().parse_args(argv)
    except SystemExit as exc:
        return int(exc.code or 0)
    try:
        return _COMMANDS[args.command](args)
    except (ShadowError, sites.SiteError, OSError) as exc:
        print(f"jev_shadow: {exc}", file=sys.stderr)
        if args.json:
            data = {"error": str(exc)}
            print(
                json.dumps(
                    {"ok": False, "command": args.command, "data": data, "skipped": []}
                )
            )
        return EXIT_ERROR


if __name__ == "__main__":
    sys.exit(main())
