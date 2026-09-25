"""Tests for sha-literal-nudge.py - a full sha nobody showed this session may have been invented.

From `feedback-a-sha-you-did-not-derive-is-one-you-may-have-invented` (recurrence 5): a short sha
padded out to 40 hex characters passes every shape check (`ci_wait`'s FULL_SHA_RE, a `headSha ==`
filter, `gh run list --commit` answering `[]` with exit 0), so a wait armed on it polls to its
deadline. The prose rule was retrieved, restated and violated inside one session, so this is the
command-side half. ASCII only.
"""
import io
import json

import pytest

import sha_literal_nudge as N

S = "fb3330bd1ad7088658dda3716342906364ca87e2"            # a real-looking full sha
PADDED = "fb3330b1d7b7b8c1e9fba1bb5cb6eb48e7d1b5ff"       # the measured padding of `fb3330b`
OTHER = "3ae9c6d1d2f0a4b5c6d7e8f90123456789abcdef"


# --- fires: a bare literal the command did not derive --------------------------------------------

@pytest.mark.parametrize("command", [
    f"uv run /x/scripts/ci_wait.py --sha {S}",
    f"gh run list --commit {S} --json status,conclusion",
    f"until gh run list --commit {S} | grep -q completed; do sleep 30; done",
    f'uv run ci_wait.py --sha "{S}"',                      # a quoted ARGUMENT is still an argument
    f"gh api repos/o/r/commits/{S}/check-runs",
    f"git log --format=%H | grep -q {S} && echo landed",   # grep fails SILENTLY on absence
    f"test -f head.txt && test {S} = xyz",
    f"git show {S} && gh run list --commit {S}",           # one silent consumer is enough
])
def test_a_bare_full_sha_literal_is_nudged(command):
    message = N.notice(command)
    assert message is not None
    assert "rev-parse" in message and "cat-file -e" in message


@pytest.mark.parametrize("command", [
    f"git show --stat {S}",
    f"git update-ref refs/heads/topic {OTHER} {S}",
    f"git push --force-with-lease=topic:{S} origin topic",
    f"cd /repo && git log -1 {S}",
    f"git -C /repo diff {OTHER} {S}",
])
def test_a_sha_only_a_loud_local_git_verb_consumes_is_left_alone(command):
    """Git refuses a nonexistent object loudly there, so an invented sha costs one round trip and
    cannot become the silent deadline-long wait this hook exists for."""
    assert N.notice(command) is None


def test_the_measured_padding_case_is_nudged():
    assert N.notice(f"uv run ci_wait.py --sha {PADDED}") is not None


def test_the_notice_never_asks_to_block():
    """Non-blocking by design: a sha pasted from a CI URL or by the user must stay usable."""
    message = N.notice(f"gh run list --commit {S}")
    assert "permissionDecision" not in message


# --- silent: derived, asserted, or not a sha at all -----------------------------------------------

@pytest.mark.parametrize("command", [
    "uv run ci_wait.py --sha $(git rev-parse HEAD)",
    "uv run ci_wait.py --sha `git rev-parse HEAD`",
    f"SHA=$(git rev-parse --verify -q HEAD); test \"$SHA\" = {S}",
    f"git rev-parse --verify -q {S}^{{commit}}",           # this IS the assertion
    f"git cat-file -e {S}^{{commit}} && echo ok",          # so is this
    f"git cat-file -t {S}",
    f"git merge-base --is-ancestor {S} HEAD",              # an existence-checking question too
])
def test_a_derived_or_asserted_sha_is_left_alone(command):
    assert N.notice(command) is None


@pytest.mark.parametrize("command", [
    f"cat > note.md <<'EOF'\nthe fix landed in {S}\nEOF",
    f'git commit -m "revert {S}"',
    f"echo {S}",
    f"printf '%s\\n' {S}",
    f"ls   # was {S}",
    f"gh pr create --title t --body 'reverts {S}'",
    f'gh pr comment 5 --body "reverts {S}"',               # not a sink program: the FLAG decides
    f"gh release create v1 --notes='built from {S}'",
])
def test_a_sha_in_a_data_region_is_left_alone(command):
    """Prose documenting a sha must not trip the guard about using one."""
    assert N.notice(command) is None


@pytest.mark.parametrize("command", [
    f"git show {S[:39]}",                                  # 39 hex: not a full sha
    f"git show {S}a",                                      # 41 hex
    "sha256sum x | grep " + "ab" * 32,                     # 64 hex: a sha256, not a commit
    f"git show x{S}",                                      # hex run inside a longer word
    f"git show {S}_old",
    f"gpg --recv-keys {S.upper()}",                        # uppercase: a fingerprint, not a sha
    "test " + "1" * 40 + " -gt 0",                         # all digits: a number
    "git log --oneline -5",
])
def test_things_that_are_not_a_bare_full_sha_are_left_alone(command):
    assert N.notice(command) is None


def test_non_string_input_is_ignored():
    assert N.notice(None) is None
    assert N.notice(123) is None
    assert N.notice("") is None


# --- the transcript: a sha the session was SHOWN is not an invented one ---------------------------

def _transcript(tmp_path, name, records):
    path = tmp_path / name
    path.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
    return path


def _tool_result(text):
    return {"type": "user", "message": {"role": "user", "content": [
        {"type": "tool_result", "tool_use_id": "t1", "content": text}]}}


