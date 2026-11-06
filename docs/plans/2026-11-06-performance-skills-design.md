# Performance skills: generic, Python, Rust - design

Date: 2026-11-06. Status: design approved, implementation plan to follow.

## Goal

Cover performance work for any language, not only Python. Today the only performance skill is
`coding-python-performance-review`; a Rust or a generic request never triggers it, and the
language-neutral measurement discipline lives nowhere in one place.

## Measured starting point

- `coding-python-performance-review/SKILL.md` is 610 lines; its description triggers only on
  reviewing Python code for performance.
- 7 of its 8 tool scripts need Python ASTs, cProfile or pytest. `validate_perf_claims.py`
  extracts speed claims from a unified diff and works for any language.
- `coding-rust/SKILL.md` (76 lines) has no performance content.
- The Python skill holds interleaved timing only inside its cache-profiling step; core pinning on
  hybrid CPUs, reproducing the recorded before figure and identical-settings comparison are not in
  any skill.
- Renaming the Python skill would touch 2 live references (`process-review-enhance-code-quality`,
  `web-frontend-responsive-ux/analysis.py`) plus generated files. It is not renamed.
- On the dev host: cargo and clippy 0.1.95 are installed; clippy's `perf` group has 36 lints,
  including `regex-creation-in-loops`. perf, cargo-flamegraph, valgrind, heaptrack, hyperfine and
  samply are not installed.

## Decisions (user, 2026-11-06)

1. Shape: three skills, not one extended skill and not one generic skill with per-language
   references. Reason: each description triggers on its own language, and an invoked SKILL.md
   loads whole, so a Rust task must not load the 610-line Python body.
2. The generic skill holds the method AND a language-neutral review checklist, plus a router.
3. The Rust skill is a checklist plus tool recipes, with no bundled scripts.
4. Names: `coding-performance-review` (generic), `coding-rust-performance-review` (Rust); the
   Python skill keeps `coding-python-performance-review`.

## 1. Who holds what

### `coding-performance-review` (new, generic)

- Method:
  - profile before optimising;
  - reproduce the recorded before figure before trusting an after figure;
  - identical settings on both sides;
  - interleaved A/B runs, at least 3 per arm, with the noise sized;
  - pin cores on hybrid CPUs;
  - prove the change took effect;
  - check speed claims in a diff with `validate_perf_claims.py`, moved here with its tests.
- Language-neutral checklist:
  - unbounded memory and unbounded input (the "Always flag" section moves here from the Python
    skill);
  - quadratic loops;
  - N+1 queries or calls;
  - per-item I/O that could be batched;
  - repeated work that could be cached;
  - blocking calls on hot paths.
- Router table: Python goes to `coding-python-performance-review`, Rust to
  `coding-rust-performance-review`, any other language uses this skill alone.

### `coding-python-performance-review` (slimmed)

- Keeps its pipeline and its seven Python-specific scripts.
- Its method text and "Always flag" section are replaced by a pointer to the generic skill. A
  Python review therefore loads two skills; that is the price of not duplicating the method.
- Its review-pipeline mode calls the moved claim checker at its new path.

### `coding-rust-performance-review` (new, no scripts)

- Checklist: needless clones and allocations in hot loops, missing `with_capacity`, `Box<dyn>` on
  hot paths, locks held across `.await`, blocking calls inside async code, collect-then-iterate,
  unbuffered I/O.
- Tool recipes: clippy's perf group, criterion for before/after benchmarks, a sampling profiler
  for flamegraphs, heaptrack or DHAT for allocations, release-profile settings (lto,
  codegen-units, debug symbols), and never timing a debug build.
- Profiler recipes are marked unverified until run on a real host.

### Housekeeping

- `coding-rust`'s "See also" points at the Rust performance skill.
- Each new skill starts its `.skillwriter/decisions.jsonl` ledger with the four decisions above.
- One minor release; the trigger map, `docs/skills.md` and the README skill count are regenerated.

## 2. Build and verification

- Every SKILL.md goes through `bitranox:meta-skill-writer` with a RED probe on the current skills
  showing the gap (a Rust performance task gets no criterion or release-profile advice; a bash
  review gets no N+1 or batching check), then GREEN with the new text. Plan and skill texts are
  authored on fable; executions run on opus.
- `validate_perf_claims.py` moves with `git mv`; its test moves into the generic skill's own
  `tests/` with a `conftest.py`. The Python skill's pipeline step names the new path, and a test
  pins that path.
- The Rust skill ships no script, so it needs no sibling tests. Before shipping, its clippy perf
  command is run once against a small real crate, so at least one recipe is executed.
- Gates: `repo-gate.py --ci` (frontmatter, trigger map, docs catalogue, README count, full
  suite). None of the three skills has a mirrored twin in a tool repo.
- Work happens in a worktree from origin/master; finishing is bump, push and CI watch.
