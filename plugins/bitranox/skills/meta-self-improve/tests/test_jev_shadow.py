"""Tests for jev_shadow.py: the Jev shadow tool for skill judgment sites.

Every test drives the real CLI through `main(argv)`. The only thing faked is the external edge:
a fake `uvx` executable placed first on PATH, which answers `jev-judge --version`, `check-key`
and `run` with canned rows and records every invocation it receives. HOME is pointed at a
temporary directory, so the knob file, the key lookup and the audit log all resolve there through
the same `Path.home()` seam the hooks use. Nothing inside jev_shadow is patched.
"""

import json
import os
import re
import stat
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

import jev_shadow as js
import jev_shadow_log as slog
import jev_shadow_sites as sites

# The store writer, from the module that put hooks/ on sys.path: a top-level import of it
# would depend on import order, which the import sorter does not preserve.
ME = sites.ME
SKILL_DIR = Path(__file__).resolve().parent.parent
SITES_DIR = SKILL_DIR / "jev_sites"
JEV_SKILL = SKILL_DIR.parent / "ai-llm-jev-judge" / "SKILL.md"

# The fake is a POSIX shell wrapper around a Python script. On Windows a fake found by
# shutil.which must be a .cmd/.bat file, and cmd.exe parses the `>=` inside the `--from
# btx-skill-jev-judge>=X` argument as an output redirection, so the fake could never receive the
# argv the real uvx.exe gets. The subprocess tests therefore run on POSIX only.
posix_only = pytest.mark.skipif(
    os.name == "nt",
    reason="a fake uvx on Windows must be a batch file, and cmd.exe reads the >= in the "
    "--from spec as a redirection, so it cannot receive the real argv",
)

FAKE_UVX = r"""
import json, os, sys

argv = sys.argv[1:]
with open(os.environ["FAKE_UVX_LOG"], "a", encoding="utf-8") as fh:
    fh.write(json.dumps(argv) + "\n")
if argv[:1] == ["--from"]:
    argv = argv[2:]
assert argv[0] == "jev-judge", argv
args = argv[1:]
if args == ["--version"]:
    print("btx-skill-jev-judge version 0.2.4")
    sys.exit(0)
if args[0] == "check-key":
    sys.exit(0 if os.environ.get("FAKE_JEV_KEY") == "present" else 1)
if args[0] != "run":
    sys.exit(2)


def opt(name):
    return args[args.index(name) + 1]


canned = json.load(open(os.environ["FAKE_JEV_ROWS"], encoding="utf-8"))
items = [json.loads(line) for line in open(opt("--items"), encoding="utf-8") if line.strip()]
seen = os.environ.get("FAKE_JEV_SEEN")
if seen:
    with open(seen, "w", encoding="utf-8") as fh:
        json.dump({"items": items, "questions": json.load(open(opt("--questions"), encoding="utf-8"))}, fh)
rows, failed, tokens = [], [], 0
for it in items:
    row = canned.get(it["id"])
    if row is None:
        rows.append({"id": it["id"], "ok": False, "answers": {}, "reason": "canned failure"})
        failed.append(it["id"])
        continue
    rows.append({"id": it["id"], "ok": True, "answers": row, "input_tokens": 100,
                 "latency_ms": 300, "model": "jev-1.13"})
    tokens += 100
with open(opt("--out"), "w", encoding="utf-8") as fh:
    for r in rows:
        fh.write(json.dumps(r) + "\n")
data = {"rows": len(rows), "answered": len(rows) - len(failed), "failed": failed,
        "out": opt("--out"), "input_tokens": tokens, "cost_usd": tokens * 0.042 / 1e6,
        "redactions": 0, "models": ["jev-1.13"], "seconds": 0.1}
print(json.dumps({"ok": not failed, "command": "run", "data": data, "skipped": []}))
sys.exit(1 if failed else 0)
"""

TOKEN = "ghp_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8"


# ---- fixtures -----------------------------------------------------------------------------


@pytest.fixture
def home(tmp_path, monkeypatch):
    """A HOME of our own: knob file, key lookup and audit log all resolve under it."""
    h = tmp_path / "home"
    (h / ".claude").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    return h


