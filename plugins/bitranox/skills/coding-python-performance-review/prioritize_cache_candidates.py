"""Cross-reference cache candidates with profiling hotspots.

Usage: python prioritize_cache_candidates.py CANDIDATES.txt HOTSPOTS.txt

A candidate is high priority when a hotspot names the same function in the same file. The
two reports spell paths differently - find(1) gives ``src/m.py``, cProfile records the
absolute path, on Windows with a drive letter and backslashes - so files match when the
shorter path's components are a suffix of the longer one's.

Exit codes: 0 the report was produced (whether or not anything matched), 2 an input file
could not be read or the arguments were invalid.
"""
import argparse
import re
import sys

# One report line: "<path>:<line> - <function>()", optionally wrapped in markdown bold.
# The path is greedy so a drive letter ("C:\\...") stays part of it: the anchor is the
# LAST ":<digits> - " on the line, never the first colon.
_LINE = re.compile(r'^(?:\*\*)?(.+):(\d+) - (\w+)\(\)', re.MULTILINE)
_WINDOWS_SHAPE = re.compile(r'\\|^[A-Za-z]:')


def _parse_report(path):
    # utf-8-sig: a BOM would otherwise become part of the first path.
    with open(path, encoding="utf-8-sig") as f:
        content = f.read()
    return [{'file': m[0], 'line': int(m[1]), 'function': m[2]} for m in _LINE.findall(content)]


def parse_candidates(candidate_file):
    """Parse cache candidates file."""
    return _parse_report(candidate_file)


def parse_hotspots(hotspot_file):
    """Parse hotspots file."""
    return _parse_report(hotspot_file)


def _components(path):
    return [part for part in re.split(r'[\\/]', path) if part not in ('', '.')]


def same_file(a, b):
    """True when the shorter path's components are a suffix of the longer one's."""
    left, right = _components(a), _components(b)
    if _WINDOWS_SHAPE.search(a) or _WINDOWS_SHAPE.search(b):
        left, right = [p.casefold() for p in left], [p.casefold() for p in right]
    n = min(len(left), len(right))
    return n > 0 and left[-n:] == right[-n:]


def prioritize(candidates, hotspots):
    """Find candidates that are also hot spots (HIGH PRIORITY)."""
    priority = []

    for candidate in candidates:
        for hotspot in hotspots:
            if candidate['function'] == hotspot['function'] and same_file(candidate['file'], hotspot['file']):
                priority.append(candidate)
                break

    return priority


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


def main(argv=None):
    _utf8_output()
    parser = argparse.ArgumentParser(description="Cross-reference cache candidates with hotspots.")
    parser.add_argument('candidates', metavar='CANDIDATES.txt')
    parser.add_argument('hotspots', metavar='HOTSPOTS.txt')
    args = parser.parse_args(argv)

    try:
        candidates = parse_candidates(args.candidates)
        hotspots = parse_hotspots(args.hotspots)
    except (OSError, UnicodeDecodeError) as e:
        print(f"ERROR reading input: {e}", file=sys.stderr)
        return 2

    priority = prioritize(candidates, hotspots)

    print("# High-Priority Cache Candidates\n")
    print("These functions are BOTH pure AND frequently called:\n")

    for p in priority:
        print(f"**{p['file']}:{p['line']} - {p['function']}()**")
        print("  Action: Profile with caching to measure benefit\n")

    print(f"\nTotal high-priority candidates: {len(priority)}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
