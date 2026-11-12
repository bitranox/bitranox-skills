"""Tests that every writer of a level's pointer block follows ONE cap rule: a write is refused
only when the block would END past MAX_RENDER_BLOCK_BYTES and GROW (end larger than it is now).
`add` (a placed fact's multi-level rewrite included), `amend-pinned`, `retitle` and `rename` are
held to it before any write; `render-topics` no longer refuses a render that leaves an already
over-full block no larger than it is (one uncapped write used to wedge every render on that
chain). A refusal writes nothing, prints `! refused:` and exits 2, and names a route that works;
each route is run here as a subprocess from a cwd outside the tree. All content ASCII, so a
byte count is a character count.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

import memory_engine as E
import pytest
import self_improve_signals as sig
import uuid_store as us

CAP = E.MAX_RENDER_BLOCK_BYTES
ENGINE_ROOT = Path(E.__file__).resolve().parents[1]
HOOK = "When a rule is about one stack, bind it to that stack's topic."


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch):
    h = tmp_path / "home"
    h.mkdir(exist_ok=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    return h


def _main(*args):
    return E.main([str(a) for a in args])


def _tree(tmp_path):
    """A tree with a topic list (python, rust) and levels a, a/py (python), b, b/py (python)."""
    anchor = tmp_path / "tree"
    anchor.mkdir()
    (anchor / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (anchor / us.STORE_DIRNAME).mkdir()
    listing = tmp_path / "list.json"
    listing.write_text(json.dumps({"tagger": "jev", "topics": {"python": "about python",
                                                                "rust": "about rust"}}),
                       encoding="utf-8")
    assert _main("topics-set-list", "--proj", anchor, "--from-file", listing) == 0
    assert _main("set-scope", "--proj", anchor, "--scope", "WHAT: the top") == 0
    out = {"": str(anchor)}
    for rel, topics in (("a", None), ("a/py", "python"), ("b", None), ("b/py", "python")):
        level = Path(anchor, *rel.split("/"))
        level.mkdir(parents=True)
        (level / "CLAUDE.md").write_text("x\n", encoding="utf-8")
        assert _main("set-scope", "--proj", level, "--scope", "WHAT: " + rel) == 0
        if topics:
            assert _main("set-level-topics", "--proj", level, "--topics", topics) == 0
        out[rel] = str(level)
    return out


def _fact(level, slug, topics=None, pin=False, hook=HOOK):
    args = ["add", "--proj", level, "--title", "T " + slug, "--hook", hook, "--body",
            "body " + slug, "--type", "feedback", "--slug", slug]
    assert _main(*args, *(["--pin"] if pin else [])) == 0
    if topics:
        assert _main("set-topics", "--proj", level, "--slug", slug, "--topics", topics) == 0


def _plant(level, pointers):
    local = sig.claude_local_md_path(level)
    text = local.read_text(encoding="utf-8")
    scope, have = us.parse_pointer_index(text)
    local.write_text(us.upsert_pointer_block(text, scope, have + list(pointers)), encoding="utf-8")


def _bytes(level):
    text = sig.claude_local_md_path(level).read_text(encoding="utf-8")
    return sum(E._line_size(p) for p in us.parse_pointer_index(text)[1])


def _fill_to(level, total):
    """Plant body-less (never managed) lines at `level` until its block holds exactly `total`."""
    text = sig.claude_local_md_path(level).read_text(encoding="utf-8")
    pointers, left, i = [], total - _bytes(level), len(us.parse_pointer_index(text)[1])
    while left:
        slug = "feedback-fill%05d" % i
        base = E._line_size(us.Pointer(slug=slug, title="T", hook=""))
        n = 1000 if left - E._line_size(us.Pointer(slug=slug, title="T", hook="k" * 1000)) >= base + 1 \
            else left - base
        assert n >= 1
        pointers.append(us.Pointer(slug=slug, title="T", hook="k" * n))
        left -= E._line_size(pointers[-1])
        i += 1
    _plant(level, pointers)
    assert _bytes(level) == total


def _snapshot(anchor):
    return {str(p): p.read_bytes() for p in sorted(Path(anchor).rglob("*"))
            if p.is_file() and not p.name.endswith(".lock")}


def _run(tmp_path, *args):
    outside = tmp_path / "outside"
    outside.mkdir(exist_ok=True)
    done = subprocess.run([sys.executable, str(ENGINE_ROOT / "hooks" / "memory_engine.py"),
                           *map(str, args)], cwd=str(outside), capture_output=True, text=True,
                          encoding="utf-8", errors="replace", check=False)
    return done.returncode, done.stdout + done.stderr


def _refused(capsys, *args):
    capsys.readouterr()
    rc = _main(*args)
    out = capsys.readouterr().out
    assert rc == 2 and out.startswith("! refused: "), (rc, out)
    return out


def _shrink(out):
    m = re.search(r"at least (\d+) (?:bytes|characters) shorter", out)
    assert m is not None, out
    return int(m.group(1))


def _placed_near_cap(tmp_path, level_key="a/py"):
    """feedback-py0 placed by topic at a/py and b/py, and `level_key`'s block filled so a line
    only a little longer than the one there passes the cap."""
    L = _tree(tmp_path)
    _fact(L[""], "feedback-py0", "python")
    assert _main("render-topics", "--proj", L[""], "--scope", "tree") == 0
    _fill_to(L[level_key], CAP - 40)
    return L


def test_add_growing_a_placed_line_past_the_cap_is_refused_and_its_route_works(tmp_path, capsys):
    """Reviewer A's case: an add on a placed fact at a near-full level took it past the cap."""
    L = _placed_near_cap(tmp_path)
    before = _snapshot(L[""])
    long_hook = "When x, " + "y" * 480
    out = _refused(capsys, "add", "--proj", L["a/py"], "--slug", "feedback-py0", "--title",
                   "T feedback-py0", "--hook", long_hook)
    assert _snapshot(L[""]) == before
    assert "add would leave the block at %s" % L["a/py"] in out and "larger than it is now" in out
    shrink = _shrink(out)
    hook_file = tmp_path / "hook.txt"
    hook_file.write_text(long_hook[:-(shrink - 1)], encoding="utf-8")     # one byte too long
    rc, said = _run(tmp_path, "add", "--proj", L["a/py"], "--slug", "feedback-py0", "--title",
                    "T feedback-py0", "--hook-file", hook_file)
    assert rc == 2 and "! refused:" in said, said
    route = re.search(r"(hooks/memory_engine\.py add --proj (\S+) --slug feedback-py0) --title "
                      r"<title> --hook-file <file>", out)
    assert route is not None and route.group(2) == L["a/py"], out
    hook_file.write_text(long_hook[:-shrink], encoding="utf-8")
    rc, said = _run(tmp_path, *route.group(1).split()[1:], "--title", "T feedback-py0",
                    "--hook-file", hook_file)
    assert rc == 0, said
    assert _bytes(L["a/py"]) == CAP and _bytes(L["b/py"]) < CAP


