"""Tests for factedit.py - read a memory fact, recompose it through the engine. ASCII only.

No test reads or writes a real memory store, but the PARSER is never faked. The engine dir built
on tmp_path holds the INSTALLED uuid_store and capture_constraints, copied verbatim; only the
write path is a stand-in, and only because it is the one piece that would touch a real store.

That split is the lesson this file paid for. A hand-written uuid_store used to stand in for the
parser, and its Pointer kept a `source` field the engine dropped in 5.300.0 - so 38 tests proved
factedit agreed with a parser that no longer existed, while every verb raised AttributeError on
every real fact. A copy of a dependency's SHAPE is a second source of truth, and the copy is the
one the suite believes.

Pure judging (judge_hook) still takes a fake EngineRules: that is the tool's own injection seam,
a set of predicates, not a borrowed grammar that can silently disagree with the engine.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import factedit as FE  # tests/conftest.py puts the skill dir on sys.path
import pytest

# Resolved from the imported module, never a hard-coded layout: the tool sits at the skill
# root here and in a tools/ dir in the personal toolbox it came from, and a path constant
# would silently point at nothing after a move - which reads as the CLI exiting 2.
TOOL = Path(FE.__file__).resolve()


# ---- the engine surface: injected rules for pure judging, the real modules for parsing ---------

def fake_rules(**over) -> FE.EngineRules:
    """An EngineRules with the shipped 350/500 numbers and simple stand-in predicates.

    Only for judge_hook, which is pure given its rules. Nothing here parses a pointer.
    """
    def parse_index(text):
        return "", []

    base = {
        "soft_max": 350, "hard_max": 500, "escalate_at": 2,
        "over_soft": lambda h: len(h) > 350,
        "over_hard": lambda h: len(h.strip()) > 500,
        "missing_trigger": lambda h: not h.lower().startswith("when"),
        "advise": lambda h, b: [],
        "recurrence": lambda b: None,
        "parse_index": parse_index,
        "engine_path": Path("/fake/memory_engine.py"),
    }
    base.update(over)
    return FE.EngineRules(**base)


# The parser modules are COPIED from the installed engine, never re-implemented here. uuid_store
# owns the pointer grammar and the caps; capture_constraints owns the advisories; uuid_store
# imports self_improve_signals, and all three are stdlib-only beyond each other, so this is the
# whole closure. Re-implementing any of them would recreate the divergence in the docstring above.
_PARSER_MODULES = ("uuid_store.py", "capture_constraints.py", "self_improve_signals.py")

# The one deliberate stand-in: the WRITE path. It records the argv it was handed and exits 0, so a
# test can assert WHICH verb and files factedit chose without a real engine touching a real store.
RECORDING_ENGINE = '''
import sys
open(sys.argv[0] + ".called", "a", encoding="utf-8").write(repr(sys.argv[1:]) + "\\n")
print("fake-engine-ok")
'''


def make_engine_dir(tmp_path: Path) -> Path:
    """An engine dir: the REAL parser modules, plus a write path that only records its argv.

    Skips rather than falling back to a hand-written parser. A skip is visible in the run summary;
    a stand-in grammar is not, and that is the trade this file already lost once.
    """
    try:
        src = FE.find_engine().parent
    except FE.EngineNotFound:
        pytest.skip("no installed memory engine - these tests bind to the real parser by design")
    d = tmp_path / "hooks"
    d.mkdir(parents=True, exist_ok=True)
    for name in _PARSER_MODULES:
        shutil.copy2(src / name, d / name)
    (d / "memory_engine.py").write_text(RECORDING_ENGINE, encoding="utf-8")
    return d / "memory_engine.py"


def flag_value(argv: list[str], flag: str) -> str | None:
    """The value of `flag` in an engine argv, which carries every value flag as ONE `flag=value`
    item (a separate item starting with '-' would be read by argparse as another option)."""
    assert flag not in argv, f"{flag} travelled as a separate argv item: {argv!r}"
    for item in argv:
        if item.startswith(flag + "="):
            return item[len(flag) + 1:]
    return None


def make_tree(tmp_path: Path, *, pin: bool = False) -> Path:
    """A minimal two-level tree with a store and one fact, so read_fact has something real.

    The anchor carries a CLAUDE.md as well as the store, because that pair is what the engine
    anchors on; a store with no CLAUDE.md above it is not where the engine keeps bodies."""
    anchor = tmp_path / "tree"
    level = anchor / "proj"
    (anchor / ".claude-memory" / "facts").mkdir(parents=True)
    (anchor / "CLAUDE.md").write_text("anchor\n", encoding="utf-8")
    level.mkdir(parents=True)
    meta = "bx:src=session-x" + (" bx:pin" if pin else "")
    (level / "CLAUDE.local.md").write_text(
        "# Memory index\n"
        f"- [A Title](mem:feedback-demo) - When something happens, do the thing. <!-- {meta} -->\n",
        encoding="utf-8")
    (anchor / ".claude-memory" / "facts" / "feedback-demo.md").write_text(
        "---\nname: feedback-demo\n"
        "description: When something happens, do the thing.\n"
        "metadata:\n  type: feedback\n---\n\nThe body prose.\n", encoding="utf-8")
    return level


def over_hard_hook(engine: Path) -> str:
    """A hook the given engine must refuse, sized from ITS cap rather than a remembered 500."""
    return "When " + "x" * (FE.load_rules(engine).hard_max + 50)


def sys_tmp(tmp_path: Path) -> Path:
    """The temp dir run_cli hands the tool, so a stage dir it leaves behind is visible to a test
    instead of piling up in the machine's real /tmp (where 1,600+ of them once accumulated)."""
    d = tmp_path / "systmp"
    d.mkdir(exist_ok=True)
    return d


def run_cli(args, tmp_path):
    """The tool as a real process, so exit codes and stream separation are measured, not asserted."""
    t = str(sys_tmp(tmp_path))
    env = dict(os.environ, TMPDIR=t, TEMP=t, TMP=t)
    env.pop("BITRANOX_MEMORY_ENGINE", None)
    return subprocess.run([sys.executable, str(TOOL)] + args, capture_output=True, text=True,
                          encoding="utf-8", check=False, env=env, cwd=str(tmp_path))


# ---- judge_hook: pure, and the refusal/advisory split -------------------------------------------

