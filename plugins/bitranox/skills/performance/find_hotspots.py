import pstats
import sys

# Constants for hotspot detection
MIN_CALLS = 100  # Minimum number of calls to be considered a hotspot
MIN_CUMTIME = 0.1  # Minimum cumulative time in seconds

def find_hotspots(prof_file, min_calls=MIN_CALLS, min_cumtime=MIN_CUMTIME):
    """Find functions called frequently AND taking significant time."""
    stats = pstats.Stats(prof_file)
    stats_dict = stats.stats

    hotspots = []

    for func, (cc, nc, tt, ct, callers) in stats_dict.items():
        if nc >= min_calls and ct >= min_cumtime:
            # Extract function name and file
            filename, line, func_name = func

            # Skip built-in and library functions
            if '<' in filename or 'site-packages' in filename:
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

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: find_hotspots.py <profile.prof>", file=sys.stderr)
        sys.exit(1)
    prof_file = sys.argv[1]

    hotspots = find_hotspots(prof_file)

    print("# Hot Spots (High Call Count + High Cumulative Time)\n")
    print(f"Found {len(hotspots)} hot spots\n")

    for h in hotspots[:30]:
        print(f"{h['file']}:{h['line']} - {h['function']}()")
        print(f"  Calls: {h['calls']}, Cumtime: {h['cumtime']:.4f}s, Per call: {h['percall']:.6f}s\n")
