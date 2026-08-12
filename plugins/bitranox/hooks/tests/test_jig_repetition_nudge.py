"""Tests for jig-repetition-nudge.

Two load-bearing cases, and they pull in opposite directions.

The NEGATIVE one: a hook that fires on any two scripts of the same language would be noise, and
noise gets ignored, which is how the catalogue hook's silence went unnoticed for six variants.

The POSITIVE one, which the copy-only design failed: three scripts that solve ONE job by
successively DIFFERENT means. `test_rewrites_score_below_the_copy_threshold` measures that they do
not look alike, so the shingle channel provably cannot see them - and the lineage must still be
handed to the model, via the topic channel and the ledger.
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

# ---------------------------------------------------------------------------------------------
# The REWRITE lineage: excerpts of the three real scripts (delwinold -> finishdel -> delrobo) that
# solved one job - delete C:\Windows.old - three different ways in one session. Kept faithful to
# the originals rather than retyped as look-alikes, because the whole point is how little they
# share: a fixture written to "look like a rewrite" would test the fixture, not the hook.
# ---------------------------------------------------------------------------------------------

REWRITE_1 = """# Delete C:\\Windows.old WITHOUT touching permissions anywhere.
#
# Windows.old is largely HARD LINKS into the live installation. Deleting a link is safe - it only
# decrements the link count. REWRITING permissions through one is not.
$ErrorActionPreference = 'Continue'
$root = 'C:\\Windows.old'
$blockers = @()
foreach ($item in Get-ChildItem $root -Recurse -Force -EA SilentlyContinue) {
    try { Remove-Item $item.FullName -Force -Recurse -EA Stop }
    catch { $blockers += $item.FullName }
}
Write-Host ("blockers : " + $blockers.Count)
"""

REWRITE_2 = """# Clear the residue. The remaining files sit at paths longer than MAX_PATH (260), which is why
# Remove-Item could not delete them - their attributes are plain Archive, so this is NOT the
# read-only trap and no permission change is warranted.
#
# robocopy /MIR from an EMPTY directory handles long paths natively and only deletes.
$ErrorActionPreference = 'Continue'
$root = 'C:\\Windows.old'
if (-not (Test-Path $root)) { Write-Host "RESULT=ALREADY-GONE"; exit 0 }
$before = @(Get-ChildItem $root -Recurse -File -Force -EA SilentlyContinue).Count
$scratch = Join-Path $env:TEMP 'mtdir'
New-Item -ItemType Directory -Path $scratch -Force | Out-Null
& robocopy.exe $scratch $root /MIR /R:0 /W:0 /NFL /NDL /NJH
Write-Host ("files before : " + $before)
"""

REWRITE_3 = """# Delete Windows.old the way the skill actually prescribes: robocopy /MIR from an empty directory,
# multithreaded, for the BULK - not a per-file Remove-Item loop. On 68000 the per-file loop took
# ~73 min and still left residue. This run is the timed comparison.
$ErrorActionPreference = 'Continue'
$root = 'C:\\Windows.old'
# A stale mounted WIM inside the tree must be discarded first.
$mounts = & dism.exe /English /Get-MountedImageInfo 2>&1 | Select-String 'Mount Dir'
$stamp = Get-Date
$pool = Join-Path $env:TEMP ([guid]::NewGuid())
New-Item -ItemType Directory -Path $pool -Force | Out-Null
& robocopy.exe $pool $root /MIR /MT:32 /R:0 /W:0 /NP /NFL /NDL /NJH /NJS
Write-Host ("elapsed : " + ((Get-Date) - $stamp).TotalMinutes)
"""

# The lineage's read-only sibling. It is part of the fixture because it was part of the real
# session: a rewrite lineage is not three scripts in a row, it is a job worked on from several
# angles, and the group the filter finds is made of BOTH kinds.
PROBE_DELETE = """# Is the delete progressing? Free space is the honest signal here.
$free = (Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='C:'").FreeSpace
Write-Host ("free GB : " + [math]::Round($free / 1GB, 2))
Write-Host ("present : " + (Test-Path 'C:\\Windows.old'))
"""

# A read-only probe about a DIFFERENT job, for the tests that must not be about the delete lineage.
PROBE_WINDOWS_UPDATE = """# What state is Windows Update in right now?
$svc = Get-Service wuauserv
Write-Host ("wuauserv : " + $svc.Status + " " + $svc.StartType)
Write-Host ("pending  : " + (Test-Path 'HKLM:\\SOFTWARE\\Microsoft\\WindowsUpdate\\Auto Update'))
"""


# ------------------------------------------------------------------------------- pure: shingles

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


def test_rewrites_score_below_the_copy_threshold():
    """The measurement that motivates the topic channel: rewrites do not look alike.

    RED evidence, not an assumption. If this ever starts failing, the shingle channel alone would
    have caught the lineage and the topic channel would be carrying less than it claims.
    """
    sh = [mod.shingles(t) for t in (REWRITE_1, REWRITE_2, REWRITE_3)]
    scores = [mod.similarity(sh[0], sh[1]), mod.similarity(sh[0], sh[2]), mod.similarity(sh[1], sh[2])]
    assert max(scores) < mod.SIMILARITY, f"rewrites looked like copies: {scores}"


# -------------------------------------------------------------------------------- pure: purpose

def _big_script(seed, lines=400):
    """A script far larger than SHINGLE_LIMIT, so the stored sample is a strict subset."""
    body = "\n".join(f"$v{i} = Get-Item 'C:\\p{i}'; Write-Host $v{i}.Length" for i in range(lines))
    return f"# Delete the staging tree, attempt {seed}.\n$root = 'C:\\Windows.old'\n{body}\nrobocopy $e $root /MIR\n"


def test_a_near_copy_is_still_recognised_when_it_exceeds_the_shingle_limit():
    """Both sides of a comparison must use the same sketch.

    Scoring a live FULL shingle set against a stored TRUNCATED one inflates the union without the
    intersection, so a real near-copy scores low and slips through - measured on the real corpus as
    delrobo/delrobo_xj falling from 0.298 to 0.234, under the threshold.
    """
    a, b = mod.shingles(_big_script(1)), mod.shingles(_big_script(2))
    assert len(a) > mod.SHINGLE_LIMIT, "fixture too small to exercise truncation"
    stored = {"s": [list(x) for x in sorted(mod.sketch(b))]}
    assert mod._shares_text(a, stored), "a near-copy stopped registering once it was truncated"


def test_sketch_is_bounded_and_deterministic():
    sh = mod.shingles(_big_script(3))
    assert len(mod.sketch(sh)) == mod.SHINGLE_LIMIT
    assert mod.sketch(sh) == mod.sketch(sh)
    assert mod.sketch(sh) <= sh


def test_purpose_prefers_the_first_comment_line():
    assert mod.purpose(REWRITE_1).startswith("Delete C:\\Windows.old WITHOUT touching permissions")


def test_purpose_skips_the_shebang():
    text = "#!/usr/bin/env bash\n# Wait for Windows.old to be gone.\nLOG=\"$1\"\n"
    assert mod.purpose(text) == "Wait for Windows.old to be gone."


def test_purpose_skips_boilerplate_preamble():
    """$ErrorActionPreference identifies nothing, and every script that opens with it would
    otherwise read as the same job as every other one."""
    text = "$ErrorActionPreference='Continue'\nWrite-Host (Test-Path 'C:\\Windows.old')\n"
    assert "ErrorActionPreference" not in mod.purpose(text)
    assert "Windows.old" in mod.purpose(text)


def test_purpose_falls_back_to_opening_code_when_there_is_no_comment():
    assert "Get-NetAdapter" in mod.purpose(UNRELATED)


def test_purpose_is_truncated():
    assert len(mod.purpose("# " + "x" * 500)) <= mod.PURPOSE_WIDTH


def test_purpose_of_empty_text_is_empty():
    assert mod.purpose("") == ""


# --------------------------------------------------------------------------------- pure: topic

def test_name_tokens_link_a_del_family():
    """delwinold / delrobo / delsafe share no whole word and no 4-character prefix."""
    a, b, c = (mod.name_tokens(n) for n in ("delwinold.ps1", "delrobo.ps1", "delsafe.ps1"))
    assert a & b and b & c and a & c, f"del-family did not link: {a} {b} {c}"


def test_name_tokens_ignore_a_trailing_digit():
    """delsafe2 is the second attempt at delsafe's job, not a different topic."""
    assert mod.name_tokens("delsafe.ps1") <= mod.name_tokens("delsafe2.ps1")


def test_unrelated_names_do_not_link():
    assert not (mod.name_tokens("delrobo.ps1") & mod.name_tokens("netadapters.ps1"))


def test_topic_tokens_ignore_the_body():
    """The body is where two solutions to one job diverge most - that is what a rewrite IS."""
    said = "# Delete Windows.old safely.\n"
    assert (mod.topic_tokens("del.ps1", mod.purpose(said + "Remove-Item -Recurse\n"))
            == mod.topic_tokens("del.ps1", mod.purpose(said + "& robocopy.exe $a $b /MIR\n")))


def test_topic_tokens_link_the_real_rewrites():
    pairs = [mod.topic_tokens(n, mod.purpose(t)) for n, t in
             (("delwinold.ps1", REWRITE_1), ("finishdel.ps1", REWRITE_2), ("delrobo.ps1", REWRITE_3))]
    assert pairs[0] & pairs[2], "the lineage's endpoints share no topic token"


# --------------------------------------------------------------- pure: what counts as one JOB
#
# These four came out of replaying 2689 script writes from 98 real sessions. Every fixture below
# is synthetic; the corpus supplied the SHAPES, never any text.


def test_the_same_file_spelled_two_ways_is_one_file():
    """A model writes `tests/t.py` from the repo root and `/repo/tests/t.py` a minute later.

    The ledger's path key exists so that iterating on one script is not counted as writing another
    variant of it, and a literal string key silently loses that whenever the spelling changes.
    """
    assert mod.same_file("tests/t.py", "/home/u/repo/tests/t.py")
    assert mod.same_file("del.ps1", "C:\\scratch\\del.ps1")
    assert mod.same_file("./a/b.sh", "a/b.sh")
    assert mod.same_file("/tmp/a.ps1", "/tmp/a.ps1")


def test_two_files_sharing_a_basename_in_different_directories_are_not_one_file():
    """The negative control. Porting one file into two repos BY HAND is a repeated job, and
    folding those two into one would hide exactly the case worth reporting."""
    assert not mod.same_file("/repo/a/tests/t.py", "/repo/b/tests/t.py")
    assert not mod.same_file("src/conftest.py", "tests/conftest.py")
    assert not mod.same_file("", "/tmp/a.ps1")


def test_a_numbered_name_is_the_same_script_again():
    """`probe.ps1` then `probe2.ps1` says "attempt 2" in the filename itself."""
    assert mod.numbered_retry("probe.ps1", "probe2.ps1")
    assert mod.numbered_retry("/tmp/diag3.ps1", "/tmp/diag7.ps1")
    assert mod.numbered_retry("check_it.py", "check_it2.py")


def test_a_numbered_name_does_not_link_unrelated_scripts():
    assert not mod.numbered_retry("probe2.ps1", "verify2.ps1")
    assert not mod.numbered_retry("probe.ps1", "probe.ps1"), "one file is not two attempts"
    assert not mod.numbered_retry("p1.py", "p2.py"), "a two-character stem is too generic"


def test_a_pytest_module_is_not_a_one_off_script():
    """The hook asks for "a TESTED JIG - a script with pytest cases", so a test suite is the END
    STATE it wants. Counting test modules as repeated jobs nudges the one behaviour it asks for."""
    assert mod.is_test_suite_file("test_thing.py")
    assert mod.is_test_suite_file("/repo/tests/anything.py")
    assert mod.is_test_suite_file("conftest.py")


def test_a_one_off_probe_that_merely_ends_in_test_is_still_a_script():
    """Real throwaway probes get called `rule_test.py`; suppressing those would lose the repeats
    this hook exists for. Only the `test_` prefix pytest collects on, and only for .py."""
    assert not mod.is_test_suite_file("rule_test.py")
    assert not mod.is_test_suite_file("test1.sh")
    assert not mod.is_test_suite_file("test_harness.ps1")


def test_distinct_jobs_counts_jobs_not_paths():
    group = ["/repo/probe.py", "probe.py", "/repo/tests/test_probe.py", "/repo/probe2.py"]
    assert mod.distinct_jobs(group) == ["/repo/probe.py", "/repo/probe2.py"]


# --------------------------------------------------------------------------- pure: changes_state

def test_changes_state_sees_a_delete():
    for text in (REWRITE_1, REWRITE_2, REWRITE_3, DELETE_V1):
        assert mod.changes_state(text), text[:40]


def test_changes_state_is_false_for_a_read_only_probe():
    assert not mod.changes_state(PROBE_DELETE)
    assert not mod.changes_state(PROBE_WINDOWS_UPDATE)
    assert not mod.changes_state(UNRELATED)


# ------------------------------------------------------------------------------- pure: budgets

def _spent(change=0, observe=0, last_observe=None):
    state = {"n_change": change, "n_observe": observe}
    if last_observe is not None:
        state["last_observe"] = last_observe
    return state


def test_a_spent_observe_budget_still_leaves_a_change_slot():
    """The partition that made the difference: read-only repeats fill a session and would
    otherwise spend the budget the destructive lineage needs."""
    state = _spent(observe=mod.OBSERVE_NUDGE_CAP, last_observe=90)
    assert not mod.budget_allows(state, "observe", 91)
    assert mod.budget_allows(state, "change", 91)


def test_the_change_track_stops_at_its_cap():
    assert mod.budget_allows(_spent(change=mod.CHANGE_NUDGE_CAP - 1), "change", 50)
    assert not mod.budget_allows(_spent(change=mod.CHANGE_NUDGE_CAP), "change", 50)


def test_the_observe_track_waits_for_its_cooldown():
    state = _spent(observe=1, last_observe=10)
    assert not mod.budget_allows(state, "observe", 10 + mod.OBSERVE_COOLDOWN - 1)
    assert mod.budget_allows(state, "observe", 10 + mod.OBSERVE_COOLDOWN)


def test_should_nudge_needs_fresh_scripts():
    """A group that grew by one script is the SAME finding again, not a new one."""
    group = ["a.ps1", "b.ps1", "c.ps1", "d.ps1"]
    assert mod.should_nudge(group, set(), {}, "change", 4)
    assert not mod.should_nudge(group, {"a.ps1", "b.ps1", "c.ps1"}, {}, "change", 4)


def test_should_nudge_needs_three_scripts():
    assert not mod.should_nudge(["a.ps1", "b.ps1"], set(), {}, "change", 2)


# ------------------------------------------------------------------------------- pure: message

def _entry(name, said, mutates=False):
    return {"p": "/scratch/" + name, "d": said, "m": mutates}


def test_build_message_hands_over_the_ledger_with_purposes():
    entries = [_entry("probe.ps1", "Read the CBS log"), _entry("delrobo.ps1", "Delete Windows.old", True)]
    msg = mod.build_message(["/scratch/delrobo.ps1"], entries, 1)
    assert "probe.ps1 - Read the CBS log" in msg
    assert "delrobo.ps1 [changes state] - Delete Windows.old" in msg


def test_build_message_asks_the_model_to_judge_and_offers_a_subagent():
    msg = mod.build_message(["/scratch/a.ps1"], [_entry("a.ps1", "x")], 1)
    assert "JUDGE" in msg
    assert "subagent" in msg
    assert "TESTED JIG" in msg
    assert "ignore this and carry on" in msg, "a loose filter must say what to do when it is wrong"


def test_build_message_says_which_nudge_this_is():
    """Identical repeated nudges get tuned out; each one has to look different from the last."""
    entries = [_entry("a.ps1", "x")]
    assert "first time" in mod.build_message(["/scratch/a.ps1"], entries, 1)
    assert "nudge 4" in mod.build_message(["/scratch/a.ps1"], entries, 4)


def test_build_message_bounds_the_ledger_it_hands_over():
    entries = [_entry(f"s{i}.ps1", "purpose " + "y" * 200) for i in range(200)]
    msg = mod.build_message(["/scratch/s199.ps1"], entries, 1)
    assert "s0.ps1" not in msg, "the whole session is not the recent context"
    assert len(msg) < 5000


# ---------------------------------------------------------------------------------- subprocess

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


def _context(result):
    if not result.stdout.strip():
        return ""
    return json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]


