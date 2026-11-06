# skill-writer checklist - coding-performance-review (2026-11-06, new generic skill)

A new language-neutral performance skill: a measurement method (profile first, reproduce the
recorded before figure, identical settings, interleaved arms, core pinning on hybrid CPUs, prove
the change took effect, measure concurrency changes, two-sample load, check speed claims in a
diff), a neutral review checklist (unbounded memory and input, quadratic work, N+1 calls,
per-item I/O, repeated pure work, blocking calls, eager work), and a table routing Python and
Rust to their own skills. `validate_perf_claims.py` and its tests moved here from
`coding-python-performance-review`, unchanged in content and CLI; that skill's two path mentions
point here (its own checklist covers them).

Decisions: d-20261106-36a3e614, d-20261106-178d216c, d-20261106-61dc618d

- [x] Receipt fresh (`skill_receipt.py check meta-skill-writer`). Step 0b: `show
      coding-performance-review --kind rejected,removed --full` and `show coding-performance-review`
      printed nothing (no ledger before this change).
- [x] Not mirrored: the skill is new and ships only from this marketplace.
- [x] Skill type: technique and checklist; test is application - two review scenarios, G1 (a
      bash fan-out over 5,000 hosts plus a "now 3x faster" commit) and G2 (an all-A-then-all-B
      build timing on a hybrid CPU, 12 percent lower median, write the release-notes conclusion).
- [x] Inherited-coverage check: `redcheck --corpus-cascade .` reported G1 `clean` and G2
      `inherited` (strong term overlap with a memory fact about contended CPU measurements). The
      always-loaded memory index on this machine also states interleaving A/B arms and pinning
      the core on a hybrid CPU, and the G2 cascade-arm answer quoted both ("measured 1.6x apart",
      "the failing arm's conditions"). Route taken: the behavioural RED was re-run headless from a
      directory outside the knowledge tree with all hooks disabled (no cascade, no memory index),
      and on `haiku` as well as `opus`.
- [x] RED (no skill), four cells per scenario family:
  - G1 opus, cascade arm (baseline-probe): passes both points. Parallelism: "The real fix is
    concurrency plus timeouts, not a cache." Measurement: "Build one frozen host list and run old
    and new against it in alternating order (A,B,A,B), at least 3 runs each."
  - G1 opus, clean headless: passes both points. "Replace the loop with bounded parallel ssh using
    `-n`, `BatchMode`, and `ConnectTimeout`." and "Don't merge it on that claim without the
    cold/warm, same-host-count, output-diff evidence."
  - G1 haiku, clean headless: passes both points. "Run hosts in parallel. `xargs -P 50` or GNU
    `parallel` ..." and "A '3x' needs these numbers before I'd accept it: Wall-clock time for a
    cold run (empty cache) before and after, on the same 5,000-host list, repeated several times."
  - G2 opus, cascade arm: passes. "I can't support 'B is 12 percent faster' with this data" and
    "Alternate the builds: A, B, A, B ... Pin every run to one fast core with `taskset -c <cpu>`."
  - G2 opus, clean headless: passes. "We are not claiming a speedup yet." and "Alternate the runs
    ... Either pin the build to the performance cores ... or test pinned and unpinned separately."
  - G2 haiku, clean headless: FAILS. It attributes the gain: "Build time: Build B is faster than
    build A. In our timing runs ... the median build time for B was 12% lower than for A (five
    runs each)." It asks for the spread and the same power profile but never requires
    interleaving or pinning.
  - Reading: G1 does not flip on any tier; the baseline already batches and asks for a measured
    before/after. G2 flips only on `haiku`. Recorded as found, not escalated.
- [x] Skill gaps from RED: no guidance for benchmark design or honest reporting (G2, all arms);
      the only performance skill is Python-specific (G1, G2); laptop power state and thermal
      effects not covered (G2 opus).
- [x] GREEN (SKILL.md text pasted, told it is the text under test), four cells:
  - G1 opus (baseline-probe): passes both points. "the fix is bounded parallelism, for example
    `xargs -P N`" quoting "**N+1 calls.** A query, HTTP request, subprocess or RPC per item where
    one batched call would do."; "Measure three arms: A (parent commit), B-cold ... B-warm" and
    "Order: A, B-cold, B-warm, A, B-cold, B-warm, A, B-cold, B-warm" quoting "Interleave the arms:
    A, B, A, B, at least three runs each."; "The colleague's '3x' is a figure I have read, not
    measured."
  - G1 haiku (clean headless): passes. "Parallelism is the real lever. A `xargs -P 20` or GNU
    `parallel` version ..." and "Use a fixed subset of about 50 hosts ... Run A (current), B
    (candidate), A, B, A, B with cache state controlled".
  - G2 opus (baseline-probe): passes. "This data does not support a 12 percent claim." quoting
    "**Interleave the arms: A, B, A, B, at least three runs each.** All-A-then-all-B confounds
    the arm with the clock" and "Pin each run (`taskset -c N`, `sched_setaffinity`) or record
    which core type it ran on."
  - G2 haiku (clean headless): passes, the RED failure flipped. "Release-note conclusion: do not
    publish a 12% speedup claim yet." with "Not interleaved." and "Pin both arms to the same core
    type with `taskset`".
