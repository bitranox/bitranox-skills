"""Every whole-call blocking Bash guard tells the model that NOTHING in the refused call ran.

A PreToolUse exit 2 refuses the WHOLE Bash call, not the one statement the guard objected to. An
edit, a write or a version bump bundled into the same command is lost with it, and a refusal that
names only the offending statement reads as if the rest went through. The sentence saying so lives
in one helper, `shell_text.refuse`, and this module pins that every such guard goes through it.

The guard list is DERIVED, never written down: every script hooks.json registers on a PreToolUse
matcher that covers Bash, whose source either exits 2 or calls the helper. A new guard that blocks
with a bare `return 2` therefore lands in the list and fails here until it uses the helper.
"""

import ast
import io
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

import shell_text

HOOKS_DIR = Path(__file__).resolve().parent.parent

# What a hook source looks like when it blocks: a literal exit status of 2, however spelled, or a
# call to the shared helper (which returns 2 itself).
_BLOCKS = re.compile(r"\breturn\s+2\b|\bexit\(\s*2\s*\)|SystemExit\(\s*2\s*\)|\brefuse\(")
_SCRIPT = re.compile(r"hooks/([\w.-]+\.py)")
# Claude Code reads a matcher made only of these characters as an exact name or a `|` list, and
# anything else as an unanchored regex (bitranox:meta-claude-hooks, configuration reference).
_PLAIN_MATCHER = re.compile(r"[A-Za-z0-9_| ,-]*")


def _matches_bash(matcher):
    if matcher in ("", "*"):
        return True
    if _PLAIN_MATCHER.fullmatch(matcher):
        return "Bash" in [part.strip() for part in re.split(r"[|,]", matcher)]
    return re.search(matcher, "Bash") is not None


def _bash_pretooluse_scripts():
    data = json.loads((HOOKS_DIR / "hooks.json").read_text(encoding="utf-8"))
    scripts = set()
    for group in data["hooks"].get("PreToolUse", []):
        if not _matches_bash(group.get("matcher") or ""):
            continue
        for handler in group.get("hooks", []):
            names = _SCRIPT.findall(handler.get("command") or "")
            if names:
                scripts.add(names[-1])
    return scripts


def blocking_guards():
    """The Bash PreToolUse scripts that can refuse a call, read from hooks.json and their source."""
    return sorted(name for name in _bash_pretooluse_scripts()
                  if _BLOCKS.search((HOOKS_DIR / name).read_text(encoding="utf-8")))


# A module-level name bound to 2 that is NOT a hook refusal: the exit code of a CLI mode of the same
# script. Each is proved confined to those modes by `test_a_cli_only_two_never_returns_in_hook_mode`.
_CLI_ONLY_TWOS = {"repo-gate.py": "COULD_NOT_RUN"}
# The flags a CLI-mode branch of repo-gate's `main` tests before returning its could-not-run code.
_CLI_MODE_NAMES = frozenset({"ci", "mirrors", "pre_push"})


def _module_twos(tree, exempt=None):
    """Names the module binds to the constant 2 at its top level (`BLOCK = 2`, `BLOCK: int = 2`),
    `exempt` left out."""
    names = set()
    for node in tree.body:
        targets = node.targets if isinstance(node, ast.Assign) else \
            [node.target] if isinstance(node, ast.AnnAssign) else []
        if isinstance(getattr(node, "value", None), ast.Constant) and node.value.value == 2:
            names.update(target.id for target in targets if isinstance(target, ast.Name))
    return names - {exempt}


def _is_two(node, twos):
    """True for a literal 2, or a name the module binds to 2 at its top level."""
    if isinstance(node, ast.Constant):
        return node.value == 2
    return isinstance(node, ast.Name) and node.id in twos


def _literal_exit_twos(tree, exempt=None):
    """Each place a module returns or exits with a 2 - a literal, or a module-level name bound to
    one (except `exempt`) - instead of going through the helper."""
    found, twos = [], _module_twos(tree, exempt)
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and node.value is not None and _is_two(node.value, twos):
            found.append(node.lineno)
        if isinstance(node, ast.Call) and node.args and _is_two(node.args[0], twos):
            func = node.func
            name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
            if name in ("exit", "SystemExit", "_exit"):
                found.append(node.lineno)
    return found


