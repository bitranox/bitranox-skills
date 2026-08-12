"""Tests for overwatch_ledger - the action ledger the overwatcher classifies.

Every fixture here is SYNTHETIC or uses RFC-reserved names (example.com, 192.0.2.0/24). No content
from a real transcript is stored in this repo.
"""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

HOOKS = Path(__file__).resolve().parents[1]
if str(HOOKS) not in sys.path:
    sys.path.insert(0, str(HOOKS))

spec = importlib.util.spec_from_file_location("overwatch_ledger", HOOKS / "overwatch_ledger.py")
assert spec and spec.loader
ol = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ol)


# --------------------------------------------------------------- target normalisation


def test_write_target_is_the_basename():
    assert ol.normalise_target("Write", {"file_path": "/srv/app/deploy.py"}) == "deploy.py"


def test_heredoc_script_write_is_the_target_not_the_shell():
    command = "cd /tmp/work && cat > purge.ps1 <<'EOS'\nWrite-Host hi\nEOS"
    assert ol.normalise_target("Bash", {"command": command}) == "purge.ps1"


def test_guest_id_beats_the_hostname():
    command = "ssh root@node.example.com 'qm rollback 4242 presnap'"
    assert ol.normalise_target("Bash", {"command": command}) == "vm:4242"


def test_ssh_key_path_does_not_shadow_the_real_host():
    """The fleet key is literally named `root@shared_nopass.key`, so the FIRST user@thing on an
    ssh line is a filename. Taking only the first match dropped the host from every fleet call."""
    command = "ssh -i /root/.ssh/root@shared_nopass.key admin@node.example.com 'uptime'"
    assert ol.normalise_target("Bash", {"command": command}) == "host:node.example.com"


def test_leading_cd_chain_is_stripped():
    """Without this every `cd /scratch && ...` call reports the target `cd`."""
    command = "cd /tmp/scratch && cd deeper && git commit -m x"
    assert ol.normalise_target("Bash", {"command": command}) == "git:commit"


def test_leading_cd_on_its_own_line_is_also_stripped():
    """A multi-line command opens `cd /path` then newline, with no `&&` to match."""
    assert ol.normalise_target("Bash", {"command": "cd /tmp/scratch\npytest -q"}) == "pytest"


def test_plain_command_falls_back_to_its_first_word():
    assert ol.normalise_target("Bash", {"command": "pytest -q tests/"}) == "pytest"


def test_agent_target_names_the_subagent_type():
    assert ol.normalise_target("Agent", {"subagent_type": "explorer"}) == "agent:explorer"


# --------------------------------------------------------------- recovery markers


@pytest.mark.parametrize(
    "command",
    [
        "ssh root@node.example.com 'qm rollback 4242 presnap'",
        "pct rollback 105 before",
        "zfs rollback tank/data@yesterday",
        "git reset --hard HEAD~1",
        "git revert abc1234",
        "git stash pop",
    ],
)
def test_undo_commands_are_recovery(command):
    assert ol.recovery_marker("Bash", {"command": command}) is True


@pytest.mark.parametrize(
    "command",
    [
        "qm snapshot 4242 presnap",           # TAKING a snapshot is not recovery
        "git restore --staged file.py",        # unstaging is not undoing work
        "git stash",                           # stashing is not popping
        "ls -la /var/log",
    ],
)
def test_non_undo_commands_are_not_recovery(command):
    assert ol.recovery_marker("Bash", {"command": command}) is False


def test_a_search_for_the_word_rollback_is_not_a_rollback():
    """A command-scanning marker must strip DATA regions or it fires on its own investigation."""
    assert ol.recovery_marker("Bash", {"command": "grep -c 'qm rollback' session.jsonl"}) is False
    assert ol.recovery_marker("Bash", {"command": "echo 'git reset --hard is risky'"}) is False