def test_a_short_trigger_first_hook_is_accepted_with_nothing_to_say():
    v = FE.judge_hook("When X, do Y.", "body", fake_rules())
    assert v.accepted and v.refusals == [] and v.advisories == []


def test_an_over_hard_cap_hook_is_refused_and_says_the_engine_will_not_truncate():
    v = FE.judge_hook("When " + "x" * 600, "body", fake_rules())
    assert not v.accepted
    assert len(v.refusals) == 1
    assert "refuses rather than truncating" in v.refusals[0]


def test_over_the_soft_cap_is_an_advisory_not_a_refusal():
    """The distinction that matters: a 400-char hook is legal, and must not read as rejected."""
    v = FE.judge_hook("When " + "x" * 400, "body", fake_rules())
    assert v.accepted and v.refusals == []
    assert any("soft cap" in a for a in v.advisories)


def test_a_hook_over_the_hard_cap_reports_only_the_refusal_not_also_the_soft_warning():
    """Both caps fire on a 600-char hook; telling the author to watch the soft cap is noise."""
    v = FE.judge_hook("When " + "x" * 600, "", fake_rules())
    assert not any("soft cap" in a for a in v.advisories)


def test_a_hook_with_no_trigger_phrase_is_flagged():
    v = FE.judge_hook("The thing is broken.", "", fake_rules())
    assert v.accepted
    assert any("trigger phrase" in a for a in v.advisories)


def test_a_recurrence_count_at_the_escalation_threshold_says_do_not_reword():
    v = FE.judge_hook("When X, do Y.", "recurrence: 3", fake_rules(recurrence=lambda b: 3))
    assert any("recurrence 3" in a and "guard or a jig" in a for a in v.advisories)


def test_a_recurrence_below_the_threshold_is_silent():
    v = FE.judge_hook("When X, do Y.", "once", fake_rules(recurrence=lambda b: 1))
    assert v.advisories == []


def test_engine_advisories_are_passed_through():
    v = FE.judge_hook("When X, never do Y.", "", fake_rules(advise=lambda h, b: ["say it positively"]))
    assert "say it positively" in v.advisories


# ---- body frontmatter ---------------------------------------------------------------------------

def test_body_description_reads_the_frontmatter_hook():
    text = "---\nname: s\ndescription: When A, do B.\nmetadata:\n  type: feedback\n---\n\nprose\n"
    assert FE.body_description(text) == "When A, do B."


def test_body_description_is_empty_for_an_unframed_body():
    assert FE.body_description("just prose\n") == ""


# ---- tree walking -------------------------------------------------------------------------------

def test_chain_levels_finds_every_level_narrowest_first(tmp_path):
    (tmp_path / "a" / "b").mkdir(parents=True)
    (tmp_path / "a" / "CLAUDE.local.md").write_text("x", encoding="utf-8")
    (tmp_path / "a" / "b" / "CLAUDE.local.md").write_text("x", encoding="utf-8")
    found = FE.chain_levels(tmp_path / "a" / "b")
    assert found[0] == (tmp_path / "a" / "b").resolve()
    assert (tmp_path / "a").resolve() in found


def test_anchor_dir_refuses_a_tree_with_no_store(tmp_path):
    (tmp_path / "x").mkdir()
    try:
        FE.anchor_dir(tmp_path / "x", _rules_for(tmp_path).resolve_anchor)
    except FE.NoAnchor as exc:
        assert ".claude-memory" in str(exc)
    else:
        raise AssertionError("a dir with no store must not resolve to an anchor")


# ---- read_fact ----------------------------------------------------------------------------------

def _rules_for(tmp_path):
    return FE.load_rules(make_engine_dir(tmp_path))


def test_read_fact_returns_the_pointer_hook_and_the_stored_body(tmp_path):
    level = make_tree(tmp_path)
    fact = FE.read_fact("feedback-demo", level, _rules_for(tmp_path))
    assert fact.level == level.resolve()
    assert fact.title == "A Title"
    assert fact.hook == "When something happens, do the thing."
    assert "The body prose." in fact.body
    assert fact.pin is False


def test_read_fact_reports_the_pin_flag_because_it_selects_the_engine_verb(tmp_path):
    level = make_tree(tmp_path, pin=True)
    fact = FE.read_fact("feedback-demo", level, _rules_for(tmp_path))
    assert fact.pin is True


def test_read_fact_raises_unknown_fact_for_a_slug_no_level_points_at(tmp_path):
    level = make_tree(tmp_path)
    try:
        FE.read_fact("feedback-absent", level, _rules_for(tmp_path))
    except FE.UnknownFact as exc:
        assert "feedback-absent" in str(exc)
    else:
        raise AssertionError("an absent slug must not resolve to a fact")


def test_a_body_whose_description_drifted_from_the_pointer_is_reported(tmp_path):
    level = make_tree(tmp_path)
    body = level.parent / ".claude-memory" / "facts" / "feedback-demo.md"
    body.write_text(body.read_text(encoding="utf-8").replace("do the thing", "do SOMETHING ELSE"),
                    encoding="utf-8")
    fact = FE.read_fact("feedback-demo", level, _rules_for(tmp_path))
    assert not fact.hook_in_sync
    assert "SOMETHING ELSE" in fact.body_description


# ---- engine_argv: the verb comes from the stored pin flag ---------------------------------------

def _fact(pin):
    return FE.Fact(slug="feedback-demo", level=Path("/lvl"), anchor=Path("/anch"),
                   title="A Title", hook="When X, do Y.", pin=pin,
                   body="", body_path=Path("/anch/b.md"))


def test_an_unpinned_fact_uses_add_and_carries_the_stored_title():
    engine = Path("/e/memory_engine.py")
    argv = FE.engine_argv(_fact(False), engine, hook_path=Path("/s/h.txt"),
                          body_path=None, title=None, python="py")
    # str(engine), never the literal: a Path renders with the PLATFORM separator, so a hard-coded
    # "/e/memory_engine.py" passes on POSIX and fails on Windows as "\\e\\memory_engine.py".
    # This test was written in a toolbox that only ever ran on Linux; its first CI run reddened
    # windows-latest alone, which is the shape every Linux-only suite hits on its first Windows cell.
    assert argv[:3] == ["py", str(engine), "add"]
    assert flag_value(argv, "--title") == "A Title"
    assert flag_value(argv, "--hook-file") and flag_value(argv, "--body-file") is None


