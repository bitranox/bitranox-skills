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
    # A substitution or an assertion ELSEWHERE in the command says nothing about this literal.
    f'cd "$(git rev-parse --show-toplevel)" && uv run ci_wait.py --sha {S}',
    f"gh run list --limit $(echo 5) --commit {S}",
    f"N=$(nproc); gh run list --commit {S}",
    f"ls `pwd` && gh run list --commit {S}",
    f"git rev-parse --show-toplevel && gh run list --commit {S}",
    f"git merge-base HEAD origin/master; gh run list --commit {S}",
    f"git cat-file -e {OTHER}^{{commit}} && gh run list --commit {S}",   # asserts a DIFFERENT sha
    f"R=$(gh run list --commit {S} --json databaseId -q .[0].databaseId); echo $R",
    # Comparing against a derived sha: an invented literal silently answers "not equal".
    f'SHA=$(git rev-parse --verify -q HEAD); test "$SHA" = {S}',
    # rev-parse echoes a bare full sha back with exit 0 whether or not the object exists; only a
    # peel such as ^{{commit}} makes it look the object up.
    f"git rev-parse --verify {S}",
    f"git rev-parse --verify -q {S} && gh run list --commit {S}",
])
def test_a_literal_is_judged_on_its_own_not_on_the_rest_of_the_command(command):
    assert N.notice(command) is not None


@pytest.mark.parametrize("command", [
    f"git show --stat {S}",
    f"git update-ref refs/heads/topic {OTHER} {S}",
    f"git push --force-with-lease=topic:{S} origin topic",
    f"cd /repo && git log -1 {S}",
    f"git -C /repo diff {OTHER} {S}",
    f"git branch --contains {S}",                          # 129 "no such commit"
    f"git branch topic {S}",                               # the START POINT is resolved
    f"git tag v1 {S}",
    f"git show -m {S}",                                    # -m is a bare flag for show
    f"git checkout -b topic {S}",
    f"git rebase --onto {S} main",
    f"git restore --source={S} f.txt",
])
def test_a_sha_only_a_loud_local_git_verb_consumes_is_left_alone(command):
    """Git refuses a nonexistent object loudly there, so an invented sha costs one round trip and
    cannot become the silent deadline-long wait this hook exists for."""
    assert N.notice(command) is None


@pytest.mark.parametrize("command", [
    # Matched as TEXT, not resolved: an invented sha finds nothing and git exits 0 (grep: 1).
    f"git log --grep={S}",
    f"git log --oneline --grep {S}",
    f"git log -S{S}",
    f"git log --all -S {S}",
    f"git log --author={S}",
    f"git rev-list --grep={S} HEAD",
    f"git shortlog --grep={S} HEAD",
    f"git grep {S}",
    f"git grep -q -e {S}",
    # After `--` it is a pathspec, which matches nothing and says nothing.
    f"git log --oneline -- {S}",
    f"git diff HEAD -- {S}",
    f"git show HEAD -- {S}",
    # A NAME: these create (or list) a ref called that, exit 0.
    f"git tag {S}",
    f"git branch {S}",
    f"git branch --list {S}",
    f"git checkout -b {S}",
    f"git switch -c {S}",
])
def test_a_loud_verb_does_not_excuse_a_sha_it_never_resolves(command):
    """The exemption belongs to the operand's ROLE: a revision is resolved loudly, a pattern, a
    pathspec or a new ref name is not."""
    assert N.notice(command) is not None


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
    f"git rev-parse --verify -q {S}^{{commit}}",           # this IS the assertion
    f"git rev-parse --verify -q {S}^{{commit}} && uv run ci_wait.py --sha {S}",
    f"git cat-file -e {S}^{{commit}} && echo ok",          # so is this
    f"git cat-file -e {S}^{{commit}} && gh run list --commit {S}",
    f"git cat-file -t {S}",
    f"git -C /repo cat-file -e {S} && gh run list --commit {S}",
    f"git merge-base --is-ancestor {S} HEAD",              # an existence-checking question too
    f"git merge-base --is-ancestor {S} HEAD && gh run list --commit {S}",
])
def test_a_derived_or_asserted_sha_is_left_alone(command):
    assert N.notice(command) is None


