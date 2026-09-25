"""Tests for mcp_search.py (optional basic-memory search, fallback-safe). All content ASCII."""

import json
import os
import subprocess
import sys
import types

import pytest

import mcp_search as X
import self_improve_signals as sig


@pytest.fixture
def home(tmp_path, monkeypatch):
    h = tmp_path / "home"
    (h / ".claude").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    return h


def _fake_run(stdout, rc=0):
    def run(*a, **k):
        return types.SimpleNamespace(returncode=rc, stdout=stdout, stderr="")
    return run


def test_available_reflects_which(monkeypatch):
    monkeypatch.setattr(X.shutil, "which", lambda _n: "/usr/bin/basic-memory")
    assert X.available() is True
    monkeypatch.setattr(X.shutil, "which", lambda _n: None)
    assert X.available() is False


def test_enabled_honors_knob(home, monkeypatch):
    monkeypatch.setattr(X, "available", lambda: True)
    assert X.enabled() is True                           # default mcp_search=auto
    sig.save_config({"mcp_search": "off"})
    assert X.enabled() is False
    sig.save_config({"mcp_search": "auto"})
    monkeypatch.setattr(X, "available", lambda: False)
    assert X.enabled() is False                          # auto but CLI absent


def test_search_none_when_unavailable(monkeypatch):
    monkeypatch.setattr(X, "available", lambda: False)
    assert X.search("query") is None


def test_search_none_on_error_output(monkeypatch):
    monkeypatch.setattr(X, "available", lambda: True)
    monkeypatch.setattr(subprocess, "run", _fake_run("Error during search: Project not found: 'main'."))
    assert X.search("q") is None


def test_search_parses_json(monkeypatch):
    monkeypatch.setattr(X, "available", lambda: True)
    payload = json.dumps({"results": [{"permalink": "notes/a"}, {"file_path": "notes/b.md"}]})
    monkeypatch.setattr(subprocess, "run", _fake_run(payload))
    assert X.search("q") == ["notes/a", "notes/b.md"]


def test_search_parses_lines(monkeypatch):
    monkeypatch.setattr(X, "available", lambda: True)
    monkeypatch.setattr(subprocess, "run", _fake_run("notes/a\nnotes/b\n"))
    assert X.search("q") == ["notes/a", "notes/b"]


def test_watched_roots_and_covers(home):
    (home / ".basic-memory").mkdir()
    (home / ".basic-memory" / "config.json").write_text(
        json.dumps({"projects": {"main": {"path": str(home / "kb")}}}), encoding="utf-8")
    (home / "kb" / "sub").mkdir(parents=True)
    assert str(home / "kb") in X.watched_roots()
    assert X.covers(str(home / "kb" / "sub")) is True    # ancestor project covers it
    assert X.covers("/tmp/elsewhere") is False


@pytest.mark.parametrize("content", [None, "{not json", "[1, 2]", '{"projects": ["x"]}'])
def test_a_missing_or_unusable_basic_memory_config_watches_nothing(home, content):
    if content is not None:
        (home / ".basic-memory").mkdir()
        (home / ".basic-memory" / "config.json").write_text(content, encoding="utf-8")
    (home / "kb").mkdir()
    assert X.watched_roots() == []
    assert X.covers(str(home / "kb")) is False


# ---- the real CLI boundary: a stand-in `basic-memory` on PATH, run as a real subprocess ------

_FAKE_CLI = """#!{python}
import json, sys, time
args = sys.argv[1:]
if args[:2] != ["tool", "search-notes"]:
    sys.exit(2)
mode = {mode!r}
if mode == "sleep":
    time.sleep(5)
opts, query = {{}}, None
rest = args[2:]
while rest:
    a = rest.pop(0)
    if a == "--":
        query = " ".join(rest)
        break
    if a.startswith("-"):
        opts[a] = rest.pop(0) if a == "--page-size" else True
    else:
        query = a
print(json.dumps({{"results": [{{"title": "q=%s opts=%s" % (query, sorted(opts))}}]}}))
"""


@pytest.fixture
def fake_cli(tmp_path, monkeypatch):
    """Put a stand-in `basic-memory` first on PATH. Like the real typer CLI, it reads any argument
    starting with `-` BEFORE a `--` as an option, so the argv the module builds is what is tested."""
    if os.name == "nt":
        pytest.skip("the stand-in is a shebang script; a bare-name CLI on Windows must be an .exe")
    bindir = tmp_path / "bin"
    bindir.mkdir()

    def make(mode="ok", interpreter=sys.executable):
        cli = bindir / "basic-memory"
        cli.write_text(_FAKE_CLI.format(python=interpreter, mode=mode), encoding="utf-8")
        cli.chmod(0o755)
        monkeypatch.setenv("PATH", str(bindir) + os.pathsep + os.environ.get("PATH", ""))
        return cli

    return make


@pytest.mark.parametrize("query", ["--no-verify hook bypass", "-webkit prefixes", "--vector",
                                   "--help", "plain words"])
def test_a_query_is_never_read_as_a_cli_option(fake_cli, query):
    fake_cli()
    assert X.search(query) == ["q=%s opts=['--page-size']" % query]


def test_a_keyword_list_is_joined_into_one_query(fake_cli):
    fake_cli()
    assert X.search(["zfs", "", "scrub"], limit=3) == ["q=zfs scrub opts=['--page-size']"]


@pytest.mark.parametrize("query, limit", [("q", None), ("q", "abc"), (5, 10), (None, 10),
                                          ("   ", 10), (["", " "], 10),
                                          ("q", float("inf")), ("q", float("-inf"))])
def test_search_returns_none_for_unusable_arguments_rather_than_raising(fake_cli, query, limit):
    # int(float("inf")) raises OverflowError, not ValueError/TypeError - a caller that reached
    # here with no bound on limit (or a bug upstream) must still get None, not a crash.
    fake_cli()
    assert X.search(query, limit=limit) is None


def test_search_returns_none_when_the_cli_times_out(fake_cli):
    fake_cli(mode="sleep")
    assert X.search("q", timeout=0.5) is None


def test_search_returns_none_when_the_cli_cannot_be_started(fake_cli, tmp_path, monkeypatch):
    cli = fake_cli(interpreter=str(tmp_path / "no-such-interpreter"))
    # PATH is ONLY the stand-in's dir: a failed exec makes Python try every later PATH entry,
    # which on a machine with network mounts on PATH takes seconds and tests nothing.
    monkeypatch.setenv("PATH", str(cli.parent))
    assert X.available() is True        # found on PATH, so the failure is at exec time
    assert X.search("q") is None
