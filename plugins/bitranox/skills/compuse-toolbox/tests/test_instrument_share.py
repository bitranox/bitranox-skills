"""Tests for instrument_share: classify tool calls, charge them time, attribute episodes.

The record shapes are the real corpus's: a Stop-hook block lands as a `user` record with
`isMeta: true` whose text starts "Stop hook feedback:", a typed prompt is a non-meta `user` text
record, and a tool call is a `tool_use` block inside an `assistant` record.
"""
import json
import subprocess
import sys
import tracemalloc
from datetime import date, datetime, timedelta, UTC
from pathlib import Path

import pytest

import instrument_share as ish

TOOL = Path(__file__).resolve().parents[1] / "scripts" / "instrument_share.py"
T0 = datetime(2026, 9, 30, 10, 0, tzinfo=UTC)          # ISO week 2026-W40


def _ts(minutes):
    return (T0 + timedelta(minutes=minutes)).isoformat().replace("+00:00", "Z")


def prompt(m, text="do the work", **over):
    rec = {"type": "user", "timestamp": _ts(m), "cwd": "/work/app", "entrypoint": "cli",
           "message": {"role": "user", "content": text}}
    rec.update(over)
    return rec


def stop_block(m, text):
    return {"type": "user", "isMeta": True, "timestamp": _ts(m), "cwd": "/work/app",
            "message": {"role": "user", "content": [{"type": "text",
                                                     "text": "Stop hook feedback:\n" + text}]}}


def call(m, name, tool_input, call_id, **over):
    rec = {"type": "assistant", "timestamp": _ts(m), "cwd": "/work/app",
           "message": {"role": "assistant", "content": [
               {"type": "tool_use", "id": call_id, "name": name, "input": tool_input}]}}
    rec.update(over)
    return rec


def write_session(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8",
                    newline="")
    return path


SESSION = [
    prompt(0),
    call(1, "Bash", {"command": "make build"}, "c1"),                              # work 1
    stop_block(2, "This session is carrying 404,715 tokens of context, past the 400,000."),
    call(3, "Skill", {"skill": "bitranox:meta-context-watcher"}, "c2"),            # handover 1
    call(4, "Write", {"file_path": "/work/app/handover.md", "content": "x"}, "c3"),  # handover 2
    call(6, "Bash", {"command": "pytest -q"}, "c4"),                                # work 1
    prompt(7, "now fix the hook"),
    call(8, "Edit", {"file_path": "/src/plugins/bitranox/hooks/x.py", "old_string": "a",
                     "new_string": "b"}, "c5"),                                      # detour 1
    call(9, "Bash", {"command": "uv run /p/skills/compuse-toolbox/scripts/gate.py --gate x"},
         "c6"),                                                                      # work 0
]


@pytest.fixture
def corpus(tmp_path):
    root = tmp_path / "projects"
    write_session(root / "-work-app" / "s1.jsonl", SESSION)
    return root


# ---- classification ---------------------------------------------------------------------------

@pytest.mark.parametrize("tool,tool_input,expected", [
    ("Bash", {"command": "pytest -q"}, "work"),
    ("Skill", {"skill": "bitranox:meta-context-watcher"}, "handover"),
    ("Skill", {"skill": "bitranox:meta-self-improve"}, "memory"),
    ("Skill", {"skill": "bitranox:meta-skill-writer"}, "skills-detour"),
    ("Skill", {"skill": "bitranox:coding-python-uv"}, "work"),
    ("Read", {"file_path": "/repo/OPEN-WORK.md"}, "handover"),
    ("Bash", {"command": "bash h/run-python.sh h/memory_engine.py add --slug x"}, "memory"),
    ("Edit", {"file_path": "/x/plugins/bitranox/hooks/a.py"}, "skills-detour"),
    # Running a shipped jig is USING the tooling: without the explicit work row every toolbox
    # call read as a detour into it.
    ("Bash", {"command": "uv run ~/.claude/plugins/m/skills/compuse-toolbox/scripts/newest.py ."},
     "work"),
    ("Bash", {"command": "python3 ~/.claude/skills/toolbox/tools/guestip.py vm1"}, "work"),
    # Reading a skill to use it is not editing the plugin.
    ("Read", {"file_path": "/home/u/.claude/plugins/cache/b/skills/x/SKILL.md"}, "work"),
])
def test_classify(tool, tool_input, expected):
    assert ish.classify(tool, tool_input) == expected


