"""Tests for recall-memory.py (UserPromptSubmit recall hook). All content ASCII."""

import io
import json
import sys

import pytest

import recall_memory as R
import self_improve_signals as sig


@pytest.fixture(autouse=True)
def home(tmp_path, monkeypatch):
    h = tmp_path / "home"
    (h / ".claude").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    return h


def _mem(proj, name, text):
    d = sig.memory_dir(proj)
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text(text, encoding="utf-8")
    return d


def run(monkeypatch, capsys, prompt, cwd="/p/cur", sid="t1"):
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(
        {"prompt": prompt, "cwd": cwd, "session_id": sid})))
    rc = R.main()
    return rc, capsys.readouterr().out


def test_surfaces_relevant_note_from_another_project(monkeypatch, capsys):
    _mem("/p/other", "make-test.md", "Run make test with VIRTUAL_ENV=$PWD/.venv before committing")
    rc, out = run(monkeypatch, capsys, "run make test")
    assert rc == 0
    payload = json.loads(out)
    ctx = payload["hookSpecificOutput"]["additionalContext"]
    assert payload["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"
    assert "make-test" in ctx and "VIRTUAL_ENV" in ctx      # the other tree's body is drawn in
    assert payload.get("suppressOutput") is True


def test_surfaces_sibling_claude_md(monkeypatch, capsys, tmp_path, home):
    # cross-project rules still live in CLAUDE.md (conversion phase) -> recall must search them too.
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "CLAUDE.md").write_text("workspace root rules", encoding="utf-8")
    cur = ws / "cur"
    cur.mkdir()
    (cur / "CLAUDE.md").write_text("current project rules", encoding="utf-8")
    sib = ws / "sib"
    sib.mkdir()
    (sib / "CLAUDE.md").write_text(
        "To drive the widget frobnicator, set FROB_LEVEL=9 in the service unit.", encoding="utf-8")
    rc, out = run(monkeypatch, capsys, "how do I set the frobnicator frob level", cwd=str(cur))
    assert rc == 0
    ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"]
    assert "sib/CLAUDE.md" in ctx and "frobnicator" in ctx   # sibling CLAUDE.md surfaced + labelled
    assert "cur/CLAUDE.md" not in ctx                         # current chain excluded (already loaded)


def test_excludes_current_project(monkeypatch, capsys):
    _mem("/p/cur", "current-make.md", "make test current only secret")
    _mem("/p/other", "make-test.md", "make test elsewhere")
    rc, out = run(monkeypatch, capsys, "run make test", cwd="/p/cur")
    ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"]
    assert "make-test" in ctx            # other project surfaced
    assert "current-make" not in ctx     # our own memory is NOT redrawn (dedup with current)


def test_per_session_dedup_then_new_session(monkeypatch, capsys):
    _mem("/p/other", "make-test.md", "make test note")
    _, out1 = run(monkeypatch, capsys, "make test", sid="s1")
    assert "make-test" in out1
    _, out2 = run(monkeypatch, capsys, "make test again", sid="s1")
    assert out2 == ""                    # same session -> already surfaced -> silent
    _, out3 = run(monkeypatch, capsys, "make test", sid="s2")
    assert "make-test" in out3           # new session -> surfaces again


def test_no_match_no_output(monkeypatch, capsys):
    _mem("/p/other", "make-test.md", "make test note")
    rc, out = run(monkeypatch, capsys, "completely unrelated zzzqqq topic")
    assert rc == 0 and out == ""


def test_rarity_drops_common_only_matches(monkeypatch, capsys):
    monkeypatch.setattr(R, "SPECIFIC_MAX", 1)        # treat a keyword in >1 candidate as "common"
    _mem("/p/r", "rare.md", "alpha config note")     # matches a rare term (alpha) + the common one
    _mem("/p/b", "b.md", "config only here")         # common-only
    _mem("/p/c", "c.md", "config only there")        # common-only
    rc, out = run(monkeypatch, capsys, "alpha config")
    assert "alpha config note" in out                 # rare / multi-keyword note surfaces (its body)
    assert "config only here" not in out and "config only there" not in out  # common-only dropped