# --- the PowerShell tool: the same questions in the other language --------------------------------

@pytest.mark.parametrize("command", [
    f'$x = "a`tb"; gh run list --commit {S}',              # a backtick ESCAPE, not a substitution
    f'Write-Host "done`n"; gh run list --commit {S}',
    f"$r = $(gh run list --commit {S})",                   # the literal INSIDE the subexpression
    f"git log --grep={S}",
    f"git branch {S}",
])
def test_powershell_commands_that_use_an_unverified_literal_are_nudged(command):
    assert N.notice(command, "PowerShell") is not None


@pytest.mark.parametrize("command", [
    f"Write-Host {S}",
    f'Write-Host "fixed in {S}"',
    f"Write-Output {S}",
    f"write-host {S}",                                     # PowerShell ignores command case
    f"echo {S}",
    f"ls # was {S}",
    f"git commit -m 'reverts {S}'",
    f"git show {S}",
    f"git log -1 {S}",
    "gh run list --commit $(git rev-parse HEAD)",
    f"git cat-file -e {S}; gh run list --commit {S}",
])
def test_powershell_commands_that_print_derive_or_resolve_the_sha_are_left_alone(command):
    assert N.notice(command, "PowerShell") is None


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


def _file_tool_round_trip(tool, input_, result_text, tool_use_result):
    """An assistant file-writing call and the user record carrying its result, as Claude Code
    records them: the result's `toolUseResult` repeats what the assistant wrote."""
    call = {"type": "assistant", "message": {"role": "assistant", "content": [
        {"type": "tool_use", "id": "w1", "name": tool, "input": input_}]}}
    result = {"type": "user", "message": {"role": "user", "content": [
        {"type": "tool_result", "tool_use_id": "w1", "content": result_text}]},
        "toolUseResult": tool_use_result}
    return [call, result]


def test_a_write_result_echoing_the_assistant_s_own_text_does_not_count(tmp_path):
    records = _file_tool_round_trip(
        "Write", {"file_path": "/x/notes.md", "content": f"wait on {S}\n"},
        "File created successfully at: /x/notes.md",
        {"type": "create", "filePath": "/x/notes.md", "content": f"wait on {S}\n",
         "structuredPatch": [], "originalFile": None})
    assert N.shown_shas([_transcript(tmp_path, "s.jsonl", records)], [S]) == set()


def test_an_edit_result_whose_snippet_echoes_the_new_text_does_not_count(tmp_path):
    records = _file_tool_round_trip(
        "Edit", {"file_path": "/x/a.sh", "old_string": "X", "new_string": f"SHA={S}"},
        f"The file /x/a.sh has been updated. Here's the result:\n     1\tSHA={S}\n",
        {"filePath": "/x/a.sh", "oldString": "X", "newString": f"SHA={S}",
         "originalFile": "X\n", "structuredPatch": [{"lines": [f"+SHA={S}"]}]})
    assert N.shown_shas([_transcript(tmp_path, "s.jsonl", records)], [S]) == set()


def test_a_command_result_s_structured_copy_still_counts(tmp_path):
    """The exclusion is the file-writing tools' echo, not `toolUseResult` as such: for Bash it is
    the real output."""
    call = _assistant_command("git log -1 --format=%H")
    result = {"type": "user", "message": {"role": "user", "content": [
        {"type": "tool_result", "tool_use_id": "t2", "content": S}]},
        "toolUseResult": {"stdout": S, "stderr": ""}}
    assert N.shown_shas([_transcript(tmp_path, "s.jsonl", [call, result])], [S]) == {S}


@pytest.mark.parametrize("error", [
    "fatal: bad object {sha}",
    "fatal: ambiguous argument '{sha}': unknown revision or path not in the working tree.",
    "error: no such commit {sha}",
    "fatal: Not a valid object name {sha}",
    "fatal: Not a valid commit name {sha}",
    "fatal: bad revision '{sha}..HEAD'",
    "gh: No commit found for SHA: {sha} (HTTP 422)",
])
def test_a_tool_refusing_the_sha_does_not_count_as_showing_it(tmp_path, error):
    """Git's loud refusal is the reason a loud verb is exempt; it must not also launder the
    invented sha for the NEXT command."""
    records = [_assistant_command(f"git show {S}"), _tool_result(error.format(sha=S))]
    assert N.shown_shas([_transcript(tmp_path, "s.jsonl", records)], [S]) == set()


