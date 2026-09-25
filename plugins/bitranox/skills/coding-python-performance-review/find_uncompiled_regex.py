"""Find regex patterns used without re.compile().

Scans Python files for calls like re.match(r'pattern', ...) inside a function body where
the pattern is a string literal. These should be re.compile()'d at module level to avoid
recompilation on every call. A call at module or class level runs once, so it is not
reported.

Recognised spellings: ``re.match(...)``, ``import re as X`` then ``X.match(...)``,
``from re import match [as m]`` then ``match(...)``, and the ``pattern=`` keyword.

Usage: python find_uncompiled_regex.py FILE [FILE ...]

Exit codes: 0 every file was scanned (whether or not calls were found), 2 at least one
path was missing or could not be read or parsed (its ERROR line goes to stderr; the report
for the files that were scanned is still printed), or the arguments were invalid.
"""

import argparse
import ast
import os
import sys

# re module functions that accept a pattern string
RE_FUNCTIONS = frozenset({
    'match', 'search', 'findall', 'finditer',
    'sub', 'subn', 'split', 'fullmatch',
})

_FUNCTION_NODES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)


def _re_names(tree):
    """Return (names bound to the re module, {local name: re function} from-imports)."""
    modules, functions = {'re'}, {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(a.asname for a in node.names if a.name == 're' and a.asname)
        elif isinstance(node, ast.ImportFrom) and node.module == 're' and not node.level:
            functions.update((a.asname or a.name, a.name) for a in node.names if a.name in RE_FUNCTIONS)
    return modules, functions


def _re_function(call, modules, functions):
    """The re function *call* invokes (e.g. 'match'), or None when it is not an re call."""
    func = call.func
    if isinstance(func, ast.Attribute):
        is_re = isinstance(func.value, ast.Name) and func.value.id in modules
        return func.attr if is_re and func.attr in RE_FUNCTIONS else None
    if isinstance(func, ast.Name):
        return functions.get(func.id)
    return None


def _pattern_arg(call):
    if call.args:
        return call.args[0]
    return next((kw.value for kw in call.keywords if kw.arg == 'pattern'), None)


def _finding(file_path, call, name):
    pattern = _pattern_arg(call)
    if not isinstance(pattern, (ast.Constant, ast.JoinedStr)):
        return None
    if isinstance(pattern, ast.JoinedStr):
        pattern_repr = '<f-string>'
        suggestion = 'Dynamic pattern  - cannot compile at module level; consider caching or restructuring'
    else:
        pattern_repr = repr(pattern.value)
        suggestion = f'Compile at module level: _RE = re.compile({pattern_repr})'
    return {
        'file': file_path,
        'line': call.lineno,
        'call': f're.{name}({pattern_repr}, ...)',
        'suggestion': suggestion,
    }


def _calls_in_function_bodies(tree):
    """Yield every Call that sits inside a def, async def or lambda (at any depth)."""
    def walk(node, in_function):
        for child in ast.iter_child_nodes(node):
            inside = in_function or isinstance(child, _FUNCTION_NODES)
            if inside and isinstance(child, ast.Call):
                yield child
            yield from walk(child, inside)
    yield from walk(tree, False)


def _parse(file_path):
    # Bytes, not text: ast.parse then honours a UTF-8 BOM and a PEP 263 coding cookie
    # exactly as the interpreter does.
    with open(file_path, 'rb') as f:
        return ast.parse(f.read(), filename=file_path)


def find_uncompiled_regex(file_path):
    """Return list of uncompiled regex call sites in *file_path*.

    Raises OSError, SyntaxError or ValueError when the file cannot be read or parsed, so a
    caller can tell "no findings" from "not scanned".
    """
    tree = _parse(file_path)
    modules, functions = _re_names(tree)
    findings = []
    for call in _calls_in_function_bodies(tree):
        name = _re_function(call, modules, functions)
        finding = _finding(file_path, call, name) if name else None
        if finding:
            findings.append(finding)
    findings.sort(key=lambda f: f['line'])
    return findings


def _utf8_output():
    # A cp1252 console cannot encode most non-ASCII paths; the report is read back as UTF-8.
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, 'reconfigure', None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding='utf-8', errors='backslashreplace')
        except (ValueError, OSError):
            pass


def _scan(paths):
    """Scan *paths*; return (findings, number of paths that could not be scanned)."""
    found, failed = [], 0
    for filepath in paths:
        if not os.path.exists(filepath):
            print(f"ERROR not found: {filepath}", file=sys.stderr)
            failed += 1
            continue
        try:
            found.extend(find_uncompiled_regex(filepath))
        except (OSError, SyntaxError, ValueError) as e:
            print(f"ERROR parsing {filepath}: {e}", file=sys.stderr)
            failed += 1
    return found, failed


def main(argv=None):
    _utf8_output()
    parser = argparse.ArgumentParser(description="Find regex calls that recompile a literal pattern.")
    parser.add_argument('files', nargs='+', metavar='FILE', help="Python source files to scan")
    args = parser.parse_args(argv)

    all_findings, failed = _scan(args.files)

    print("# Uncompiled Regex Analysis\n")
    print(f"Found {len(all_findings)} uncompiled regex calls\n")

    for f in all_findings:
        print(f"{f['file']}:{f['line']} - {f['call']}")
        print(f"  Fix: {f['suggestion']}\n")
    return 2 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