- [x] Diffed GREEN against RED both ways: nothing the RED arms produced is lost in GREEN (the
      stdin-swallowing `while read` / `ssh -n` finding, ConnectTimeout/BatchMode, stale cached
      uptime as a semantics change, and cold/warm cache arms all reappear in GREEN G1 opus or
      haiku). GREEN adds the per-arm spread, proof the cache was hit, and labelling read figures.
- [x] GREEN gaps worked:
  - Closed: the Common mistakes row told the reader to run `validate_perf_claims.py` on a claim
    in a commit message, but the tool reads only a diff's added lines (its own docstring:
    "Only ADDED lines are scanned"), so a message claim is never reported (G1 opus GREEN). The
    Fix cell now reads "Measure it; `validate_perf_claims.py` scans diffs, not commit messages".
    Quote-back on the final text (haiku): question 1 answered "No" quoting "`validate_perf_claims.py`
    scans diffs, not commit messages"; question 2 quoted "Measure it" plus step 10 and the
    reporting rule. No new undecided gap; its remaining gaps are listed below.
  - Declined, judgement left open: which statistic counts as "spread" and a threshold at n=5;
    whether a confounded measurement may appear with a caveat or is left out; which core type to
    pin (G2 opus/haiku). The rule is to interleave, pin and compare against the within-arm
    spread; the statistic belongs to the reader's context.
  - Declined, judgement left open: how to prove which build ran (hash, version string, build id)
    - step 6 states the requirement with examples; the method depends on the build system.
  - Declined, out of scope of a neutral checklist: laptop power state and thermal profile as
    settings (G2), network-bound jobs and remote-side drift (G1), stale data as a correctness
    severity (G1 haiku), bounded parallelism and timeouts as the remedy for a fan-out to distinct
    hosts (G1 opus) - owned by bitranox:coding-resilience for timeouts; the others are concerns
    for the plan's review, not decided here.
  - Declined, accurate as written: the exit-code comment "0 scanned, 2 unreadable" - the script
    has no exit 1 (`validate_perf_claims.py` returns only 0 or 2; docstring "Exit codes: 0 the
    diff was scanned (whether or not claims were found), 2 the diff could not be read or the
    arguments were invalid").
  - Declined, placeholder by design: `<this skill's directory>` and `origin/main` in the example;
    the reader substitutes the base directory the harness announces and the repo's default branch.
  - Declined, no tool to name: a profiler for bash; "a commit-message scanner" (the Fix cell now
    says to measure it).
- [x] Tiers and cells: RED 6 cells (G1, G2 x opus cascade, opus clean, haiku clean); GREEN 4
      cells (G1, G2 x opus, haiku); quote-back 1 cell (haiku). Every probe was asked for a
      `Skill gaps` section.
- [x] Every command the skill adds was executed: `validate_perf_claims.py` on a real 20-commit
      diff of this repository printed "Found 7 performance claim(s)" with `path:line` locations
      and exit 0; on a missing file it printed "No diff file found at: missing.diff" and exit 2;
      on a one-line diff "+now 3x faster" it printed "3x faster  (diff line 1)" and exit 0.
- [x] Frontmatter parses with a real YAML loader (`['description', 'name']`); description is 589
      characters, under the 1024 cap; ASCII only; history-phrase finder: no hit; no address,
      MAC, home or temp path; fences closed; no prose line over 100 columns (line 3 is the
      description).
- [x] Size: 1109 words, over the 500-word technique target; the text is the plan's fixed text for
      both halves the user chose (method plus neutral checklist), and the description carries the
      triggers.
- [x] Ledger: two `rule` entries (anchors "The language skills add their own tools on top of this
      one; the method is shared." and "Two halves: how to measure so that a number means what you
      think it means") and one `rejected` entry (one skill with per-language references), tier
      `user` (user decisions 2026-11-06), added with `skill_decisions.py add --from-file`;
      `skill_decisions.py check` reports 0 findings.
- [x] Tests: `tests/conftest.py` (sys.path plus the `run_script` and `clean_env` fixtures the
      moved tests use) and `tests/test_validate_perf_claims.py` (22 tests: 19 moved with the file,
      3 moved from the Python skill's shared test file) pass with CI's dependency set.
