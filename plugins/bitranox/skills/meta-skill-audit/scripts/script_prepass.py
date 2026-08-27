#!/usr/bin/env python3
"""Deterministic checks over a shipped-script corpus, run BEFORE any reviewer spends a token.

Anything a script can decide, decide with a script: it covers the whole corpus in seconds, it cannot
hallucinate a quote, and it costs nothing to re-run after every fix. The hits are then fed into each
reviewer's prompt as ALREADY KNOWN, because without that 133 reviewers independently rediscover the
same 28 lines and the triage drowns in duplicates.

WHAT IS DELIBERATELY NOT HERE. The plugin's own `hooks/repo-gate.py` and `hooks/harness_checks.py`
already implement a large gate, and re-implementing any of it would create a second rule that can
drift from the one that actually blocks a commit. Already covered there, do not add it here:

    CRLF endings ............... repo_gate.check_lf_endings
    JSON parses ................ repo_gate.check_json_valid
    a package has tests ........ repo_gate.check_tests_exist / harness_checks.packages_missing_tests
    duplicate basenames ........ repo_gate.check_duplicate_basenames
    secrets and private keys ... repo_gate.check_secrets
    SKILL.md front matter ...... repo_gate.check_frontmatter / harness_checks.frontmatter_problems
    a tests dir that cannot be collected ... harness_checks.uncollectable_tests
    a registration naming a missing path ... harness_checks.registration_problems
    an unregistered hook ................... harness_checks.orphan_scripts
    retired shims, stale bytecode .......... harness_checks.shim_problems / graveyard_entries

`test_script_prepass.py` asserts no check here shares a name with a `repo_gate.check_*`, which is the
only automatic defence against that rule rotting.

Pure standard library.
"""

import argparse
import ast
import json
import re
import subprocess
import sys
from pathlib import Path

# A hook is launched by run-python.sh, which execs a plain python3: no venv, no PEP 723 resolution.
# So a hook may import only the standard library and its own siblings.
_STDLIB = set(getattr(sys, "stdlib_module_names", ()))

_PEP723_OPEN = re.compile(r"^#\s*///\s*script\s*$", re.M)
_PEP723_CLOSE = re.compile(r"^#\s*///\s*$", re.M)
_REQUIRES_PY = re.compile(r"requires-python\s*=\s*[\"']([^\"']+)[\"']")
_FLOOR = re.compile(r">=\s*(\d+)\.(\d+)")
_TMP_LITERAL = re.compile(r"[\"'](/tmp/|/var/(?!$))")
_FLAG_IN_TEXT = re.compile(r"(?<![\w-])--[a-z][a-z0-9-]{1,30}")


def _parse(path):
    """The AST of a Python file, or None when it does not parse."""
    try:
        return ast.parse(Path(path).read_text(encoding="utf-8", errors="replace"))
    except (OSError, SyntaxError, ValueError):
        return None


def _lines(path):
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []


def syntax_errors(paths):
    """Every shipped example must at least parse. Returns [(rel, line, message)]."""
    out = []
    for rel, path in paths:
        try:
            ast.parse(Path(path).read_text(encoding="utf-8", errors="replace"))
        except SyntaxError as exc:
            out.append((rel, exc.lineno or 0, "does not parse: %s" % exc.msg))
        except (OSError, ValueError) as exc:
            out.append((rel, 0, "unreadable: %s" % exc))
    return out


def _guarded_nodes(tree):
    """Every node sitting inside a try: or a function/class body.

    An import there is conditional or lazy, which is exactly the shape the fail-open rule wants,
    so it must not be reported as unguarded."""
    guarded = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Try, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            for child in ast.walk(node):
                if child is not node:
                    guarded.add(id(child))
    return guarded


def unguarded_third_party_imports(paths, siblings=()):
    """A non-stdlib import at module level with no try/except, in something that gets no provisioning.

    AST, never grep: a line-prefix grep over this tree matches docstring prose that merely starts
    with the word `from`."""
    siblings = {str(s).replace("-", "_") for s in siblings}
    out = []
    for rel, path in paths:
        tree = _parse(path)
        if tree is None:
            continue
        guarded = _guarded_nodes(tree)
        for node in ast.walk(tree):
            if id(node) in guarded:
                continue
            if isinstance(node, ast.Import):
                names = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [] if node.level else [(node.module or "").split(".")[0]]
            else:
                continue
            for name in names:
                if name and name not in _STDLIB and name.replace("-", "_") not in siblings:
                    out.append((rel, node.lineno,
                                "module-level import of non-stdlib '%s' with no ImportError "
                                "fallback" % name))
    return out


def _call_name(node):
    """`subprocess.run` / `run` for a Call node, or ''."""
    func = node.func
    if isinstance(func, ast.Attribute):
        base = func.value.id if isinstance(func.value, ast.Name) else ""
        return ("%s.%s" % (base, func.attr)).strip(".")
    return func.id if isinstance(func, ast.Name) else ""