def test_a_stop_signature_folds_counts_and_shas_so_one_hook_is_one_trigger():
    a = ish.stop_signature("Stop hook feedback:\nThis session is carrying 404,715 tokens of x")
    b = ish.stop_signature("Stop hook feedback:\nThis session is carrying 512,000 tokens of y")
    assert a == b == "stop:this session is carrying # tokens"
    c = ish.stop_signature("You pushed 3f2a9c1d on main and")
    d = ish.stop_signature("You pushed e0aa7b21c on main and")
    assert c == d


# ---- measurement -----------------------------------------------------------------------------

def test_each_call_is_charged_until_the_next_event_and_episodes_go_to_their_trigger(corpus):
    report, skipped, read = ish.measure(corpus, exclude_cwd=None)
    assert skipped == [] and read == 1
    assert dict(report.total.minutes) == {"work": 2.0, "handover": 3.0, "skills-detour": 1.0}
    stop = report.triggers["stop:this session is carrying # tokens"]
    assert dict(stop.minutes) == {"handover": 3.0} and stop.episodes == 1
    assert dict(report.triggers["prompt"].minutes) == {"skills-detour": 1.0}
    assert report.total.as_dict()["instrumentation_share_pct"] == pytest.approx(66.7)
    assert list(report.weeks) == ["2026-W40"]


def test_a_skill_call_that_opens_an_episode_leaves_the_blame_with_the_stop_hook(corpus):
    report, _, _ = ish.measure(corpus, exclude_cwd=None)
    assert "skill:bitranox:meta-context-watcher" not in report.triggers
    assert report.triggers["stop:this session is carrying # tokens"].episodes == 1


def test_an_idle_gap_is_capped(tmp_path):
    root = tmp_path / "p"
    write_session(root / "a" / "s.jsonl", [
        prompt(0), call(1, "Bash", {"command": "ls"}, "c1"), prompt(300, "back from lunch")])
    report, _, _ = ish.measure(root, max_gap=5.0, exclude_cwd=None)
    assert report.total.minutes["work"] == 5.0


def test_a_call_copied_into_a_resumed_transcript_is_counted_once(corpus):
    write_session(corpus / "-work-app" / "s2-resumed.jsonl", SESSION)
    report, _, read = ish.measure(corpus, exclude_cwd=None)
    assert read == 2
    assert report.calls == 6 and report.duplicates_skipped == 6


def test_a_session_in_an_excluded_directory_is_skipped_and_counted(corpus):
    write_session(corpus / "-plugin" / "s.jsonl",
                  [prompt(0, cwd="/src/bitranox-skills"),
                   call(1, "Bash", {"command": "ls"}, "z1", cwd="/src/bitranox-skills")])
    report, _, _ = ish.measure(corpus)
    assert report.sessions == 1 and report.sessions_excluded == 1


def test_sidechain_records_and_subagent_transcripts_are_not_counted(corpus):
    write_session(corpus / "-work-app" / "s1" / "subagents" / "agent-1.jsonl",
                  [call(1, "Bash", {"command": "ls"}, "sub1")])
    write_session(corpus / "-other" / "s.jsonl",
                  [prompt(0), call(1, "Bash", {"command": "ls"}, "side", isSidechain=True)])
    report, _, read = ish.measure(corpus, exclude_cwd=None)
    assert read == 2 and report.calls == 6


def test_the_window_counts_only_calls_inside_it(corpus):
    report, _, _ = ish.measure(corpus, since=date(2026, 10, 1), exclude_cwd=None)
    assert report.calls == 0


# ---- the CLI ----------------------------------------------------------------------------------

