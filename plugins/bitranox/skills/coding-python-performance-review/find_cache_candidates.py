"""Find pure, expensive functions that might benefit from caching (AST heuristic).

Usage: python find_cache_candidates.py FILE [FILE ...]

Exit codes: 0 every file was scanned (whether or not candidates were found), 2 at least one
path was missing or could not be read or parsed (its ERROR line goes to stderr; the report
for the files that were scanned is still printed), or the arguments were invalid.
"""
import argparse
import ast
import os
import sys

# A call through any of these names makes the function impure (I/O, state, or a clock).
_IMPURE_NAME_CALLS = frozenset({'print', 'open', 'input', 'write',
                                'time', 'perf_counter', 'monotonic', 'process_time'})
_IMPURE_ATTR_CALLS = frozenset({'write', 'read', 'append', 'execute',
                                'now', 'today', 'utcnow', 'random', 'randint',
                                'time', 'time_ns', 'perf_counter', 'perf_counter_ns',
                                'monotonic', 'monotonic_ns', 'process_time'})
# Calling anything on these modules runs a process: never deterministic, never side-effect free.
_IMPURE_MODULES = frozenset({'subprocess'})


def _is_impure_call(node):
    func = node.func
    if isinstance(func, ast.Name):
        return func.id in _IMPURE_NAME_CALLS
    if isinstance(func, ast.Attribute):
        if func.attr in _IMPURE_ATTR_CALLS:
            return True
        return isinstance(func.value, ast.Name) and func.value.id in _IMPURE_MODULES
    return False


def _stores_into_object(node):
    """True for ``x[i] = ...`` / ``x.a = ...`` (and aug/del): it mutates an object, often an argument."""
    targets = []
    if isinstance(node, ast.Assign):
        targets = node.targets
    elif isinstance(node, (ast.AugAssign, ast.AnnAssign)):
        targets = [node.target]
    elif isinstance(node, ast.Delete):
        targets = node.targets
    return any(isinstance(t, (ast.Subscript, ast.Attribute)) for t in targets)


def is_pure_function(func_node):
    """Heuristic to detect pure functions - no I/O, no global state, no clock, no generator."""
    for node in ast.walk(func_node):
        if isinstance(node, ast.Call) and _is_impure_call(node):
            return False
        if isinstance(node, (ast.Global, ast.Nonlocal)):
            return False
        # A cached generator hands every later caller the same, already exhausted iterator.
        if isinstance(node, (ast.Yield, ast.YieldFrom)):
            return False
        if _stores_into_object(node):
            return False
    return True


def is_expensive_computation(func_node):
    """Detect potentially expensive computations."""
    expensive_indicators = []

    for node in ast.walk(func_node):
        # Complex loops
        if isinstance(node, (ast.For, ast.While)):
            expensive_indicators.append('loops')

        # Recursion
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id == func_node.name:
                    expensive_indicators.append('recursion')

        # Hash/crypto operations
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                if 'hash' in node.func.attr.lower() or 'crypt' in node.func.attr.lower():
                    expensive_indicators.append('crypto')

    return expensive_indicators

def _decorator_name(node):
    """Extract the base name from a decorator AST node."""
    # @cache / @lru_cache
    if isinstance(node, ast.Name):
        return node.id
    # @lru_cache(maxsize=128)
    if isinstance(node, ast.Call):
        return _decorator_name(node.func)
    # @functools.lru_cache
    if isinstance(node, ast.Attribute):
        return node.attr
    return ''


def _is_cache_decorator(node):
    """Check if a decorator node is a caching decorator."""
    return 'cache' in _decorator_name(node).lower()


def _parse(file_path):
    # Bytes, not text: ast.parse then honours a UTF-8 BOM and a PEP 263 coding cookie
    # exactly as the interpreter does.
    with open(file_path, 'rb') as f:
        return ast.parse(f.read(), filename=file_path)


def find_cache_candidates(file_path):
    """Find functions that might benefit from caching.

    Raises OSError, SyntaxError or ValueError when the file cannot be read or parsed, so a
    caller can tell "no candidates" from "not scanned".
    """
    tree = _parse(file_path)
    candidates = []

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            # Skip if already decorated with cache
            has_cache = any(_is_cache_decorator(dec) for dec in node.decorator_list)

            if has_cache:
                continue

            # Check if pure
            if is_pure_function(node):
                expensive = is_expensive_computation(node)

                if expensive:
                    unique = sorted(set(expensive))  # dedupe: avoid "recursion, recursion"
                    candidates.append({
                        'file': file_path,
                        'function': node.name,
                        'line': node.lineno,
                        'reason': f"Pure function with: {', '.join(unique)}",
                        'indicators': unique
                    })

    return candidates


def _utf8_output():
    # The report is read back as UTF-8 (prioritize_cache_candidates.py), and a cp1252
    # console cannot encode most non-ASCII paths at all.
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, 'reconfigure', None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding='utf-8', errors='backslashreplace')
        except (ValueError, OSError):
            pass


def _scan(paths):
    """Scan *paths*; return (candidates, number of paths that could not be scanned)."""
    found, failed = [], 0
    for filepath in paths:
        if not os.path.exists(filepath):
            print(f"ERROR not found: {filepath}", file=sys.stderr)
            failed += 1
            continue
        try:
            found.extend(find_cache_candidates(filepath))
        except (OSError, SyntaxError, ValueError) as e:
            print(f"ERROR parsing {filepath}: {e}", file=sys.stderr)
            failed += 1
    return found, failed


def main(argv=None):
    _utf8_output()
    parser = argparse.ArgumentParser(description="Find pure, expensive functions worth caching.")
    parser.add_argument('files', nargs='+', metavar='FILE', help="Python source files to scan")
    args = parser.parse_args(argv)

    all_candidates, failed = _scan(args.files)

    print("# Cache Candidates Analysis\n")
    print(f"Found {len(all_candidates)} potential candidates\n")

    for c in all_candidates:
        print(f"{c['file']}:{c['line']} - {c['function']}()")
        print(f"  Reason: {c['reason']}\n")
    return 2 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
