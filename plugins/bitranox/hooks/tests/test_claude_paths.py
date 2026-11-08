"""Tests for claude_paths: the plugin's state follows CLAUDE_CONFIG_DIR, with no fallback.

A/B arms and install tests run Claude Code with CLAUDE_CONFIG_DIR set to a throwaway dir; the
plugin's audit state must follow it, or a sandbox reads and writes the real ~/.claude state.
"""

import ast
import json
import re
from pathlib import Path

import ci_watch_gate
import claude_paths
import harness_checks
import pytest
import self_improve_signals as sig
import session_start
import skill_roster
import subagent_model_gate
import tmp_prune
import toolbox_nudge

PLUGIN = Path(__file__).resolve().parents[2]


@pytest.fixture
def homes(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.delenv("CLAUDE_CONFIG_DIR", raising=False)
    return home, tmp_path / "arm-config"


def test_unset_resolves_under_home(homes):
    home, _ = homes
    assert claude_paths.config_dir() == home / ".claude"
    assert claude_paths.audit_dir() == home / ".claude" / "self-improve-audit"


@pytest.mark.parametrize("value", ["", "   "])
def test_empty_value_counts_as_unset(homes, monkeypatch, value):
    home, _ = homes
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", value)
    assert claude_paths.audit_dir() == home / ".claude" / "self-improve-audit"


def test_set_wins_and_never_falls_back_to_home(homes, monkeypatch):
    # No fallback: the real state must stay invisible to a sandbox even when it exists and the
    # sandbox's own dir does not.
    home, arm = homes
    real = home / ".claude" / "self-improve-audit"
    real.mkdir(parents=True)
    (real / "x.nap-owed").write_text("1", encoding="utf-8")
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(arm))
    assert claude_paths.audit_dir() == arm / "self-improve-audit"
    assert not claude_paths.audit_dir().exists()


def test_the_shared_audit_dir_follows_the_variable(homes, monkeypatch):
    # self_improve_signals._audit_dir is what most hooks and skill scripts call.
    _, arm = homes
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(arm))
    assert sig._audit_dir() == arm / "self-improve-audit"                  # noqa: SLF001
    assert sig.audit_file("/proj/x").parent == arm / "self-improve-audit"
    assert sig.last_dream_file("/proj/x").parent == arm / "self-improve-audit"


# ---- every reader of a file inside Claude's config dir follows the variable ----------------------

def test_the_memory_settings_file_and_auto_memory_follow_the_variable(homes, monkeypatch):
    _, arm = homes
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(arm))
    assert sig._config_path() == arm / ".bitranox-memory.json"
    assert sig.memory_dir("/proj/x") == arm / "projects" / "-proj-x" / "memory"


def test_the_native_seed_scan_reads_the_moved_projects_root(homes, monkeypatch, tmp_path):
    home, arm = homes
    proj = tmp_path / "work"
    proj.mkdir()
    # A note under the REAL home must not count once the config dir has moved, and one under the
    # moved dir must.
    (home / ".claude" / "projects" / "-h" / "memory").mkdir(parents=True)
    (home / ".claude" / "projects" / "-h" / "memory" / "n.md").write_text("x", encoding="utf-8")
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(arm))
    assert sig.knowledge_store_empty(str(proj)) is True
    (arm / "projects" / "-a" / "memory").mkdir(parents=True)
    (arm / "projects" / "-a" / "memory" / "n.md").write_text("x", encoding="utf-8")
    assert sig.knowledge_store_empty(str(proj)) is False


def test_hook_state_files_follow_the_variable(homes, monkeypatch):
    home, arm = homes
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(arm))
    assert ci_watch_gate.sentinel_path().parent == arm
    assert toolbox_nudge._toolbox_dir() == arm / "skills" / "toolbox" / "tools"
    assert skill_roster._claude_dirs(None) == [arm]
    cfg = tmp_prune.PruneConfig.for_this_machine()
    assert (cfg.projects_dir, cfg.sessions_dir) == (arm / "projects", arm / "sessions")
    # The autoupdate opt-out marker is read from the moved dir, never from the real home.
    (home / ".claude").mkdir()
    (home / ".claude" / ".bitranox-no-autoupdate-nudge").write_text("", encoding="utf-8")
    assert session_start.autoupdate_nudge(str(home / "proj")) is not None
    arm.mkdir()
    (arm / ".bitranox-no-autoupdate-nudge").write_text("", encoding="utf-8")
    assert session_start.autoupdate_nudge(str(home / "proj")) is None


def test_installed_plugins_are_read_from_the_moved_dir(homes, monkeypatch):
    _, arm = homes
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(arm))
    (arm / "plugins").mkdir(parents=True)
    (arm / "plugins" / "installed_plugins.json").write_text(json.dumps(
        {"plugins": {"p@m": [{"installPath": "/opt/p"}]}}), encoding="utf-8")
    assert skill_roster._installed_plugin_roots() == {"p": [Path("/opt/p")]}


def test_personal_skills_and_agents_follow_the_variable_and_an_explicit_home_still_wins(
        homes, monkeypatch, tmp_path):
    home, arm = homes
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(arm))
    assert harness_checks.claude_dir() == arm
    assert harness_checks.claude_dir(home) == home / ".claude"
    assert harness_checks.under_installed_plugins(arm / "plugins" / "cache" / "x")
    assert not harness_checks.under_installed_plugins(home / ".claude" / "plugins" / "x")
    # The personal skills dir is found in the moved config dir although its parent is not named
    # `.claude`.
    (arm / "skills" / "mine").mkdir(parents=True)
    (arm / "skills" / "mine" / "SKILL.md").write_text("---\nname: mine\n---\n", encoding="utf-8")
    empty = tmp_path / "empty"
    empty.mkdir()
    assert harness_checks.discover_candidates([empty]) == [arm / "skills"]
    (arm / "agents").mkdir()
    (arm / "agents" / "a.md").write_text("---\nname: probe\nmodel: haiku\n---\n", encoding="utf-8")
    assert subagent_model_gate.agent_definition_model("probe") == "haiku"
    assert subagent_model_gate.agent_definition_model("probe", home=home) is None


