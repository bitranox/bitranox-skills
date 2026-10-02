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
skill step runs exactly as it does without shadow.

BLIND: `run` refuses (exit 2) unless the agent's verdicts file already exists, and it prints only
counts - never which items disagree - so the agent cannot drift toward Jev mid-task. `report` is
for afterwards.

Each item's state is redacted and capped with `classifier.prepare_state` before it is sent, and
the same redacted state is logged (jev_shadow_log.py), so a better question can be replayed over
logged items later. The sites, their questions and the item builders are in jev_shadow_sites.py;
the agreement report is jev_shadow_report.py.

Usage:
  jev_shadow.py status [--json]
  jev_shadow.py items  --site S [--anchor DIR | --firings F --hazard TEXT] --out items.jsonl [--json]
  jev_shadow.py run    --site S --items items.jsonl --verdicts verdicts.jsonl [--workdir DIR] [--json]
  jev_shadow.py report [--site S] [--since YYYY-MM-DD] [--disagreements OUT.jsonl] [--json]

Verdicts file, one line per item the agent judged (unjudged items are allowed):
  {"id": "<item id>", "verdict": {"<qid>": true|false|"<choice key>"|<score index>}, "note": "..."}

Exit codes: 0 done (or shadow off); 1 no (status: no run would happen; items: none built; run: Jev
answered no item; report: no records); 2 usage, input or IO error, including a missing verdicts
file. Standard library only.
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
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

# The hooks dir holds classifier and self_improve_signals; put it on sys.path before importing
# them, the same setup classifier_eval.py uses. The script's own dir goes there too: runpy and
# `python -I` do not add it, and the sibling modules live in it.
_HERE = Path(__file__).resolve().parent
_HOOKS = _HERE.parent.parent / "hooks"
for _d in (str(_HOOKS), str(_HERE)):
    if _d not in sys.path:
        sys.path.insert(0, _d)

import classifier as cl
import self_improve_signals as sig

import jev_shadow_log as slog
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


def knob_off_reason(cfg: dict[str, Any]) -> str | None:
    """Why the config keeps shadow off, or None when both knobs are on."""
    if cfg.get("classifier_backend") != "jev":
        return "classifier_backend is not jev"
    if cfg.get("classifier_skills") != "shadow":
        return "classifier_skills is not shadow"
    return None


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


def gate_without_key() -> Gate:
    """The knob and uvx part of the gate: the checks that start no subprocess."""
    reason = knob_off_reason(sig.load_config())
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


