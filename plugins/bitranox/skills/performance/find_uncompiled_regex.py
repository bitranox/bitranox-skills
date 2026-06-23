"""Find regex patterns used without re.compile().

Scans Python files for calls like re.match(r'pattern', ...) where the
pattern is a string literal.  These should be re.compile()'d at module
level to avoid recompilation on every call.
"""

import ast
import sys
import os

# re module functions that accept a pattern string
RE_FUNCTIONS = frozenset({
    'match', 'search', 'findall', 'finditer',
    'sub', 'subn', 'split', 'fullmatch',
})


def find_uncompiled_regex(file_path):
    """Return list of uncompiled regex call sites in *file_path*."""
    try:
        with open(file_path) as f:
            source = f.read()
        tree = ast.parse(source, filename=file_path)
    except Exception as e:
        print(f"ERROR parsing {file_path}: {e}", file=sys.stderr)
        return []

    findings = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        # Match re.func(pattern, ...) calls
        func = node.func
        if not isinstance(func, ast.Attribute):
            continue
        if func.attr not in RE_FUNCTIONS:
            continue

        # Check the object is 're' (Name) or an alias
        if isinstance(func.value, ast.Name) and func.value.id == 're':
            # First arg should be a string literal
            if node.args and isinstance(node.args[0], (ast.Constant, ast.JoinedStr)):
                is_fstring = isinstance(node.args[0], ast.JoinedStr)
                if is_fstring:
                    pattern_repr = '<f-string>'
                    suggestion = 'Dynamic pattern — cannot compile at module level; consider caching or restructuring'
                else:
                    pattern_repr = repr(node.args[0].value)
                    suggestion = f'Compile at module level: _RE = re.compile({pattern_repr})'

                findings.append({
                    'file': file_path,
                    'line': node.lineno,
                    'call': f're.{func.attr}({pattern_repr}, ...)',
                    'suggestion': suggestion,
                })

    return findings


if __name__ == '__main__':
    all_findings = []

    for filepath in sys.argv[1:]:
        if os.path.exists(filepath):
            all_findings.extend(find_uncompiled_regex(filepath))

    print("# Uncompiled Regex Analysis\n")
    print(f"Found {len(all_findings)} uncompiled regex calls\n")

    for f in all_findings:
        print(f"{f['file']}:{f['line']} - {f['call']}")
        print(f"  Fix: {f['suggestion']}\n")