# Sites that must keep the literal home rule: each is a standalone script that cannot import
# claude_paths and keeps a local copy of claude_paths.config_dir() instead. "path:reason".
_HOME_RULE_ALLOWLIST = {
    "skills/meta-skill-ab-test/scripts/abarm.py":
        "user_config_dir() copies config_dir(): this skill's scripts never put hooks/ on sys.path",
    "skills/compuse-toolbox/scripts/_claude_config.py":
        "config_dir() copy for the compuse-toolbox jigs, which run on their own",
}
# A string that IS a path into the default config dir (`"~/.claude/projects"`), as an argparse
# default or a constant later expanded. Prose that merely mentions one has whitespace in it.
_TILDE_PATH = re.compile(r"~[/\\]\.claude(?:[/\\]\S*)?")


def _is_home_call(node):
    """`Path.home()`, `pathlib.Path.home()`, `os.path.expanduser("~")` or `expanduser("~")`."""
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
    if name == "home" and not node.args:
        return True
    return (name == "expanduser" and len(node.args) == 1
            and isinstance(node.args[0], ast.Constant) and node.args[0].value == "~")


def _home_claude_paths(tree):
    """Line of every `<home> / ".claude"` expression, <home> being a home call anywhere in the
    left operand: bare, wrapped (`Path(os.path.expanduser("~"))`) or in a conditional
    (`(Path(home) if home is not None else Path.home())`). An `os.path.join(<home>, ".claude")`
    counts too, and so does a string that is a `~/.claude/...` path (docstrings excepted). A
    caller-supplied `Path(home) / ".claude"` has no home call and is not flagged."""
    hits = []
    docstrings = {id(n.body[0].value) for n in ast.walk(tree)
                  if isinstance(n, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
                  and n.body and isinstance(n.body[0], ast.Expr)
                  and isinstance(n.body[0].value, ast.Constant)}
    for node in ast.walk(tree):
        if (isinstance(node, ast.Constant) and isinstance(node.value, str)
                and id(node) not in docstrings and _TILDE_PATH.fullmatch(node.value)):
            hits.append(node.lineno)
            continue
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            left, rights = node.left, [node.right]
        elif (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
              and node.func.attr == "join" and node.args):
            left, rights = node.args[0], node.args[1:2]
        else:
            continue
        if not any(isinstance(r, ast.Constant) and r.value == ".claude" for r in rights):
            continue
        if any(_is_home_call(sub) for sub in ast.walk(left)):
            hits.append(node.lineno)
    return hits


def _shipped_python():
    for py in sorted(PLUGIN.rglob("*.py")):
        if "tests" in py.parts or "__pycache__" in py.parts or py.name == "claude_paths.py":
            continue
        yield py


def test_no_shipped_python_builds_the_claude_config_dir_from_home_by_hand():
    # Claude Code moves its whole config dir to CLAUDE_CONFIG_DIR when that is set, so every
    # path inside it resolves through claude_paths.config_dir(). A hand-built home path reads
    # the real ~/.claude from a sandbox, or misses the user's real config when it was moved.
    offenders, allowed_hits = [], set()
    scanned = 0
    for py in _shipped_python():
        rel = py.relative_to(PLUGIN).as_posix()
        lines = _home_claude_paths(ast.parse(py.read_text(encoding="utf-8")))
        scanned += 1
        if rel in _HOME_RULE_ALLOWLIST:
            allowed_hits.update([rel] if lines else [])
            continue
        offenders.extend(f"{rel}:{line}" for line in lines)
    print(f"scanned {scanned} shipped .py files")
    assert scanned > 100, f"scan examined {scanned} files - refusing a vacuous pass"
    assert offenders == []
    # A stale allowlist entry would exempt a file that no longer needs it.
    assert allowed_hits == set(_HOME_RULE_ALLOWLIST), sorted(set(_HOME_RULE_ALLOWLIST) - allowed_hits)


@pytest.mark.parametrize("source, flagged", [
    ('Path.home() / ".claude" / "x"', True),
    ('pathlib.Path.home() / ".claude"', True),
    ('Path(os.path.expanduser("~")) / ".claude"', True),
    ('os.path.expanduser("~") / ".claude"', True),
    ('(Path(h) if h is not None else Path.home()) / ".claude"', True),
    ('Path(h if h is not None else Path.home()) / ".claude"', True),
    ('os.path.join(os.path.expanduser("~"), ".claude", "x")', True),
    ('Path(home) / ".claude"', False),
    ('Path(proj) / ".claude" / "settings.json"', False),
    ('Path.home() / ".config" / "gh"', False),
    ('os.path.expanduser("~/.ssh") / ".claude"', False),
    ('ap.add_argument("--root", default="~/.claude/projects")', True),
    ('ROOT = "~/.claude"', True),
    ('MSG = "enable it in ~/.claude/settings.json, then restart"', False),
    ('def f():\n    """~/.claude/projects"""', False),
    ('X = "~/.claude-bx-selflearning"', False),
])
def test_the_scan_recognises_each_home_spelling(source, flagged):
    # The detector is proven on positives and negatives, so a green scan means something.
    assert bool(_home_claude_paths(ast.parse(source))) is flagged
