# skill-writer checklist - coding-rust-performance-review (2026-11-07, trigger words and claims)

Three changes. The description is reworded so the keywords the router derives from its head are
Rust and performance words instead of general ones. The profiler paragraph scopes "unverified" to
the flamegraph, samply, perf and heaptrack recipes and states that the `dhat` snippet is verified.
The `panic = "abort"` arm says it changes behaviour as well as speed.

Decisions: d-20261107-c3150209

- [x] Receipt fresh (`skill_receipt.py check meta-skill-writer`). Step 0b: `show
      coding-rust-performance-review --kind rejected,removed --full` lists one rejected entry
      (scripted-pipeline), untouched by this change; the live `rule` anchor ("ships no scripts,
      because clippy and criterion already do the mechanical part.") is unchanged.
- [x] Mechanism read before the rewrite: `build_skill_triggers.py` keeps the first 14 distinct
      tokens of 4+ characters outside its stopword list, then appends only identifier-shaped
      tokens no other skill claims; `skill-router.py` `match()` nominates at 2 distinct
      word-boundary hits and returns at most 2 skills.
- [x] RED (pre-change description, `match()` over the map built from the skills directory):
      "review this Rust code for secrets handling and crate choices" and "review this Rust async
      code with tokio" nominate this skill (rust + code, 2 hits each); "my Python loop is slow"
      nominates it alone (slow + loop); "set up criterion benchmarks for my Rust parser", "profile
      my rust binary with a flamegraph" and "this async rust handler holds a lock across .await"
      nominate nothing.
- [x] GREEN (new description, regenerated map; new head rust, slow, performance, benchmark,
      criterion, flamegraph, samply, perf, heaptrack, dhat, clones, with_capacity, spawn_blocking,
      await): the two coding-rust prompts score 0 here and nominate coding-rust; the Python loop
      prompt scores 0 and nominates nothing; the criterion, flamegraph and .await prompts nominate
      this skill (2 hits each).
- [x] Controls: "my python script is slow, profile it" scores 0 here and nominates
      coding-performance-review only. "fix the clippy warnings in this rust crate" scores 1 here
      (`clippy` is not in the head, on purpose: fixing clippy warnings is not a performance task,
      and a perf-lint prompt still reaches 2 through `perf`) and nominates coding-rust only.
      "how should I handle errors in this Rust library, thiserror or anyhow?" nominates
      coding-rust only. "my rust cargo build fails with a linker error" and "the release pipeline
      is slow" nominate nothing (`cargo` and `release` are kept out of the head).
- [x] Residual over-trigger, accepted: two generic performance words still reach 2 without
      "rust". "the python benchmark is slow" nominates coding-performance-review and this skill;
      "python performance is slow" scores 2 here but the top two are the generic and the Python
      skill. Keeping `benchmark` buys "benchmark my rust parser against the old build" (2 hits;
      0 without it).
- [x] Replay over 2478 distinct typed prompts from local transcripts: the old head nominated this
      skill on 8, seven unrelated (a UAC prompt with "slow machine", a pasted backlog line, a
      pasted permission warning, two skill notes, a free-threading test note, a Rust design idea)
      and one Rust performance review request; the new head nominates it on that one only.
- [x] Routing through the model-read skill listing is unverified: the old description is installed
      on this machine, so a live probe would answer from it. The `match()` measurement above is the
      evidence. Text check: the new description keeps every trigger and keyword of the old one
      (slow code and loops, clones, allocations, Vec or String without capacity, Regex::new or
      format! in a loop, blocking async and a lock across .await, unbuffered I/O, criterion and
      cargo bench, profiler and flamegraph, release-profile settings, timing two builds, clippy
      perf, samply, heaptrack, DHAT, with_capacity, spawn_blocking).
- [x] Front matter parses with a YAML loader (`['description', 'name']`); description length
      measured with `len()`: 485 characters, under the 1024 cap; starts "Use when", triggers only,
      ASCII only.
- [x] Derived artifacts regenerated: `build_skill_triggers.py` (only this skill's entry changed)
      and `build_skill_docs.py`; both `--check`s report in sync.
- [x] `panic = "abort"` claim executed: one `main.rs` with a `Drop` type inside `catch_unwind`
      around a `panic!`. Built with `-C panic=unwind` it prints "drop ran" and
      "catch_unwind returned is_err=true", exit 0; with `-C panic=abort` it prints the panic
      message only and exits 134 (SIGABRT).
- [x] Quote-back on the final text (both paragraphs, opus effort medium and haiku, skill text
      pasted, first assistant text block read). Both tiers quote "The flamegraph, samply, perf and
      heaptrack recipes are unverified: none of those tools has been run for this skill. The
      `dhat` crate snippet is verified: it writes `dhat-heap.json`." for the verified question,
      and "`panic = "abort"` (a behaviour change as well: a panic no longer unwinds, so `Drop`
      does not run and `catch_unwind` catches nothing)" for the behaviour question. 2 tiers,
      2 cells.
- [x] Skill gaps reported by the quote-back, decided:
      - No verified flamegraph route: declined, the tools are not available on the authoring host,
        which is what the scoped label now says.
      - `dhat` setup (feature flag, the dhat allocator slowing the build it profiles): declined for
        this change, out of scope of the review findings it fixes; open for the next edit.
      - Profiler symbols not linked to the recipes: declined, covered by the "Keep symbols without
        changing code generation" bullet under "Measure the build you ship".
      - Debug symbols set as a default while profile settings are A/B arms (haiku): declined,
        the same bullet says "Debug info does not change the optimisation level".
      - Whether a 3% result is real, and a panic in a thread ending the process: declined, the
        measurement method is owned by `bitranox:coding-performance-review`, and the clause flags
        `panic = "abort"` as a behaviour change, which is what the arm needs to be judged as.
- [x] Width and fence check over the added lines printed nothing; the paragraphs after both
      insertion points (the "Lint first: clippy" heading and the recipe list) read unchanged.
- [x] Ledger: one `rejected` entry for the general-word head (`skill_decisions.py add`);
      `skill_decisions.py check coding-rust-performance-review` reports 0 findings.
