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
returns findings, and a __main__ block that prints a report.
"""

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


def _has_chunk_kwarg(node):
    return any(kw.arg in _CHUNK_KWARGS for kw in node.keywords if kw.arg)


def find_unbounded_memory(file_path):
    """Return list of unbounded-memory candidate call sites in *file_path*."""
    try:
        with open(file_path, encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=file_path)
    except Exception as e:  # noqa: BLE001
        print(f"ERROR parsing {file_path}: {e}", file=sys.stderr)
        return []

    findings = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Attribute):
            continue
        attr = func.attr

        kind = call = suggestion = None
        if attr == "read" and not node.args:          # read(size) is bounded -> ignore
            kind, call, suggestion = "read", "<obj>.read()", _SUGGEST["read"]
        elif attr == "readlines":
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


if __name__ == "__main__":
    all_findings = []
    for filepath in sys.argv[1:]:
        if os.path.exists(filepath):
            all_findings.extend(find_unbounded_memory(filepath))

    print("# Unbounded Memory Analysis\n")
    print(f"Found {len(all_findings)} whole-materialization candidate(s) - review whether the source can grow unbounded\n")
    for f in all_findings:
        print(f"{f['file']}:{f['line']} - {f['call']}")
        print(f"  Risk: {f['suggestion']}\n")