def test_a_rollback_named_inside_a_heredoc_body_is_not_a_rollback():
    """An embedded analysis program that COUNTS rollbacks performs none; this self-matched on a
    real session until heredoc bodies were stripped."""
    command = (
        "python3 - <<'PY'\n"
        "import re\n"
        "for m in re.finditer(r'qm rollback (\\d+)', text): print(m)\n"
        "PY"
    )
    assert ol.recovery_marker("Bash", {"command": command}) is False


def test_a_real_rollback_outside_a_heredoc_still_counts():
    """Control for the strip: it must not swallow the genuine case that shares the command."""
    command = "qm rollback 4242 presnap\npython3 - <<'PY'\nprint(1)\nPY"
    assert ol.recovery_marker("Bash", {"command": command}) is True


def test_non_bash_tools_are_never_recovery():
    assert ol.recovery_marker("Write", {"file_path": "/x/qm rollback.txt"}) is False


# --------------------------------------------------------------- outcomes


def test_is_error_flag_is_an_error():
    assert ol.outcome_of({"is_error": True, "content": "boom"}) == "err"


def test_non_zero_exit_preamble_is_an_error_even_without_the_flag():
    """A Bash non-zero exit arrives as text with the harness flag unset; counting only the flag
    under-reports failures several-fold."""
    assert ol.outcome_of({"content": "Exit code 1\nTraceback..."}) == "err"


def test_exit_code_zero_is_not_an_error():
    assert ol.outcome_of({"content": "Exit code 0"}) == "ok"


def test_tool_use_error_wrapper_is_an_error():
    assert ol.outcome_of({"content": "<tool_use_error>Blocked: ...</tool_use_error>"}) == "err"


def test_plain_output_is_ok():
    assert ol.outcome_of({"content": "total 12\ndrwx..."}) == "ok"


def test_missing_result_is_ok_not_a_crash():
    assert ol.outcome_of({}) == "ok"
    assert ol.outcome_of(None) == "ok"


# --------------------------------------------------------------- rendering


def test_ledger_line_is_one_line_and_marks_recovery():
    record = ol.LedgerRecord(7, "Bash", "vm:4242", "roll back the guest", "ok", recovery=True)
    line = ol.ledger_line(record)
    assert "\n" not in line
    assert line == "7|Bash|vm:4242|roll back the guest|ok RECOVERY"


def test_ledger_line_without_recovery_has_no_marker():
    record = ol.LedgerRecord(2, "Read", "a.py", "read a.py", "ok")
    assert ol.ledger_line(record) == "2|Read|a.py|read a.py|ok"


def test_render_window_takes_the_tail_and_is_inclusive():
    ledger = [ol.LedgerRecord(i, "Bash", f"t{i}", f"i{i}", "ok") for i in range(1, 11)]
    text = ol.render_window(ledger, end=10, size=3)
    assert text.splitlines() == ["8|Bash|t8|i8|ok", "9|Bash|t9|i9|ok", "10|Bash|t10|i10|ok"]


def test_render_window_appends_the_pending_action_last():
    """The PreToolUse shape: the action about to run is what the verdict is about."""
    ledger = [ol.LedgerRecord(i, "Bash", f"t{i}", f"i{i}", "ok") for i in range(1, 4)]
    pending = ol.LedgerRecord(4, "Bash", "vm:9", "delete it again", "ok")
    lines = ol.render_window(ledger, end=3, size=2, pending=pending).splitlines()
    assert lines[-1] == "PENDING|Bash|vm:9|delete it again|(not yet run)"
    assert len(lines) == 3


def test_render_window_without_pending_is_unchanged():
    ledger = [ol.LedgerRecord(1, "Bash", "t", "i", "ok")]
    assert ol.render_window(ledger, end=1, size=5) == "1|Bash|t|i|ok"


def test_prompt_explains_the_pending_line():
    assert "PENDING" in ol.build_prompt("x")


def test_render_window_clamps_at_the_start():
    ledger = [ol.LedgerRecord(i, "Bash", f"t{i}", f"i{i}", "ok") for i in range(1, 4)]
    assert len(ol.render_window(ledger, end=2, size=50).splitlines()) == 2