def test_state_is_isolated_to_the_given_home(tmp_path):
    """Guards the isolation itself: the state file must land under the redirected HOME."""
    _run(_write_event("sess-iso", "/tmp/a.ps1", DELETE_V1), tmp_path)
    assert list(tmp_path.rglob("*.jig-ledger.json")), "state did not land under the test HOME"


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


def test_rewrite_lineage_nudges_although_it_does_not_look_like_a_copy(tmp_path):
    """The regression this design exists for.

    Three real scripts, one job, three different means. test_rewrites_score_below_the_copy_threshold
    proves the shingle channel cannot see them; this proves the hook speaks up anyway.
    """
    sess = "sess-rewrite"
    quiet = [_run(_write_event(sess, path, body), tmp_path) for path, body in (
        ("/scratch/delwinold.ps1", REWRITE_1),
        ("/scratch/delprogress.ps1", PROBE_DELETE),
        ("/scratch/finishdel.ps1", REWRITE_2))]
    ctx = _context(_run(_write_event(sess, "/scratch/delrobo.ps1", REWRITE_3), tmp_path))
    assert [r.stdout.strip() for r in quiet] == ["", "", ""], "nudged before there was a pattern"
    assert ctx, "the rewrite lineage never reached the model"
    assert "delrobo.ps1" in ctx and "delwinold.ps1" in ctx and "finishdel.ps1" in ctx


