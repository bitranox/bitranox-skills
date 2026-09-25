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
import traceback
from pathlib import Path

# A hook is launched by run-python.sh, which execs a plain python3: no venv, no PEP 723 resolution.
# So a hook may import only the standard library and its own siblings.
_STDLIB = set(getattr(sys, "stdlib_module_names", ()))

_PEP723_OPEN = re.compile(r"^#\s*///\s*script\s*$", re.M)
_PEP723_CLOSE = re.compile(r"^#\s*///\s*$", re.M)
_REQUIRES_PY = re.compile(r"requires-python\s*=\s*[\"']([^\"']+)[\"']")
_FLOOR = re.compile(r">=\s*(\d+)\.(\d+)")
# A quoted /tmp or /var, bare or followed by a path: `Path("/tmp") / "x"` is the same hazard as
# "/tmp/x". A longer name that merely starts with those letters ("/variable") is not.
_TMP_LITERAL = re.compile(r"[\"'](/tmp|/var)(/|[\"'])")
_FLAG_IN_TEXT = re.compile(r"(?<![\w-])--[a-z][a-z0-9-]{1,30}")
_LINE_BREAK = re.compile(r"\r\n|\r|\n")


def _source(path):
    """A file's text as Python reads it: a UTF-8 BOM stripped, undecodable bytes replaced.

    Plain `utf-8` keeps the BOM as U+FEFF, which ast.parse rejects - so a file the interpreter
    runs happily was reported as not parsing and then skipped by every AST check. Raises OSError."""
    return Path(path).read_text(encoding="utf-8-sig", errors="replace")


def _parse(path):
    """The AST of a Python file, or None when it does not parse."""
    try:
        return ast.parse(_source(path))
    except (OSError, SyntaxError, ValueError):
        return None


def _lines(path):
    """Physical lines, split on CR/LF only so they carry the line numbers Python reports.

    `str.splitlines()` also splits on form feed and U+2028, numbering every later line too high."""
    try:
        text = _source(path)
    except OSError:
        return []
    lines = _LINE_BREAK.split(text)
    if lines and lines[-1] == "":
        lines.pop()
    return lines


def syntax_errors(paths):
    """Every shipped example must at least parse. Returns [(rel, line, message)]."""
    out = []
    for rel, path in paths:
        try:
            ast.parse(_source(path))
        except SyntaxError as exc:
            out.append((rel, exc.lineno or 0, "does not parse: %s" % exc.msg))
        except (OSError, ValueError) as exc:
            out.append((rel, 0, "unreadable: %s" % exc))
    return out


_IMPORT_ERROR_CATCHERS = frozenset({"ImportError", "ModuleNotFoundError", "Exception",
                                    "BaseException"})
_TRY_NODES = tuple(t for t in (ast.Try, getattr(ast, "TryStar", None)) if t is not None)


def _catches_import_error(handler):
    """True when this except clause would catch a failed import."""
    if handler.type is None:
        return True
    kinds = handler.type.elts if isinstance(handler.type, ast.Tuple) else [handler.type]
    for kind in kinds:
        name = kind.id if isinstance(kind, ast.Name) else getattr(kind, "attr", "")
        if name in _IMPORT_ERROR_CATCHERS:
            return True
    return False


def _is_guard(node):
    """A lazy scope (function or class body), or a try: whose handlers catch ImportError.

    A try: with only `except ValueError` or only `finally` still lets ModuleNotFoundError out,
    so counting every try: as a fallback hid exactly the crash this check exists to find."""
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return True
    return isinstance(node, _TRY_NODES) and any(_catches_import_error(h) for h in node.handlers)


def _guarded_nodes(tree):
    """Every node sitting inside an ImportError-catching try: or a function/class body.

    An import there is conditional or lazy, which is exactly the shape the fail-open rule wants,
    so it must not be reported as unguarded."""
    guarded = set()
    for node in ast.walk(tree):
        if _is_guard(node):
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


_PLATFORM_ATTRS = frozenset({("os", "name"), ("sys", "platform")})


def _reads_platform(node):
    """True when this node reads `os.name`, `sys.platform`, or calls `platform.system()`."""
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
        return (node.value.id, node.attr) in _PLATFORM_ATTRS
    if isinstance(node, ast.Call):
        func = node.func
        return (isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name)
                and func.value.id == "platform" and func.attr in ("system", "machine"))
    return False


def _names_windows_or_posix(node):
    """True when a string literal in this node names Windows or POSIX.

    Only those two sides decide X_OK. A `sys.platform == "darwin"` branch tests the platform but
    leaves Windows falling through to the os.access call, so it must not count as a guard."""
    for n in ast.walk(node):
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            value = n.value.lower()
            if value in ("nt", "posix", "cygwin", "msys") or value.startswith("win"):
                return True
    return False


