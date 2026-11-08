# skill-writer checklist - coding-rust-performance-review (2026-11-07, criterion interleave)

The criterion before/after recipe (`--save-baseline before` on the old code, then `--baseline
before` on the new code) is one all-A-then-all-B pair, which the generic method calls noise and
which the hyperfine paragraph right below already flags. The recipe now says to alternate old and
new at least three times each, saving each run under its own name, and to compare saved runs with
`--load-baseline new1 --baseline old1`.

Decisions: none - aligns the criterion recipe with the generic interleaving rule; no new rule.

- [x] Step 0b: the edit guard printed the two rejected entries (d-20261107-7305f1f6 scripted
      pipeline, d-20261107-c3150209 old description); neither is touched.
- [x] Executed on a scratch crate (criterion from crates.io, one `bench_function`):
      `cargo bench --bench hot_path -- --help` lists `--save-baseline`, `--baseline` and
      `--load-baseline` ("Load a previous baseline instead of sampling new data");
      `-- --save-baseline old1` rc 0, `-- --save-baseline new1` rc 0,
      `-- --load-baseline new1 --baseline old1` rc 0 and printed
      "change: [-2.3472% -1.0551% +0.2309%] (p = 0.11 > 0.05)" / "No change in performance
      detected." (minus signs as printed, shown here in ASCII).
- [x] RED, pre-edit paragraph from `git show HEAD:`, opus and haiku. Q: one save/compare pair says
      "Performance has improved" (-12%, p < 0.05); enough? Neither tier produced a criterion
      re-run: both answered with "confirm a win on the real workload too" and the hyperfine loop.
- [x] GREEN, edited paragraph, opus and haiku: both quoted the new sentence and listed the runs
      `--save-baseline old1`, `new1`, then old2/new2, old3/new3, then
      `--load-baseline new1 --baseline old1` per pair. 2 tiers, 4 cells.
- [x] Gaps, declined:
      - core pinning not mentioned here: the skill's opening paragraph lists "pin the core" as part
        of the generic method it defers to (SKILL.md:8-10);
      - which pairs to compare and how three comparisons make a verdict: each new run against its
        own old run is the shown example; the verdict rule is the generic method item 4 (median
        and spread per arm);
      - how to switch between old and new code: left to the reader (worktree, checkout).
- [x] Added lines: none over 100 columns, no fence. ASCII only.