def test_a_module_constant_bound_to_two_counts_as_a_literal_two():
    """OPEN-WORK [1070]: `BLOCK = 2` then `return BLOCK` exits 2 without the helper as surely as
    `return 2` does, and the literal-only check let it through."""
    source = (
        "import sys\n"
        "BLOCK = 2\n"
        "QUIET: int = 0\n"
        "def f():\n"
        "    return BLOCK\n"
        "def g():\n"
        "    sys.exit(BLOCK)\n"
        "def h():\n"
        "    return QUIET\n"
    )
    assert _literal_exit_twos(ast.parse(source)) == [5, 7]


def test_control_a_name_bound_to_two_only_inside_a_function_is_not_resolved():
    """Only a MODULE-level binding is a constant the whole file shares; a local may be rebound."""
    source = "def f():\n    code = 2\n    return code\n"
    assert _literal_exit_twos(ast.parse(source)) == []


def _parents(tree):
    return {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}


def _guarded_by_a_cli_mode(node, parents):
    """True when an `if` around `node` tests one of the CLI-mode flags."""
    while node in parents:
        node = parents[node]
        if isinstance(node, ast.If) and {n.id for n in ast.walk(node.test)
                                         if isinstance(n, ast.Name)} & _CLI_MODE_NAMES:
            return True
    return False


@pytest.mark.parametrize("guard, name", sorted(_CLI_ONLY_TWOS.items()))
def test_a_cli_only_two_never_returns_in_hook_mode(guard, name):
    """The exemption holds only while every `return <name>` sits where hook mode cannot reach it:
    in `main` before hook mode is decided or under a CLI-mode `if`, or in `entry` behind its
    CLI-flag check. A new `return <name>` anywhere else fails here, not silently."""
    tree = ast.parse((HOOKS_DIR / guard).read_text(encoding="utf-8"))
    parents, functions = _parents(tree), {}
    for function in ast.walk(tree):
        if isinstance(function, ast.FunctionDef):
            for node in ast.walk(function):
                functions.setdefault(node, function)
    main = next(f for f in tree.body if isinstance(f, ast.FunctionDef) and f.name == "main")
    decided = next(n.lineno for n in ast.walk(main) if isinstance(n, ast.Assign)
                   and any(getattr(t, "id", "") == "hook_mode" for t in n.targets))
    sites = [n for n in ast.walk(tree) if isinstance(n, ast.Return)
             and isinstance(n.value, ast.Name) and n.value.id == name]
    assert sites, f"{guard} no longer returns {name}: drop the exemption"
    for site in sites:
        function = functions[site]
        if function.name == "entry":
            assert "_CLI_FLAGS" in ast.unparse(function), site.lineno
            continue
        assert function.name == "main", (site.lineno, function.name)
        assert site.lineno < decided or _guarded_by_a_cli_mode(site, parents), site.lineno


def test_control_an_unguarded_cli_two_is_caught():
    """The confinement check must fail on a `return COULD_NOT_RUN` that hook mode reaches."""
    source = ("COULD_NOT_RUN = 2\n"
              "def main():\n"
              "    hook_mode = True\n"
              "    return COULD_NOT_RUN\n")
    tree = ast.parse(source)
    site = tree.body[1].body[1]
    assert not _guarded_by_a_cli_mode(site, _parents(tree))
    assert site.lineno > tree.body[1].body[0].lineno


def test_the_enumeration_finds_the_known_guards():
    # A derived list that came back empty would pass every parametrized case below vacuously.
    guards = blocking_guards()
    assert "block-partial-typecheck.py" in guards
    assert "block-git-semicolon-chain.py" in guards
    assert "git-footgun-guard.py" in guards
    assert len(guards) >= 10, guards


def test_the_enumeration_skips_advisory_hooks():
    # A nudge that only adds context never refuses a call, so it owes no footer.
    assert "gated-prep-nudge.py" not in blocking_guards()


@pytest.mark.parametrize("guard", blocking_guards())
def test_every_blocking_guard_refuses_through_the_shared_helper(guard):
    source = (HOOKS_DIR / guard).read_text(encoding="utf-8")
    assert _literal_exit_twos(ast.parse(source), _CLI_ONLY_TWOS.get(guard)) == [], (
        f"{guard} blocks with a literal 2; use `return shell_text.refuse(message)` so the refusal "
        "says that nothing in the call ran")
    assert re.search(r"\brefuse\(", source), f"{guard} never calls shell_text.refuse"