def subprocess_text_without_encoding(paths):
    """`text=True` with no `encoding=`: decodes with the machine's locale codec.

    Fails differently on each platform and never on the author's: Windows decodes in a reader thread
    so stdout comes back None, POSIX raises past handlers that only catch OSError."""
    wanted = {"run", "Popen", "check_output", "subprocess.run", "subprocess.Popen",
              "subprocess.check_output"}
    out = []
    for rel, path in paths:
        tree = _parse(path)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or _call_name(node) not in wanted:
                continue
            kw = {k.arg for k in node.keywords if k.arg}
            textish = {"text", "universal_newlines"} & kw
            if textish and "encoding" not in kw:
                out.append((rel, node.lineno,
                            "subprocess with %s and no encoding= (locale-codec decode)"
                            % sorted(textish)[0]))
    return out


def _is_platform_guarded(func):
    """True when a function already branches on the platform.

    `harness_checks.is_executable` is the reference shape: it returns False off POSIX before ever
    reaching os.access, so its X_OK call is correct and reporting it is a false positive."""
    source = ast.dump(func)
    return ("attr='name'" in source and "id='os'" in source) or \
           ("attr='platform'" in source and "id='sys'" in source) or \
           "posix" in source


def os_access_x_ok(paths, allow=()):
    """An UNGUARDED `os.access(p, os.X_OK)` reports True for every file on Windows.

    The concept does not exist there, so the branch under it is dead and the check silently stops
    checking. A call inside a platform-guarded function is fine and is not reported."""
    allow = set(allow)
    out = []
    for rel, path in paths:
        if rel in allow:
            continue
        tree = _parse(path)
        if tree is None:
            continue
        guarded = set()
        for func in ast.walk(tree):
            if isinstance(func, (ast.FunctionDef, ast.AsyncFunctionDef)) and _is_platform_guarded(func):
                guarded.update(id(c) for c in ast.walk(func))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or _call_name(node) != "os.access":
                continue
            if id(node) in guarded:
                continue
            for arg in node.args[1:]:
                if isinstance(arg, ast.Attribute) and arg.attr == "X_OK":
                    out.append((rel, node.lineno,
                                "unguarded os.access(..., os.X_OK) is always True on Windows"))
    return out


def shlex_on_paths(paths, allow=()):
    """`shlex` in POSIX mode eats the backslashes out of a Windows path. Reported as a lead."""
    allow = set(allow)
    out = []
    for rel, path in paths:
        if rel in allow:
            continue
        tree = _parse(path)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and _call_name(node) in ("shlex.split", "shlex.quote"):
                out.append((rel, node.lineno,
                            "shlex in POSIX mode eats backslashes in a Windows path (lead)"))
    return out


def hardcoded_tmp(paths):
    """A literal /tmp or /var path is drive-relative on Windows."""
    out = []
    for rel, path in paths:
        for n, line in enumerate(_lines(path), 1):
            if line.lstrip().startswith("#"):
                continue
            if _TMP_LITERAL.search(line):
                out.append((rel, n, "hard-coded POSIX path literal (drive-relative on Windows)"))
    return out


def pep723_block(path):
    """The text of a script's PEP 723 inline metadata block, or ''."""
    text = "\n".join(_lines(path))
    opened = _PEP723_OPEN.search(text)
    if not opened:
        return ""
    closed = _PEP723_CLOSE.search(text, opened.end())
    return text[opened.end():closed.start()] if closed else ""


def pep723_problems(paths, ci_min="3.11", hook_kinds=()):
    """A hook must carry NO PEP 723 block, and no script may demand MORE than CI's oldest cell.

    A hook is launched by `run-python.sh`, which resolves nothing, so inline metadata on one is a
    claim the runtime never honours.

    On floors: ci.yml states 3.11 is the supported minimum and that shipped scripts declare their
    own floors, so a floor BELOW that (`>=3.10`) is a deliberate, wider promise and is correct. Only
    a floor ABOVE ci_min is a defect - that script cannot run on the oldest cell CI tests."""
    minimum = tuple(int(p) for p in ci_min.split("."))
    hook_rels = set(hook_kinds)
    out = []
    for rel, path in paths:
        block = pep723_block(path)
        if not block:
            continue
        if rel in hook_rels:
            out.append((rel, 1, "a hook carries PEP 723 metadata, but run-python.sh resolves none"))
            continue
        found = _REQUIRES_PY.search(block)
        if not found:
            continue
        floor = _FLOOR.search(found.group(1))
        if floor and (int(floor.group(1)), int(floor.group(2))) > minimum:
            out.append((rel, 1, "requires-python floor %s is ABOVE the CI minimum %s, so the "
                                "oldest cell cannot run it" % (found.group(1), ci_min)))
    return out


