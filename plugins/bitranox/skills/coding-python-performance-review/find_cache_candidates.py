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


# Constructors that always return a NEW container. A shallow copy (list(x), dict(x), x.copy())
# is new at the top level only: its elements are still the caller's objects.
_FRESH_CONTAINER_CALLS = frozenset({'list', 'dict', 'set', 'bytearray',
                                    'Counter', 'OrderedDict', 'deque', 'defaultdict'})
_FRESH_ELEMENT_FACTORIES = frozenset({'list', 'dict', 'set', 'bytearray'})
_INFINITE = float('inf')


def _call_name(func):
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return ''


def _fresh_depth(expr):
    """How many subscript levels of *expr*'s value are objects created right here.

    0: not known to be new (a parameter, a global, any other call's result). 1: a new container
    whose elements may be shared (``[0] * n``, ``dict(base)``). 2: a new container of new
    containers (``[[0] * m for _ in range(n)]``). A store ``x[i][j] = ...`` is local only
    when the depth of every value ``x`` is ever bound to covers both subscripts."""
    if isinstance(expr, (ast.List, ast.Set, ast.Tuple)):
        return 1 + min((_fresh_depth(e) for e in expr.elts), default=0)
    if isinstance(expr, ast.Dict):
        return 1 + min((_fresh_depth(v) for v in expr.values), default=0)
    if isinstance(expr, (ast.ListComp, ast.SetComp)):
        return 1 + _fresh_depth(expr.elt)
    if isinstance(expr, ast.DictComp):
        return 1 + _fresh_depth(expr.value)
    if isinstance(expr, ast.BinOp) and isinstance(expr.op, ast.Mult):
        # [0] * n and n * [0]: repetition copies the element references, not the elements
        return max(_fresh_depth(expr.left), _fresh_depth(expr.right))
    if isinstance(expr, ast.Call):
        return _fresh_call_depth(expr)
    return 0


def _fresh_call_depth(call):
    name = _call_name(call.func)
    if name == 'copy' and isinstance(call.func, ast.Attribute) and not call.args:
        return 1  # x.copy(): a new container holding x's elements
    if name not in _FRESH_CONTAINER_CALLS:
        return 0
    factory = call.args[0] if call.args else None
    if name == 'defaultdict' and isinstance(factory, ast.Name) \
            and factory.id in _FRESH_ELEMENT_FACTORIES:
        return 2  # every missing key gets a new list/dict/set from the factory
    return 1


def _target_names(target):
    """The plain names an assignment target binds; x[i] and x.a bind none (they store)."""
    if isinstance(target, ast.Name):
        return [target.id]
    if isinstance(target, ast.Starred):
        return _target_names(target.value)
    if isinstance(target, (ast.Tuple, ast.List)):
        return [name for elt in target.elts for name in _target_names(elt)]
    return []


def _not_new(target):
    return [(name, 0) for name in _target_names(target)]


def _target_depths(target, value):
    """Pair each name in *target* with the fresh depth of the value it receives."""
    if isinstance(target, ast.Name):
        return [(target.id, _fresh_depth(value))]
    pairwise = (isinstance(target, (ast.Tuple, ast.List)) and isinstance(value, (ast.Tuple, ast.List))
                and len(target.elts) == len(value.elts)
                and not any(isinstance(e, ast.Starred) for e in (*target.elts, *value.elts)))
    if pairwise:  # prev, cur = [0] * n, [0] * n
        return [pair for t, v in zip(target.elts, value.elts) for pair in _target_depths(t, v)]
    return _not_new(target)


def _binding_depths(node):
    """(name, fresh depth) for each name *node* binds; depth 0 when the value is not new."""
    if isinstance(node, ast.Assign):
        return [pair for t in node.targets for pair in _target_depths(t, node.value)]
    if isinstance(node, ast.AnnAssign):
        return _target_depths(node.target, node.value) if node.value is not None else []
    if isinstance(node, ast.NamedExpr):
        return [(node.target.id, _fresh_depth(node.value))]
    if isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name):
        # x += y keeps a mutable x's identity but can bring in y's elements
        return [(node.target.id, 1)]
    if isinstance(node, (ast.For, ast.AsyncFor, ast.comprehension)):
        return _not_new(node.target)
    if isinstance(node, ast.withitem) and node.optional_vars is not None:
        return _not_new(node.optional_vars)
    if isinstance(node, ast.ExceptHandler) and node.name:
        return [(node.name, 0)]
    if isinstance(node, ast.arguments):  # this function's, a nested one's, a lambda's
        args = [*node.posonlyargs, *node.args, *node.kwonlyargs, node.vararg, node.kwarg]
        return [(a.arg, 0) for a in args if a is not None]
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        return [((a.asname or a.name).split('.')[0], 0) for a in node.names]
    return []


def _local_container_depths(func_node):
    """Name -> how deep a subscript store into it stays inside objects this function created.

    Every binding of the name anywhere in the function counts, nested functions and lambdas
    included (their parameters too): one binding to something not created here - a
    parameter, an alias, a loop variable - makes a store through that name a store into an
    object the caller may hold. A name bound nowhere in the function is a global or a closure."""
    depths = {}
    for node in ast.walk(func_node):
        for name, depth in _binding_depths(node):
            depths[name] = min(depths.get(name, _INFINITE), depth)
    return depths


def _store_targets(node):
    if isinstance(node, ast.Assign):
        return node.targets
    if isinstance(node, (ast.AugAssign, ast.AnnAssign)):
        return [node.target]
    if isinstance(node, ast.Delete):
        return node.targets
    return []


def _is_shared_store(target, local_depths):
    """True when storing into *target* (``x[i] = ...``, ``x.a = ...``) can mutate an object
    the caller sees. A subscript store into a container created in this function is local."""
    if not isinstance(target, (ast.Subscript, ast.Attribute)):
        return False
    levels, node = 0, target
    while isinstance(node, ast.Subscript):
        levels += 1
        node = node.value
    if not isinstance(node, ast.Name):
        # an attribute anywhere in the chain (self.x, obj.table[i]) reaches an object the
        # function did not create, as does a store through a call's result
        return True
    return local_depths.get(node.id, 0) < levels


def _stores_into_shared_object(node, local_depths):
    for target in _store_targets(node):
        # (a, b[i]) = ... stores through each element of the tuple target
        elts = target.elts if isinstance(target, (ast.Tuple, ast.List)) else [target]
        if any(_is_shared_store(t, local_depths) for t in elts):
            return True
    return False


def is_pure_function(func_node):
    """Heuristic to detect pure functions - no I/O, no global state, no clock, no generator.

    A store into a container the function created itself (a DP table, a local tally dict)
    stays pure; a store into a parameter, a global, a closure variable or an attribute
    (self.x) does not."""
    local_depths = _local_container_depths(func_node)
    for node in ast.walk(func_node):
        if isinstance(node, ast.Call) and _is_impure_call(node):
            return False
        if isinstance(node, (ast.Global, ast.Nonlocal)):
            return False
        # A cached generator hands every later caller the same, already exhausted iterator.
        if isinstance(node, (ast.Yield, ast.YieldFrom)):
            return False
        if _stores_into_shared_object(node, local_depths):
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
