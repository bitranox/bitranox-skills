"""factedit `apply --batch`: several facts recomposed through the engine, one engine call each,
with the whole batch validated before anything is written. ASCII only.

Every case drives the tool as a process. The recording engine from test_factedit stands in for the
write path where a test asserts WHICH calls were made; the cases that must prove what the STORE
ends up holding run the plugin's own engine against a tree under tmp_path with HOME redirected.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

import factedit as FE
from test_factedit import (
    TOOL,
    _real_engine_env,
    make_engine_dir,
    over_hard_hook,
    run_cli,
)

SLUGS = ("feedback-one", "feedback-two", "feedback-three")


def make_multi_tree(tmp_path: Path, *, pinned: tuple[str, ...] = ()) -> Path:
    """A two-level tree whose one level points at every slug in SLUGS, each with a framed body."""
    anchor = tmp_path / "tree"
    level = anchor / "proj"
    facts = anchor / ".claude-memory" / "facts"
    facts.mkdir(parents=True)
    (anchor / "CLAUDE.md").write_text("anchor\n", encoding="utf-8")
    level.mkdir(parents=True)
    lines = ["# Memory index"]
    for slug in SLUGS:
        meta = "bx:src=session-x" + (" bx:pin" if slug in pinned else "")
        lines.append(f"- [Title {slug}](mem:{slug}) - When {slug} happens, do it. <!-- {meta} -->")
        (facts / f"{slug}.md").write_text(
            f"---\nname: {slug}\ndescription: When {slug} happens, do it.\n"
            "metadata:\n  type: feedback\n---\n\nOld prose.\n", encoding="utf-8")
    (level / "CLAUDE.local.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return level


def write_bodies(tmp_path: Path, slugs=SLUGS) -> dict[str, Path]:
    out = {}
    for slug in slugs:
        p = tmp_path / "bodies" / f"{slug}.md"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(f"New prose for {slug}.\n", encoding="utf-8")
        out[slug] = p
    return out


def write_batch(tmp_path: Path, entries, name: str = "batch.jsonl") -> Path:
    """Entries are dicts (one JSON line each) or raw strings (written verbatim as one line)."""
    p = tmp_path / name
    p.write_text("".join((e if isinstance(e, str) else json.dumps(e)) + "\n" for e in entries),
                 encoding="utf-8")
    return p


def calls(eng: Path) -> list[str]:
    log = eng.parent / "memory_engine.py.called"
    return log.read_text(encoding="utf-8").splitlines() if log.exists() else []


def batch(eng: Path, level: Path, batch_file: Path, tmp_path: Path, *extra: str):
    return run_cli(["apply", "--engine", str(eng), "--json", "--from", str(level),
                    "--batch", str(batch_file), *extra], tmp_path)


# ---- the happy path -----------------------------------------------------------------------------

def test_a_batch_runs_one_engine_call_per_entry_in_file_order(tmp_path):
    eng = make_engine_dir(tmp_path)
    level = make_multi_tree(tmp_path)
    bodies = write_bodies(tmp_path)
    bf = write_batch(tmp_path, [{"slug": s, "body_file": str(bodies[s])} for s in SLUGS])
    r = batch(eng, level, bf, tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    env = json.loads(r.stdout)
    assert env["ok"] is True and env["command"] == "apply"
    assert env["data"]["applied"] == list(SLUGS)
    assert env["data"]["not_applied"] == [] and env["data"]["failed"] is None
    made = calls(eng)
    assert len(made) == 3
    for slug, line in zip(SLUGS, made, strict=True):
        assert f"'--slug={slug}'" in line and "'add'" in line and "--body-file=" in line


def test_a_batch_dry_run_stages_every_entry_and_invokes_nothing(tmp_path):
    eng = make_engine_dir(tmp_path)
    level = make_multi_tree(tmp_path)
    bodies = write_bodies(tmp_path)
    stage = tmp_path / "stage"
    bf = write_batch(tmp_path, [{"slug": s, "body_file": str(bodies[s])} for s in SLUGS])
    r = batch(eng, level, bf, tmp_path, "--dry-run", "--stage-dir", str(stage))
    assert r.returncode == 0, r.stdout + r.stderr
    data = json.loads(r.stdout)["data"]
    assert data["staged"] == list(SLUGS) and data["applied"] == []
    assert all((stage / f"{s}.body.md").is_file() for s in SLUGS)
    assert [x["command"] for x in data["results"]], "each staged entry prints its command"
    assert calls(eng) == []


def test_relative_paths_in_an_entry_resolve_against_the_batch_files_dir(tmp_path):
    eng = make_engine_dir(tmp_path)
    level = make_multi_tree(tmp_path)
    write_bodies(tmp_path, ("feedback-one",))
    bf = write_batch(tmp_path, [{"slug": "feedback-one", "body_file": "bodies/feedback-one.md"}])
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    r = subprocess.run([sys.executable, str(TOOL), "apply", "--engine", str(eng), "--json",
                        "--from", str(level), "--batch", str(bf)],
                       capture_output=True, text=True, encoding="utf-8", check=False,
                       cwd=str(elsewhere))
    assert r.returncode == 0, r.stdout + r.stderr
    assert len(calls(eng)) == 1


def test_an_entry_can_carry_hook_file_title_type_and_level(tmp_path):
    eng = make_engine_dir(tmp_path)
    level = make_multi_tree(tmp_path)
    hook = tmp_path / "h.txt"
    hook.write_text("When feedback-one happens now, do the new thing.\n", encoding="utf-8")
    bf = write_batch(tmp_path, [{"slug": "feedback-one", "hook_file": str(hook),
                                 "title": "New title", "type": "project", "level": str(level)}])
    r = run_cli(["apply", "--engine", str(eng), "--json", "--from", str(tmp_path),
                 "--batch", str(bf)], tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    (line,) = calls(eng)
    assert "'--title=New title'" in line and "'--type=project'" in line and "--hook-file=" in line


def test_the_text_output_names_each_slugs_outcome(tmp_path):
    eng = make_engine_dir(tmp_path)
    level = make_multi_tree(tmp_path)
    bodies = write_bodies(tmp_path)
    bf = write_batch(tmp_path, [{"slug": s, "body_file": str(bodies[s])} for s in SLUGS])
    r = run_cli(["apply", "--engine", str(eng), "--from", str(level), "--batch", str(bf)], tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    for slug in SLUGS:
        assert re.search(rf"(?m)^applied\s+{slug}$", r.stdout), r.stdout


# ---- the whole batch is validated before anything is written ------------------------------------

def test_every_problem_is_listed_and_nothing_is_written(tmp_path):
    eng = make_engine_dir(tmp_path)
    level = make_multi_tree(tmp_path)
    bodies = write_bodies(tmp_path)
    bf = write_batch(tmp_path, [
        {"slug": "feedback-one", "body_file": str(bodies["feedback-one"])},       # fine
        {"slug": "feedback-nope", "body_file": str(bodies["feedback-two"])},      # unknown slug
        {"slug": "feedback-two", "body_file": str(tmp_path / "missing.md")},      # missing file
        {"slug": "feedback-one", "body_file": str(bodies["feedback-one"])},       # duplicate
        {"slug": "feedback-three", "bodyfile": "x"},                               # bad key
        {"body_file": str(bodies["feedback-three"])},                              # no slug
        "{not json",                                                               # bad line
        {"slug": "feedback-three"},                                                # nothing to change
    ])
    r = batch(eng, level, bf, tmp_path)
    assert r.returncode == 2, r.stdout + r.stderr
    env = json.loads(r.stdout)
    assert env["ok"] is False
    problems = env["data"]["problems"]
    text = "\n".join(problems)
    assert "line 2" in text and "feedback-nope" in text
    assert "line 3" in text and "missing.md" in text
    assert "line 4" in text and "duplicate" in text
    assert "line 5" in text and "bodyfile" in text
    assert "line 6" in text and "slug" in text
    assert "line 7" in text and "JSON" in text
    assert "line 8" in text and "nothing to change" in text
    assert not any(p.startswith(("line 1 ", "line 1:")) for p in problems)
    assert env["data"]["applied"] == []
    assert calls(eng) == [], "a refused batch must not reach the engine at all"


def test_an_unknown_slug_and_a_missing_file_on_one_entry_are_both_reported(tmp_path):
    eng = make_engine_dir(tmp_path)
    level = make_multi_tree(tmp_path)
    bf = write_batch(tmp_path, [{"slug": "feedback-nope", "body_file": str(tmp_path / "gone.md")}])
    r = batch(eng, level, bf, tmp_path)
    assert r.returncode == 2
    text = "\n".join(json.loads(r.stdout)["data"]["problems"])
    assert "gone.md" in text and "feedback-nope" in text and "UnknownFact" in text


def test_an_over_cap_hook_in_one_entry_refuses_the_whole_batch(tmp_path):
    eng = make_engine_dir(tmp_path)
    level = make_multi_tree(tmp_path)
    bodies = write_bodies(tmp_path)
    long_hook = tmp_path / "long.txt"
    long_hook.write_text(over_hard_hook(eng), encoding="utf-8")
    bf = write_batch(tmp_path, [{"slug": "feedback-one", "body_file": str(bodies["feedback-one"])},
                                {"slug": "feedback-two", "hook_file": str(long_hook)}])
    r = batch(eng, level, bf, tmp_path)
    assert r.returncode == 2
    assert "HARD cap" in "\n".join(json.loads(r.stdout)["data"]["problems"])
    assert calls(eng) == []


def test_a_pinned_entry_without_allow_pinned_refuses_the_whole_batch(tmp_path):
    eng = make_engine_dir(tmp_path)
    level = make_multi_tree(tmp_path, pinned=("feedback-two",))
    bodies = write_bodies(tmp_path)
    bf = write_batch(tmp_path, [{"slug": s, "body_file": str(bodies[s])} for s in SLUGS])
    r = batch(eng, level, bf, tmp_path)
    assert r.returncode == 2
    assert "PinnedFact" in "\n".join(json.loads(r.stdout)["data"]["problems"])
    assert calls(eng) == []


def test_allow_pinned_routes_the_pinned_entry_through_amend_pinned(tmp_path):
    eng = make_engine_dir(tmp_path)
    level = make_multi_tree(tmp_path, pinned=("feedback-two",))
    bodies = write_bodies(tmp_path)
    bf = write_batch(tmp_path, [{"slug": s, "body_file": str(bodies[s])} for s in SLUGS])
    r = batch(eng, level, bf, tmp_path, "--allow-pinned")
    assert r.returncode == 0, r.stdout + r.stderr
    verbs = ["amend-pinned" if "'amend-pinned'" in c else "add" for c in calls(eng)]
    assert verbs == ["add", "amend-pinned", "add"]


def test_an_unknown_type_in_an_entry_refuses_the_batch(tmp_path):
    eng = make_engine_dir(tmp_path)
    level = make_multi_tree(tmp_path)
    bf = write_batch(tmp_path, [{"slug": "feedback-one", "type": "nonsense"}])
    r = batch(eng, level, bf, tmp_path)
    assert r.returncode == 2
    assert "nonsense" in "\n".join(json.loads(r.stdout)["data"]["problems"])
    assert calls(eng) == []


def test_a_non_string_value_is_a_problem_not_a_crash(tmp_path):
    eng = make_engine_dir(tmp_path)
    level = make_multi_tree(tmp_path)
    bf = write_batch(tmp_path, [{"slug": "feedback-one", "body_file": 7}, ["a", "list"]])
    r = batch(eng, level, bf, tmp_path)
    assert r.returncode == 2, r.stdout + r.stderr
    text = "\n".join(json.loads(r.stdout)["data"]["problems"])
    assert "line 1" in text and "body_file" in text and "line 2" in text
    assert calls(eng) == []


def test_an_empty_batch_is_refused(tmp_path):
    eng = make_engine_dir(tmp_path)
    level = make_multi_tree(tmp_path)
    bf = tmp_path / "empty.jsonl"
    bf.write_text("\n\n", encoding="utf-8")
    r = batch(eng, level, bf, tmp_path)
    assert r.returncode == 2
    assert json.loads(r.stdout)["ok"] is False


def test_a_non_utf8_batch_file_is_exit_2_with_json(tmp_path):
    eng = make_engine_dir(tmp_path)
    level = make_multi_tree(tmp_path)
    bf = tmp_path / "bad.jsonl"
    bf.write_bytes(b'{"slug": "feedback-one\xff"}\n')
    r = batch(eng, level, bf, tmp_path)
    assert r.returncode == 2
    env = json.loads(r.stdout)
    assert env["ok"] is False and "BadInput" in env["error"]


def test_a_missing_batch_file_is_exit_2_with_json(tmp_path):
    eng = make_engine_dir(tmp_path)
    level = make_multi_tree(tmp_path)
    r = batch(eng, level, tmp_path / "nope.jsonl", tmp_path)
    assert r.returncode == 2
    assert "BadInput" in json.loads(r.stdout)["error"]


# ---- --batch and the single-fact options do not mix ---------------------------------------------

def test_batch_with_a_single_fact_option_is_refused(tmp_path):
    eng = make_engine_dir(tmp_path)
    level = make_multi_tree(tmp_path)
    bodies = write_bodies(tmp_path)
    bf = write_batch(tmp_path, [{"slug": "feedback-one", "body_file": str(bodies["feedback-one"])}])
    for extra in (["--slug", "feedback-one"], ["--body-file", str(bodies["feedback-two"])],
                  ["--title", "x"], ["--type", "project"], ["--hook", "When x, y."]):
        r = batch(eng, level, bf, tmp_path, *extra)
        assert r.returncode == 2, extra
        assert json.loads(r.stdout)["error"].startswith("BadInput:"), extra
    assert calls(eng) == []


def test_apply_with_neither_slug_nor_batch_is_refused(tmp_path):
    eng = make_engine_dir(tmp_path)
    level = make_multi_tree(tmp_path)
    r = run_cli(["apply", "--engine", str(eng), "--json", "--from", str(level),
                 "--body-file", str(write_bodies(tmp_path)["feedback-one"])], tmp_path)
    assert r.returncode == 2
    err = json.loads(r.stdout)["error"]
    assert err.startswith("BadInput:") and "--batch" in err and "--slug" in err


# ---- a failure mid-way stops the batch and says what was and was not applied --------------------

FAIL_ON_TWO_ENGINE = '''
import sys
open(sys.argv[0] + ".called", "a", encoding="utf-8").write(repr(sys.argv[1:]) + "\\n")
if "--slug=feedback-two" in sys.argv:
    print("refused: simulated collision")
    sys.exit(2)
print("fake-engine-ok")
'''


def test_a_failure_mid_way_stops_and_reports_applied_failed_and_not_applied(tmp_path):
    eng = make_engine_dir(tmp_path)
    eng.write_text(FAIL_ON_TWO_ENGINE, encoding="utf-8")
    level = make_multi_tree(tmp_path)
    bodies = write_bodies(tmp_path)
    bf = write_batch(tmp_path, [{"slug": s, "body_file": str(bodies[s])} for s in SLUGS])
    r = batch(eng, level, bf, tmp_path)
    assert r.returncode == 2, r.stdout + r.stderr
    env = json.loads(r.stdout)
    data = env["data"]
    assert env["ok"] is False
    assert data["applied"] == ["feedback-one"]
    assert data["failed"]["slug"] == "feedback-two"
    assert "simulated collision" in data["failed"]["reason"]
    assert data["not_applied"] == ["feedback-three"]
    assert len(calls(eng)) == 2, "nothing after the failed entry may reach the engine"


def test_a_failure_mid_way_is_spelled_out_in_the_text_output(tmp_path):
    eng = make_engine_dir(tmp_path)
    eng.write_text(FAIL_ON_TWO_ENGINE, encoding="utf-8")
    level = make_multi_tree(tmp_path)
    bodies = write_bodies(tmp_path)
    bf = write_batch(tmp_path, [{"slug": s, "body_file": str(bodies[s])} for s in SLUGS])
    r = run_cli(["apply", "--engine", str(eng), "--from", str(level), "--batch", str(bf)], tmp_path)
    assert r.returncode == 2
    assert re.search(r"(?m)^applied\s+feedback-one$", r.stdout), r.stdout
    assert re.search(r"(?m)^FAILED\s+feedback-two\b", r.stdout), r.stdout
    assert re.search(r"(?m)^not applied\s+feedback-three$", r.stdout), r.stdout


# ---- against the REAL engine: the store ends up holding every new body --------------------------

def test_a_batch_through_the_real_engine_rewrites_every_body(tmp_path):
    level = make_multi_tree(tmp_path)
    bodies = write_bodies(tmp_path)
    bf = write_batch(tmp_path, [{"slug": s, "body_file": str(bodies[s])} for s in SLUGS])
    r = subprocess.run([sys.executable, str(TOOL), "apply", "--engine", str(FE.OWN_ENGINE),
                        "--json", "--from", str(level), "--batch", str(bf)],
                       capture_output=True, text=True, encoding="utf-8", check=False,
                       env=_real_engine_env(tmp_path), cwd=str(tmp_path))
    assert r.returncode == 0, r.stdout + r.stderr
    facts = level.parent / ".claude-memory" / "facts"
    for slug in SLUGS:
        text = (facts / f"{slug}.md").read_text(encoding="utf-8")
        assert f"New prose for {slug}." in text and "Old prose." not in text, text
    index = (level / "CLAUDE.local.md").read_text(encoding="utf-8")
    assert all(f"(mem:{s})" in index for s in SLUGS)