def _jsonl(path: Path, what: str) -> Iterator[tuple[int, Any]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError as exc:
        raise ShadowError(f"{what} file {path} does not exist") from exc
    except (OSError, UnicodeError) as exc:
        raise ShadowError(f"cannot read {what} file {path}: {exc}") from exc
    for number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            yield number, json.loads(line)
        except ValueError as exc:
            raise ShadowError(f"{path.name} line {number} is not JSON: {exc}") from exc


def _item(raw: Any, site: sites.Site, where: str) -> sites.ShadowItem:
    if (
        not isinstance(raw, dict)
        or not isinstance(raw.get("state"), dict)
        or "id" not in raw
    ):
        raise ShadowError(f'{where} is not {{"id": ..., "state": {{...}}}}')
    state = raw["state"]
    if set(state) != set(site.state_fields):
        raise ShadowError(
            f"{where}: state fields {sorted(state)}, the site {site.name} needs exactly "
            f"{sorted(site.state_fields)}"
        )
    return sites.ShadowItem(str(raw["id"]), {k: str(v) for k, v in state.items()})


def read_items(path: Path, site: sites.Site) -> list[sites.ShadowItem]:
    """The items file, each state checked to carry exactly the site's state fields.

    Raises:
        ShadowError: The file is missing or unreadable, a line is malformed, a state carries
            other fields than the site's, or an id repeats.
    """
    items, seen = [], set()
    for number, raw in _jsonl(path, "items"):
        item = _item(raw, site, f"{path.name} line {number}")
        if item.id in seen:
            raise ShadowError(f"{path.name} line {number}: duplicate id")
        seen.add(item.id)
        items.append(item)
    return items


def _valid_value(question: dict[str, Any], value: Any) -> bool:
    """A noul takes a bool, a choice one of its keys, a score an int index into its levels."""
    qtype = question["type"]
    if qtype == "noul":
        return isinstance(value, bool)
    if qtype == "choice":
        return isinstance(value, str) and value in question["criteria"]
    is_int = isinstance(value, int) and not isinstance(value, bool)
    return is_int and 0 <= value < len(question["criteria"])


def _verdict(site: sites.Site, raw: Any, where: str) -> tuple[str, slog.Verdict]:
    if (
        not isinstance(raw, dict)
        or "id" not in raw
        or not isinstance(raw.get("verdict"), dict)
    ):
        raise ShadowError(f'{where} is not {{"id": ..., "verdict": {{...}}}}')
    types = site.types()
    for qid, value in raw["verdict"].items():
        if qid not in types:
            raise ShadowError(f"{where}: {qid!r} is not a question of {site.name}")
        if not _valid_value(site.question(qid), value):
            raise ShadowError(f"{where}: {qid} is not a valid {types[qid]} answer")
    note = raw.get("note")
    return str(raw["id"]), slog.Verdict(
        dict(raw["verdict"]), None if note is None else str(note)
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
        item_id, verdict = _verdict(site, raw, f"{path.name} line {number}")
        if item_id not in item_ids or item_id in out:
            raise ShadowError(f"{path.name} line {number}: id is unknown or repeated")
        out[item_id] = verdict
    return out


# ---- asking Jev ---------------------------------------------------------------------------


def _read_rows(path: Path) -> dict[str, dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return {}
    rows = {}
    for line in lines:
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict) and "id" in row:
            rows[str(row["id"])] = row
    return rows


def _envelope_data(stdout: str) -> dict[str, Any]:
    """The `data` of jev-judge's --json envelope (its last stdout line), or {}."""
    try:
        env = json.loads(stdout.strip().splitlines()[-1]) if stdout.strip() else {}
    except ValueError:
        return {}
    data = env.get("data") if isinstance(env, dict) else None
    return data if isinstance(data, dict) else {}


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), "utf-8"
    )


def _failure(proc: subprocess.CompletedProcess[str] | None) -> str:
    if proc is None:
        return "jev-judge run could not start or timed out"
    detail = slog.short_reason(proc.stderr or proc.stdout)
    return f"jev-judge run exited {proc.returncode}: {detail}"


