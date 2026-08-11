"""Tests for jig-repetition-nudge.

The load-bearing case is the NEGATIVE one: a hook that fires on any two scripts of the same
language would be noise, and noise gets ignored, which is how the catalogue hook's silence went
unnoticed for six variants. So similarity is asserted to separate copy-paste lineage from
"both happen to be PowerShell".
"""
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

HOOK = Path(__file__).resolve().parent.parent / "jig-repetition-nudge.py"

spec = importlib.util.spec_from_file_location("jig_repetition_nudge", HOOK)
mod = importlib.util.module_from_spec(spec)
sys.modules["jig_repetition_nudge"] = mod
spec.loader.exec_module(mod)


DELETE_V1 = """
$root = 'C:\\Windows.old'
$links = Get-ChildItem $root -Recurse -Directory -Force -Attributes ReparsePoint
foreach ($l in $links) { cmd /c rd /q $l.FullName }
$empty = Join-Path $env:TEMP ([guid]::NewGuid())
robocopy $empty $root /MIR /XJ /R:0 /W:0 /MT:16
cmd /c rd /s /q $root
Write-Host ("free " + (Get-CimInstance Win32_LogicalDisk).FreeSpace)
"""

DELETE_V2 = """
$root = 'C:\\Windows.old'
$links = Get-ChildItem $root -Recurse -Directory -Force -Attributes ReparsePoint
foreach ($l in $links) { cmd /c rd /q $l.FullName }
$empty = Join-Path $env:TEMP ([guid]::NewGuid())
robocopy $empty $root /MIR /XJ /R:0 /W:0 /MT:16 /NFL /NDL
cmd /c rd /s /q $root
Write-Host ("reclaimed " + (Get-CimInstance Win32_LogicalDisk).FreeSpace)
"""

DELETE_V3 = """
$root = 'C:\\Windows.old'
$links = Get-ChildItem $root -Recurse -Directory -Force -Attributes ReparsePoint
foreach ($l in $links) { cmd /c rd /q $l.FullName }
if (Test-Path $root) { Write-Host 'gate' }
$empty = Join-Path $env:TEMP ([guid]::NewGuid())
robocopy $empty $root /MIR /XJ /R:0 /W:0 /MT:16
cmd /c rd /s /q $root
"""

UNRELATED = """
$adapters = Get-NetAdapter | Sort-Object Name
foreach ($a in $adapters) {
    Write-Host ($a.Name + ' ' + $a.MacAddress + ' ' + $a.Status)
}
$ip = Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notlike '127.*' }
$ip | ForEach-Object { Write-Host $_.IPAddress }
Get-Service wuauserv | Select-Object Name, Status, StartType
"""


def test_near_duplicates_score_high():
    assert mod.similarity(mod.shingles(DELETE_V1), mod.shingles(DELETE_V2)) >= mod.SIMILARITY


def test_unrelated_scripts_score_below_threshold():
    """The negative control: same language, different job, must NOT look like a variant."""
    score = mod.similarity(mod.shingles(DELETE_V1), mod.shingles(UNRELATED))
    assert score < mod.SIMILARITY, f"unrelated scripts scored {score}"


def test_comments_do_not_create_similarity():
    a = mod.shingles("# delete windows.old safely with robocopy mirror\n$x = 1\n")
    b = mod.shingles("# delete windows.old safely with robocopy mirror\n$y = 2\n")
    assert mod.similarity(a, b) == 0.0


def test_count_kin_ignores_same_path():
    """Iterating on ONE file is editing, not authoring a new variant."""
    sh = mod.shingles(DELETE_V1)
    store = {"/tmp/a.ps1": [list(t) for t in sh]}
    assert mod.count_kin(store, "/tmp/a.ps1", sh) == []


def _run(payload, home):
    """Run the hook with HOME redirected.

    The hook is a SUBPROCESS and its state dir resolves through Path.home(), so a parent-process
    monkeypatch.setenv never reaches it - an earlier version of these tests wrote into the real
    audit dir, passed once on a clean machine, and failed on re-run against its own leftover
    state. The env must be handed to the child.
    """
    env = dict(os.environ, HOME=str(home), USERPROFILE=str(home))
    return subprocess.run([sys.executable, str(HOOK)], input=json.dumps(payload),
                          capture_output=True, text=True, encoding="utf-8", timeout=60, env=env)


def _write_event(session, path, content):
    return {"tool_name": "Write", "session_id": session,
            "tool_input": {"file_path": path, "content": content}}


def test_state_is_isolated_to_the_given_home(tmp_path):
    """Guards the isolation itself: the state file must land under the redirected HOME."""
    _run(_write_event("sess-iso", "/tmp/a.ps1", DELETE_V1), tmp_path)
    assert list(tmp_path.rglob("*.jig-shingles.json")), "state did not land under the test HOME"


