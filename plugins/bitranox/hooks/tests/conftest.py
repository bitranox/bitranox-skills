"""Pytest config: load the hyphenated hook modules so tests can import them.

The hook files use hyphenated names (validate-structured-files.py), which are not
importable with a plain `import`. Load each from its path and register it in
sys.modules under an underscore alias so test files can `import <alias>`.
"""

import importlib.util
import sys
from pathlib import Path

HOOKS_DIR = Path(__file__).resolve().parent.parent

# Put the hooks dir on sys.path so the hyphenated hooks can import sibling underscore
# modules (e.g. self_improve_signals) at load time, and test files can import them directly.
if str(HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(HOOKS_DIR))

# filename stem -> import alias used by the test modules
_HOOK_MODULES = {
    "validate-structured-files": "validate_structured_files",
    "block-pgrep-self-match": "block_pgrep_self_match",
    "block-partial-typecheck": "block_partial_typecheck",
    "self-improve-gate": "self_improve_gate",
    "self-improve-audit": "self_improve_audit",
    "post-compact-nudge": "post_compact_nudge",
    "repo-gate": "repo_gate",
    "tell-sweep": "tell_sweep",
    "commit-tell-sweep": "commit_tell_sweep",
    "git-footgun-guard": "git_footgun_guard",
    "git-commit-branch-guard": "git_commit_branch_guard",
    "block-sed-structured-files": "block_sed_structured_files",
    "session-start": "session_start",
    "session-banner": "session_banner",
    "reformat-md-tables": "reformat_md_tables",
    "recall-memory": "recall_memory",
    "subagent-model-gate": "subagent_model_gate",
    "subagent-backstop-nudge": "subagent_backstop_nudge",
    "skill-edit-guard": "skill_edit_guard",
    "skill-router": "skill_router",
    "store-edit-guard": "store_edit_guard",
}

for _stem, _alias in _HOOK_MODULES.items():
    _spec = importlib.util.spec_from_file_location(_alias, HOOKS_DIR / (_stem + ".py"))
    _module = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_module)
    sys.modules[_alias] = _module


import types as _types

import pytest as _pytest


@_pytest.fixture
def two_trees(tmp_path, monkeypatch):
    """Two INDEPENDENT knowledge trees under tmp_path/work (OUTSIDE the isolated HOME at
    tmp_path/home): work/marketing and work/bakery, each with its own top CLAUDE.md +
    .claude-memory store + a nested project dir carrying its own CLAUDE.md."""
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True, exist_ok=True)   # tolerate a module-level home fixture
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    work = tmp_path / "work"
    tops = {}
    for name in ("marketing", "bakery"):
        top = work / name
        proj = top / "campaigns" / "proj1" if name == "marketing" else top / "recipes" / "proj1"
        proj.mkdir(parents=True)
        (top / "CLAUDE.md").write_text("%s tree top\n" % name, encoding="utf-8")
        (top / ".claude-memory").mkdir()
        (proj / "CLAUDE.md").write_text("%s proj\n" % name, encoding="utf-8")
        tops[name] = (top, proj)
    return _types.SimpleNamespace(
        home=home, root=work,
        top_a=tops["marketing"][0], proj_a=tops["marketing"][1],
        top_b=tops["bakery"][0], proj_b=tops["bakery"][1],
    )
