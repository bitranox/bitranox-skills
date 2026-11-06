---
name: coding-performance-review
description: Use when measuring, comparing or reviewing performance in any language - before optimising, when a change or commit message claims a speedup, when timing two versions, builds or configurations against each other, when an A/B timing reads as a clear win or a clear null, when reviewing code for algorithmic cost, N+1 queries or calls, per-item I/O, repeated work, blocking calls, or unbounded memory and input, or when the language has no performance skill of its own (bash, JavaScript, Go, SQL). Routes Python to coding-python-performance-review and Rust to coding-rust-performance-review.
---

# Performance review and measurement (any language)

Two halves: how to measure so that a number means what you think it means, and what to look for
in code. The language skills add their own tools on top of this one; the method is shared.

## Route by language

| Code under review | Load as well                                                                  |
|-------------------|-------------------------------------------------------------------------------|
| Python            | `bitranox:coding-python-performance-review` (profiling pipeline, AST finders) |
| Rust              | `bitranox:coding-rust-performance-review` (clippy, criterion, profilers)      |
| anything else     | nothing: this skill alone                                                     |

## Method: a number you can believe

1. **Profile before optimising.** Find where the time goes on a real workload (the project's own
   test suite, a recorded production input, the real request), not on a hand-made
   micro-benchmark. An optimisation outside the hot path is cost without benefit.
2. **Reproduce the recorded BEFORE figure first.** When the defect already has a measured before
   number (an issue, a backlog line, a saved profile), run your probe on the unfixed code and
   require it to land within an order of magnitude of that figure before you trust your after
   number. A probe that hits an early return is fast in both arms, so the fix looks enormous
   while the slow path never ran.
3. **Identical settings on both sides.** Same build mode and flags, input, data size, warm or cold
   state, host and concurrency. Diff what each side RESOLVED, defaults included, not its config
   file.
4. **Interleave the arms: A, B, A, B, at least three runs each.** All-A-then-all-B confounds the
   arm with the clock (thermal state, other load, caches). Report the median and the spread per
   arm; a difference smaller than the spread within one arm is noise.
5. **Pin the core on a hybrid CPU.** On a CPU with performance and efficiency cores (on Linux,
   compare `cpuinfo_max_freq` across `/sys/devices/system/cpu/cpu*/cpufreq/`), identical code
   spreads widely by core placement alone. Pin each run (`taskset -c N`, `sched_setaffinity`) or
   record which core type it ran on.
6. **Prove the change took effect.** Before believing an A/B, above all a null one, show that the
   variable moved inside the system under test (the cache was hit, the flag was read, the new
   build is the one that ran) and that nothing else moved.
7. **Do not write off an approach measured with your own constraint still on it.** List every
   constraint you added to make a variant correct (a lock, serialisation, a cap) and measure it
   without the incidental ones before calling the approach slow.
8. **Measure a concurrency or queueing change; never predict it** from the architecture. The
   cost often sits somewhere the design diagram does not show.
9. **Read current load from two samples, not from a lifetime average.** `ps -o pcpu` averages
   over the whole life of the process; use the second sample of `top -b -n2`, `pidstat`, or two
   reads of `/proc/<pid>/stat`.
10. **Check every speed claim in a diff.** `validate_perf_claims.py` (in this skill's directory)
    extracts phrases like "40% faster", "3x speedup" or "reduced latency by 30%" from a unified
    diff's added lines and prints each with its `path:line`. It reaches no verdict: check each
    claim against a measured run and report the ones that are unproven or contradicted.

```bash
git diff origin/main...HEAD > changes.diff
python3 "<this skill's directory>/validate_perf_claims.py" changes.diff   # 0 scanned, 2 unreadable
```

Report every finding with the measured number, the spread, the runs per arm and the command that
produced it. A figure you did not run yourself is labelled as read or estimated, never as
measured.

## What to flag in code (any language)

Severity: SEVERE can exhaust memory or time on real input; MEDIUM costs measurably on a hot
path; MINOR is cheap to fix but not shown to be hot. Each finding names the input size at which
it starts to hurt.

- **Unbounded memory (usually SEVERE).** Reading a big file, a huge query result or a huge log
  fully into memory, or accumulating an unbounded list, map or string, instead of streaming,
  iterating, chunking or paginating. Only a provably small, fixed-size input may be materialised.
- **Unbounded or unsafe input.** Input with no length bound, unvalidated types, or unhandled
  encodings and characters (non-ASCII, emoji, CJK, control characters, binary). Adversarial input
  must not blow up time or memory (catastrophic regex backtracking, quadratic blow-ups,
  out-of-memory); the bound is validated and tested.
- **Untrusted structured input.** A map, JSON document or deserialised payload used without
  parsing or validating its shape at the boundary.
- **Quadratic work.** A nested loop over the same collection, a membership test against a list
  inside a loop, a repeated sort or search inside a loop, or string building by repeated
  concatenation where the language copies on every step.
- **N+1 calls.** A query, HTTP request, subprocess or RPC per item where one batched call would
  do.
- **Per-item I/O.** An open, close, flush, fsync or system call per record; unbuffered writes.
- **Repeated pure work.** The same parse, compile (a regex, a template) or lookup redone on every
  call with the same input. Hoist or cache it after confirming the work is pure and the hit rate
  is real.
- **Blocking calls on a hot or async path.** A sleep, synchronous network or disk I/O inside an
  event loop, or a lock held while waiting.
- **Eager work that is mostly thrown away.** Building a full list to take its first element, or
  loading every column to use one.

## Common mistakes

| Mistake                                          | Fix                                                                    |
|--------------------------------------------------|------------------------------------------------------------------------|
| Optimising before profiling                      | Profile the real workload first; fix only the hot path                 |
| Timing all A runs, then all B runs               | Interleave A, B, A, B, at least three each                             |
| Trusting an after figure on its own              | Reproduce the recorded before figure with the same probe               |
| Accepting "N times faster" from a commit message | Measure it; `validate_perf_claims.py` scans diffs, not commit messages |
| Reading a null A/B as "no effect"                | Prove the variable moved and its mechanism fired                       |
| Quoting `ps` %CPU as current load                | Take two samples                                                       |
