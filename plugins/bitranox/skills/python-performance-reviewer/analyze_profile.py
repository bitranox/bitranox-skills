import pstats
import sys

def analyze_profile(prof_file):
    """Analyze profiling data and generate report."""
    stats = pstats.Stats(prof_file)

    print("=" * 80)
    print("TOP 30 FUNCTIONS BY CUMULATIVE TIME")
    print("=" * 80)
    stats.sort_stats('cumulative')
    stats.print_stats(30)

    print("\n" + "=" * 80)
    print("TOP 30 FUNCTIONS BY CALL COUNT")
    print("=" * 80)
    stats.sort_stats('calls')
    stats.print_stats(30)

    print("\n" + "=" * 80)
    print("TOP 30 FUNCTIONS BY TIME PER CALL")
    print("=" * 80)
    stats.sort_stats('time')
    stats.print_stats(30)

    # Identify hot spots (called often AND expensive)
    print("\n" + "=" * 80)
    print("HOT SPOTS (High call count + High cumulative time)")
    print("=" * 80)

    # Get function stats
    stats_dict = stats.stats
    hotspots = []

    for func, (cc, nc, tt, ct, callers) in stats_dict.items():
        if nc > 100 and ct > 0.1:  # Called >100 times and >0.1s cumulative
            hotspots.append((func, nc, ct))

    # Sort by cumulative time
    hotspots.sort(key=lambda x: x[2], reverse=True)

    for func, calls, cumtime in hotspots[:20]:
        print(f"{func}: {calls} calls, {cumtime:.4f}s cumulative")

if __name__ == '__main__':
    if len(sys.argv) > 1:
        analyze_profile(sys.argv[1])
    else:
        analyze_profile('LLM-CONTEXT/review-anal/perf/test_profile.prof')