def test_the_nudge_carries_scripts_the_lexical_filter_did_not_group(tmp_path):
    """The ledger, not the trigger group, is the payload.

    The lexical filter cannot see every member of a rewrite lineage - that is the premise of the
    whole design - so the model has to be shown the session's other scripts to judge for itself.
    """
    sess = "sess-ledger"
    for path, body in (("/scratch/wuerr.ps1", UNRELATED),
                       ("/scratch/delwinold.ps1", REWRITE_1),
                       ("/scratch/delprogress.ps1", PROBE_DELETE),
                       ("/scratch/finishdel.ps1", REWRITE_2)):
        _run(_write_event(sess, path, body), tmp_path)
    ctx = _context(_run(_write_event(sess, "/scratch/delrobo.ps1", REWRITE_3), tmp_path))
    trigger, _, ledger = ctx.partition("Scripts written this session")
    assert "wuerr.ps1" not in trigger, "the unrelated script should not be in the lexical group"
    assert "wuerr.ps1" in ledger, "the ledger must carry it anyway, for the model to judge"


def test_does_not_re_nudge_without_fresh_scripts(tmp_path):
    """One more variant of an already-reported lineage is the same finding, not a new one."""
    sess = "sess-once"
    for path, body in (("/tmp/a.ps1", DELETE_V1), ("/tmp/b.ps1", DELETE_V2)):
        _run(_write_event(sess, path, body), tmp_path)
    first = _run(_write_event(sess, "/tmp/c.ps1", DELETE_V3), tmp_path)
    second = _run(_write_event(sess, "/tmp/d.ps1", DELETE_V1 + "\n$z = 9\n"), tmp_path)
    assert "TESTED JIG" in first.stdout
    assert second.stdout.strip() == "", "must not repeat a finding that gained one script"