def _cli(*args):
    proc = subprocess.run([sys.executable, str(TOOL), *map(str, args)], capture_output=True,
                          text=True, encoding="utf-8", errors="replace", timeout=120)
    return proc.returncode, proc.stdout, proc.stderr


def test_json_prints_the_envelope_with_the_tables(corpus):
    rc, out, _ = _cli("--root", corpus, "--exclude-cwd", "", "--json")
    env = json.loads(out)
    assert rc == 0 and env["ok"] is True and env["command"] == "instrument_share"
    assert env["data"]["total"]["instrumentation_minutes"] == 4.0
    assert "2026-W40" in env["data"]["weeks"]


def test_a_range_with_no_call_is_exit_1(corpus):
    rc, out, _ = _cli("--root", corpus, "--since", "2027-01-01", "--json")
    assert rc == 1 and json.loads(out)["ok"] is True


@pytest.mark.parametrize("args,needle", [
    (["--since", "yesterday"], "not a YYYY-MM-DD"),
    (["--max-gap", "0"], "--max-gap"),
    (["--exclude-cwd", "("], ""),
])
def test_a_bad_option_is_exit_2_with_the_envelope(corpus, args, needle):
    rc, out, _ = _cli("--root", corpus, *args, "--json")
    env = json.loads(out)
    assert rc == 2 and env["ok"] is False and needle in env["error"]


def test_a_missing_root_is_exit_2(tmp_path):
    rc, out, _ = _cli("--root", tmp_path / "nope", "--json")
    assert rc == 2 and json.loads(out)["ok"] is False


# --- memory: a transcript is streamed line by line, never decoded whole ----------------------------


def _bulky_session(path, filler_lines):
    """Two calls with `filler_lines` assistant text records of about 1 KB between them."""
    filler = json.dumps({"type": "assistant", "timestamp": _ts(1), "cwd": "/work/app",
                         "message": {"content": [{"type": "text", "text": "x" * 1000}]}})
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(json.dumps(call(0, "Bash", {"command": "make"}, "c1")) + "\n")
        for _ in range(filler_lines):
            fh.write(filler + "\n")
        fh.write(json.dumps(call(2, "Bash", {"command": "make"}, "c2")) + "\n")


def _peak_bytes(fn):
    tracemalloc.start()
    try:
        fn()
        return tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()


def test_measure_peak_memory_does_not_grow_with_the_transcript(tmp_path):
    # Reading the whole file held its bytes, the decoded text and every line at once: 1.2 GB RSS
    # to tally a 217 MB transcript. Events are kept; the bulk around them must not be.
    small, large = tmp_path / "small.jsonl", tmp_path / "large.jsonl"
    _bulky_session(small, 500)
    _bulky_session(large, 4000)
    peak_small = _peak_bytes(lambda: ish.measure(small, exclude_cwd=None))
    peak_large = _peak_bytes(lambda: ish.measure(large, exclude_cwd=None))
    assert ish.measure(large, exclude_cwd=None)[0].calls == 2
    assert peak_large < 2 * peak_small, (peak_small, peak_large)


def test_measure_reads_a_bom_and_a_crlf_line_as_records(tmp_path):
    path = tmp_path / "s.jsonl"
    path.write_bytes(b"\xef\xbb\xbf" + json.dumps(call(0, "Bash", {"command": "a"}, "c1")).encode()
                     + b"\r\n" + json.dumps(call(1, "Bash", {"command": "b"}, "c2")).encode()
                     + b"\n")
    assert ish.measure(path, exclude_cwd=None)[0].calls == 2


def test_an_event_with_a_kind_outside_the_vocabulary_is_refused():
    # A misspelt kind is neither a call nor a trigger, so _charge_session would skip it silently.
    with pytest.raises(ValueError):
        ish.Event(T0, "cal")


def test_an_event_kind_is_parsed_into_the_enum_and_keeps_its_string():
    ev = ish.Event(T0, "trigger", "session-start")
    assert type(ev.kind) is ish.EventKind and ev.kind == "trigger" and str(ev.kind) == "trigger"
    assert {k.value for k in ish.EventKind} == {"call", "prompt", "trigger"}