def test_refuse_writes_the_message_then_the_footer_and_returns_two():
    stream = io.StringIO()
    assert shell_text.refuse("BLOCKED: reason", stream=stream) == 2
    assert stream.getvalue() == "BLOCKED: reason\n" + shell_text.WHOLE_CALL_REFUSED + "\n"
    assert "NOTHING" in shell_text.WHOLE_CALL_REFUSED


def test_refuse_does_not_double_the_newline_of_a_message_that_has_one():
    stream = io.StringIO()
    shell_text.refuse("line one\n", stream=stream)
    assert stream.getvalue() == "line one\n" + shell_text.WHOLE_CALL_REFUSED + "\n"


def test_refuse_defaults_to_the_real_stderr(capsys):
    shell_text.refuse("x")
    assert shell_text.WHOLE_CALL_REFUSED in capsys.readouterr().err


# End to end over the real scripts: the footer reaches the stderr Claude Code shows the model.
_TRIGGERS = {
    "git-footgun-guard.py": "git rev-parse --short HEAD HEAD~1",
    "block-git-semicolon-chain.py": "git commit -m x; git push",
    "block-pgrep-self-match.py": "pgrep -f nginx",
    "block-sed-structured-files.py": "sed -i 's/a/b/' config.json",
    "shell-prefix-selfref-guard.py": 'TOKEN=abc echo "$TOKEN"',
}


@pytest.mark.parametrize("guard", sorted(_TRIGGERS))
def test_a_real_refusal_ends_with_the_footer(guard, tmp_path):
    assert guard in blocking_guards()
    event = {"tool_name": "Bash", "hook_event_name": "PreToolUse", "cwd": str(tmp_path),
             "tool_input": {"command": _TRIGGERS[guard]}}
    env = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
    run = subprocess.run([sys.executable, str(HOOKS_DIR / guard)], input=json.dumps(event),
                         capture_output=True, text=True, encoding="utf-8", errors="replace",
                         cwd=str(tmp_path), env=env, timeout=60)
    assert run.returncode == 2, run.stderr
    assert shell_text.WHOLE_CALL_REFUSED in run.stderr


# A `permissionDecision: deny` refuses the whole call just as exit 2 does (OPEN-WORK [1070]).
# A Bash-matched script that denies only OTHER tools owes no footer; each such exemption names the
# one function its deny is confined to, and the test below proves the confinement still holds.
_DENIES_ONLY_ELSEWHERE = {
    "missing-mechanism-nudge.py": "_answer_question",   # refuses AskUserQuestion, never a shell call
}


def deny_guards():
    """The Bash PreToolUse scripts whose source emits a `permissionDecision: deny`."""
    return sorted(name for name in _bash_pretooluse_scripts()
                  if re.search(r"[\"']deny[\"']", (HOOKS_DIR / name).read_text(encoding="utf-8")))


def test_the_deny_enumeration_finds_the_known_guard():
    assert "sha-literal-nudge.py" in deny_guards()


@pytest.mark.parametrize("guard", deny_guards())
def test_every_bash_deny_carries_the_footer(guard):
    source = (HOOKS_DIR / guard).read_text(encoding="utf-8")
    if guard in _DENIES_ONLY_ELSEWHERE:
        return
    assert re.search(r"\bdeny_reason\(", source), (
        f"{guard} denies a Bash call without the whole-call footer; build the reason with "
        "`shell_text.deny_reason(message)`")


@pytest.mark.parametrize("guard, confined_to", sorted(_DENIES_ONLY_ELSEWHERE.items()))
def test_an_exempt_deny_is_still_confined_to_its_one_function(guard, confined_to):
    tree = ast.parse((HOOKS_DIR / guard).read_text(encoding="utf-8"))
    callers = {function.name for function in ast.walk(tree) if isinstance(function, ast.FunctionDef)
               for node in ast.walk(function)
               if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "_deny"}
    assert callers == {confined_to}, callers


def test_deny_reason_appends_the_footer_once():
    assert shell_text.deny_reason("BLOCKED: x") == "BLOCKED: x\n" + shell_text.WHOLE_CALL_REFUSED
    assert shell_text.deny_reason("BLOCKED: x\n") == "BLOCKED: x\n" + shell_text.WHOLE_CALL_REFUSED