@pytest.fixture
def fake(tmp_path, monkeypatch, home):
    """The fake uvx first on PATH, with a key present and no canned rows yet."""
    bindir = tmp_path / "bin"
    bindir.mkdir()
    script = bindir / "fake_uvx.py"
    script.write_text(FAKE_UVX, encoding="utf-8")
    wrapper = bindir / "uvx"
    wrapper.write_text(
        f'#!/bin/sh\nexec "{sys.executable}" "{script}" "$@"\n', encoding="utf-8"
    )
    wrapper.chmod(wrapper.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    log = tmp_path / "uvx-calls.jsonl"
    rows = tmp_path / "canned.json"
    rows.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("PATH", str(bindir) + os.pathsep + os.environ.get("PATH", ""))
    monkeypatch.setenv("FAKE_UVX_LOG", str(log))
    monkeypatch.setenv("FAKE_JEV_ROWS", str(rows))
    monkeypatch.setenv("FAKE_JEV_KEY", "present")
    return {"log": log, "rows": rows, "seen": tmp_path / "seen.json"}


def knob(home, on=True):
    cfg = {"classifier_backend": "jev", "classifier_skills": "shadow"} if on else {}
    (home / ".claude" / ".bitranox-memory.json").write_text(
        json.dumps(cfg), encoding="utf-8"
    )


def write_jsonl(path, rows):
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    return path


def read_jsonl(path):
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def audit(home):
    return home / ".claude" / "self-improve-audit"


def shadow_logs(home):
    d = audit(home)
    return sorted(d.glob("jev-skill-shadow-*.jsonl")) if d.is_dir() else []


def calls(fake):
    return read_jsonl(fake["log"]) if fake["log"].exists() else []


def subcommands(fake):
    """The jev-judge subcommand of every uvx call the fake received."""
    out = []
    for argv in calls(fake):
        rest = argv[2:] if argv[:1] == ["--from"] else argv
        out.append(rest[1] if len(rest) > 1 else "")
    return out


def noul(v):
    return {"type": "noul", "value": v}


PRUNE_ITEMS = [
    {
        "id": "slug-alpha",
        "state": {"hook": "When X, do Y.", "body": "Body with " + TOKEN + " inside."},
    },
    {"id": "slug-beta", "state": {"hook": "When Z, do W.", "body": "Body two."}},
    {"id": "slug-gamma", "state": {"hook": "When Q, do R.", "body": "Body three."}},
]
PRUNE_VERDICTS = [
    {
        "id": "slug-alpha",
        "verdict": {"untestable_negative": True, "unlabelled_unsolved": False},
        "note": "claims a tool fails, no version",
    },
    {"id": "slug-beta", "verdict": {"untestable_negative": True}},
]
PRUNE_ROWS = {
    "slug-alpha": {"untestable_negative": noul(0.9), "unlabelled_unsolved": noul(0.7)},
    "slug-beta": {"untestable_negative": noul(0.2), "unlabelled_unsolved": noul(0.1)},
    "slug-gamma": {"untestable_negative": noul(0.4), "unlabelled_unsolved": noul(0.6)},
}


def run_prune(tmp_path, fake, rows=PRUNE_ROWS, verdicts=PRUNE_VERDICTS, extra=()):
    fake["rows"].write_text(json.dumps(rows), encoding="utf-8")
    items = write_jsonl(tmp_path / "items.jsonl", PRUNE_ITEMS)
    vpath = write_jsonl(tmp_path / "verdicts.jsonl", verdicts)
    return js.main(
        [
            "run",
            "--site",
            "dream-prune",
            "--items",
            str(items),
            "--verdicts",
            str(vpath),
            *extra,
        ]
    )


# ---- run: the gates ---------------------------------------------------------------------------


@posix_only
def test_knob_off_runs_no_subprocess_and_writes_no_log(tmp_path, fake, home, capsys):
    knob(home, on=False)
    rc = run_prune(tmp_path, fake)
    out = capsys.readouterr().out
    assert rc == 0
    assert out.startswith("shadow: off (")
    assert calls(fake) == []
    assert shadow_logs(home) == []


@posix_only
def test_backend_off_alone_keeps_shadow_off(tmp_path, fake, home, capsys):
    """classifier_skills=shadow is not enough: the backend is the master switch."""
    (home / ".claude" / ".bitranox-memory.json").write_text(
        json.dumps({"classifier_skills": "shadow"}), encoding="utf-8"
    )
    assert run_prune(tmp_path, fake) == 0
    assert "shadow: off (" in capsys.readouterr().out
    assert calls(fake) == []


@posix_only
def test_no_key_is_shadow_off_and_writes_no_log(
    tmp_path, fake, home, capsys, monkeypatch
):
    knob(home)
    monkeypatch.setenv("FAKE_JEV_KEY", "absent")
    rc = run_prune(tmp_path, fake)
    assert rc == 0
    assert "shadow: off (" in capsys.readouterr().out
    assert "run" not in subcommands(fake)
    assert shadow_logs(home) == []


@posix_only
def test_missing_verdicts_file_is_exit_2_and_calls_nothing(
    tmp_path, fake, home, capsys
):
    knob(home)
    items = write_jsonl(tmp_path / "items.jsonl", PRUNE_ITEMS)
    rc = js.main(
        [
            "run",
            "--site",
            "dream-prune",
            "--items",
            str(items),
            "--verdicts",
            str(tmp_path / "absent.jsonl"),
        ]
    )
    assert rc == 2
    assert "verdicts" in capsys.readouterr().err
    assert calls(fake) == []
    assert shadow_logs(home) == []


@posix_only
def test_items_with_the_wrong_state_fields_are_refused_before_any_call(
    tmp_path, fake, home, capsys
):
    knob(home)
    items = write_jsonl(tmp_path / "items.jsonl", [{"id": "a", "state": {"hook": "h"}}])
    vpath = write_jsonl(tmp_path / "verdicts.jsonl", [])
    rc = js.main(
        [
            "run",
            "--site",
            "dream-prune",
            "--items",
            str(items),
            "--verdicts",
            str(vpath),
        ]
    )
    assert rc == 2
    assert "body" in capsys.readouterr().err
    assert calls(fake) == []


@posix_only
def test_a_verdict_of_the_wrong_type_is_refused_before_any_call(
    tmp_path, fake, home, capsys
):
    knob(home)
    rc = run_prune(
        tmp_path,
        fake,
        verdicts=[{"id": "slug-alpha", "verdict": {"untestable_negative": "yes"}}],
    )
    assert rc == 2
    assert "untestable_negative" in capsys.readouterr().err
    assert calls(fake) == []


# ---- run: the happy path ----------------------------------------------------------------------


@posix_only
def test_happy_path_logs_one_record_per_item_and_pairs_the_judged_ones(
    tmp_path, fake, home, capsys
):
    knob(home)
    rc = run_prune(tmp_path, fake)
    assert rc == 0, capsys.readouterr()
    logs = shadow_logs(home)
    assert len(logs) == 1
    assert re.fullmatch(r"jev-skill-shadow-\d{4}-\d{2}\.jsonl", logs[0].name)
    recs = {r["item_id"]: r for r in read_jsonl(logs[0])}
    assert set(recs) == {"slug-alpha", "slug-beta", "slug-gamma"}
    paired = [
        r for r in recs.values() if r["agent"] is not None and r["jev"] is not None
    ]
    assert len(paired) == 2
    # noul compared at 0.5: agent True vs 0.9 agrees, agent False vs 0.7 does not
    assert recs["slug-alpha"]["agree"] == {
        "untestable_negative": True,
        "unlabelled_unsolved": False,
    }
    # a question the agent left out is null, not a disagreement
    assert recs["slug-beta"]["agree"] == {
        "untestable_negative": False,
        "unlabelled_unsolved": None,
    }
    assert recs["slug-gamma"]["agent"] is None
    assert recs["slug-gamma"]["agree"] == {
        "untestable_negative": None,
        "unlabelled_unsolved": None,
    }
    assert recs["slug-alpha"]["agent_note"] == "claims a tool fails, no version"
    assert recs["slug-alpha"]["jev"]["untestable_negative"]["value"] == 0.9


@posix_only
def test_every_record_carries_the_documented_fields(tmp_path, fake, home):
    knob(home)
    assert run_prune(tmp_path, fake) == 0
    rec = read_jsonl(shadow_logs(home)[0])[0]
    expected = {
        "ts",
        "run_id",
        "site",
        "site_version",
        "questions_sha",
        "plugin_version",
        "jev_judge_version",
        "model",
        "cwd",
        "git_head",
        "item_id",
        "state",
        "redactions",
        "jev",
        "jev_reason",
        "agent",
        "agent_note",
        "agree",
        "latency_ms",
        "input_tokens",
        "cost_usd",
    }
    assert set(rec) == expected
    assert rec["site"] == "dream-prune"
    assert rec["jev_judge_version"] == "0.2.4"
    assert rec["model"] == "jev-1.13"
    assert rec["input_tokens"] == 100
    assert rec["cost_usd"] == pytest.approx(100 * 0.042 / 1e6)


@posix_only
def test_a_planted_token_never_reaches_the_log_or_jev(
    tmp_path, fake, home, monkeypatch
):
    knob(home)
    monkeypatch.setenv("FAKE_JEV_SEEN", str(fake["seen"]))
    assert run_prune(tmp_path, fake) == 0
    text = shadow_logs(home)[0].read_text(encoding="utf-8")
    assert TOKEN not in text
    alpha = next(
        r for r in read_jsonl(shadow_logs(home)[0]) if r["item_id"] == "slug-alpha"
    )
    assert alpha["redactions"] >= 1
    assert "[REDACTED]" in alpha["state"]["body"]
    assert TOKEN not in fake["seen"].read_text(encoding="utf-8")


@posix_only
def test_jev_is_asked_the_site_questions_as_a_plain_list(
    tmp_path, fake, home, monkeypatch
):
    """jev-judge --questions takes a JSON list; the site file is an object holding one."""
    knob(home)
    monkeypatch.setenv("FAKE_JEV_SEEN", str(fake["seen"]))
    assert run_prune(tmp_path, fake) == 0
    sent = json.loads(fake["seen"].read_text(encoding="utf-8"))
    site = json.loads((SITES_DIR / "dream-prune.json").read_text(encoding="utf-8"))
    assert sent["questions"] == site["questions"]


@posix_only
def test_a_failed_jev_row_is_still_logged_with_its_reason(tmp_path, fake, home):
    knob(home)
    rows = {k: v for k, v in PRUNE_ROWS.items() if k != "slug-beta"}
    assert run_prune(tmp_path, fake, rows=rows) == 0
    recs = {r["item_id"]: r for r in read_jsonl(shadow_logs(home)[0])}
    beta = recs["slug-beta"]
    assert beta["jev"] is None
    assert "canned failure" in beta["jev_reason"]
    assert beta["agent"] == {"untestable_negative": True}
    assert beta["agree"] == {"untestable_negative": None, "unlabelled_unsolved": None}


@posix_only
def test_run_prints_counts_but_never_an_item_id(tmp_path, fake, home, capsys):
    knob(home)
    assert run_prune(tmp_path, fake) == 0
    cap = capsys.readouterr()
    assert "3 items" in cap.out and "2 paired" in cap.out
    for item in PRUNE_ITEMS:
        assert item["id"] not in cap.out
        assert item["id"] not in cap.err


@posix_only
def test_run_json_envelope_carries_counts_only(tmp_path, fake, home, capsys):
    knob(home)
    assert run_prune(tmp_path, fake, extra=("--json",)) == 0
    env = json.loads(capsys.readouterr().out)
    assert set(env) == {"ok", "command", "data", "skipped"}
    assert env["ok"] is True and env["command"] == "run"
    assert env["data"]["items"] == 3 and env["data"]["paired"] == 2
    assert "slug-alpha" not in json.dumps(env)


@posix_only
@pytest.mark.parametrize(
    ("agent", "jev", "agree"),
    [
        ("whitespace_only", "whitespace_only", True),
        ("whitespace_only", "substantive_drift", False),
    ],
)
def test_a_choice_agrees_by_key(tmp_path, fake, home, agent, jev, agree):
    knob(home)
    state = {
        "heading": "## Build",
        "copies": "4 copies, 2 variants",
        "variants": "a | b",
    }
    fake["rows"].write_text(
        json.dumps(
            {
                "g1": {
                    "cause": {
                        "type": "choice",
                        "value": jev,
                        "probabilities": {jev: 0.9},
                        "confidence": 0.9,
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    items = write_jsonl(tmp_path / "items.jsonl", [{"id": "g1", "state": state}])
    vpath = write_jsonl(
        tmp_path / "verdicts.jsonl", [{"id": "g1", "verdict": {"cause": agent}}]
    )
    assert (
        js.main(
            [
                "run",
                "--site",
                "consolidate-cause",
                "--items",
                str(items),
                "--verdicts",
                str(vpath),
            ]
        )
        == 0
    )
    assert read_jsonl(shadow_logs(home)[0])[0]["agree"] == {"cause": agree}


@posix_only
@pytest.mark.parametrize(
    ("agent", "jev", "agree"), [(2, 1.6, True), (0, 1.4, False), (1, 1.4, True)]
)
def test_a_score_agrees_by_index(tmp_path, fake, home, agent, jev, agree):
    knob(home)
    state = {"hook": "h", "body": "b", "level_scope": "s"}
    answer = {
        "type": "score",
        "value": jev,
        "probabilities": {"0": 0.1, "1": 0.5, "2": 0.4},
        "confidence": 0.5,
    }
    fake["rows"].write_text(
        json.dumps({"s|.": {"fits_level": answer}}), encoding="utf-8"
    )
    items = write_jsonl(tmp_path / "items.jsonl", [{"id": "s|.", "state": state}])
    vpath = write_jsonl(
        tmp_path / "verdicts.jsonl", [{"id": "s|.", "verdict": {"fits_level": agent}}]
    )
    assert (
        js.main(
            [
                "run",
                "--site",
                "dream-placement",
                "--items",
                str(items),
                "--verdicts",
                str(vpath),
            ]
        )
        == 0
    )
    assert read_jsonl(shadow_logs(home)[0])[0]["agree"] == {"fits_level": agree}


# ---- retention ------------------------------------------------------------------------------


def _month_name(d):
    return f"jev-skill-shadow-{d.year:04d}-{d.month:02d}.jsonl"


@posix_only
def test_retention_drops_a_month_past_400_days_and_never_the_current_one(
    tmp_path, fake, home
):
    knob(home)
    today = datetime.now(UTC).date()
    d = audit(home)
    d.mkdir(parents=True)
    old = d / _month_name(
        today - timedelta(days=432)
    )  # its last day is >= 401 days ago
    kept = d / _month_name(
        today - timedelta(days=380)
    )  # its last day is < 400 days ago
    current = d / _month_name(today)
    for p in (old, kept, current):
        p.write_text('{"ts": "x"}\n', encoding="utf-8")
    assert run_prune(tmp_path, fake) == 0
    assert not old.exists()
    assert kept.exists()
    assert current.exists()


@posix_only
def test_retention_drops_oldest_past_the_size_cap_but_not_the_current_month(
    tmp_path, fake, home
):
    knob(home)
    today = datetime.now(UTC).date()
    d = audit(home)
    d.mkdir(parents=True)
    big = d / _month_name(today - timedelta(days=70))
    with open(big, "wb") as fh:  # sparse where the filesystem allows it
        fh.truncate(slog.LOG_MAX_BYTES + 1)
    newer = d / _month_name(today - timedelta(days=35))
    newer.write_text('{"ts": "x"}\n', encoding="utf-8")
    assert run_prune(tmp_path, fake) == 0
    assert not big.exists()
    assert newer.exists()
    assert (d / _month_name(today)).exists()


@posix_only
def test_the_current_month_survives_even_when_it_alone_is_over_the_cap(
    tmp_path, fake, home
):
    knob(home)
    today = datetime.now(UTC).date()
    d = audit(home)
    d.mkdir(parents=True)
    current = d / _month_name(today)
    with open(current, "wb") as fh:
        fh.truncate(slog.LOG_MAX_BYTES + 1)
    older = d / _month_name(today - timedelta(days=35))
    older.write_text('{"ts": "x"}\n', encoding="utf-8")
    assert run_prune(tmp_path, fake) == 0
    assert not older.exists()
    assert current.exists()


# ---- report ---------------------------------------------------------------------------------


def _rec(
    item, agent, jev_value, *, site="dream-prune", qid="untestable_negative", cost=0.001
):
    jev = (
        None
        if jev_value is None
        else {qid: {"value": jev_value, "probabilities": None, "confidence": None}}
    )
    agree = {
        qid: None if agent is None or jev is None else (agent == (jev_value >= 0.5))
    }
    return {
        "ts": "2026-10-01T10:00:00+00:00",
        "run_id": "r1",
        "site": site,
        "site_version": 1,
        "questions_sha": "x",
        "plugin_version": "7.38.0",
        "jev_judge_version": "0.2.4",
        "model": "jev-1.13",
        "cwd": "/w",
        "git_head": None,
        "item_id": item,
        "state": {"hook": "h-" + item, "body": "b"},
        "redactions": 0,
        "jev": jev,
        "jev_reason": None,
        "agent": None if agent is None else {qid: agent},
        "agent_note": None,
        "agree": agree,
        "latency_ms": 300,
        "input_tokens": 100,
        "cost_usd": cost,
    }


def _two_question_fixture(home):
    """q1 is constant at 0.9 (FLAT); q2 spreads (the control)."""
    d = audit(home)
    d.mkdir(parents=True, exist_ok=True)
    recs = []
    q2_values = [0.05, 0.3, 0.5, 0.75, 0.95, 0.1]
    q2_agent = [False, False, True, True, True, True]
    for i in range(6):
        r1 = _rec(f"i{i}", i < 5, 0.9)
        r2 = _rec(f"i{i}", q2_agent[i], q2_values[i], qid="unlabelled_unsolved")
        r1["jev"].update(r2["jev"])
        r1["agent"].update(r2["agent"])
        r1["agree"].update(r2["agree"])
        recs.append(r1)
    write_jsonl(d / "jev-skill-shadow-2026-10.jsonl", recs)
    return recs


def test_report_counts_agreement_band_and_flags_only_the_flat_question(home, capsys):
    _two_question_fixture(home)
    rc = js.main(["report", "--site", "dream-prune", "--json"])
    env = json.loads(capsys.readouterr().out)
    assert rc == 0 and env["ok"] is True and env["command"] == "report"
    q = env["data"]["sites"]["dream-prune"]["questions"]
    q1, q2 = q["untestable_negative"], q["unlabelled_unsolved"]
    assert q1["n"] == 6 and q1["paired"] == 6
    assert q1["agreement_pct"] == pytest.approx(500 / 6, abs=0.1)
    assert q1["flat"] is True
    assert q2["flat"] is False  # the control: a varied column never flags
    assert q2["band_pct"] == pytest.approx(50.0)  # 0.3, 0.5, 0.75 of six
    # i0 agrees (F/0.05), i1 agrees (F/0.3), i2 agrees (T/0.5), i3 (T/.75), i4 (T/.95), i5 no (T/.1)
    assert q2["agreement_pct"] == pytest.approx(500 / 6, abs=0.1)
    # outside the band: i0, i4, i5 -> 2 of 3 agree
    assert q2["agreement_outside_band_pct"] == pytest.approx(200 / 3, abs=0.1)
    assert q1["confusion"]["agent=true/jev=true"] == 5
    assert q1["confusion"]["agent=false/jev=true"] == 1
    assert env["data"]["sites"]["dream-prune"]["cost_usd"] == pytest.approx(0.006)


def test_report_writes_disagreements_with_their_state(home, tmp_path, capsys):
    _two_question_fixture(home)
    out = tmp_path / "dis.jsonl"
    assert js.main(["report", "--disagreements", str(out)]) == 0
    rows = read_jsonl(out)
    ids = sorted(r["item_id"] for r in rows)
    assert ids == ["i5"]  # i5 disagrees on both questions; one line
    assert rows[0]["state"]["hook"] == "h-i5"
    assert "dream-prune" in capsys.readouterr().out


def test_report_since_filters_records_by_date(home, capsys):
    _two_question_fixture(home)
    assert js.main(["report", "--since", "2026-10-02"]) == 1
    capsys.readouterr()
    assert js.main(["report", "--since", "not-a-date"]) == 2


def test_report_with_no_log_is_exit_1(home, capsys):
    assert js.main(["report"]) == 1


# ---- the site files -------------------------------------------------------------------------

SITE_FILES = sorted(SITES_DIR.glob("*.json"))
EXPECTED_SITES = {
    "guard-firing",
    "quality-polarity",
    "quality-param-hit",
    "dream-prune",
    "dream-firing",
    "crosstree-misplaced",
    "data-arch-dict",
    "dream-placement",
    "consolidate-cause",
    "collect-relevance",
}


def test_there_is_one_site_file_per_site():
    assert {p.stem for p in SITE_FILES} == EXPECTED_SITES


def test_every_site_is_either_built_here_or_agent_built_never_both():
    assert set(sites.BUILDERS) | sites.AGENT_BUILT == EXPECTED_SITES
    assert not set(sites.BUILDERS) & sites.AGENT_BUILT


@pytest.mark.parametrize("path", SITE_FILES, ids=lambda p: p.stem)
def test_a_site_file_is_well_formed(path):
    site = json.loads(path.read_text(encoding="utf-8"))
    assert set(site) == {"site", "version", "questions", "state_fields"}
    assert site["site"] == path.stem
    assert isinstance(site["version"], int)
    fields = site["state_fields"]
    assert fields and len(set(fields)) == len(fields)
    referenced = set()
    for q in site["questions"]:
        assert q["type"] in {"noul", "choice", "score"}
        if q["type"] == "choice":
            assert "none" in q["criteria"]
        referenced |= set(re.findall(r"`([^`]+)`", q["instructions"]))
    assert referenced == set(fields), (
        "every backticked name must be a state field and vice versa"
    )


def test_the_floor_constant_matches_the_jev_judge_skill():
    floors = set(
        re.findall(
            r"btx-skill-jev-judge>=([0-9][0-9.]*[0-9])",
            JEV_SKILL.read_text(encoding="utf-8"),
        )
    )
    assert floors == {js.JEV_JUDGE_FLOOR}


# ---- items: the builders --------------------------------------------------------------------


def _fields(site):
    return set(
        json.loads((SITES_DIR / (f"{site}.json")).read_text(encoding="utf-8"))[
            "state_fields"
        ]
    )


@pytest.fixture
def store(tmp_path):
    """One tree: top (anchor) and top/proj, a fact at each, and a second tree for misplacement."""
    work = tmp_path / "work"
    trees = {}
    for name in ("alpha", "beta"):
        top = work / name
        proj = top / "proj"
        proj.mkdir(parents=True)
        (top / "CLAUDE.md").write_text(f"{name} top\n", encoding="utf-8")
        (proj / "CLAUDE.md").write_text(f"{name} proj\n", encoding="utf-8")
        (top / ".claude-memory").mkdir()
        trees[name] = (top, proj)
    top, proj = trees["alpha"]
    ME.add_or_update_entry(
        str(top),
        "Top rule",
        "When anything, do the top thing.",
        body="The top body.",
        scope_default="WHAT: the alpha tree",
    )
    ME.add_or_update_entry(
        str(proj),
        "Proj rule",
        "When building proj, run make.",
        body="The proj body.",
        scope_default="WHAT: the proj",
    )
    ME.add_or_update_entry(
        str(proj),
        "Beta deploy",
        "When deploying beta, drain first.",
        body="Edit {}/service.py then restart.".format(trees["beta"][1]),
    )
    return {"anchor": top, "proj": proj}


def test_items_dream_prune_yields_one_item_per_fact_with_hook_and_body(
    store, tmp_path, home, capsys
):
    out = tmp_path / "items.jsonl"
    assert (
        js.main(
            [
                "items",
                "--site",
                "dream-prune",
                "--anchor",
                str(store["anchor"]),
                "--out",
                str(out),
            ]
        )
        == 0
    )
    items = {i["id"]: i["state"] for i in read_jsonl(out)}
    assert set(items) == {"top-rule", "proj-rule", "beta-deploy"}
    assert items["proj-rule"] == {
        "hook": "When building proj, run make.",
        "body": "The proj body.",
    }


def test_items_dream_placement_pairs_each_fact_with_its_levels(store, tmp_path, home):
    out = tmp_path / "items.jsonl"
    assert (
        js.main(
            [
                "items",
                "--site",
                "dream-placement",
                "--anchor",
                str(store["anchor"]),
                "--out",
                str(out),
            ]
        )
        == 0
    )
    ids = {i["id"] for i in read_jsonl(out)}
    assert {"proj-rule|.", "proj-rule|proj", "top-rule|.", "top-rule|proj"} <= ids


def test_items_crosstree_misplaced_yields_only_the_candidate(store, tmp_path, home):
    out = tmp_path / "items.jsonl"
    assert (
        js.main(
            [
                "items",
                "--site",
                "crosstree-misplaced",
                "--anchor",
                str(store["anchor"]),
                "--out",
                str(out),
            ]
        )
        == 0
    )
    assert [i["id"] for i in read_jsonl(out)] == ["beta-deploy"]


def test_items_guard_firing_reads_the_firings_file(tmp_path, home):
    firings = write_jsonl(
        tmp_path / "firings.jsonl",
        [
            {
                "id": "toolu_1",
                "transcript": "/t.jsonl",
                "cwd": "/w",
                "command": "git status",
                "error": None,
            },
            {
                "id": "toolu_2",
                "transcript": "/t.jsonl",
                "cwd": "/w",
                "command": "rm -rf x",
                "error": "boom",
            },
        ],
    )
    out = tmp_path / "items.jsonl"
    assert (
        js.main(
            [
                "items",
                "--site",
                "guard-firing",
                "--firings",
                str(firings),
                "--hazard",
                "deletes the wrong dir",
                "--out",
                str(out),
            ]
        )
        == 0
    )
    items = read_jsonl(out)
    assert [i["id"] for i in items] == ["toolu_1", "toolu_2"]
    assert items[1]["state"] == {
        "hazard": "deletes the wrong dir",
        "command": "rm -rf x",
        "error": "boom",
    }


@pytest.mark.parametrize(
    "site",
    [
        "dream-prune",
        "dream-firing",
        "dream-placement",
        "crosstree-misplaced",
        "guard-firing",
    ],
)
def test_each_builder_emits_exactly_its_site_state_fields(site, store, tmp_path, home):
    out = tmp_path / "items.jsonl"
    if site == "guard-firing":
        firings = write_jsonl(
            tmp_path / "f.jsonl",
            [{"id": "t", "transcript": "x", "cwd": "/", "command": "c", "error": None}],
        )
        argv = ["--firings", str(firings), "--hazard", "h"]
    else:
        argv = ["--anchor", str(store["anchor"])]
    assert js.main(["items", "--site", site, *argv, "--out", str(out)]) == 0
    items = read_jsonl(out)
    assert items
    for item in items:
        assert set(item["state"]) == _fields(site)


@pytest.mark.parametrize(
    "site",
    [
        "quality-polarity",
        "quality-param-hit",
        "data-arch-dict",
        "consolidate-cause",
        "collect-relevance",
    ],
)
def test_an_agent_built_site_has_no_builder_and_says_which_fields_to_write(
    site, tmp_path, home, capsys
):
    rc = js.main(["items", "--site", site, "--out", str(tmp_path / "i.jsonl")])
    assert rc == 2
    err = capsys.readouterr().err
    for name in _fields(site):
        assert name in err


def test_an_unknown_site_is_a_usage_error(tmp_path, home, capsys):
    assert js.main(["items", "--site", "nope", "--out", str(tmp_path / "i.jsonl")]) == 2


# ---- status ---------------------------------------------------------------------------------


@posix_only
def test_status_says_whether_a_run_would_happen(fake, home, capsys):
    assert js.main(["status", "--json"]) == 1
    env = json.loads(capsys.readouterr().out)
    assert env["data"]["would_run"] is False
    knob(home)
    assert js.main(["status", "--json"]) == 0
    env = json.loads(capsys.readouterr().out)
    assert env["data"]["would_run"] is True and env["data"]["key"] is True