def ask_jev(
    uvx: str, site: sites.Site, items: list[sites.ShadowItem], workdir: Path
) -> slog.JevRun:
    """Write the redacted items and the site's questions, run jev-judge, read its rows back.

    jev-judge takes `--questions` as a JSON LIST, so the site file's `questions` are written out
    on their own rather than passing the site file.
    """
    items_path, questions_path = workdir / "items.jsonl", workdir / "questions.json"
    rows_path = workdir / "rows.jsonl"
    _write_jsonl(items_path, [{"id": i.id, "state": i.state} for i in items])
    questions_path.write_text(json.dumps(site.questions), encoding="utf-8")
    argv = ["run", "--items", str(items_path), "--questions", str(questions_path)]
    proc = _jev(uvx, *argv, "--out", str(rows_path), "--json", timeout=_RUN_TIMEOUT)
    rows = _read_rows(rows_path)
    data = _envelope_data(proc.stdout) if proc is not None else {}
    cost = data.get("cost_usd")
    return slog.JevRun(
        rows=rows,
        cost_usd=float(cost) if isinstance(cost, (int, float)) else None,
        input_tokens=int(data.get("input_tokens") or 0),
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
    data: dict[str, Any],
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
    gate = with_key(gate_without_key())
    cfg = sig.load_config()
    data = {
        "classifier_backend": cfg.get("classifier_backend"),
        "classifier_skills": cfg.get("classifier_skills"),
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
    _emit(
        args,
        "items",
        bool(items),
        data,
        f"{site.name}: {len(items)} items written to {out}",
    )
    return EXIT_OK if items else EXIT_NO


def _off(args: argparse.Namespace, reason: str) -> int:
    _emit(
        args,
        "run",
        True,
        {"shadow": "off", "reason": reason},
        f"shadow: off ({reason})",
    )
    return EXIT_OK


@contextmanager
def _workdir(given: str | None) -> Iterator[Path]:
    """--workdir when given (kept), else a temporary directory removed afterwards."""
    if given:
        path = Path(given)
        path.mkdir(parents=True, exist_ok=True)
        yield path
        return
    with tempfile.TemporaryDirectory(prefix="jev-shadow-") as tmp:
        yield Path(tmp)


def _counts(records: list[dict[str, Any]], jev: slog.JevRun) -> dict[str, Any]:
    """Counts only - never an item id, which would let the agent see where Jev disagrees."""
    votes = [v for r in records for v in r["agree"].values() if v is not None]
    return {
        "items": len(records),
        "paired": sum(
            1 for r in records if r["agent"] is not None and r["jev"] is not None
        ),
        "answers_paired": len(votes),
        "answers_agreed": sum(votes),
        "jev_failed": sum(1 for r in records if r["jev"] is None),
        "cost_usd": jev.cost_usd,
    }


def _human_counts(c: dict[str, Any]) -> str:
    cost = "" if c["cost_usd"] is None else f", ~${c['cost_usd']:.6f}"
    return (
        f"shadow: {c['items']} items, {c['paired']} paired, {c['answers_agreed']} of "
        f"{c['answers_paired']} answers agreed, {c['jev_failed']} without a Jev answer{cost}"
    )


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
        # The classifier's own manifest reader, so shadow rows name the release the same way.
        plugin_version=cl._plugin_version(),
        jev=jev,
    )


def _redacted(items: list[sites.ShadowItem]) -> list[tuple[sites.ShadowItem, int]]:
    """Each item with its state redacted and capped as it will be sent and logged."""
    out = []
    for item in items:
        state, n = cl.prepare_state(item.state)
        out.append((sites.ShadowItem(item.id, state), n))
    return out


def cmd_run(args: argparse.Namespace) -> int:
    """Ask Jev the site's questions about items the agent has already judged, and log both."""
    site = sites.load_site(args.site)
    gate = gate_without_key()
    if not gate.on:
        return _off(args, str(gate.reason))
    items = read_items(Path(args.items), site)
    verdicts = read_verdicts(Path(args.verdicts), site, {i.id for i in items})
    gate = with_key(gate)
    if not gate.on or gate.uvx is None:
        return _off(args, str(gate.reason))
    prepared = _redacted(items)
    with _workdir(args.workdir) as workdir:
        jev = ask_jev(gate.uvx, site, [i for i, _n in prepared], workdir)
    now = datetime.now(UTC)
    ctx = _context(site, gate.uvx, jev, now)
    records = [slog.build_record(ctx, i, n, verdicts.get(i.id)) for i, n in prepared]
    slog.append_records(records, now)
    counts = _counts(records, jev)
    if jev.reason:
        print(f"jev_shadow: {jev.reason}", file=sys.stderr)
    answered = counts["jev_failed"] < counts["items"]
    _emit(args, "run", answered, counts, _human_counts(counts))
    return EXIT_OK if answered else EXIT_NO


def _check_since(since: str | None) -> None:
    if since is None:
        return
    try:
        date.fromisoformat(since)
    except ValueError as exc:
        raise ShadowError(f"--since {since!r} is not YYYY-MM-DD") from exc


def cmd_report(args: argparse.Namespace) -> int:
    """Agreement per site and question over the shadow log."""
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
    types = {name: sites.load_site(name).types() for name in sites.site_names()}
    summary = rpt.summarize(log.records, types)
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
    except (ShadowError, sites.SiteError, slog.LogLocked) as exc:
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