def per_file_test_module(paths, test_roots=()):
    """A shipped script with no test module naming its stem. A LEAD: coverage may live elsewhere.

    Distinct from `repo_gate.check_tests_exist`, which asks the question per PACKAGE and passes as
    long as the package has any tests at all."""
    corpus = []
    for root in test_roots:
        for path in Path(root).rglob("test_*.py"):
            corpus.append(path.read_text(encoding="utf-8", errors="replace"))
    blob = "\n".join(corpus)
    out = []
    for rel, path in paths:
        if not str(rel).endswith(".py"):
            continue
        stem = Path(rel).stem
        if stem not in blob and stem.replace("-", "_") not in blob:
            out.append((rel, 0, "no test module anywhere names '%s' (lead: coverage may be "
                                "indirect)" % stem))
    return out


def _run(cmd, cwd, timeout=20):
    """Default subprocess seam, injectable so the tests never spawn anything."""
    return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=timeout)


def argparse_flags_vs_docs(targets, room, docs_text, run=_run):
    """Flags the shipped documentation names that `--help` does not accept.

    A non-zero exit or a timeout is UNMEASURED, never a finding: plenty of these cannot run in a
    room with no host, no browser and no network."""
    out = []
    for rel in targets:
        documented = set(_FLAG_IN_TEXT.findall(docs_text.get(rel, "")))
        if not documented:
            continue
        try:
            proc = run([sys.executable, rel, "--help"], room)
        except Exception:
            continue                                     # UNMEASURED: could not even launch it
        if proc.returncode != 0:
            continue                                     # UNMEASURED: no parser, or it needs stdin
        offered = set(_FLAG_IN_TEXT.findall(proc.stdout or ""))
        for flag in sorted(documented - offered):
            out.append((rel, 0, "documentation names %s but --help does not offer it" % flag))
    return out


def js_parse(paths, run=_run, room="."):
    """`node --check` where node exists; silent otherwise. The only mechanical check for the JS."""
    out = []
    for rel, _path in paths:
        try:
            proc = run(["node", "--check", rel], room)
        except Exception:
            return []                                    # UNMEASURED: no node on this machine
        if proc.returncode != 0:
            out.append((rel, 0, "node --check fails: %s" % (proc.stderr or "").strip()[:200]))
    return out


CHECKS = {
    "syntax_errors": syntax_errors,
    "unguarded_third_party_imports": unguarded_third_party_imports,
    "subprocess_text_without_encoding": subprocess_text_without_encoding,
    "os_access_x_ok": os_access_x_ok,
    "shlex_on_paths": shlex_on_paths,
    "hardcoded_tmp": hardcoded_tmp,
    "pep723_problems": pep723_problems,
    "per_file_test_module": per_file_test_module,
}


def group_by_file(hits):
    """{rel: ["line N: message", ...]} - the shape a reviewer prompt interpolates."""
    out = {}
    for rel, line, message in hits:
        out.setdefault(rel, []).append("line %d: %s" % (line, message) if line else message)
    return out


def run_prepass(room, targets, ci_min="3.11"):
    """Every deterministic check over the enumerated corpus. Returns (per_file, summary_lines)."""
    room = Path(room)
    py = [(rel, room / rel) for rel, _k in targets if rel.endswith(".py")]
    js = [(rel, room / rel) for rel, _k in targets if rel.endswith(".js")]
    hooks = [rel for rel, kind in targets if kind in ("hook", "hook-lib")]
    hook_py = [(rel, path) for rel, path in py if rel in set(hooks)]
    siblings = [p.stem for p in room.rglob("*.py")]
    test_roots = [d for d in room.rglob("tests") if d.is_dir()]

    hits, summary = [], []
    for name, fn in (("syntax_errors", lambda: syntax_errors(py)),
                     ("unguarded_third_party_imports",
                      lambda: unguarded_third_party_imports(hook_py, siblings)),
                     ("subprocess_text_without_encoding",
                      lambda: subprocess_text_without_encoding(py)),
                     ("os_access_x_ok", lambda: os_access_x_ok(py)),
                     ("shlex_on_paths", lambda: shlex_on_paths(py)),
                     ("hardcoded_tmp", lambda: hardcoded_tmp(py)),
                     ("pep723_problems", lambda: pep723_problems(py, ci_min, hooks)),
                     ("per_file_test_module", lambda: per_file_test_module(py, test_roots))):
        found = fn()
        hits.extend(found)
        summary.append("%-34s %d hit(s)" % (name, len(found)))
    return group_by_file(hits), summary


def main(argv=None):
    ap = argparse.ArgumentParser(description="Deterministic pre-pass over a shipped-script corpus.")
    ap.add_argument("--room", required=True, help="the room's plugin dir")
    ap.add_argument("--json", action="store_true", help="emit the per-file map as JSON")
    args = ap.parse_args(sys.argv[1:] if argv is None else argv)
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import audit_skills  # noqa: PLC0415 - sibling script, resolved from this file's own dir

    targets = audit_skills.script_targets(args.room)
    per_file, summary = run_prepass(args.room, targets)
    if args.json:
        print(json.dumps(per_file, indent=2, sort_keys=True))
        return 0
    for line in summary:
        print(line)
    print("TOTAL: %d file(s) with at least one hit" % len(per_file))
    return 0


if __name__ == "__main__":
    sys.exit(main())