def _assistant_command(command):
    return {"type": "assistant", "message": {"role": "assistant", "content": [
        {"type": "tool_use", "id": "t2", "name": "Bash", "input": {"command": command}}]}}


def test_a_sha_a_tool_printed_earlier_is_not_nudged(tmp_path):
    path = _transcript(tmp_path, "s.jsonl", [_tool_result(f"{S}\n")])
    assert N.notice(f"gh run list --commit {S}", shown=N.shown_shas([path], [S])) is None


def test_a_sha_the_user_pasted_is_not_nudged(tmp_path):
    user = {"type": "user", "message": {"role": "user", "content": f"check CI for {S} please"}}
    path = _transcript(tmp_path, "s.jsonl", [user])
    assert N.notice(f"gh run list --commit {S}", shown=N.shown_shas([path], [S])) is None


def test_only_the_short_prefix_was_shown_so_the_padded_sha_is_nudged(tmp_path):
    """The measured failure: `fb3330b` was printed, the 40-char form was typed."""
    path = _transcript(tmp_path, "s.jsonl", [_tool_result("[master fb3330b] a commit\n")])
    shown = N.shown_shas([path], [PADDED])
    assert N.notice(f"uv run ci_wait.py --sha {PADDED}", shown=shown) is not None


def test_a_sha_only_the_assistant_wrote_does_not_count_as_shown(tmp_path):
    """Its own earlier tool_use carrying the sha is the invention, not evidence against it."""
    path = _transcript(tmp_path, "s.jsonl", [_assistant_command(f"git show {S}")])
    assert N.shown_shas([path], [S]) == set()


def test_a_sha_inside_a_longer_hex_run_in_the_transcript_does_not_count(tmp_path):
    path = _transcript(tmp_path, "s.jsonl", [_tool_result(S + "00ff")])
    assert N.shown_shas([path], [S]) == set()


def test_a_missing_transcript_reads_as_unknown_not_as_nothing_shown(tmp_path):
    """'Not shown' is a claim about a transcript that was read; none was, so it is unknown."""
    assert N.shown_shas([tmp_path / "absent.jsonl"], [S]) is None


def test_the_notice_says_it_was_not_shown_when_the_transcript_was_read(tmp_path):
    path = _transcript(tmp_path, "s.jsonl", [_tool_result("nothing here")])
    message = N.notice(f"gh run list --commit {S}", shown=N.shown_shas([path], [S]))
    assert "not appear" in message


# --- main(): the hook contract --------------------------------------------------------------------

def _run_main(monkeypatch, capsys, event):
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(event)))
    assert N.main() == 0
    return capsys.readouterr().out


def test_main_emits_additional_context_and_no_decision(monkeypatch, capsys, tmp_path):
    path = _transcript(tmp_path, "s.jsonl", [_tool_result("[master fb3330b] x")])
    out = _run_main(monkeypatch, capsys, {
        "tool_name": "Bash", "transcript_path": str(path),
        "tool_input": {"command": f"uv run ci_wait.py --sha {PADDED}"}})
    payload = json.loads(out)["hookSpecificOutput"]
    assert payload["hookEventName"] == "PreToolUse"
    assert PADDED[:12] in payload["additionalContext"]
    assert "permissionDecision" not in payload


def test_main_is_silent_when_the_transcript_showed_the_sha(monkeypatch, capsys, tmp_path):
    path = _transcript(tmp_path, "s.jsonl", [_tool_result(S)])
    out = _run_main(monkeypatch, capsys, {
        "tool_name": "Bash", "transcript_path": str(path),
        "tool_input": {"command": f"gh run list --commit {S}"}})
    assert out == ""


def test_main_reads_the_subagent_s_own_transcript(monkeypatch, capsys, tmp_path):
    """In a subagent transcript_path is the MAIN session's; the brief lives in the agent's file."""
    main_path = _transcript(tmp_path, "sess.jsonl", [_tool_result("unrelated")])
    agents = tmp_path / "sess" / "subagents"
    agents.mkdir(parents=True)
    brief = {"type": "user", "message": {"role": "user", "content": f"watch CI for {S}"}}
    _transcript(agents, "agent-abc123.jsonl", [brief])
    out = _run_main(monkeypatch, capsys, {
        "tool_name": "Bash", "transcript_path": str(main_path), "agent_id": "abc123",
        "tool_input": {"command": f"gh run list --commit {S}"}})
    assert out == ""


def test_main_without_a_transcript_still_nudges(monkeypatch, capsys):
    out = _run_main(monkeypatch, capsys, {
        "tool_name": "Bash", "tool_input": {"command": f"gh run list --commit {S}"}})
    assert "could not be checked" in json.loads(out)["hookSpecificOutput"]["additionalContext"]


def test_main_with_an_unreadable_transcript_says_unknown(monkeypatch, capsys, tmp_path):
    out = _run_main(monkeypatch, capsys, {
        "tool_name": "Bash", "transcript_path": str(tmp_path / "gone.jsonl"),
        "tool_input": {"command": f"gh run list --commit {S}"}})
    assert "could not be checked" in json.loads(out)["hookSpecificOutput"]["additionalContext"]


def test_main_ignores_other_tools_and_bad_stdin(monkeypatch, capsys):
    assert _run_main(monkeypatch, capsys, {"tool_name": "Read", "tool_input": {"file_path": S}}) == ""
    monkeypatch.setattr("sys.stdin", io.StringIO("not json"))
    assert N.main() == 0