def test_a_pinned_fact_uses_amend_pinned_because_add_refuses_before_writing():
    argv = FE.engine_argv(_fact(True), Path("/e/memory_engine.py"), hook_path=Path("/s/h.txt"),
                          body_path=Path("/s/b.md"), title=None, python="py")
    assert argv[2] == "amend-pinned"
    # amend-pinned keeps the stored title when none is given; passing one would be a retitle.
    assert flag_value(argv, "--title") is None
    # No provenance flag: the engine has no --source since 5.300.0, so emitting one would build a
    # call it rejects on the argument parser, before ever reaching the store.
    assert "--source" not in argv


def test_the_engine_is_launched_with_a_stable_interpreter_not_uv_s_ephemeral_one():
    """A printed --dry-run command is meant to be pasted, and sys.executable under `uv run` is a
    build venv under the uv cache that is gone by then."""
    chosen = FE.default_python()
    assert not chosen.startswith(str(Path.home() / ".cache" / "uv"))
    assert not FE._in_a_venv(Path(chosen))
    argv = FE.engine_argv(_fact(False), Path("/e/memory_engine.py"), hook_path=Path("/s/h.txt"),
                          body_path=None, title=None)
    assert argv[0] == chosen


def test_default_python_skips_a_venv_interpreter_even_when_it_comes_first_on_path(tmp_path):
    """uv puts its ephemeral venv first on PATH, so which(python3) alone picks exactly the wrong one."""
    venv = tmp_path / "ephemeral"
    (venv / "bin").mkdir(parents=True)
    (venv / "pyvenv.cfg").write_text("home = /usr\n", encoding="utf-8")
    (venv / "bin" / "python3").write_text("#!/bin/sh\n", encoding="utf-8")
    (venv / "bin" / "python3").chmod(0o755)
    real = tmp_path / "usrbin"
    real.mkdir()
    (real / "python3").write_text("#!/bin/sh\n", encoding="utf-8")
    (real / "python3").chmod(0o755)
    # Both fakes are layout only (an empty `#!/bin/sh` script "runs" on POSIX and cannot start on
    # Windows), so the run probe is injected: this test is about the venv skip, nothing else.
    picked = FE.default_python(f"{venv / 'bin'}{os.pathsep}{real}", runs=lambda p: True)
    assert picked == str(real / "python3")


def test_the_hook_always_travels_as_a_file_never_as_an_argument():
    """A real-length hook via --hook "$(cat f)" is a shell command substitution the guard denies."""
    argv = FE.engine_argv(_fact(False), Path("/e/memory_engine.py"), hook_path=Path("/s/h.txt"),
                          body_path=None, title=None, python="py")
    assert flag_value(argv, "--hook") is None


# ---- engine discovery ---------------------------------------------------------------------------

def test_engine_candidates_pick_the_newest_by_mtime_not_by_the_version_in_the_path(tmp_path):
    """5.9.0 sorts AFTER 5.267.3 as text, so a name sort would silently read the older caps."""
    base = tmp_path / ".claude/plugins/cache/bitranox-skills/bitranox"
    for ver, when in (("5.267.3", 20000), ("5.9.0", 10000)):
        d = base / ver / "hooks"
        d.mkdir(parents=True)
        f = d / "memory_engine.py"
        f.write_text("x", encoding="utf-8")
        os.utime(f, (when, when))
    assert FE.engine_candidates(tmp_path)[0].parts[-3] == "5.267.3"


def test_find_engine_refuses_a_path_that_does_not_exist(tmp_path):
    try:
        FE.find_engine(str(tmp_path / "nope.py"))
    except FE.EngineNotFound as exc:
        assert "nope.py" in str(exc)
    else:
        raise AssertionError("a missing engine must refuse, never fall back to stale caps")


def test_find_engine_refuses_rather_than_guessing_when_the_machine_has_none(tmp_path, monkeypatch):
    """Fail closed: a cap check against a remembered number is a green that means nothing.

    The env var is cleared explicitly. find_engine consults it before searching, so without this
    the test asserts "no engine anywhere" while an inherited BITRANOX_MEMORY_ENGINE supplies one,
    and it passes only because the developer's shell happens not to set it.
    """
    monkeypatch.delenv("BITRANOX_MEMORY_ENGINE", raising=False)
    try:
        FE.find_engine(None, home=tmp_path, own=tmp_path / "no-sibling" / "memory_engine.py")
    except FE.EngineNotFound:
        pass
    else:
        raise AssertionError("no engine anywhere must refuse")


def test_load_rules_binds_the_caps_from_the_engine_dir_it_was_given(tmp_path):
    """Assert the BOUNDARY, never the numbers: a test that hardcodes 350/500 is remembering the
    caps, which is the exact thing this tool refuses to do."""
    rules = FE.load_rules(make_engine_dir(tmp_path))
    assert 0 < rules.soft_max <= rules.hard_max
    assert rules.over_hard("x" * (rules.hard_max + 1))
    assert not rules.over_hard("x" * rules.hard_max)
    assert rules.over_soft("x" * (rules.soft_max + 1))


# ---- CLI: exit codes and stream separation, measured by running it ------------------------------

def test_check_exits_0_and_says_accept_for_a_legal_hook(tmp_path):
    eng = make_engine_dir(tmp_path)
    r = run_cli(["check", "--engine", str(eng), "--hook", "When X, do Y."], tmp_path)
    assert r.returncode == 0
    assert "would ACCEPT" in r.stdout


def test_check_exits_1_for_a_hook_the_engine_would_refuse(tmp_path):
    eng = make_engine_dir(tmp_path)
    r = run_cli(["check", "--engine", str(eng), "--hook", over_hard_hook(eng)], tmp_path)
    assert r.returncode == 1
    assert "would REFUSE" in r.stdout


def test_check_json_envelope_has_the_house_shape_and_ok_false_on_a_refusal(tmp_path):
    eng = make_engine_dir(tmp_path)
    r = run_cli(["check", "--engine", str(eng), "--json", "--hook", over_hard_hook(eng)], tmp_path)
    assert r.returncode == 1
    env = json.loads(r.stdout)
    assert set(env) >= {"ok", "command", "data", "skipped"}
    assert env["ok"] is False and env["command"] == "check"
    assert env["data"]["hook_chars"] > env["data"]["hard_max"]
    assert env["skipped"]                      # body advisories were not checked


