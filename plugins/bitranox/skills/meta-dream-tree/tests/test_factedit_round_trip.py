"""factedit: a show/apply round trip stores the body it read, a pinned fact needs an explicit opt-in,
and "no pointer" says where the pointer IS when the chain walk missed it. ASCII only.

Every case drives the tool as a process. The ones that must prove what the STORE ends up holding
run the plugin's own engine against a tree under tmp_path with HOME redirected there too; the rest
use the recording engine from test_factedit, which never writes a store.
"""

import json
import subprocess
import sys
from pathlib import Path

import factedit as FE
from test_factedit import (TOOL, _real_engine_env, make_engine_dir, make_tree, run_cli)


def _body_file(level: Path) -> Path:
    return level.parent / ".claude-memory" / "facts" / "feedback-demo.md"


def _real(args, tmp_path):
    return subprocess.run([sys.executable, str(TOOL)] + args + ["--engine", str(FE.OWN_ENGINE)],
                          capture_output=True, text=True, encoding="utf-8", check=False,
                          env=_real_engine_env(tmp_path), cwd=str(tmp_path))


# ---- show --body prints the body alone on stdout ------------------------------------------------

def test_show_body_puts_only_the_stored_body_on_stdout_and_the_header_on_stderr(tmp_path):
    level = make_tree(tmp_path)
    r = run_cli(["show", "--engine", str(make_engine_dir(tmp_path)), "--body",
                 "--slug", "feedback-demo", "--from", str(level)], tmp_path)
    assert r.returncode == 0, r.stderr
    assert r.stdout == _body_file(level).read_text(encoding="utf-8")
    assert "slug        feedback-demo" in r.stderr


def test_control_show_without_body_keeps_the_header_on_stdout(tmp_path):
    level = make_tree(tmp_path)
    r = run_cli(["show", "--engine", str(make_engine_dir(tmp_path)),
                 "--slug", "feedback-demo", "--from", str(level)], tmp_path)
    assert r.returncode == 0
    assert "slug        feedback-demo" in r.stdout