def test_read_only_repeats_are_rate_limited(tmp_path):
    """A session's probes repeat constantly. They may speak once, not every third script."""
    sess = "sess-observe"
    fired = 0
    for i in range(9):
        body = PROBE_WINDOWS_UPDATE + f"\nWrite-Host 'sample {i}'\n"
        if _context(_run(_write_event(sess, f"/scratch/wustate{i}.ps1", body), tmp_path)):
            fired += 1
    assert fired == 1, f"read-only repeats nudged {fired} times in 9 scripts"


def test_a_session_of_probes_leaves_the_change_budget_intact(tmp_path):
    """The partition, end to end: probes first, then the rewrite lineage still gets through.

    This is the failure the single-budget design had: replaying the real session, one shared
    clock-paced budget reached the destructive lineage in 0% of unperturbed runs, this one in 100%.
    """
    sess = "sess-partition"
    for i in range(9):
        _run(_write_event(sess, f"/scratch/wustate{i}.ps1",
                          PROBE_WINDOWS_UPDATE + f"\nWrite-Host 'sample {i}'\n"), tmp_path)
    for path, body in (("/scratch/delwinold.ps1", REWRITE_1),
                       ("/scratch/delprogress.ps1", PROBE_DELETE),
                       ("/scratch/finishdel.ps1", REWRITE_2)):
        _run(_write_event(sess, path, body), tmp_path)
    ctx = _context(_run(_write_event(sess, "/scratch/delrobo.ps1", REWRITE_3), tmp_path))
    assert ctx, "the change track was starved by read-only repeats"