def _platform_test(node):
    """True when this node TESTS for Windows or POSIX, rather than merely mentioning a platform.

    Two shapes: a comparison somewhere containing a platform read (`os.name == "posix"`,
    `platform.system() == "Windows"`), and a method call ON a platform read
    (`sys.platform.startswith("win")`) - either way against a Windows or POSIX value. This is a
    direction test, not a dominance proof: a Windows test anywhere in the function still counts."""
    if isinstance(node, ast.Compare):
        return any(_reads_platform(n) for n in ast.walk(node)) and _names_windows_or_posix(node)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        return _reads_platform(node.func.value) and _names_windows_or_posix(node)
    return False


def _is_platform_guarded(func):
    """True when a function already branches on the platform.

    Structural, never a substring of the dumped AST. The substring form suppressed real defects
    three ways: `"posix" in source` matched a DOCSTRING saying "only meaningful on posix", or a
    parameter named `posix`; and `attr='name' and id='os'` matched an unrelated `os.path.join(f.name)`.
    Every one of those reads as a guard while the `os.access(X_OK)` under it is genuinely unguarded,
    and this function's only job is to SUPPRESS a finding - so a loose rule here is silent.

    `harness_checks.is_executable` is the reference shape: `(os.name == "posix") if posix is None
    else posix` returns False off POSIX before ever reaching os.access, so its X_OK call is correct
    and reporting it is a false positive."""
    return any(_platform_test(node) for node in ast.walk(func))


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
            if not isinstance(node, ast.Call) or _call_name(node) not in ("os.access", "access"):
                continue
            if id(node) in guarded:
                continue
            if any(_names_x_ok(arg) for arg in node.args[1:]):
                out.append((rel, node.lineno,
                            "unguarded os.access(..., os.X_OK) is always True on Windows"))
    return out


def _names_x_ok(arg):
    """True when a mode argument includes X_OK in any spelling: `os.X_OK`, a bare `X_OK` from
    `from os import X_OK`, or either inside an OR (`os.X_OK | os.R_OK`)."""
    for n in ast.walk(arg):
        if isinstance(n, ast.Attribute) and n.attr == "X_OK":
            return True
        if isinstance(n, ast.Name) and n.id == "X_OK":
            return True
    return False


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
    long as the package has any tests at all.

    "Names" means a real reference, never a substring: a `test_<stem>.py` file, an import of the
    stem, the literal `<stem>.py`, or the stem as a whole quoted string - the form a conftest
    loader takes (`load_script("batch_convert")`, a hyphenated hook's alias map), which is why
    conftest.py files are read too. A substring test let every short stem pass - `check.py` was
    "covered" by an unrelated `test_check_output` - so the lead was lost exactly where it mattered."""
    corpus, files = [], set()
    for root in test_roots:
        for pattern in ("test_*.py", "conftest.py"):
            for path in Path(root).rglob(pattern):
                files.add(path.name)
                corpus.append(_source(path))
    blob = "\n".join(corpus)
    out = []
    for rel, _path in paths:
        if not str(rel).endswith(".py"):
            continue
        stem = Path(rel).stem
        if not _test_names(stem, files, blob):
            out.append((rel, 0, "no test module anywhere names '%s' (lead: coverage may be "
                                "indirect)" % stem))
    return out


def _test_names(stem, test_files, blob):
    """True when a test module file is named for `stem`, imports it, or names `<stem>.py`."""
    for name in {stem, stem.replace("-", "_")}:
        if "test_%s.py" % name in test_files:
            return True
        word = r"(?<![\w-])%s(?![\w-])" % re.escape(name)
        if re.search(r"^[ \t]*(?:import|from)[ \t][^\n#]*" + word, blob, re.M):
            return True
        if re.search(r"(?<![\w-])%s\.py(?!\w)" % re.escape(name), blob):
            return True
        if re.search(r"[\"']%s[\"']" % re.escape(name), blob):
            return True
    return False


def _run(cmd, cwd, timeout=20):
    """Default subprocess seam, injectable so the tests never spawn anything."""
    return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=timeout)


def argparse_flags_vs_docs(targets, room, docs_text, run=_run):
    """Flags the shipped documentation names that `--help` does not accept.

    A manual instrument, deliberately NOT one of `run_prepass`'s checks: it executes every target
    with `--help`, and the sweep's own rule is that a script whose name says it mutates a host is
    never run. Call it by hand over a vetted target list.

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
    "js_parse": js_parse,
}

# A hit that is a SETTLED FACT and a hit that is a LEAD need opposite instructions, and a single
# ALREADY KNOWN - DO NOT RE-REPORT block gives them the same one. `text=True` with no encoding is
# settled: it is wrong wherever it appears and one line names the fix. `shlex.split` on a path and
# "no test module names this stem" are not: whether either is a defect depends on what the code
# does with the result, which is exactly the judgement the reviewer exists to make. Suppressing
# those silences the only reader who can answer, in the files most likely to hold a real defect.
LEAD_CHECKS = frozenset({"shlex_on_paths", "per_file_test_module"})


def group_by_file(hits):
    """{rel: ["line N: message", ...]} - the shape a reviewer prompt interpolates."""
    out = {}
    for rel, line, message in hits:
        out.setdefault(rel, []).append("line %d: %s" % (line, message) if line else message)
    return out