def test_a_failing_command_returns_2_and_still_emits_json_not_a_traceback(tmp_path):
    """Run the real failure, do not read the code: --json must survive the error path."""
    r = run_cli(["show", "--engine", str(make_engine_dir(tmp_path)), "--json",
                 "--slug", "whatever", "--from", str(tmp_path)], tmp_path)
    assert r.returncode == 2
    assert "Traceback" not in r.stderr
    env = json.loads(r.stdout)
    assert env["ok"] is False and env["error"].startswith("NoAnchor:")


def test_an_absent_slug_is_a_no_answer_exit_1_not_an_error(tmp_path):
    level = make_tree(tmp_path)
    r = run_cli(["show", "--engine", str(make_engine_dir(tmp_path)), "--json",
                 "--slug", "feedback-absent", "--from", str(level)], tmp_path)
    assert r.returncode == 1
    assert json.loads(r.stdout)["error"].startswith("UnknownFact:")


def test_show_prints_the_hook_its_size_and_the_verb_the_engine_needs(tmp_path):
    level = make_tree(tmp_path, pin=True)
    r = run_cli(["show", "--engine", str(make_engine_dir(tmp_path)), "--json",
                 "--slug", "feedback-demo", "--from", str(level)], tmp_path)
    assert r.returncode == 0
    data = json.loads(r.stdout)["data"]
    assert data["pinned"] is True and data["engine_verb"] == "amend-pinned"
    assert data["hook_chars"] == len("When something happens, do the thing.")
    assert data["hook_in_sync"] is True


def test_apply_dry_run_stages_the_files_and_prints_the_command_without_running_it(tmp_path):
    eng = make_engine_dir(tmp_path)
    level = make_tree(tmp_path)
    stage = tmp_path / "stage"
    hookfile = tmp_path / "new.txt"
    hookfile.write_text("When the new thing happens, do the new thing.\n", encoding="utf-8")
    r = run_cli(["apply", "--engine", str(eng), "--json", "--slug", "feedback-demo",
                 "--from", str(level), "--hook-file", str(hookfile),
                 "--stage-dir", str(stage), "--dry-run"], tmp_path)
    assert r.returncode == 0
    data = json.loads(r.stdout)["data"]
    assert (stage / "feedback-demo.hook.txt").is_file()
    assert data["argv"][2] == "add" and data["dry_run"] is True
    assert not (eng.parent / "memory_engine.py.called").exists()


def test_apply_refuses_an_over_cap_hook_before_staging_or_invoking_anything(tmp_path):
    eng = make_engine_dir(tmp_path)
    level = make_tree(tmp_path)
    stage = tmp_path / "stage2"
    hookfile = tmp_path / "long.txt"
    hookfile.write_text(over_hard_hook(eng), encoding="utf-8")
    r = run_cli(["apply", "--engine", str(eng), "--json", "--slug", "feedback-demo",
                 "--from", str(level), "--hook-file", str(hookfile),
                 "--stage-dir", str(stage)], tmp_path)
    assert r.returncode == 1
    assert not stage.exists(), "a refusal must not leave staged files behind"
    assert not (eng.parent / "memory_engine.py.called").exists()


def test_apply_invokes_the_engine_with_the_staged_files(tmp_path):
    eng = make_engine_dir(tmp_path)
    level = make_tree(tmp_path)
    hookfile = tmp_path / "new.txt"
    hookfile.write_text("When the new thing happens, do the new thing.\n", encoding="utf-8")
    r = run_cli(["apply", "--engine", str(eng), "--json", "--slug", "feedback-demo",
                 "--from", str(level), "--hook-file", str(hookfile)], tmp_path)
    assert r.returncode == 0
    called = (eng.parent / "memory_engine.py.called").read_text(encoding="utf-8")
    assert "'add'" in called and "'--hook-file=" in called
    assert json.loads(r.stdout)["data"]["engine_stdout"] == "fake-engine-ok"


def test_apply_with_nothing_to_change_refuses_instead_of_a_no_op_write(tmp_path):
    r = run_cli(["apply", "--engine", str(make_engine_dir(tmp_path)), "--json",
                 "--slug", "feedback-demo", "--from", str(make_tree(tmp_path))], tmp_path)
    assert r.returncode == 2
    assert json.loads(r.stdout)["error"].startswith("BadInput:")


def test_a_body_only_change_records_that_the_hook_was_kept(tmp_path):
    eng = make_engine_dir(tmp_path)
    level = make_tree(tmp_path)
    bodyfile = tmp_path / "b.md"
    bodyfile.write_text("new prose\n", encoding="utf-8")
    r = run_cli(["apply", "--engine", str(eng), "--json", "--slug", "feedback-demo",
                 "--from", str(level), "--body-file", str(bodyfile)], tmp_path)
    assert r.returncode == 0
    data = json.loads(r.stdout)["data"]
    assert data["body_file"] and data["hook_chars"] == len("When something happens, do the thing.")


# ---- fidelity to the LIVE engine ----------------------------------------------------------------

def test_the_live_engine_caps_are_read_not_remembered():
    """If this machine has an engine, the tool must bind ITS numbers, whatever they now are."""
    try:
        rules = FE.load_rules(FE.find_engine())
    except FE.EngineNotFound:
        pytest.skip("no installed memory engine on this machine")
    assert isinstance(rules.soft_max, int) and isinstance(rules.hard_max, int)
    assert 0 < rules.soft_max <= rules.hard_max
    assert rules.over_hard("x" * (rules.hard_max + 1))
    assert not rules.over_hard("x" * rules.hard_max)


def test_read_fact_only_uses_attributes_the_live_pointer_actually_carries(tmp_path):
    """The pointer is parsed by the ENGINE's parser, so a Fact may be built only from fields the
    LIVE Pointer has. The fake in this file cannot prove that and did the opposite: it kept a
    `source` attribute the engine dropped in 5.300.0, so every test here stayed green while `show`
    raised AttributeError on every real fact in the store.
    """
    try:
        rules = FE.load_rules(FE.find_engine())
    except FE.EngineNotFound:
        pytest.skip("no installed memory engine on this machine")
    level = make_tree(tmp_path)
    # Control: the live parser must actually SEE this pointer. Without it a parser that returns
    # nothing would raise UnknownFact and read as an ordinary miss rather than an instrument failure.
    _scope, pointers = rules.parse_index((level / "CLAUDE.local.md").read_text(encoding="utf-8"))
    assert [p.slug for p in pointers] == ["feedback-demo"]
    fact = FE.read_fact("feedback-demo", level, rules)
    assert fact.hook == "When something happens, do the thing."
    assert fact.title == "A Title"