def test_single_rare_keyword_still_surfaces(monkeypatch, capsys):
    # a lone specific keyword (matches few notes) is a STRONG signal - must surface (not dropped)
    _mem("/p/x", "bindsnap-note.md", "bindsnap divert shim details")
    rc, out = run(monkeypatch, capsys, "bindsnap")
    assert "bindsnap-note" in out


def test_corpus_common_keyword_is_dropped(monkeypatch, capsys):
    # a word present in a LARGE fraction of the whole store carries no signal for THIS user
    # (e.g. "memory" in a memory-centric store) - it must not drive recall, even though it is not
    # generic-English filler. A note matching ONLY such words is dropped; a rare term still surfaces.
    for i in range(8):
        _mem("/p/o%d" % i, "n%d.md" % i, "widget gadget item number %d" % i)  # 'widget' in 9 notes
    _mem("/p/rare", "frob.md", "widget gadget frobnitz special")              # also a RARE term
    rc, out = run(monkeypatch, capsys, "widget frobnitz")
    ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"]
    assert "frob" in ctx                                  # the note with the rare term surfaces
    assert "n0" not in ctx and "n7" not in ctx            # widget-only notes dropped (corpus-common)


def test_no_keywords_no_output(monkeypatch, capsys):
    _mem("/p/other", "make-test.md", "make test note")
    rc, out = run(monkeypatch, capsys, "do it")     # all stopwords/short
    assert rc == 0 and out == ""


def test_filler_only_prompt_no_output(monkeypatch, capsys):
    # the reported bug: a conversational prompt of pure filler must surface NOTHING.
    _mem("/p/other", "make-test.md", "make test note")
    rc, out = run(monkeypatch, capsys,
                  "i got again hits on my previous answer - is that normal again")
    assert rc == 0 and out == ""


def test_unknown_keywords_are_queued_for_the_dream(monkeypatch, capsys):
    # per prompt we do NOT classify (no model); we queue not-yet-classified keywords for the dream,
    # keyed to the CURRENT project (cwd="/p/cur").
    _mem("/p/other", "bindsnap.md", "bindsnap divert shim")
    run(monkeypatch, capsys, "bindsnap divert details")
    assert {"bindsnap", "divert", "details"} <= set(sig.load_pending_keywords("/p/cur"))


def test_known_topical_keyword_not_requeued(monkeypatch, capsys):
    sig.add_topical_words(["bindsnap"], "/p/cur")              # known-topical for THIS project
    _mem("/p/other", "bindsnap.md", "bindsnap divert shim")
    run(monkeypatch, capsys, "bindsnap divert")
    pending = sig.load_pending_keywords("/p/cur")
    assert "bindsnap" not in pending and "divert" in pending   # known-topical skipped, new queued


def test_malformed_stdin_exits_zero(monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", io.StringIO("not json"))
    assert R.main() == 0
    assert capsys.readouterr().out == ""


def test_label_curated_memory_and_facts():
    import recall_memory as R
    assert R._label("/x/projZ/.claude-bx-selflearning/index.md") == "projZ/memory"
    assert R._label("/x/projZ/.claude-bx-selflearning/facts/foo.md") == "foo"
    assert R._label("/x/projZ/CLAUDE.md") == "projZ/CLAUDE.md"


def test_snippet_strips_scope_block(tmp_path):
    import recall_memory as R
    m = tmp_path / "index.md"
    m.write_text("<!-- bitranox:self-learning -->\nSCOPE DESCRIPTOR TEXT\n<!-- /bitranox:self-learning -->\n\n"
                 "# Memory index\n\n- [X](#x) - a keyword fact\n", encoding="utf-8")
    snip = R._snippet(str(m), ["keyword"], 10000)
    assert "SCOPE DESCRIPTOR TEXT" not in snip and "keyword fact" in snip
