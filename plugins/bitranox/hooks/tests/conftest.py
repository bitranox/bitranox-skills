"""Pytest config: load the hyphenated hook modules so tests can import them.

The hook files use hyphenated names (validate-structured-files.py), which are not
importable with a plain `import`. Load each from its path and register it in
sys.modules under an underscore alias so test files can `import <alias>`.
"""

import importlib.util
import sys
from pathlib import Path

HOOKS_DIR = Path(__file__).resolve().parent.parent

# filename stem -> import alias used by the test modules
_HOOK_MODULES = {
    "validate-structured-files": "validate_structured_files",
    "block-pgrep-self-match": "block_pgrep_self_match",
    "self-improve-gate": "self_improve_gate",
    "repo-gate": "repo_gate",
    "tell-sweep": "tell_sweep",
    "git-footgun-guard": "git_footgun_guard",
    "session-start": "session_start",
}

for _stem, _alias in _HOOK_MODULES.items():
    _spec = importlib.util.spec_from_file_location(_alias, HOOKS_DIR / (_stem + ".py"))
    _module = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_module)
    sys.modules[_alias] = _module