def test_show_runs_end_to_end_against_the_live_engine(tmp_path):
    """The crash was in the verb, not only in read_fact: the renderer read the same dropped field.
    Run the tool as a process against the REAL engine, which is the invocation that was failing.
    """
    try:
        engine = FE.find_engine()
    except FE.EngineNotFound:
        pytest.skip("no installed memory engine on this machine")
    level = make_tree(tmp_path)
    r = run_cli(["show", "--engine", str(engine), "--json",
                 "--slug", "feedback-demo", "--from", str(level)], tmp_path)
    assert "Traceback" not in r.stderr, r.stderr
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout)["data"]["slug"] == "feedback-demo"


def test_body_description_matches_the_engine_on_a_real_stored_fact():
    """The frontmatter reader here mirrors an engine private; pin it to the real file format."""
    store = Path("/media/srv-main-softdev/.claude-memory/facts")
    if not store.is_dir():
        pytest.skip(f"no store at {store} on this machine")
    for path in sorted(store.glob("*.md"))[:5]:
        text = path.read_text(encoding="utf-8")
        assert FE.body_description(text), f"no description parsed from {path.name}"


# ---- the stored type: visible in `show`, changeable only on purpose ------------------------------

def test_engine_argv_forwards_an_explicit_type_for_an_unpinned_fact():
    argv = FE.engine_argv(_fact(False), Path("/e/memory_engine.py"), hook_path=Path("/s/h.txt"),
                          body_path=None, title=None, type_="reference", python="py")
    assert flag_value(argv, "--type") == "reference"


def test_engine_argv_carries_no_type_when_the_caller_asks_for_none():
    # Not an omission to tidy up later: passing a DERIVED type would re-introduce the guess this
    # exists to avoid. No --type means "leave the stored kind alone", which the engine honours.
    argv = FE.engine_argv(_fact(False), Path("/e/memory_engine.py"), hook_path=Path("/s/h.txt"),
                          body_path=None, title=None, python="py")
    assert flag_value(argv, "--type") is None


def test_show_reports_the_stored_type_so_an_amend_can_see_what_it_would_rewrite(tmp_path):
    r = run_cli(["show", "--engine", str(make_engine_dir(tmp_path)), "--json",
                 "--slug", "feedback-demo", "--from", str(make_tree(tmp_path))], tmp_path)
    assert r.returncode == 0
    assert json.loads(r.stdout)["data"]["type"] == "feedback"


def test_apply_forwards_the_type_to_the_engine(tmp_path):
    eng = make_engine_dir(tmp_path)
    level = make_tree(tmp_path)
    body = tmp_path / "b.md"
    body.write_text("new prose\n", encoding="utf-8")
    r = run_cli(["apply", "--engine", str(eng), "--json", "--slug", "feedback-demo",
                 "--from", str(level), "--body-file", str(body), "--type", "reference"], tmp_path)
    assert r.returncode == 0
    called = (eng.parent / "memory_engine.py.called").read_text(encoding="utf-8")
    assert "'--type=reference'" in called


def test_apply_forwards_the_type_on_a_pinned_fact_too(tmp_path):
    # `amend-pinned` is the ONLY route to a pinned fact's kind - `add` refuses a pinned entry - so
    # this must forward rather than refuse. A pinned fact is the one whose classification matters
    # most, and leaving it unreachable freezes a fact captured under the wrong kind for good.
    eng = make_engine_dir(tmp_path)
    level = make_tree(tmp_path, pin=True)
    body = tmp_path / "b.md"
    body.write_text("new prose\n", encoding="utf-8")
    r = run_cli(["apply", "--engine", str(eng), "--json", "--slug", "feedback-demo",
                 "--from", str(level), "--body-file", str(body), "--type", "reference"], tmp_path)
    assert r.returncode == 0
    called = (eng.parent / "memory_engine.py.called").read_text(encoding="utf-8")
    assert "'amend-pinned'" in called and "'--type=reference'" in called


def test_a_type_the_engine_does_not_know_is_refused_before_anything_is_staged(tmp_path):
    r = run_cli(["apply", "--engine", str(make_engine_dir(tmp_path)), "--json",
                 "--slug", "feedback-demo", "--from", str(make_tree(tmp_path)),
                 "--type", "notatype"], tmp_path)
    assert r.returncode == 2
    assert json.loads(r.stdout)["error"].startswith("BadInput:")


# ---- the anchor is the ENGINE's, never merely the nearest store ---------------------------------

def test_a_decoy_store_lower_down_does_not_answer_for_the_real_body(tmp_path):
    level = make_tree(tmp_path)
    (level / "CLAUDE.md").write_text("proj\n", encoding="utf-8")
    (level / ".claude-memory" / "facts").mkdir(parents=True)
    (level / ".claude-memory" / "facts" / "feedback-demo.md").write_text(
        "---\nname: feedback-demo\ndescription: When something ELSE happens.\n"
        "metadata:\n  type: project\n---\n\nDecoy.\n", encoding="utf-8")
    fact = FE.read_fact("feedback-demo", level, _rules_for(tmp_path))
    assert fact.anchor == (tmp_path / "tree").resolve()
    assert fact.type_ == "feedback" and fact.hook_in_sync


# ---- engine argv: a dash-leading value must not become an option -------------------------------

def test_every_value_flag_is_one_argv_item_so_a_dash_leading_title_survives():
    argv = FE.engine_argv(_fact(False), Path("/e/memory_engine.py"), hook_path=Path("/s/h.txt"),
                          body_path=Path("/s/b.md"), title="-draft", type_="project", python="py")
    assert flag_value(argv, "--title") == "-draft"
    assert flag_value(argv, "--proj") and flag_value(argv, "--slug") == "feedback-demo"
    assert flag_value(argv, "--body-file") and flag_value(argv, "--type") == "project"