def test_show_body_then_apply_body_file_leaves_the_stored_body_byte_identical(tmp_path):
    level = make_tree(tmp_path)
    before = _body_file(level).read_text(encoding="utf-8")
    shown = _real(["show", "--body", "--slug", "feedback-demo", "--from", str(level)], tmp_path)
    assert shown.returncode == 0, shown.stderr
    f = tmp_path / "body.md"
    f.write_text(shown.stdout, encoding="utf-8")
    r = _real(["apply", "--slug", "feedback-demo", "--from", str(level), "--body-file", str(f)],
              tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    assert _body_file(level).read_text(encoding="utf-8") == before


def test_a_shown_body_applied_with_a_new_hook_stores_the_new_description(tmp_path):
    level = make_tree(tmp_path)
    shown = _real(["show", "--body", "--slug", "feedback-demo", "--from", str(level)], tmp_path)
    f = tmp_path / "body.md"
    f.write_text(shown.stdout, encoding="utf-8")
    h = tmp_path / "hook.txt"
    h.write_text("When something else happens, do the other thing.\n", encoding="utf-8")
    r = _real(["apply", "--slug", "feedback-demo", "--from", str(level), "--body-file", str(f),
               "--hook-file", str(h)], tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    text = _body_file(level).read_text(encoding="utf-8")
    assert "description: When something else happens, do the other thing.\n" in text, text


# ---- apply refuses a body that carries show's header, and trims blank edges ---------------------

def test_apply_refuses_a_body_file_carrying_the_show_header(tmp_path):
    eng = make_engine_dir(tmp_path)
    level = make_tree(tmp_path)
    f = tmp_path / "b.md"
    f.write_text("slug        feedback-demo\nlevel       /x\n\n---- body ----\nprose\n",
                 encoding="utf-8")
    r = run_cli(["apply", "--engine", str(eng), "--json", "--slug", "feedback-demo",
                 "--from", str(level), "--body-file", str(f)], tmp_path)
    assert r.returncode == 2, r.stdout
    assert json.loads(r.stdout)["error"].startswith("BadInput:")
    assert "---- body ----" in json.loads(r.stdout)["error"]
    assert not (eng.parent / "memory_engine.py.called").exists()


def test_apply_trims_leading_and_trailing_blank_lines_from_the_body_file(tmp_path):
    eng = make_engine_dir(tmp_path)
    level = make_tree(tmp_path)
    stage = tmp_path / "stage"
    f = tmp_path / "b.md"
    f.write_text("\n\n    indented first line\nsecond\n\n\n", encoding="utf-8")
    r = run_cli(["apply", "--engine", str(eng), "--json", "--slug", "feedback-demo",
                 "--from", str(level), "--body-file", str(f), "--stage-dir", str(stage),
                 "--dry-run"], tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    staged = (stage / "feedback-demo.body.md").read_text(encoding="utf-8")
    assert staged == "    indented first line\nsecond\n"


# ---- a pinned fact needs --allow-pinned ---------------------------------------------------------

def test_apply_refuses_a_pinned_fact_without_allow_pinned(tmp_path):
    eng = make_engine_dir(tmp_path)
    level = make_tree(tmp_path, pin=True)
    f = tmp_path / "b.md"
    f.write_text("new prose\n", encoding="utf-8")
    r = run_cli(["apply", "--engine", str(eng), "--json", "--slug", "feedback-demo",
                 "--from", str(level), "--body-file", str(f)], tmp_path)
    assert r.returncode == 2, r.stdout
    env = json.loads(r.stdout)
    assert env["error"].startswith("PinnedFact:") and "--allow-pinned" in env["error"]
    assert not (eng.parent / "memory_engine.py.called").exists()


def test_a_dry_run_of_a_pinned_fact_needs_no_opt_in_since_it_writes_nothing(tmp_path):
    eng = make_engine_dir(tmp_path)
    level = make_tree(tmp_path, pin=True)
    f = tmp_path / "b.md"
    f.write_text("new prose\n", encoding="utf-8")
    r = run_cli(["apply", "--engine", str(eng), "--json", "--slug", "feedback-demo",
                 "--from", str(level), "--body-file", str(f), "--dry-run"], tmp_path)
    assert r.returncode == 0, r.stdout
    assert json.loads(r.stdout)["data"]["engine_verb"] == "amend-pinned"


def test_allow_pinned_takes_a_pinned_fact_through_amend_pinned(tmp_path):
    eng = make_engine_dir(tmp_path)
    level = make_tree(tmp_path, pin=True)
    f = tmp_path / "b.md"
    f.write_text("new prose\n", encoding="utf-8")
    r = run_cli(["apply", "--engine", str(eng), "--json", "--slug", "feedback-demo",
                 "--from", str(level), "--body-file", str(f), "--allow-pinned"], tmp_path)
    assert r.returncode == 0, r.stdout
    assert "'amend-pinned'" in (eng.parent / "memory_engine.py.called").read_text(encoding="utf-8")


# ---- "no pointer" names the level that has it ---------------------------------------------------

def _sibling(level: Path) -> Path:
    sib = level.parent / "other"
    sib.mkdir()
    (sib / "CLAUDE.local.md").write_text("# Memory index\n", encoding="utf-8")
    return sib


def test_a_sibling_owned_fact_is_named_with_the_exact_level_retry(tmp_path):
    level = make_tree(tmp_path)
    sib = _sibling(level)
    r = run_cli(["show", "--engine", str(make_engine_dir(tmp_path)), "--json",
                 "--slug", "feedback-demo", "--from", str(sib)], tmp_path)
    assert r.returncode == 1
    err = json.loads(r.stdout)["error"]
    assert "ancestor" in err and f"--level {level.resolve()}" in err, err


def test_a_descendant_owned_fact_is_named_too(tmp_path):
    level = make_tree(tmp_path)
    (level.parent / "CLAUDE.local.md").write_text("# Memory index\n", encoding="utf-8")
    r = run_cli(["show", "--engine", str(make_engine_dir(tmp_path)), "--json",
                 "--slug", "feedback-demo", "--from", str(level.parent)], tmp_path)
    assert r.returncode == 1
    assert f"--level {level.resolve()}" in json.loads(r.stdout)["error"]


def test_a_slug_with_no_body_anywhere_says_no_such_fact_exists(tmp_path):
    level = make_tree(tmp_path)
    r = run_cli(["show", "--engine", str(make_engine_dir(tmp_path)), "--json",
                 "--slug", "feedback-absent", "--from", str(level)], tmp_path)
    assert r.returncode == 1
    err = json.loads(r.stdout)["error"]
    assert "no body" in err and "--level" not in err, err


def test_a_body_no_level_points_at_is_called_dangling(tmp_path):
    level = make_tree(tmp_path)
    (level / "CLAUDE.local.md").write_text("# Memory index\n", encoding="utf-8")
    r = run_cli(["show", "--engine", str(make_engine_dir(tmp_path)), "--json",
                 "--slug", "feedback-demo", "--from", str(level)], tmp_path)
    assert r.returncode == 1
    assert "dangling" in json.loads(r.stdout)["error"]


def test_a_search_out_of_time_prints_the_find_command(tmp_path):
    level = make_tree(tmp_path)
    sib = _sibling(level)
    rules = FE.load_rules(make_engine_dir(tmp_path))
    try:
        FE.read_fact("feedback-demo", sib, rules, search_budget_s=0)
    except FE.UnknownFact as exc:
        assert "find " in str(exc) and "mem:feedback-demo)" in str(exc), str(exc)
    else:
        raise AssertionError("a sibling-owned fact must not resolve from the sibling")


def test_the_owner_search_skips_vendored_and_hidden_dirs(tmp_path):
    level = make_tree(tmp_path)
    anchor = level.parent
    for junk in (".git", "node_modules", ".venv-3.12"):
        d = anchor / junk / "deep"
        d.mkdir(parents=True)
        (d / "CLAUDE.local.md").write_text(
            "# Memory index\n- [T](mem:feedback-demo) - When x, do y.\n", encoding="utf-8")
    owners, complete = FE.find_pointer_owners(anchor, "feedback-demo",
                                              FE.load_rules(make_engine_dir(tmp_path)).parse_index)
    assert complete and owners == [level.resolve()]
