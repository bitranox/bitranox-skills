"""factedit: what the tool tells a caller who reads its output by script. ASCII only.

Three gaps a reviewer or a merge pass fell into, each measured on a real run:

- `check` answered rc 0 for a body full of typographic tells, and a body stored through the
  engine is written from a file, so no Write/Edit tell hook ever sees it;
- `show` run from outside any tree said only that no store was found, not that the walk starts at
  the current directory and --from moves it;
- `show --body` prints the frame first, whose `description:` repeats the current hook verbatim, so
  a loss check that searches the whole output finds every dropped clause there.

Every case drives the tool as a process, as the callers did. Tell characters are built with chr()
so this source stays ASCII.
"""

import json

from test_factedit import make_engine_dir, make_tree, run_cli

EM_DASH = chr(0x2014)
CURLY_APOSTROPHE = chr(0x2019)


def _write(tmp_path, name, text):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


# ---- check scans the body and the hook for tells ------------------------------------------------

def test_check_reports_a_tell_in_the_body_file_and_still_answers_the_engine_question(tmp_path):
    eng = make_engine_dir(tmp_path)
    body = _write(tmp_path, "body.md", f"First line.\nA merged clause {EM_DASH} with a dash.\n")
    r = run_cli(["check", "--engine", str(eng), "--hook", "When X, do Y.",
                 "--body-file", str(body), "--json"], tmp_path)
    # The engine stores a body with tells, so the exit code keeps answering "would it accept".
    assert r.returncode == 0, r.stderr
    data = json.loads(r.stdout)["data"]
    tell_lines = [a for a in data["advisories"] if "U+2014" in a]
    assert len(tell_lines) == 1, data["advisories"]
    assert "2:" in tell_lines[0]        # the line it sits on, so the caller can find it
    assert "body" in tell_lines[0]


def test_check_reports_a_tell_in_the_hook(tmp_path):
    eng = make_engine_dir(tmp_path)
    r = run_cli(["check", "--engine", str(eng), "--hook",
                 f"When X, do Y {EM_DASH} always.", "--json"], tmp_path)
    assert r.returncode == 0, r.stderr
    advisories = json.loads(r.stdout)["data"]["advisories"]
    assert [a for a in advisories if "U+2014" in a and "hook" in a], advisories


def test_a_clean_body_and_a_tell_inside_inline_code_draw_no_tell_advisory(tmp_path):
    """Control: the scan must not fire on clean prose, nor on a body that DOCUMENTS a tell in code,
    which is how a fact about the tell rule itself is written."""
    eng = make_engine_dir(tmp_path)
    body = _write(tmp_path, "body.md",
                  f"Plain prose.\nThe tell is `{CURLY_APOSTROPHE}`, written in code.\n")
    r = run_cli(["check", "--engine", str(eng), "--hook", "When X, do Y.",
                 "--body-file", str(body), "--json"], tmp_path)
    assert r.returncode == 0, r.stderr
    advisories = json.loads(r.stdout)["data"]["advisories"]
    assert not [a for a in advisories if "U+" in a], advisories


# ---- show from outside the tree names --from ----------------------------------------------------

def test_show_from_outside_any_tree_says_the_walk_starts_at_the_cwd_and_names_from(tmp_path):
    eng = make_engine_dir(tmp_path)
    make_tree(tmp_path)              # a real tree exists, just not above the cwd (tmp_path)
    r = run_cli(["show", "--engine", str(eng), "--slug", "feedback-demo"], tmp_path)
    assert r.returncode == 2
    assert "--from" in r.stderr, r.stderr
    assert "current directory" in r.stderr, r.stderr


# ---- show --prose-only leaves the frame out -----------------------------------------------------

def test_show_prose_only_prints_the_body_without_the_frame_that_repeats_the_hook(tmp_path):
    level = make_tree(tmp_path)
    r = run_cli(["show", "--engine", str(make_engine_dir(tmp_path)), "--slug", "feedback-demo",
                 "--from", str(level), "--prose-only"], tmp_path)
    assert r.returncode == 0, r.stderr
    assert r.stdout == "The body prose.\n"
    assert "description:" not in r.stdout
    # Control: --body still prints the whole stored body, frame included.
    whole = run_cli(["show", "--engine", str(make_engine_dir(tmp_path)), "--slug", "feedback-demo",
                     "--from", str(level), "--body"], tmp_path)
    assert whole.returncode == 0, whole.stderr
    assert "description: When something happens, do the thing." in whole.stdout


def test_show_prose_only_json_carries_the_prose_in_data_body(tmp_path):
    level = make_tree(tmp_path)
    r = run_cli(["show", "--engine", str(make_engine_dir(tmp_path)), "--slug", "feedback-demo",
                 "--from", str(level), "--prose-only", "--json"], tmp_path)
    assert r.returncode == 0, r.stderr
    data = json.loads(r.stdout)["data"]
    assert data["body"] == "The body prose.\n"