def _real_engine_env(tmp_path: Path) -> dict:
    """The environment for a run against the REAL engine: every state dir inside tmp_path."""
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    env = dict(os.environ, HOME=str(home), USERPROFILE=str(home),
               XDG_STATE_HOME=str(home / "state"), XDG_CONFIG_HOME=str(home / "config"))
    env.pop("BITRANOX_MEMORY_ENGINE", None)
    return env


def test_a_dash_leading_title_reaches_the_real_engine_as_a_value(tmp_path):
    level = make_tree(tmp_path)
    hookfile = tmp_path / "h.txt"
    hookfile.write_text("When something happens, do the other thing.\n", encoding="utf-8")
    r = subprocess.run([sys.executable, str(TOOL), "apply", "--engine", str(FE.OWN_ENGINE),
                        "--json", "--slug", "feedback-demo", "--from", str(level),
                        "--hook-file", str(hookfile), "--title=-draft"],
                       capture_output=True, text=True, encoding="utf-8", check=False,
                       env=_real_engine_env(tmp_path), cwd=str(tmp_path))
    assert r.returncode == 0, r.stdout + r.stderr
    assert json.loads(r.stdout)["data"]["engine_returncode"] == 0
    assert "[-draft](mem:feedback-demo)" in (level / "CLAUDE.local.md").read_text(encoding="utf-8")


# ---- a pinned fact whose STORED hook is over the cap --------------------------------------------

def _pinned_over_cap(tmp_path: Path, eng: Path) -> Path:
    level = make_tree(tmp_path, pin=True)
    long_hook = over_hard_hook(eng)
    (level / "CLAUDE.local.md").write_text(
        f"# Memory index\n- [A Title](mem:feedback-demo) - {long_hook} <!-- bx:pin -->\n",
        encoding="utf-8")
    return level