# ------------------------------------------------------------- cross-session behaviour, measured
#
# The hook was originally tuned on ONE session. These three encode what replaying 98 sessions
# (2689 script writes) said about the other 97. Fixtures are synthetic - the corpus supplied the
# shapes and the counts, never any text.

MODULE_UNDER_TEST = """# Ledger of the things this tool has seen, with a bounded window.
def record(entry, entries):
    entries.append(entry)
    return entries[-200:]
"""


def _suite_case(name, case):
    return f'''# Tests for the ledger {name}.
def test_{case}():
    assert record({{"p": "x"}}, []) == [{{"p": "x"}}]
'''


def test_a_module_and_its_test_suite_stay_silent(tmp_path):
    """The single largest false positive across the corpus, and the most self-defeating.

    This hook's remedy is "build it once as a TESTED JIG - a script with pytest cases", so a
    session writing a module and then filling up tests/ is doing precisely what it asks for.
    Test-suite files are a quarter of all script writes measured, and every session the pytest
    rule silenced had been nudged for writing a module beside its tests.
    """
    sess = "sess-suite"
    written = [_run(_write_event(sess, "/repo/src/ledger.py", MODULE_UNDER_TEST), tmp_path)]
    for name, case in (("window", "the_window_is_bounded"), ("io", "a_reread_round_trips"),
                       ("bounds", "an_empty_ledger_is_not_an_error")):
        written.append(_run(_write_event(sess, f"/repo/tests/test_ledger_{name}.py",
                                         _suite_case(name, case)), tmp_path))
    written.append(_run(_write_event(sess, "/repo/tests/conftest.py",
                                     "# Put src on sys.path.\nimport sys\n"), tmp_path))
    assert [r.stdout.strip() for r in written] == [""] * 5, "nudged a session for writing tests"