def run_prepass(room, targets, ci_min="3.11", vendored=(), run=_run):
    """Every deterministic check over the enumerated corpus.

    Returns (facts_per_file, leads_per_file, summary_lines). The two maps carry opposite
    instructions to a reviewer, so they must not be merged - see LEAD_CHECKS.

    `vendored` is the corpus that is deliberately kept OUT of the reviewer sweep, because fixing a
    defect in upstream sample code diverges our copy from upstream. It still gets `ast.parse`: that
    is the one property we own whatever upstream says, and without it those files were the only
    shipped Python in the plugin that nothing checked at all. Nothing else is run over them, and
    they reach no reviewer prompt - the hits are for the operator reading the summary.

    `run` is the subprocess seam `js_parse` uses for `node --check` over the JS targets."""
    room = Path(room)
    py = [(rel, room / rel) for rel, _k in targets if rel.endswith(".py")]
    js = [(rel, room / rel) for rel, _k in targets if rel.endswith(".js")]
    hooks = [rel for rel, kind in targets if kind in ("hook", "hook-lib")]
    hook_py = [(rel, path) for rel, path in py if rel in set(hooks)]
    siblings = [p.stem for p in room.rglob("*.py")]
    test_roots = [d for d in room.rglob("tests") if d.is_dir()]
    vendored_py = [(rel, room / rel) for rel, _k in vendored if rel.endswith(".py")]

    facts, leads, summary = [], [], []
    for name, fn in (("syntax_errors", lambda: syntax_errors(py + vendored_py)),
                     ("unguarded_third_party_imports",
                      lambda: unguarded_third_party_imports(hook_py, siblings)),
                     ("subprocess_text_without_encoding",
                      lambda: subprocess_text_without_encoding(py)),
                     ("os_access_x_ok", lambda: os_access_x_ok(py)),
                     ("shlex_on_paths", lambda: shlex_on_paths(py)),
                     ("hardcoded_tmp", lambda: hardcoded_tmp(py)),
                     ("pep723_problems", lambda: pep723_problems(py, ci_min, hooks)),
                     ("per_file_test_module", lambda: per_file_test_module(py, test_roots)),
                     ("js_parse", lambda: js_parse(js, run=run, room=room))):
        found = fn()
        (leads if name in LEAD_CHECKS else facts).extend(found)
        summary.append("%-34s %d hit(s)%s" % (name, len(found),
                                              " (lead)" if name in LEAD_CHECKS else ""))
    return group_by_file(facts), group_by_file(leads), summary


def vendored_targets(audit_skills, room):
    """The vendored corpus: everything the reviewer sweep excludes, and nothing it includes.

    Derived as a set difference rather than by re-testing each path, so it cannot disagree with
    `script_targets`' own exclusion rule - which is the rule that decides who gets a reviewer."""
    reviewed = {rel for rel, _k in audit_skills.script_targets(room)}
    return [(rel, kind) for rel, kind in audit_skills.script_targets(room, include_vendored=True)
            if rel not in reviewed]


def _tolerant_stdio():
    """Replace, rather than crash on, a character a cp1252 console cannot encode."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except (AttributeError, ValueError, OSError):
            pass


def room_problem(room):
    """Why `room` is not a plugin dir to scan, or '' when it is.

    A missing path, a file, or a skill dir enumerates zero targets, and zero targets printed a
    clean "0 hits" report with exit 0 - indistinguishable from a corpus that really is clean."""
    room = Path(room)
    if not room.is_dir():
        return "%s is not a directory" % room
    if not (room / "hooks").is_dir() and not (room / "skills").is_dir():
        return "%s has neither hooks/ nor skills/ - pass the plugin dir itself" % room
    return ""


def main(argv=None):
    """Exit 0 after a scan (hits or not), 2 when the room is refused or the scan crashes."""
    _tolerant_stdio()
    ap = argparse.ArgumentParser(
        description="Deterministic pre-pass over a shipped-script corpus.",
        epilog="Exit codes: 0 the scan ran (with or without hits); 2 refused or crashed.")
    ap.add_argument("--room", required=True, help="the room's plugin dir")
    ap.add_argument("--json", action="store_true", help="emit the per-file map as JSON")
    args = ap.parse_args(sys.argv[1:] if argv is None else argv)
    problem = room_problem(args.room)
    if problem:
        print("script_prepass: %s" % problem, file=sys.stderr)
        return 2
    try:
        return _scan(args)
    except Exception:
        traceback.print_exc()
        print("script_prepass: crashed before a result (exit 2)", file=sys.stderr)
        return 2


def _scan(args):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import audit_skills  # noqa: PLC0415 - sibling script, resolved from this file's own dir

    targets = audit_skills.script_targets(args.room)
    facts, leads, summary = run_prepass(args.room, targets,
                                        vendored=vendored_targets(audit_skills, args.room))
    if args.json:
        print(json.dumps({"facts": facts, "leads": leads}, indent=2, sort_keys=True))
        return 0
    for line in summary:
        print(line)
    print("TOTAL: %d target(s) scanned, %d file(s) with a settled hit, %d with a lead"
          % (len(targets), len(facts), len(leads)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