def test_a_body_only_edit_of_a_pinned_over_cap_fact_is_not_blocked_by_the_stored_hook(tmp_path):
    eng = make_engine_dir(tmp_path)
    level = _pinned_over_cap(tmp_path, eng)
    body = tmp_path / "b.md"
    body.write_text("new prose\n", encoding="utf-8")
    r = run_cli(["apply", "--engine", str(eng), "--json", "--slug", "feedback-demo",
                 "--from", str(level), "--body-file", str(body)], tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    called = (eng.parent / "memory_engine.py.called").read_text(encoding="utf-8")
    assert "'amend-pinned'" in called and "--hook-file" not in called


def test_an_unpinned_over_cap_stored_hook_is_still_refused(tmp_path):
    """Control: `add` needs the hook re-sent, and the engine refuses it over the cap."""
    eng = make_engine_dir(tmp_path)
    level = make_tree(tmp_path)
    (level / "CLAUDE.local.md").write_text(
        f"# Memory index\n- [A Title](mem:feedback-demo) - {over_hard_hook(eng)}\n",
        encoding="utf-8")
    body = tmp_path / "b.md"
    body.write_text("new prose\n", encoding="utf-8")
    r = run_cli(["apply", "--engine", str(eng), "--json", "--slug", "feedback-demo",
                 "--from", str(level), "--body-file", str(body)], tmp_path)
    assert r.returncode == 1
    assert not (eng.parent / "memory_engine.py.called").exists()


# ---- engine discovery prefers the plugin's own sibling engine -----------------------------------

def test_the_plugins_own_engine_is_found_with_no_home_install(tmp_path, monkeypatch):
    monkeypatch.delenv("BITRANOX_MEMORY_ENGINE", raising=False)
    found = FE.find_engine(None, home=tmp_path)
    assert found == FE.OWN_ENGINE and found.is_file()


def test_the_own_engine_wins_over_a_newer_cache_copy(tmp_path, monkeypatch):
    monkeypatch.delenv("BITRANOX_MEMORY_ENGINE", raising=False)
    cached = tmp_path / ".claude/plugins/cache/bitranox-skills/bitranox/1.0.0/hooks"
    cached.mkdir(parents=True)
    (cached / "memory_engine.py").write_text("x", encoding="utf-8")
    assert FE.find_engine(None, home=tmp_path) == FE.OWN_ENGINE


# ---- errors are typed, exit 2, with the envelope ------------------------------------------------

def test_a_non_utf8_level_is_exit_2_with_json(tmp_path):
    level = make_tree(tmp_path)
    (level / "CLAUDE.local.md").write_bytes(b"# Memory index\n- \xff\n")
    r = run_cli(["show", "--engine", str(make_engine_dir(tmp_path)), "--json",
                 "--slug", "feedback-demo", "--from", str(level)], tmp_path)
    assert r.returncode == 2, r.stdout + r.stderr
    assert "Traceback" not in r.stderr and json.loads(r.stdout)["ok"] is False


def test_a_non_utf8_hook_file_is_exit_2_with_json(tmp_path):
    hookfile = tmp_path / "h.txt"
    hookfile.write_bytes(b"When \xff happens, do it.\n")
    r = run_cli(["check", "--engine", str(make_engine_dir(tmp_path)), "--json",
                 "--hook-file", str(hookfile)], tmp_path)
    assert r.returncode == 2, r.stdout + r.stderr
    assert json.loads(r.stdout)["error"].startswith("BadInput:")


def test_a_bom_in_a_hook_file_is_not_part_of_the_hook(tmp_path):
    hookfile = tmp_path / "h.txt"
    hookfile.write_bytes(b"\xef\xbb\xbfWhen X, do Y.\n")
    r = run_cli(["check", "--engine", str(make_engine_dir(tmp_path)), "--json",
                 "--hook-file", str(hookfile)], tmp_path)
    assert r.returncode == 0
    assert json.loads(r.stdout)["data"]["hook_chars"] == len("When X, do Y.")


def test_an_interpreter_that_cannot_be_launched_is_exit_2_with_json(tmp_path):
    level = make_tree(tmp_path)
    hookfile = tmp_path / "h.txt"
    hookfile.write_text("When X, do Y.\n", encoding="utf-8")
    r = run_cli(["apply", "--engine", str(make_engine_dir(tmp_path)), "--json",
                 "--slug", "feedback-demo", "--from", str(level), "--hook-file", str(hookfile),
                 "--python", str(tmp_path / "no-such-python")], tmp_path)
    assert r.returncode == 2, r.stdout + r.stderr
    assert "Traceback" not in r.stderr and json.loads(r.stdout)["ok"] is False


NO_CHMOD = not hasattr(os, "geteuid") or os.geteuid() == 0


@pytest.mark.skipif(NO_CHMOD, reason="needs a non-root POSIX user for chmod 000")
def test_an_unreadable_level_is_an_error_not_no_such_fact(tmp_path):
    level = make_tree(tmp_path)
    (level / "CLAUDE.local.md").chmod(0)
    try:
        r = run_cli(["show", "--engine", str(make_engine_dir(tmp_path)), "--json",
                     "--slug", "feedback-demo", "--from", str(level)], tmp_path)
    finally:
        (level / "CLAUDE.local.md").chmod(0o644)
    assert r.returncode == 2, r.stdout + r.stderr


@pytest.mark.skipif(NO_CHMOD, reason="needs a non-root POSIX user for chmod 000")
def test_an_unreadable_body_is_an_error_not_an_empty_body(tmp_path):
    level = make_tree(tmp_path)
    body = tmp_path / "tree" / ".claude-memory" / "facts" / "feedback-demo.md"
    body.chmod(0)
    try:
        r = run_cli(["show", "--engine", str(make_engine_dir(tmp_path)), "--json",
                     "--slug", "feedback-demo", "--from", str(level)], tmp_path)
    finally:
        body.chmod(0o644)
    assert r.returncode == 2, r.stdout + r.stderr


# ---- the engine's own exit code: refused is 1, an engine error is 2 -----------------------------

@pytest.mark.parametrize(("code", "expected"), [(1, 1), (2, 2), (3, 2)])
def test_the_engine_exit_code_maps_to_no_or_error(tmp_path, code, expected):
    eng = make_engine_dir(tmp_path)
    eng.write_text(f"import sys\nprint('engine says {code}')\nsys.exit({code})\n",
                   encoding="utf-8")
    level = make_tree(tmp_path)
    hookfile = tmp_path / "h.txt"
    hookfile.write_text("When X, do Y.\n", encoding="utf-8")
    r = run_cli(["apply", "--engine", str(eng), "--json", "--slug", "feedback-demo",
                 "--from", str(level), "--hook-file", str(hookfile)], tmp_path)
    assert r.returncode == expected, r.stdout + r.stderr
    data = json.loads(r.stdout)["data"]
    assert data["engine_returncode"] == code and data["accepted"] is False


def test_level_forces_the_owning_level(tmp_path):
    level = make_tree(tmp_path)
    r = run_cli(["show", "--engine", str(make_engine_dir(tmp_path)), "--json",
                 "--slug", "feedback-demo", "--from", str(tmp_path), "--level", str(level)],
                tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    assert json.loads(r.stdout)["data"]["level"] == str(level.resolve())


def test_hook_and_hook_file_together_are_refused(tmp_path):
    hookfile = tmp_path / "h.txt"
    hookfile.write_text("When X, do Y.\n", encoding="utf-8")
    r = run_cli(["check", "--engine", str(make_engine_dir(tmp_path)), "--json",
                 "--hook", "When A, do B.", "--hook-file", str(hookfile)], tmp_path)
    assert r.returncode == 2
    assert "not both" in json.loads(r.stdout)["error"]


def test_the_python_flag_is_the_interpreter_in_the_engine_command(tmp_path):
    level = make_tree(tmp_path)
    hookfile = tmp_path / "h.txt"
    hookfile.write_text("When X, do Y.\n", encoding="utf-8")
    r = run_cli(["apply", "--engine", str(make_engine_dir(tmp_path)), "--json", "--dry-run",
                 "--slug", "feedback-demo", "--from", str(level), "--hook-file", str(hookfile),
                 "--python", sys.executable], tmp_path)
    assert r.returncode == 0
    assert json.loads(r.stdout)["data"]["argv"][0] == sys.executable


# ---- default_python on a Windows layout ---------------------------------------------------------

def test_default_python_takes_a_python_exe_on_path(tmp_path):
    d = tmp_path / "win"
    d.mkdir()
    exe = d / "python.exe"
    exe.write_text("", encoding="utf-8")
    exe.chmod(0o755)
    # The layout is faked, so the run probe is too: these tests are about WHERE it looks.
    assert FE.default_python(str(d), base_prefix=tmp_path / "nobase",
                             runs=lambda p: True) == str(exe)


def test_default_python_falls_back_to_the_windows_base_prefix_root(tmp_path):
    base = tmp_path / "Python313"
    base.mkdir()
    (base / "python.exe").write_text("", encoding="utf-8")
    assert FE.default_python("", base_prefix=base, runs=lambda p: True) == str(base / "python.exe")


def test_a_base_prefix_interpreter_that_does_not_run_is_not_chosen(tmp_path):
    base = tmp_path / "Python313"
    base.mkdir()
    (base / "python.exe").write_text("", encoding="utf-8")
    assert FE.default_python("", base_prefix=base, runs=lambda p: False) == sys.executable


def test_the_run_probe_accepts_a_real_interpreter_and_refuses_a_file_that_is_not_one(tmp_path):
    """The default seam, on every platform: a real interpreter passes, and an empty file named
    like one - which is_file() and os.access(X_OK) both accept - does not."""
    assert FE.runs_python3(Path(sys.executable)) is True
    fake = tmp_path / ("python.exe" if sys.platform == "win32" else "python3")
    fake.write_text("", encoding="utf-8")
    fake.chmod(0o755)
    assert fake.is_file() and os.access(fake, os.X_OK)
    assert FE.runs_python3(fake) is False
    assert FE.runs_python3(tmp_path / "missing") is False


def test_a_cp1252_stdout_does_not_crash_on_a_non_ascii_hook(tmp_path):
    level = make_tree(tmp_path)
    (level / "CLAUDE.local.md").write_text(
        "# Memory index\n- [A Title](mem:feedback-demo) - When 日本 happens, do it.\n",
        encoding="utf-8")
    env = dict(os.environ, PYTHONIOENCODING="cp1252")
    env.pop("PYTHONUTF8", None)
    env.pop("BITRANOX_MEMORY_ENGINE", None)
    r = subprocess.run([sys.executable, str(TOOL), "show", "--engine",
                        str(make_engine_dir(tmp_path)), "--slug", "feedback-demo",
                        "--from", str(level)],
                       capture_output=True, check=False, env=env, cwd=str(tmp_path))
    assert b"Traceback" not in r.stderr, r.stderr.decode("utf-8", "replace")
    assert r.returncode == 0


# ---- default_python must RUN a candidate before trusting it -------------------------------------

def _shell_interpreter(path: Path, body: str) -> Path:
    path.write_text("#!/bin/sh\n" + body + "\n", encoding="utf-8")
    path.chmod(0o755)
    return path


@pytest.mark.skipif(sys.platform == "win32", reason="builds its interpreters as shell scripts")
def test_default_python_skips_a_store_stub_that_comes_first_on_path(tmp_path):
    """The Windows Store alias is a file named python3.exe/python.exe that exits 9009 printing
    "Python was not found". Measured on a real Windows 11 box: with WindowsApps ahead of the real
    install on PATH, or the real install not on PATH at all (the python.org default), the stub was
    chosen and every live apply died with engine exit 9009. Existing on disk proves nothing."""
    stubs = tmp_path / "WindowsApps"
    stubs.mkdir()
    for name in ("python3.exe", "python.exe"):
        _shell_interpreter(stubs / name, "echo 'Python was not found' >&2\nexit 49")
    real = tmp_path / "Python314"
    real.mkdir()
    exe = _shell_interpreter(real / "python.exe", f'exec "{sys.executable}" "$@"')
    picked = FE.default_python(f"{stubs}{os.pathsep}{real}", base_prefix=tmp_path / "nobase")
    assert picked == str(exe)


@pytest.mark.skipif(sys.platform == "win32", reason="builds its interpreters as shell scripts")
def test_default_python_skips_a_python_2(tmp_path):
    """The probe asks for Python 3, the same bar run-python.sh sets, not merely a zero exit."""
    py2 = tmp_path / "py2"
    py2.mkdir()
    _shell_interpreter(py2 / "python3", "exit 1")  # what `sys.exit(0 if major >= 3 else 1)` does
    real = tmp_path / "real"
    real.mkdir()
    exe = _shell_interpreter(real / "python3", f'exec "{sys.executable}" "$@"')
    assert FE.default_python(f"{py2}{os.pathsep}{real}", base_prefix=tmp_path / "nb") == str(exe)


# ---- the default stage dir: removed after success, kept (and named) after anything else ---------

def test_a_successful_apply_removes_the_default_stage_dir(tmp_path):
    eng = make_engine_dir(tmp_path)
    level = make_tree(tmp_path)
    hookfile = tmp_path / "new.txt"
    hookfile.write_text("When the new thing happens, do the new thing.\n", encoding="utf-8")
    r = run_cli(["apply", "--engine", str(eng), "--json", "--slug", "feedback-demo",
                 "--from", str(level), "--hook-file", str(hookfile)], tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    assert (eng.parent / "memory_engine.py.called").is_file(), "the engine must have run"
    assert list(sys_tmp(tmp_path).glob("factedit-*")) == []
    assert json.loads(r.stdout)["data"]["stage_kept"] is False


def test_a_refused_apply_keeps_the_default_stage_dir_and_names_it(tmp_path):
    eng = make_engine_dir(tmp_path)
    eng.write_text("import sys\nprint('refused')\nsys.exit(1)\n", encoding="utf-8")
    level = make_tree(tmp_path)
    hookfile = tmp_path / "new.txt"
    hookfile.write_text("When the new thing happens, do the new thing.\n", encoding="utf-8")
    r = run_cli(["apply", "--engine", str(eng), "--slug", "feedback-demo",
                 "--from", str(level), "--hook-file", str(hookfile)], tmp_path)
    assert r.returncode == 1, r.stdout + r.stderr
    kept = list(sys_tmp(tmp_path).glob("factedit-*"))
    assert len(kept) == 1 and (kept[0] / "feedback-demo.hook.txt").is_file()
    assert str(kept[0]) in r.stdout, "a kept stage dir is only useful if the reader is told where"


def test_a_launch_failure_keeps_the_default_stage_dir_and_names_it(tmp_path):
    level = make_tree(tmp_path)
    hookfile = tmp_path / "h.txt"
    hookfile.write_text("When X, do Y.\n", encoding="utf-8")
    r = run_cli(["apply", "--engine", str(make_engine_dir(tmp_path)), "--json",
                 "--slug", "feedback-demo", "--from", str(level), "--hook-file", str(hookfile),
                 "--python", str(tmp_path / "no-such-python")], tmp_path)
    assert r.returncode == 2, r.stdout + r.stderr
    kept = list(sys_tmp(tmp_path).glob("factedit-*"))
    assert len(kept) == 1 and (kept[0] / "feedback-demo.hook.txt").is_file()
    assert str(kept[0]) in json.loads(r.stdout)["error"]


def test_a_dry_run_keeps_the_default_stage_dir_its_printed_command_names(tmp_path):
    """Control: the printed command is meant to be pasted, so its files must still exist."""
    eng = make_engine_dir(tmp_path)
    level = make_tree(tmp_path)
    hookfile = tmp_path / "new.txt"
    hookfile.write_text("When the new thing happens, do the new thing.\n", encoding="utf-8")
    r = run_cli(["apply", "--engine", str(eng), "--json", "--slug", "feedback-demo",
                 "--from", str(level), "--hook-file", str(hookfile), "--dry-run"], tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    data = json.loads(r.stdout)["data"]
    assert Path(data["hook_file"]).is_file()
    assert Path(data["stage_dir"]).parent == sys_tmp(tmp_path)


def test_an_explicit_stage_dir_is_never_removed(tmp_path):
    """Control: a --stage-dir the caller named is the caller's, success or not."""
    eng = make_engine_dir(tmp_path)
    level = make_tree(tmp_path)
    stage = tmp_path / "mine"
    hookfile = tmp_path / "new.txt"
    hookfile.write_text("When the new thing happens, do the new thing.\n", encoding="utf-8")
    r = run_cli(["apply", "--engine", str(eng), "--json", "--slug", "feedback-demo",
                 "--from", str(level), "--hook-file", str(hookfile),
                 "--stage-dir", str(stage)], tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    assert (stage / "feedback-demo.hook.txt").is_file()