# --------------------------------------------------------------- transcript walk


def _transcript(tmp_path, entries):
    path = tmp_path / "t.jsonl"
    path.write_text("\n".join(json.dumps(e) for e in entries), encoding="utf-8")
    return path


def _use(uid, name, tool_input):
    return {
        "type": "assistant",
        "message": {"content": [{"type": "tool_use", "id": uid, "name": name, "input": tool_input}]},
    }


def _result(uid, content, is_error=False):
    block = {"type": "tool_result", "tool_use_id": uid, "content": content}
    if is_error:
        block["is_error"] = True
    return {"type": "user", "message": {"content": [block]}}


def test_build_ledger_pairs_calls_with_their_results(tmp_path):
    path = _transcript(
        tmp_path,
        [
            _use("a", "Bash", {"command": "pytest -q", "description": "run the suite"}),
            _result("a", "Exit code 1\nFAILED"),
            _use("b", "Write", {"file_path": "/x/fix.py"}),
            _result("b", "ok"),
        ],
    )
    ledger = ol.build_ledger(path)
    assert [(r.index, r.target, r.intent, r.outcome) for r in ledger] == [
        (1, "pytest", "run the suite", "err"),
        (2, "fix.py", "write fix.py", "ok"),
    ]


def test_build_ledger_skips_subagent_sidechain_events(tmp_path):
    """A dispatched subagent's own calls are not the main session's actions; folding them in makes
    one dispatch look like a repetition burst."""
    main = _use("a", "Bash", {"command": "ls", "description": "list"})
    side = _use("b", "Bash", {"command": "ls", "description": "list"})
    side["isSidechain"] = True
    ledger = ol.build_ledger(_transcript(tmp_path, [main, side]))
    assert len(ledger) == 1


def test_build_ledger_survives_a_corrupt_line(tmp_path):
    path = tmp_path / "t.jsonl"
    path.write_text(
        "{not json\n" + json.dumps(_use("a", "Bash", {"command": "ls", "description": "d"})),
        encoding="utf-8",
    )
    assert len(ol.build_ledger(path)) == 1


def test_build_ledger_is_empty_for_an_empty_transcript(tmp_path):
    assert ol.build_ledger(_transcript(tmp_path, [])) == []


# --------------------------------------------------------------- verdict contract


def test_prompt_embeds_the_window_and_names_every_verdict():
    prompt = ol.build_prompt("1|Bash|x|y|ok")
    assert "1|Bash|x|y|ok" in prompt
    for verdict in ol.VERDICTS:
        assert verdict in prompt


def test_parse_verdict_reads_a_clean_reply():
    got = ol.parse_verdict('{"verdict":"repeating_failure","evidence":[1,2],"reason":"r","action":"a"}')
    assert got["verdict"] == "repeating_failure"
    assert got["evidence"] == [1, 2]
    assert got["action"] == "a"


def test_parse_verdict_tolerates_surrounding_prose_and_a_fence():
    reply = 'Here is my answer:\n```json\n{"verdict":"repeating_job","evidence":[]}\n```\nThanks!'
    assert ol.parse_verdict(reply)["verdict"] == "repeating_job"


@pytest.mark.parametrize("reply", ["", "no json here", "{broken", '{"verdict":"banana"}', "[]"])
def test_unparseable_or_unknown_verdicts_fall_back_to_none(reply):
    """An overwatcher that cannot read its classifier must stay SILENT, never invent a stop."""
    assert ol.parse_verdict(reply)["verdict"] == "none"


def test_evidence_is_capped_and_type_filtered():
    got = ol.parse_verdict('{"verdict":"none","evidence":[1,2,3,4,5,6,{"a":1}]}')
    assert got["evidence"] == [1, 2, 3, 4]


def test_stop_verdicts_are_a_strict_subset_of_verdicts():
    assert set(ol.STOP_VERDICTS) < set(ol.VERDICTS)
    assert "repeating_job" not in ol.STOP_VERDICTS