NUMBERED_PROBES = ("# Which shells does the runner have?\nls -1 /bin/*sh\n",
                   "# Does the array slice behave?\narr=(a b c); echo \"${arr[@]:1}\"\n",
                   "# Is the trap inherited by the subshell?\ntrap 'echo bye' EXIT; (exit 3)\n")


def test_a_numbered_family_nudges_although_the_names_share_one_short_token(tmp_path):
    """The other side of the same coin: silence where the repetition is undeniable.

    `net1.sh` .. `net3.sh` reduce to ONE name token, and the topic channel needs two, so a family
    that says "attempt N" in its own filename went unreported. Measured: two corpus sessions that
    wrote nine `testN.sh` and three `*_testN.py` got no nudge at all before this channel.
    """
    sess = "sess-numbered"
    quiet = [_run(_write_event(sess, f"/scratch/net{i}.sh", body), tmp_path)
             for i, body in enumerate(NUMBERED_PROBES[:2], 1)]
    third = _run(_write_event(sess, "/scratch/net3.sh", NUMBERED_PROBES[2]), tmp_path)
    assert [r.stdout.strip() for r in quiet] == ["", ""]
    ctx = _context(third)
    assert ctx, "a numbered retry family never reached the model"
    assert "net1.sh" in ctx and "net3.sh" in ctx


def test_respelling_one_path_does_not_make_it_a_second_variant(tmp_path):
    """Two scripts plus a re-write of one of them is two jobs, not three.

    The ledger is keyed by path so that iterating on a file is not counted as authoring another
    variant; writing it once relative and once absolute defeated that. Measured: 133 of 2689 real
    script writes respell a path already in the ledger.
    """
    sess = "sess-respelt"
    body = "# Audit the staging tree for leftovers.\nfind /srv/staging -type f | wc -l\n"
    results = [_run(_write_event(sess, "/work/audit_files.sh", body), tmp_path),
               _run(_write_event(sess, "audit_files.sh", body + "echo done\n"), tmp_path),
               _run(_write_event(sess, "/work/audit_files2.sh", body + "echo again\n"), tmp_path)]
    assert [r.stdout.strip() for r in results] == ["", "", ""], "counted one file as two variants"


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


def test_utf8_content_survives_the_round_trip(tmp_path):
    """A script full of non-ASCII must neither crash the hook nor mangle its state."""
    sess = "sess-utf8"
    body = "# Loesche C:\\Windows.old - Zugriff verweigert, \u00fcberpr\u00fcfen \u2713 \u4e2d\u6587\n" + REWRITE_1
    for i in range(3):
        r = _run(_write_event(sess, f"/scratch/loeschen{i}.ps1", body + f"\n$i = {i}\n"), tmp_path)
        assert r.returncode == 0, r.stderr[-500:]
    assert list(tmp_path.rglob("*.jig-ledger.json"))


def test_a_corrupt_state_file_does_not_wedge_the_hook(tmp_path):
    sess = "sess-corrupt"
    _run(_write_event(sess, "/tmp/a.ps1", DELETE_V1), tmp_path)
    for stale in tmp_path.rglob("*.jig-ledger.json"):
        stale.write_text("{not json at all", encoding="utf-8")
    r = _run(_write_event(sess, "/tmp/b.ps1", DELETE_V2), tmp_path)
    assert r.returncode == 0
    assert r.stdout.strip() == ""


# ------------------------------------------------------------------------------------ heredocs

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
