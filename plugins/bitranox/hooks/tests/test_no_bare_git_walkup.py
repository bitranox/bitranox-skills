"""No shipped script walks up the tree taking any `.git` entry as a repository.

An empty `.git` directory left in /tmp by some other process made every path under it read as
one repository rooted at /tmp, twice in two days, each time through a walker that tested bare
existence: first two hooks, then `queue_home` and git_state's ancestor walk, which the first fix
had missed. git accepts only a `.git` directory holding HEAD or a `.git` file starting
`gitdir: ` (`shell_text.is_work_tree_root`). This test finds every function that walks
`.parents` and asks an existence-style question of a `.git` path, so the next walker cannot be
missed the same way; a site that is right to test bare existence is listed with its reason.
"""

import ast
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2]

# A function that walks up and asks whether ANY `.git` entry exists. Each answer here must say
# why an empty `.git` directory cannot make it misreport.
ALLOWED = {
    ("hooks/repo-gate.py", "_in_main_checkout"):
        "a `.git` directory ends the walk with None (not a linked worktree), the safe answer",
    ("skills/compuse-toolbox/scripts/grep_all.py", "_has_git_entry"):
        "asked only after git rev-parse failed: any `.git` entry makes the count unknown, never zero",
}

_EXISTENCE_CALLS = {"exists", "is_dir", "lexists", "isdir"}


def _mentions_git(node):
    return any(isinstance(n, ast.Constant) and n.value == ".git" for n in ast.walk(node))


def _walks_parents(func):
    return any(isinstance(n, ast.Attribute) and n.attr == "parents" for n in ast.walk(func))


def _bare_git_existence(func):
    for node in ast.walk(func):
        if not isinstance(node, ast.Call):
            continue
        name = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", "")
        if name not in _EXISTENCE_CALLS:
            continue
        if _mentions_git(node):
            return True
        # `marker = root / ".git"` then `marker.is_dir()`: follow one local name.
        target = node.func.value if isinstance(node.func, ast.Attribute) else None
        if isinstance(target, ast.Name) and _assigned_git(func, target.id):
            return True
    return False


def _assigned_git(func, name):
    for node in ast.walk(func):
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == name for t in node.targets):
            if _mentions_git(node.value):
                return True
    return False


def _offenders():
    found = []
    for path in sorted(PLUGIN.rglob("*.py")):
        rel = path.relative_to(PLUGIN).as_posix()
        if "/tests/" in rel or rel.startswith("tests/") or "/." in rel:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
        for func in ast.walk(tree):
            if isinstance(func, (ast.FunctionDef, ast.AsyncFunctionDef)) and _walks_parents(func) \
                    and _bare_git_existence(func):
                found.append((rel, func.name))
    return found


def test_no_walker_takes_a_bare_git_entry_as_a_repository():
    offenders = [site for site in _offenders() if site not in ALLOWED]
    assert offenders == [], (
        "these functions walk up and test a `.git` path for bare existence; use "
        "shell_text.is_work_tree_root (hooks) or a HEAD/gitdir check, or list the site in "
        "ALLOWED with why an empty `.git` directory cannot make it misreport: %r" % offenders)


def test_every_allowed_site_still_exists():
    # An entry whose function was renamed or fixed would silently allow the next one of that name.
    assert set(ALLOWED) <= set(_offenders())


def test_the_scan_sees_a_planted_walker(tmp_path):
    source = (
        "def find(start):\n"
        "    for p in (start, *start.parents):\n"
        "        marker = p / '.git'\n"
        "        if marker.is_dir():\n"
        "            return p\n")
    func = ast.parse(source).body[0]
    assert _walks_parents(func) and _bare_git_existence(func)
