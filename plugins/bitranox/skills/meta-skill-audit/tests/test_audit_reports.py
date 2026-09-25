"""Tests for how audit_skills.py stages its room and records what a reviewer returned. ASCII only.

Every reviewer here is injected at the `runner` seam; nothing spawns `claude`."""

import json

import pytest

import audit_skills as A


def _plugin(tmp_path, skills=("alpha",)):
    root = tmp_path / "src" / "plugin"
    for s in skills:
        d = root / "skills" / s
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text("# %s\n" % s, encoding="utf-8")
    (root / "hooks").mkdir(parents=True)
    (root / "hooks" / "gate.py").write_text("# hook\n", encoding="utf-8")
    return root


# ---- the room never deletes its own input -------------------------------------------------------

def test_prepare_room_refuses_to_delete_the_source_it_was_handed(tmp_path):
    """`--plugin <room>/plugin --room <room>` used to rmtree the source and then fail to copy it."""
    room = A.prepare_room(_plugin(tmp_path), tmp_path / "room")
    with pytest.raises(A.RoomError):
        A.prepare_room(room, tmp_path / "room")
    assert (room / "skills" / "alpha" / "SKILL.md").is_file(), "the input was deleted"


def test_prepare_room_refuses_a_source_nested_inside_the_room_copy(tmp_path):
    room = A.prepare_room(_plugin(tmp_path), tmp_path / "room")
    with pytest.raises(A.RoomError):
        A.prepare_room(room / "skills", tmp_path / "room")
    assert (room / "skills" / "alpha" / "SKILL.md").is_file()


def test_prepare_room_from_skills_refuses_a_skills_dir_inside_the_room(tmp_path):
    room = A.prepare_room(_plugin(tmp_path), tmp_path / "room")
    with pytest.raises(A.RoomError):
        A.prepare_room_from_skills(room / "skills", tmp_path / "room")
    assert (room / "skills" / "alpha" / "SKILL.md").is_file()


def test_prepare_room_from_skills_refuses_a_hooks_dir_inside_the_room(tmp_path):
    src = _plugin(tmp_path)
    room = A.prepare_room(src, tmp_path / "room")
    with pytest.raises(A.RoomError):
        A.prepare_room_from_skills(src / "skills", tmp_path / "room", hooks_dir=room / "hooks")
    assert (room / "hooks" / "gate.py").is_file()


def test_reusing_the_room_with_a_source_inside_it_is_still_allowed(tmp_path):
    """The control: --reuse-room deletes nothing, so there is nothing to refuse."""
    room = A.prepare_room(_plugin(tmp_path), tmp_path / "room")
    assert A.prepare_room(room, tmp_path / "room", reuse=True) == room
    assert (room / "skills" / "alpha" / "SKILL.md").is_file()


def test_a_source_that_merely_shares_a_name_prefix_is_not_refused(tmp_path):
    """`<room>/plugin-src` is not inside `<room>/plugin`: a string-prefix test would say it is."""
    room_root = tmp_path / "room"
    A.prepare_room(_plugin(tmp_path), room_root)
    sibling = room_root / "plugin-src"
    (sibling / "skills" / "beta").mkdir(parents=True)
    (sibling / "skills" / "beta" / "SKILL.md").write_text("# beta\n", encoding="utf-8")
    room = A.prepare_room(sibling, room_root)
    assert (room / "skills" / "beta" / "SKILL.md").is_file()


# ---- counting what a report claims --------------------------------------------------------------

def test_a_report_missing_marker_counts_as_exactly_one_finding(tmp_path):
    stored = A.store_report(tmp_path / "r.txt", "alpha", "Looking back, nothing unsettled.")
    assert A.count_findings(stored) == 1
    assert sum(A.count_by_class(stored).values()) == 1


def test_finding_mentioned_mid_line_is_not_counted():
    text = ("FINDING: BUG | a.py:1 | the parser treats 'FINDING:' in prose as a finding\n"
            "WHY: a line saying FINDING: inside it is still one finding\n")
    assert A.count_findings(text) == 1


def test_count_findings_control_one_real_line_and_no_findings():
    assert A.count_findings("FINDING: WRONG | SKILL.md | x\nQUOTE: y\n") == 1
    assert A.count_findings("NO FINDINGS") == 0


def test_prose_quoting_the_finding_label_is_not_a_complete_report():
    """A reply that talks ABOUT the label is not a report; only a line that starts with it is."""
    assert not A.report_is_complete("I produced no FINDING: lines this time.\n")
    assert A.report_is_complete("preamble\nFINDING: BUG | a.py:1 | x\n")


# ---- the missing-report marker names its real cause ---------------------------------------------

def test_a_failed_reviewer_run_is_not_blamed_on_a_stop_hook(tmp_path):
    out = A.RunnerOutcome("(no stdout) Invalid API key", "claude exited 1")
    body = A.store_report(tmp_path / "r.txt", "alpha", out)
    first = body.splitlines()[0]
    assert first.startswith(A.REPORT_MISSING_MARKER)
    assert "claude exited 1" in first
    assert "Stop" not in first
    assert "Invalid API key" in body, "the raw output must be kept"


