"""Find the project's own functions that are called often AND take significant time.

Usage: python find_hotspots.py PROFILE.prof

Built-ins, the standard library and installed packages (site-packages / dist-packages)
are left out: the report is about code the project can change.

Exit codes: 0 the profile was read (whether or not hotspots were found), 2 the profile
could not be read or the arguments were invalid.
"""
import argparse
import os
import pstats
import sys
import sysconfig

# Constants for hotspot detection
MIN_CALLS = 100  # Minimum number of calls to be considered a hotspot
MIN_CUMTIME = 0.1  # Minimum cumulative time in seconds


def _norm(path):
    return os.path.normcase(os.path.abspath(path))


def stdlib_roots():
    """The interpreter's standard-library directories (the profile's interpreter runs this too)."""
    paths = sysconfig.get_paths()
    return sorted({_norm(paths[k]) for k in ('stdlib', 'platstdlib') if paths.get(k)})


def _under(filename, roots):
    path = _norm(filename)
    return any(path == root or path.startswith(root.rstrip(os.sep) + os.sep) for root in roots)


def _is_foreign(filename, func_name, roots):
    """True for built-ins, synthesized code, installed packages and the standard library."""
    if '<' in filename or filename == '~' or func_name.startswith('<'):
        return True
    if 'site-packages' in filename or 'dist-packages' in filename:
        return True
    return _under(filename, roots)


def find_hotspots(prof_file, min_calls=MIN_CALLS, min_cumtime=MIN_CUMTIME, exclude_roots=None):
    """Find functions called frequently AND taking significant time.

    *exclude_roots* lists directories whose files are never reported; it defaults to the
    standard library of the running interpreter.
    """
    roots = [_norm(r) for r in exclude_roots] if exclude_roots is not None else stdlib_roots()
    stats = pstats.Stats(prof_file)
    hotspots = []

    for func, (cc, nc, tt, ct, callers) in stats.stats.items():
        filename, line, func_name = func
        if nc < min_calls or ct < min_cumtime or _is_foreign(filename, func_name, roots):
            continue
        hotspots.append({
            'file': filename,
            'line': line,
            'function': func_name,
            'calls': nc,
            'cumtime': ct,
            'percall': ct / nc if nc > 0 else 0
        })

    # Sort by cumulative time
    hotspots.sort(key=lambda x: x['cumtime'], reverse=True)

    return hotspots


def _utf8_output():
    # prioritize_cache_candidates.py reads this report as UTF-8, and a cp1252 console
    # cannot encode most non-ASCII paths at all.
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, 'reconfigure', None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding='utf-8', errors='backslashreplace')
        except (ValueError, OSError):
            pass


def main(argv=None):
    _utf8_output()
    parser = argparse.ArgumentParser(description="Find frequently called, slow project functions.")
    parser.add_argument('prof_file', metavar='PROFILE', help="a cProfile output file (.prof)")
    args = parser.parse_args(argv)

    try:
        hotspots = find_hotspots(args.prof_file)
    except Exception as e:  # noqa: BLE001 - pstats raises OSError, ValueError, EOFError, TypeError...
        print(f"ERROR reading profile {args.prof_file}: {e}", file=sys.stderr)
        return 2

    print("# Hot Spots (High Call Count + High Cumulative Time)\n")
    print(f"Found {len(hotspots)} hot spots\n")

    for h in hotspots[:30]:
        print(f"{h['file']}:{h['line']} - {h['function']}()")
        print(f"  Calls: {h['calls']}, Cumtime: {h['cumtime']:.4f}s, Per call: {h['percall']:.6f}s\n")
    return 0


if __name__ == '__main__':
    sys.exit(main())
