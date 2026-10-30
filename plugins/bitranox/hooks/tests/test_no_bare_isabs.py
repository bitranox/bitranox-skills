"""No shipped plugin Python calls `os.path.isabs` except where the path cannot be a drive-less root.

From Python 3.13 `os.path.isabs` on Windows answers False for a root with no drive (`/work/x`,
`\\work\\x`), while Git Bash and PowerShell still land at that root. A path read from a COMMAND's
text is exactly such a path, so a check written with `isabs` decides differently by host Python
version, and the defect reaches only the Windows CI cell of the newest Python. It shipped twice
that way although the rule was written down, so it is enforced here: use `shell_text.is_rooted`
(or `posixpath.isabs` inside a POSIX-only arm).

`ALLOWED` names the few calls whose operand never comes from command text, each with its reason.
"""
import ast
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[2]
_SKIP_PARTS = {"__pycache__", "node_modules", "tests"}

# (file relative to the plugin root, enclosing function) -> why `os.path.isabs` is right there.
ALLOWED = {
    ("hooks/shell_text.py", "is_rooted"): "the sanctioned helper itself, which adds the drive-less "
                                          "root on Windows",
    ("hooks/self_improve_signals.py", "ensure_gitignored"): "the operand is a path git printed "
                                                           "(rev-parse --git-path), which carries "
                                                           "its drive on Windows",
}


def _shipped_python_files():
    for path in sorted(PLUGIN_ROOT.rglob("*.py")):
        rel = path.relative_to(PLUGIN_ROOT).parts
        if any(p in _SKIP_PARTS or p.startswith(".venv") for p in rel):
            continue
        yield path


def _isabs_aliases(tree):
    """Names bound to os.path.isabs by `from os.path import isabs [as x]`."""
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "os.path":
            names |= {alias.asname or alias.name for alias in node.names if alias.name == "isabs"}
    return names


def _is_os_path_isabs(func, aliases):
    if isinstance(func, ast.Name):
        return func.id in aliases
    return (isinstance(func, ast.Attribute) and func.attr == "isabs"
            and isinstance(func.value, ast.Attribute) and func.value.attr == "path"
            and isinstance(func.value.value, ast.Name) and func.value.value.id == "os")


def _calls(source):
    """(line, enclosing function name or '<module>') of every os.path.isabs call in `source`."""
    tree = ast.parse(source)
    aliases = _isabs_aliases(tree)
    found = []

    def visit(node, owner):
        for child in ast.iter_child_nodes(node):
            inner = child.name if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) else owner
            if isinstance(child, ast.Call) and _is_os_path_isabs(child.func, aliases):
                found.append((child.lineno, owner))
            visit(child, inner)

    visit(tree, "<module>")
    return found


def test_the_walk_sees_the_plugin_tree():
    """A walk rooted at the wrong directory finds nothing and passes vacuously."""
    names = {p.name for p in _shipped_python_files()}
    assert {"shell_text.py", "repo-gate.py", "git-path-not-here-nudge.py"} <= names


def test_the_detector_finds_each_spelling_and_its_owner():
    source = (
        "import os\nfrom os.path import isabs as ia\n"
        "def f(p):\n    return os.path.isabs(p)\n"
        "def g(p):\n    return ia(p)\n"
        "import posixpath\ndef h(p):\n    return posixpath.isabs(p)\n"
    )
    assert _calls(source) == [(4, "f"), (6, "g")]


def test_every_allowed_entry_is_still_a_real_call():
    """An allowance whose call is gone would silently permit a new one in that function."""
    present = set()
    for path in _shipped_python_files():
        rel = path.relative_to(PLUGIN_ROOT).as_posix()
        present |= {(rel, owner) for _line, owner in _calls(path.read_text(encoding="utf-8"))}
    assert set(ALLOWED) <= present, set(ALLOWED) - present


def test_no_shipped_python_judges_a_path_with_bare_os_path_isabs():
    offenders = []
    for path in _shipped_python_files():
        rel = path.relative_to(PLUGIN_ROOT).as_posix()
        for line, owner in _calls(path.read_text(encoding="utf-8")):
            if (rel, owner) not in ALLOWED:
                offenders.append("%s:%d in %s" % (rel, line, owner))
    assert offenders == [], ("use shell_text.is_rooted (os.path.isabs rejects /x on Windows "
                             "from Python 3.13):\n" + "\n".join(offenders))
