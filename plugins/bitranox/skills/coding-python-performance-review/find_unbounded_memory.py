"""Find code that loads large/unbounded data fully into memory.

Static AST scan for the classic memory-growth patterns - reading a big file,
huge database result set, or huge log file all at once instead of streaming.
These are CANDIDATES for review (a small, provably-bounded dataset may be fine);
the reviewer confirms whether the source can grow unbounded.

Flags:
  - f.read() / f.readlines()              whole-stream read (read(size) is OK, bounded)
  - Path(...).read_text() / read_bytes()  whole-file read
  - cursor.fetchall()                     whole result set (fetchmany/server-side cursor stream)
  - pandas read_csv/read_sql/... without  whole-dataset load (pass chunksize=/iterator=/nrows=)
    a chunking keyword

Pure standard library (ast). Same shape as the other detectors: a function that
returns findings, and a main() that prints a report.

Usage: python find_unbounded_memory.py FILE [FILE ...]

Exit codes: 0 every file was scanned (whether or not candidates were found), 2 at least one
path was missing or could not be read or parsed (its ERROR line goes to stderr; the report
for the files that were scanned is still printed), or the arguments were invalid.
"""

import argparse
import ast
import os
import sys

# whole-file pathlib reads (always materialize)
_PATH_READS = frozenset({"read_text", "read_bytes"})
# DB cursor full materialization
_FETCH = frozenset({"fetchall"})
# pandas-style readers that load the whole dataset unless told to chunk
_PANDAS_READERS = frozenset({
    "read_csv", "read_json", "read_sql", "read_sql_query", "read_sql_table",
    "read_parquet", "read_excel", "read_table", "read_feather", "read_orc",
    "read_fwf", "read_stata", "read_hdf",
})
_CHUNK_KWARGS = frozenset({"chunksize", "iterator", "nrows"})

_SUGGEST = {
    "read": "read() loads the whole stream; iterate the file line by line or read fixed-size chunks: read(size).",
    "readlines": "readlines() materializes every line; iterate the file object instead (for line in f).",
    "read_text": "read_text() loads the whole file; for large files open() and stream/iterate lines or chunks.",
    "read_bytes": "read_bytes() loads the whole file; stream in fixed-size chunks for large files.",
    "fetchall": "fetchall() materializes the whole result set; use fetchmany(size) in a loop or a server-side cursor.",
    "pandas": "loads the entire dataset; pass chunksize= (or iterator=True / nrows=) and process in chunks.",
}


def _is_literal_off(value):
    """True for a literal None or False: chunksize=None / iterator=False do not chunk."""
    return isinstance(value, ast.Constant) and value.value in (None, False)


def _has_chunk_kwarg(node):
    return any(kw.arg in _CHUNK_KWARGS and not _is_literal_off(kw.value)
               for kw in node.keywords if kw.arg)


def _literal_int(node):
    """The int a literal such as ``8192`` or ``-1`` spells, or None when it is not one."""
    if isinstance(node, ast.Constant) and isinstance(node.value, int) and not isinstance(node.value, bool):
        return node.value
    if (isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub)
            and isinstance(node.operand, ast.Constant) and isinstance(node.operand.value, int)):
        return -node.operand.value
    return None


def _read_is_unbounded(node):
    """read() / read(-1) / read(None) return the whole stream; read(n >= 0) is bounded."""
    if not node.args:
        return True
    arg = node.args[0]
    if isinstance(arg, ast.Constant) and arg.value is None:
        return True
    size = _literal_int(arg)
    return size is not None and size < 0


def _readlines_is_unbounded(node):
    """readlines() and a hint of None or <= 0 read every line; a positive hint bounds it."""
    if not node.args:
        return True
    arg = node.args[0]
    if isinstance(arg, ast.Constant) and arg.value is None:
        return True
    hint = _literal_int(arg)
    return hint is not None and hint <= 0


def _parse(file_path):
    # Bytes, not text: ast.parse then honours a UTF-8 BOM and a PEP 263 coding cookie
    # exactly as the interpreter does.
    with open(file_path, "rb") as f:
        return ast.parse(f.read(), filename=file_path)


def find_unbounded_memory(file_path):
    """Return list of unbounded-memory candidate call sites in *file_path*.

    Raises OSError, SyntaxError or ValueError when the file cannot be read or parsed, so a
    caller can tell "no findings" from "not scanned".
    """
    tree = _parse(file_path)

    findings = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Attribute):
            continue
        attr = func.attr

        kind = call = suggestion = None
        if attr == "read" and _read_is_unbounded(node):   # read(size) is bounded -> ignore
            kind, call, suggestion = "read", "<obj>.read()", _SUGGEST["read"]
        elif attr == "readlines" and _readlines_is_unbounded(node):
            kind, call, suggestion = "readlines", "<obj>.readlines()", _SUGGEST["readlines"]
        elif attr in _PATH_READS:
            kind, call, suggestion = attr, f"<path>.{attr}()", _SUGGEST[attr]
        elif attr in _FETCH:
            kind, call, suggestion = attr, "<cursor>.fetchall()", _SUGGEST["fetchall"]
        elif attr in _PANDAS_READERS and not _has_chunk_kwarg(node):
            kind, call, suggestion = "pandas", f"<pd>.{attr}(...)", f"{attr}() {_SUGGEST['pandas']}"

        if kind:
            findings.append({
                "file": file_path, "line": node.lineno,
                "kind": kind, "call": call, "suggestion": suggestion,
            })
    return findings


def _utf8_output():
    # A cp1252 console cannot encode most non-ASCII paths; the report is read back as UTF-8.
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="backslashreplace")
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
            found.extend(find_unbounded_memory(filepath))
        except (OSError, SyntaxError, ValueError) as e:
            print(f"ERROR parsing {filepath}: {e}", file=sys.stderr)
            failed += 1
    return found, failed


def main(argv=None):
    _utf8_output()
    parser = argparse.ArgumentParser(description="Find code that loads unbounded data into memory.")
    parser.add_argument("files", nargs="+", metavar="FILE", help="Python source files to scan")
    args = parser.parse_args(argv)

    all_findings, failed = _scan(args.files)

    print("# Unbounded Memory Analysis\n")
    print(f"Found {len(all_findings)} whole-materialization candidate(s) - review whether the source can grow unbounded\n")
    for f in all_findings:
        print(f"{f['file']}:{f['line']} - {f['call']}")
        print(f"  Risk: {f['suggestion']}\n")
    return 2 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