def test_add_of_a_placed_fact_checks_every_level_it_rewrites_before_writing_any(tmp_path, capsys):
    L = _placed_near_cap(tmp_path, level_key="b/py")
    before = _snapshot(L[""])
    out = _refused(capsys, "add", "--proj", L["a/py"], "--slug", "feedback-py0", "--title",
                   "T feedback-py0", "--hook", "When x, " + "y" * 480)
    assert "the block at %s" % L["b/py"] in out, out
    assert _snapshot(L[""]) == before                      # a/py, the body and b/py untouched


def test_add_that_does_not_grow_an_over_full_block_goes_through(tmp_path, capsys):
    L = _placed_near_cap(tmp_path)
    _fill_to(L["a/py"], CAP + 500)                          # over the cap already
    assert _main("add", "--proj", L["a/py"], "--slug", "feedback-py0", "--title",
                 "T feedback-py0", "--hook", HOOK.replace("one stack", "one stick")) == 0
    assert _bytes(L["a/py"]) == CAP + 500


def test_a_new_fact_at_a_full_level_is_refused_and_another_level_takes_it(tmp_path, capsys):
    L = _tree(tmp_path)
    _fill_to(L["a"], CAP)
    before = _snapshot(L[""])
    out = _refused(capsys, "add", "--proj", L["a"], "--slug", "feedback-new", "--title", "T new",
                   "--hook", HOOK, "--body", "body", "--type", "feedback")
    assert _snapshot(L[""]) == before
    route = re.search(r"(hooks/memory_engine\.py add) --proj <level> --slug feedback-new", out)
    assert route is not None, out
    rc, said = _run(tmp_path, "add", "--proj", L[""], "--slug", "feedback-new", "--title",
                    "T new", "--hook", HOOK, "--body", "body", "--type", "feedback")
    assert rc == 0, said
    move = re.search(r"hooks/memory_engine\.py (move --from-level (\S+)) --to-level <level>", out)
    assert move is not None and move.group(2) == L["a"], out
    rc, said = _run(tmp_path, *move.group(1).split(), "--to-level", L[""], "--slug",
                    "feedback-fill00000")
    assert rc == 0, said
    assert _main("move", "--from-level", L[""], "--to-level", L["a"], "--slug",
                 "feedback-new") == 0


