"""End-to-end tests for memory recall in DECIDE mode (`classifier_recall_rerank = decide`).

The hook runs in-process as Claude Code drives it (event JSON on stdin, the injection on stdout),
with a real config file, a real API key env var and the loopback base-URL override pointing at a
local fake TypeSafe server. The fake scores each note from a `score=<x>` tag in its description,
so every test states exactly what Jev said about which note. Nothing inside the hook is patched;
`subprocess.Popen` is recorded (and still run) at the process edge to see whether a shadow child
was started.

What decide mode promises (a blind panel on 2026-10-06 found the keyword top 4 6% relevant):

* only the shortlisted notes Jev scores at or above the site threshold are injected, best first,
  whatever the keyword ranking thought of them;
* Jev scoring every note below the threshold injects nothing;
* Jev not answering injects nothing - the keyword ranking is not a fallback;
* every shortlisted note is asked at once, so 30 requests fit the hook's deadline;
* no shadow child is started, and one row per prompt lands in the log naming the path.
"""

import io
import json
import re
import subprocess
import sys

import pytest

import classifier as cl
import recall_memory as R
import self_improve_signals as sig

PROMPT = "how do I tune the zebrafish widget throttle"
_SCORE = re.compile(r"score=([0-9.]+)")


def _scored(request):
    """The fake's answer: the `score=` tag of the note it was asked about, 0.0 without one."""
    note = (request.get("state") or {}).get("memory_note") or ""
    m = _SCORE.search(note)
    value = float(m.group(1)) if m else 0.0
    return {"model": "jev-test", "usage": {"input_tokens": 10},
            "answers": {qid: {"type": "noul", "noul": value} for qid in request["questions"]}}


@pytest.fixture
def env(tmp_path, monkeypatch, fake_jev):
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.setenv("TYPESAFE_API_KEY", "k" * 20)
    (home / ".claude" / ".bitranox-memory.json").write_text(json.dumps(
        {"classifier_backend": "jev", "classifier_recall_rerank": "decide"}), encoding="utf-8")
    return {"home": home, "monkeypatch": monkeypatch, "fake_jev": fake_jev}


def _serve(env, **kw):
    fake = env["fake_jev"](answer_fn=kw.pop("answer_fn", _scored), **kw)
    env["monkeypatch"].setenv(cl.BASE_URL_ENV, fake.url)
    return fake


def _note(name, score):
    d = sig.memory_dir("/p/other")
    d.mkdir(parents=True, exist_ok=True)
    (d / (name + ".md")).write_text(
        "---\nname: %s\ndescription: zebrafish widget throttle tuning, score=%s\n---\n"
        "Body of %s about the zebrafish widget throttle.\n" % (name, score, name),
        encoding="utf-8")


def _run(monkeypatch, capsys, sid="t1"):
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(
        {"prompt": PROMPT, "cwd": "/p/cur", "session_id": sid})))
    rc = R.main()
    return rc, capsys.readouterr().out


def _rows(env):
    rows = []
    for path in cl.shadow_log_files(env["home"] / ".claude" / "self-improve-audit"):
        rows += [json.loads(line) for line in path.read_text("utf-8").splitlines() if line]
    return [r for r in rows if r.get("site") == "recall_rerank"]


def test_injects_only_notes_scored_at_or_above_the_threshold_best_first(env, monkeypatch, capsys):
    _serve(env)
    for name, score in (("note-high", "0.85"), ("note-edge", "0.80"), ("note-under", "0.79"),
                        ("note-low", "0.10")):
        _note(name, score)
    rc, out = _run(monkeypatch, capsys)
    assert rc == 0
    ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"]
    assert "### note-high" in ctx and "### note-edge" in ctx
    assert "note-under" not in ctx and "note-low" not in ctx
    assert ctx.index("### note-high") < ctx.index("### note-edge")


def test_injects_nothing_when_jev_scores_every_note_low(env, monkeypatch, capsys):
    _serve(env)
    _note("note-a", "0.30")
    _note("note-b", "0.79")
    rc, out = _run(monkeypatch, capsys)
    assert rc == 0 and out.strip() == ""
    (row,) = _rows(env)
    assert row["mode"] == "decide" and row["decide_path"] == "none" and row["picks"] == []


def test_injects_nothing_when_jev_does_not_answer(env, monkeypatch, capsys):
    _serve(env, status=500, answer_fn=None)
    _note("note-a", "0.95")
    rc, out = _run(monkeypatch, capsys)
    assert rc == 0 and out.strip() == ""
    (row,) = _rows(env)
    assert row["decide_path"].startswith("fallback-")


def test_logs_one_decide_row_naming_the_picks(env, monkeypatch, capsys):
    _serve(env)
    _note("note-high", "0.9")
    _note("note-low", "0.2")
    _run(monkeypatch, capsys)
    (row,) = _rows(env)
    assert row["mode"] == "decide" and row["decide_path"] == "jev"
    assert [p.rsplit("/", 1)[-1] for p in row["picks"]] == ["note-high.md"]
    assert len(row["results"]) == len(row["regex"]["shortlist"]) == 2


def test_asks_every_shortlisted_note_at_once(env, monkeypatch, capsys):
    fake = _serve(env, delay=0.2)
    for i in range(12):
        _note("note-%02d" % i, "0.5")
    _run(monkeypatch, capsys)
    assert len(fake.requests) == 12
    assert fake.max_in_flight == 12


def test_starts_no_shadow_child(env, monkeypatch, capsys):
    _serve(env)
    _note("note-high", "0.9")
    calls, real = [], subprocess.Popen

    def recording(args, *a, **kw):
        calls.append([str(x) for x in args])
        return real(args, *a, **kw)

    monkeypatch.setattr(subprocess, "Popen", recording)
    _run(monkeypatch, capsys)
    assert not [c for c in calls if "--shadow" in c]