def test_a_prose_reply_with_no_report_block_says_so(tmp_path):
    body = A.store_report(tmp_path / "r.txt", "alpha", "Looking back, nothing unsettled.")
    first = body.splitlines()[0]
    assert first.startswith(A.REPORT_MISSING_MARKER) and "no report block" in first
    assert "FINDING:" not in first, "the marker sentence must not carry the finding label"


def test_a_failed_run_is_missing_even_if_its_output_looks_like_a_report(tmp_path):
    """A timeout or a non-zero exit cannot vouch for whatever text came back before it."""
    body = A.store_report(tmp_path / "r.txt", "alpha", A.RunnerOutcome("NO FINDINGS", "timeout"))
    assert body.startswith(A.REPORT_MISSING_MARKER)
    assert A.report_missing(body)


def test_a_successful_run_with_a_report_is_stored_verbatim(tmp_path):
    body = A.store_report(tmp_path / "r.txt", "alpha", A.RunnerOutcome("NO FINDINGS", ""))
    assert body == "NO FINDINGS" and not A.report_missing(body)


def test_audit_all_records_the_runner_failure_in_the_report(tmp_path):
    A.audit_all(_plugin(tmp_path), tmp_path / "room", jobs=1, log=lambda *_a: None,
                runner=lambda *_a: A.RunnerOutcome("(no stdout) boom", "claude exited 2"))
    body = (tmp_path / "room" / "reports" / "alpha.audit.txt").read_text(encoding="utf-8")
    assert "claude exited 2" in body.splitlines()[0]


# ---- hook registration matches a whole file name ------------------------------------------------

def _hooks_json(room, commands, bom=False):
    data = {"hooks": {}}
    for event, matcher, script in commands:
        data["hooks"].setdefault(event, []).append(
            {"matcher": matcher, "hooks": [{"type": "command",
             "command": 'bash "${ROOT}/hooks/run-python.sh" "${ROOT}/hooks/%s"' % script}]})
    text = json.dumps(data)
    (room / "hooks").mkdir(parents=True, exist_ok=True)
    (room / "hooks" / "hooks.json").write_bytes((b"\xef\xbb\xbf" if bom else b"") + text.encode())


def test_hook_registration_does_not_credit_a_hook_with_a_longer_named_sibling(tmp_path):
    _hooks_json(tmp_path, [("PreToolUse", "Bash", "commit-tell-sweep.py"),
                           ("PostToolUse", "Write|Edit", "tell-sweep.py")])
    reg = A.hook_registration(tmp_path, "hooks/tell-sweep.py")
    assert reg == [("PostToolUse", "Write|Edit",
                    'bash "${ROOT}/hooks/run-python.sh" "${ROOT}/hooks/tell-sweep.py"')]


def test_hook_registration_control_the_longer_name_finds_only_itself(tmp_path):
    _hooks_json(tmp_path, [("PreToolUse", "Bash", "commit-tell-sweep.py"),
                           ("PostToolUse", "Write|Edit", "tell-sweep.py")])
    reg = A.hook_registration(tmp_path, "hooks/commit-tell-sweep.py")
    assert [r[0] for r in reg] == ["PreToolUse"]


def test_hook_registration_matches_an_unquoted_command_too(tmp_path):
    (tmp_path / "hooks").mkdir()
    (tmp_path / "hooks" / "hooks.json").write_text(
        '{"hooks": {"Stop": [{"hooks": [{"command": "python3 hooks/tell-sweep.py --x"}]}]}}',
        encoding="utf-8")
    assert A.hook_registration(tmp_path, "hooks/tell-sweep.py")[0][0] == "Stop"


def test_hook_registration_reads_a_hooks_json_that_carries_a_bom(tmp_path):
    """json.loads rejects a BOM, and the failure was swallowed into 'not registered'."""
    _hooks_json(tmp_path, [("Stop", "*", "gate.py")], bom=True)
    assert A.hook_registration(tmp_path, "hooks/gate.py")


# ---- line numbers follow Python's own line breaks -----------------------------------------------

def test_evidence_line_numbers_are_not_shifted_by_a_form_feed(tmp_path):
    """str.splitlines() also splits on \\f and U+2028, so every later line number drifted."""
    (tmp_path / "hooks").mkdir()
    (tmp_path / "hooks" / "m.py").write_text("a = 1\n\x0c\nb = 2\n", encoding="utf-8")
    text = ("FINDING: BUG | hooks/m.py:3 | claim\nEXHIBIT:\n  3: b = 2\nWHY: z\n"
            "CONFIDENCE: VERIFIED\n")
    assert A.evidence_problems(text, tmp_path) == []


def test_evidence_of_line_one_survives_a_bom(tmp_path):
    (tmp_path / "hooks").mkdir()
    (tmp_path / "hooks" / "m.py").write_bytes(b"\xef\xbb\xbfa = 1\n")
    text = "FINDING: BUG | hooks/m.py:1 | claim\nEXHIBIT:\n  1: a = 1\nWHY: z\n"
    assert A.evidence_problems(text, tmp_path) == []


def test_mention_block_line_numbers_are_not_shifted_by_a_line_separator(tmp_path):
    (tmp_path / "doc.md").write_text("one\u2028still one\nrun gate.py here\n", encoding="utf-8")
    assert "doc.md:2:" in A.mention_block(tmp_path, "skills/a/gate.py", ["doc.md"])