@pytest.mark.parametrize("text", [
    "fatal: bad object {other}\n{sha}\n",                  # the refusal names a different line
    "{sha} fatal: bad object",                             # the sha comes BEFORE the phrase
])
def test_a_sha_printed_apart_from_a_refusal_still_counts(tmp_path, text):
    path = _transcript(tmp_path, "s.jsonl", [_tool_result(text.format(sha=S, other=OTHER))])
    assert N.shown_shas([path], [S]) == {S}


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


def _subagent(tmp_path, parent_records, agent_records, write_parent=True):
    """A session file plus one subagent file at the path Claude Code uses for it."""
    main_path = tmp_path / "sess.jsonl"
    if write_parent:
        _transcript(tmp_path, "sess.jsonl", parent_records)
    agents = tmp_path / "sess" / "subagents"
    agents.mkdir(parents=True)
    return main_path, _transcript(agents, "agent-abc123.jsonl", agent_records)


def _brief(text):
    return {"type": "user", "isSidechain": True, "message": {"role": "user", "content": text}}


def _run_in_subagent(monkeypatch, capsys, transcript_path):
    return _run_main(monkeypatch, capsys, {
        "tool_name": "Bash", "transcript_path": str(transcript_path), "agent_id": "abc123",
        "tool_input": {"command": f"gh run list --commit {S}"}})


def test_a_sha_only_the_brief_carries_is_nudged(monkeypatch, capsys, tmp_path):
    """The parent ASSISTANT wrote the brief, so a sha it invented reaches the subagent there."""
    main_path, _agent = _subagent(tmp_path, [_tool_result("unrelated")],
                                  [_brief(f"watch CI for {S}")])
    out = _run_in_subagent(monkeypatch, capsys, main_path)
    assert "not appear" in json.loads(out)["hookSpecificOutput"]["additionalContext"]


def test_a_brief_sha_the_parent_was_shown_is_not_nudged(monkeypatch, capsys, tmp_path):
    main_path, _agent = _subagent(tmp_path, [_tool_result(f"{S}\n")],
                                  [_brief(f"watch CI for {S}")])
    assert _run_in_subagent(monkeypatch, capsys, main_path) == ""


def test_a_sha_the_subagent_s_own_tool_printed_is_not_nudged(monkeypatch, capsys, tmp_path):
    main_path, _agent = _subagent(tmp_path, [_tool_result("unrelated")],
                                  [_brief("watch CI for HEAD"), _tool_result(f"{S}\n")])
    assert _run_in_subagent(monkeypatch, capsys, main_path) == ""


def test_a_brief_sha_is_nudged_when_the_parent_cannot_be_read(monkeypatch, capsys, tmp_path):
    """Fail open: an unreadable parent cannot vouch for the brief."""
    main_path, _agent = _subagent(tmp_path, [], [_brief(f"watch CI for {S}")],
                                  write_parent=False)
    assert _run_in_subagent(monkeypatch, capsys, main_path) != ""


@pytest.mark.parametrize("shown_in_parent", [True, False])
def test_a_transcript_path_naming_the_subagent_file_finds_the_parent(
        monkeypatch, capsys, tmp_path, shown_in_parent):
    parent = [_tool_result(f"{S}\n" if shown_in_parent else "unrelated")]
    _main, agent_path = _subagent(tmp_path, parent, [_brief(f"watch CI for {S}")])
    out = _run_in_subagent(monkeypatch, capsys, agent_path)
    assert (out == "") is shown_in_parent


def test_main_nudges_under_the_powershell_tool(monkeypatch, capsys, tmp_path):
    path = _transcript(tmp_path, "s.jsonl", [_tool_result("[master fb3330b] x")])
    out = _run_main(monkeypatch, capsys, {
        "tool_name": "PowerShell", "transcript_path": str(path),
        "tool_input": {"command": f'$x = "a`tb"; gh run list --commit {PADDED}'}})
    assert PADDED[:12] in json.loads(out)["hookSpecificOutput"]["additionalContext"]


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