def test_retitle_growing_past_the_cap_is_refused_and_its_route_works(tmp_path, capsys):
    L = _tree(tmp_path)
    _fact(L["a"], "feedback-tt")
    _fill_to(L["a"], CAP - 10)
    before = _snapshot(L[""])
    title = "T feedback-tt " + "w" * 40
    out = _refused(capsys, "retitle", "--level", L["a"], "--slug", "feedback-tt", "--to-title",
                   title)
    assert _snapshot(L[""]) == before
    shrink = _shrink(out)
    route = re.search(r"hooks/memory_engine\.py (retitle --level \S+ --slug feedback-tt) "
                      r"--to-title <title>", out)
    assert route is not None, out
    rc, said = _run(tmp_path, *route.group(1).split(), "--to-title", title[:-(shrink - 1)])
    assert rc == 2 and "! refused:" in said, said
    rc, said = _run(tmp_path, *route.group(1).split(), "--to-title", title[:-shrink])
    assert rc == 0, said
    assert _bytes(L["a"]) == CAP


def test_rename_growing_past_the_cap_is_refused_and_its_route_works(tmp_path, capsys):
    L = _tree(tmp_path)
    _fact(L["a"], "feedback-rn")
    _fill_to(L["a"], CAP - 10)
    before = _snapshot(L[""])
    to_slug = "feedback-rn-" + "q" * 40
    out = _refused(capsys, "rename", "--level", L["a"], "--slug", "feedback-rn", "--to-slug",
                   to_slug)
    assert _snapshot(L[""]) == before
    shrink = _shrink(out)
    route = re.search(r"hooks/memory_engine\.py (rename --level \S+ --slug feedback-rn) "
                      r"--to-slug <slug>", out)
    assert route is not None, out
    rc, said = _run(tmp_path, *route.group(1).split(), "--to-slug", to_slug[:-shrink])
    assert rc == 0, said
    assert _bytes(L["a"]) == CAP


def test_amend_pinned_growing_past_the_cap_is_refused_and_its_route_works(tmp_path, capsys):
    L = _tree(tmp_path)
    _fact(L["a"], "feedback-pn", pin=True)
    _fill_to(L["a"], CAP - 10)
    before = _snapshot(L[""])
    long_hook = HOOK + " " + "z" * 60
    out = _refused(capsys, "amend-pinned", "--proj", L["a"], "--slug", "feedback-pn", "--hook",
                   long_hook)
    assert _snapshot(L[""]) == before
    assert out.startswith("! refused: amend-pinned would leave"), out
    shrink = _shrink(out)
    hook_file = tmp_path / "hook.txt"
    hook_file.write_text(long_hook[:-shrink], encoding="utf-8")
    rc, said = _run(tmp_path, "amend-pinned", "--proj", L["a"], "--slug", "feedback-pn",
                    "--hook-file", hook_file)
    assert rc == 0, said
    assert _bytes(L["a"]) == CAP


def test_a_render_that_adds_nothing_to_an_over_full_level_goes_through(tmp_path, capsys):
    """One uncapped write left a/py over the cap; every render on its chain refused after it."""
    L = _placed_near_cap(tmp_path)
    _fill_to(L["a/py"], CAP + 500)
    before = _snapshot(L[""])
    assert _main("render-topics", "--proj", L[""], "--scope", "tree") == 0
    assert _main("render-topics", "--proj", L["a/py"], "--scope", "chain") == 0
    assert _snapshot(L[""]) == before


def test_a_render_that_grows_an_over_full_level_is_still_refused(tmp_path, capsys):
    L = _placed_near_cap(tmp_path)
    _fill_to(L["a/py"], CAP + 500)
    _fact(L["b"], "feedback-py1", "python")       # off the a/py chain: its chain render adds it
    before = _snapshot(L[""])
    for scope, proj in (("tree", L[""]), ("chain", L["a/py"])):
        out = _refused(capsys, "render-topics", "--proj", proj, "--scope", scope)
        assert "larger than the %d bytes it holds now" % (CAP + 500) in out, out
        assert _snapshot(L[""]) == before


def test_the_rule_needs_both_halves(tmp_path):
    """Pins the predicate itself: over the cap alone, or growth alone, is never a refusal."""
    assert not E._grows_past_cap(CAP + 10, CAP + 10)          # over, not grown
    assert not E._grows_past_cap(CAP - 50, CAP)               # grown, not over
    assert E._grows_past_cap(CAP, CAP + 1)
    assert not E._grows_past_cap(CAP + 20, CAP + 5)           # shrinks while over