def test_third_variant_nudges_and_first_two_do_not(tmp_path):
    sess = "sess-jig-1"
    r1 = _run(_write_event(sess, "/tmp/del_v1.ps1", DELETE_V1), tmp_path)
    r2 = _run(_write_event(sess, "/tmp/del_v2.ps1", DELETE_V2), tmp_path)
    r3 = _run(_write_event(sess, "/tmp/del_v3.ps1", DELETE_V3), tmp_path)
    for r in (r1, r2, r3):
        assert r.returncode == 0
    assert r1.stdout.strip() == "", "first script must be silent"
    assert r2.stdout.strip() == "", "second script must be silent"
    assert "TESTED JIG" in r3.stdout, f"third variant should nudge, got: {r3.stdout!r}"


def test_nudges_only_once_per_session(tmp_path):
    sess = "sess-once"
    for path, body in (("/tmp/a.ps1", DELETE_V1), ("/tmp/b.ps1", DELETE_V2)):
        _run(_write_event(sess, path, body), tmp_path)
    first = _run(_write_event(sess, "/tmp/c.ps1", DELETE_V3), tmp_path)
    second = _run(_write_event(sess, "/tmp/d.ps1", DELETE_V1 + "\n$z = 9\n"), tmp_path)
    assert "TESTED JIG" in first.stdout
    assert second.stdout.strip() == "", "must not nudge twice in one session"


def test_unrelated_second_script_never_nudges(tmp_path):
    sess = "sess-jig-3"
    a = _run(_write_event(sess, "/tmp/x1.ps1", DELETE_V1), tmp_path)
    b = _run(_write_event(sess, "/tmp/x2.ps1", UNRELATED), tmp_path)
    assert a.stdout.strip() == ""
    assert b.stdout.strip() == "", "an unrelated second script must not nudge"


def test_non_script_files_ignored(tmp_path):
    sess = "sess-jig-4"
    for i in range(4):
        r = _run(_write_event(sess, f"/tmp/doc{i}.md", DELETE_V1), tmp_path)
        assert r.stdout.strip() == ""
        assert r.returncode == 0


def _heredoc(path, body, marker="EOS", quoted=True, op=">"):
    q = "'" if quoted else ""
    return f"cd /tmp && cat {op} {path} <<{q}{marker}{q}\n{body}\n{marker}\n"


def _bash_event(session, command):
    return {"tool_name": "Bash", "session_id": session, "tool_input": {"command": command}}


def test_heredoc_write_is_extracted():
    got = mod.heredoc_writes(_heredoc("del_v1.ps1", DELETE_V1))
    assert len(got) == 1
    assert got[0][0] == "del_v1.ps1"
    assert "robocopy" in got[0][1]


def test_heredoc_variants_written_via_bash_nudge(tmp_path):
    """The regression this hook exists for: the scripts that motivated it were heredocs, not Writes."""
    sess = "sess-heredoc"
    r1 = _run(_bash_event(sess, _heredoc("del_v1.ps1", DELETE_V1)), tmp_path)
    r2 = _run(_bash_event(sess, _heredoc("del_v2.ps1", DELETE_V2, marker="PS")), tmp_path)
    r3 = _run(_bash_event(sess, _heredoc("del_v3.ps1", DELETE_V3, quoted=False)), tmp_path)
    assert r1.stdout.strip() == ""
    assert r2.stdout.strip() == ""
    assert "TESTED JIG" in r3.stdout, f"heredoc-written third variant should nudge, got {r3.stdout!r}"


def test_append_redirect_and_unquoted_marker_are_seen():
    got = mod.heredoc_writes(_heredoc("x.sh", DELETE_V1, quoted=False, op=">>"))
    assert [p for p, _ in got] == ["x.sh"]


def test_heredoc_into_non_script_ignored():
    assert mod.heredoc_writes(_heredoc("notes.md", DELETE_V1)) == []


def test_stdin_heredoc_without_a_file_is_ignored():
    """`python3 - <<PY ... PY` writes no file; it must not be counted as authoring a script."""
    assert mod.heredoc_writes("python3 - <<'PY'\nprint(1)\nPY\n") == []


def test_redirect_inside_the_body_is_not_taken_as_the_target():
    cmd = "cat > real.ps1 <<'EOS'\nrobocopy $empty $root /MIR > decoy.ps1\nEOS\n"
    assert [p for p, _ in mod.heredoc_writes(cmd)] == ["real.ps1"]


def test_broken_stdin_exits_zero():
    r = subprocess.run([sys.executable, str(HOOK)], input="not json",
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0
    assert r.stdout.strip() == ""
