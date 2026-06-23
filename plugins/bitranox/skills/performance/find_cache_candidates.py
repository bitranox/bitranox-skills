import ast
import sys
import os

def is_pure_function(func_node):
    """Heuristic to detect pure functions - no I/O, no global state."""
    for node in ast.walk(func_node):
        # Check for I/O operations
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id in ['print', 'open', 'input', 'write']:
                    return False
            elif isinstance(node.func, ast.Attribute):
                if node.func.attr in ['write', 'read', 'append', 'execute']:
                    return False
        # Check for global/nonlocal (state modification)
        if isinstance(node, (ast.Global, ast.Nonlocal)):
            return False
        # Check for time/random (non-deterministic)
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                if node.func.attr in ['now', 'today', 'random', 'randint']:
                    return False

    return True

def is_expensive_computation(func_node):
    """Detect potentially expensive computations."""
    expensive_indicators = []

    for node in ast.walk(func_node):
        # File I/O
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id in ['open']:
                    expensive_indicators.append('file_io')

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


def find_cache_candidates(file_path):
    """Find functions that might benefit from caching."""
    try:
        with open(file_path) as f:
            tree = ast.parse(f.read(), filename=file_path)
    except Exception as e:
        print(f"ERROR parsing {file_path}: {e}", file=sys.stderr)
        return []

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
                    candidates.append({
                        'file': file_path,
                        'function': node.name,
                        'line': node.lineno,
                        'reason': f"Pure function with: {', '.join(expensive)}",
                        'indicators': expensive
                    })

    return candidates

if __name__ == '__main__':
    all_candidates = []

    for filepath in sys.argv[1:]:
        if os.path.exists(filepath):
            candidates = find_cache_candidates(filepath)
            all_candidates.extend(candidates)

    print(f"# Cache Candidates Analysis\n")
    print(f"Found {len(all_candidates)} potential candidates\n")

    for c in all_candidates:
        print(f"{c['file']}:{c['line']} - {c['function']}()")
        print(f"  Reason: {c['reason']}\n")
