# skill-writer checklist - coding-rust-performance-review (2026-11-06, new skill)

A new Rust performance skill: measure the release build, keep symbols without changing code
generation, profile settings as A/B arms; a clippy command (the `perf` group as errors plus eight
off-by-default lints); criterion before/after with saved baselines; hyperfine as a cross-check to
an interleaved loop; profiler and allocation recipes; and a table of Rust patterns to flag. No
scripts. The measurement method and the language-neutral checklist stay in
`bitranox:coding-performance-review`, which this skill tells the reader to load alongside.

Decisions: d-20261107-b46d031b, d-20261107-7305f1f6

- [x] Receipt fresh (armed for the session). Step 0b before the first edit: `show
      coding-rust-performance-review --kind rejected,removed --full` exited 2 ("no skill"), the
      skill did not exist. After the ledger was written, `show` lists the two entries above and
      `skill_decisions.py check coding-rust-performance-review` reports 0 findings.
- [x] Not mirrored: the skill is new and ships only from this marketplace.
- [x] Skill type: technique plus reference (checklist and tool recipes); test is application,
      two review scenarios:
      - R1: `summarize(items)` with `Vec::new()` pushed per item, `item.name.clone()`,
        `Regex::new(r"\d+")` inside the loop, and `out = out + &format!(...)`; "I timed
        `cargo run` before and after the fix and it got 20 percent faster. Review the code and the
        measurement."
      - R2: an axum handler holding a `std::sync::Mutex` guard across two `.await`s and calling
        `std::fs::read_to_string` on a 2 GB file. "Review it for performance."
      Every dispatch ended by asking for a "Skill gaps" section.
- [x] Probe set-up: headless `claude -p --output-format stream-json --verbose`, opus at effort
      medium and haiku, prompt on stdin, run from a scratch directory outside the knowledge tree;
      the prompt says text only, no tools, no skill. The answer is the FIRST assistant text block
      of the stream-json output. 8 cells for RED and GREEN, plus 4 for the final-text re-run.
- [x] Inherited-coverage check: `redcheck --scenario <R1> --corpus-cascade <probe dir>` read 2
      documents and reported `clean`. Run from the repo instead, it lists only generic term
      overlap (cargo, regex, percent, reply) with memory facts about gates and process, none about
      Rust performance; the probes did not run from the repo.
- [x] Contamination note: in all four RED cells a hook told the agent to load `bitranox:coding-rust`
      and each declined, as the prompt asked. The installed plugin has no Rust performance skill,
      and the RED haiku R1 arm said so ("No available skill covers Rust performance review").

## RED (no skill), 4 cells

Points required by the plan: R1 - release build or criterion, `with_capacity`, the clone, the
regex in the loop, clippy's perf lints. R2 - the guard across `.await`, blocking I/O in async
(`spawn_blocking` or `tokio::fs`), the unbounded read.

- [x] R1 opus: release build ("`cargo run` uses the debug profile by default"), criterion
      ("Save a baseline before the change (`cargo bench -- --save-baseline before`)"), the clone
      ("`name` is cloned for no reason"), the regex ("The regex is compiled once per item"),
      `with_capacity` only inside its rewrite (`String::with_capacity(items.len() * 32)`).
      MISSING: clippy, in any form. hyperfine suggested with no word on its run order.
- [x] R1 haiku: release build ("Plain `cargo run` is a debug build"), criterion, the clones
      ("Redundant clones"), the regex ("Regex compiled on every iteration"), `with_capacity` in its
      rewrite. MISSING: clippy. hyperfine "--runs 30 ./old ./new" with no word on run order.
- [x] R2 opus: guard ("A `std::sync::Mutex` guard is held across both `.await`s"), blocking I/O
      ("`std::fs::read_to_string` blocks a Tokio worker", fix uses `tokio::task::spawn_blocking`),
      unbounded read ("2 GB is allocated per request just to count lines"). No measurement plan:
      "the throughput claims are reasoned, not benchmarked".
- [x] R2 haiku: guard ("`std::sync::MutexGuard` held across `.await`"), blocking I/O ("Blocks an
      async worker thread", `spawn_blocking` named in point 4), unbounded read ("Allocates about
      2 GB"). No measurement plan: "I did not measure any of this."
- [x] RED verdict: R1 fails on both tiers (clippy absent); R2 passes its three content points on
      both tiers, a tie on the action; neither R2 arm says how to measure the change.

## Commands executed before GREEN (scratch crates, clippy 0.1.95, cargo/rustc 1.95.0)

- [x] The clippy command, verbatim from the SKILL.md, from the crate root. On the plan's fixture
      alone (a loop-carried `re.clone()` and `collect::<Vec<char>>().iter().collect()`): exit 0,
      no lint, no "unknown lint". `redundant_clone` is conservative and does not see that clone;
      the skill already says it "finds some". Fixtures added from the lints' own `--explain`
      examples, plus a `manual_memcpy` loop:

      ```text
      warning: avoid using `collect()` when not needed
         = note: requested on the command line with `-W clippy::needless-collect`
      warning: redundant clone
         = note: requested on the command line with `-W clippy::redundant-clone`
      warning: use of `format!` to build up a string from an iterator
         = note: requested on the command line with `-W clippy::format-collect`
      error: it looks like you're manually copying between slices
         = note: `-D clippy::manual-memcpy` implied by `-D clippy::perf`
      error: could not compile `probe` (lib) due to 1 previous error; 3 warnings emitted
      ```

      Exit 101. Lint names reported: needless_collect, redundant_clone, format_collect,
      manual_memcpy.
- [x] Control for "no unknown lint": the same run with `-W clippy::redundant_clones` (typo)
      prints `warning[E0602]: unknown lint: clippy::redundant_clones`, so the clean runs above
      prove the eight names are known.
- [x] Lint facts: `cargo clippy -- -W help` lists the `clippy::perf` group with 36 members,
      including regex-creation-in-loops, manual-memcpy and large-enum-variant; all eight `-W`
      lints are `allow` by default; `await-holding-lock` is `warn` by default.
- [x] criterion: `cargo add --dev criterion` (0.8.2), the `[[bench]]` block and the bench file as
      written (with `load_input` and `parse` defined). `cargo bench --bench hot_path --
      --save-baseline before`: "parse time: [81.633 us 82.159 us 82.800 us]". Unchanged code,
      `-- --baseline before`: "change: [-1.4861% -0.3554% +0.5308%] (p = 0.54 > 0.05) No change in
      performance detected." A rewrite of `parse`: "change: [+14.121% +15.440% +16.517%] (p = 0.00 <
      0.05) Performance has regressed."
- [x] `CARGO_PROFILE_RELEASE_DEBUG=line-tables-only cargo build --release`: "Finished `release`
      profile [optimized + debuginfo]".
- [x] hyperfine 1.20.0 (installed into the scratch directory): `hyperfine --warmup 3 ./old ./new`
      with each script appending its name to a log; the log holds 3666 `old` lines, then 3343
      `new` lines, in two contiguous runs, so hyperfine does run all of one command's runs first.
- [x] dhat crate: the `#[global_allocator]` and `dhat::Profiler::new_heap()` lines in a release
      binary print "dhat: The data has been saved to dhat-heap.json" and write the file.
- [x] `String + &str` claim (table row, added in REFACTOR): a release binary doing
      `out = out + &format!(..)` 50 times on a pre-sized `String` keeps the same buffer pointer
      ("same buffer: true").
- [x] Not executed: `cargo flamegraph`, `samply`, `perf`, `heaptrack` (not installed); the skill
      labels those recipes unverified.

## GREEN (both skills pasted: the generic SKILL.md and this one), 4 cells

- [x] R1 opus: release ("Never time a debug build. `cargo run` and `cargo test` without
      `--release` build the dev profile"), criterion ("`cargo bench --bench hot_path --
      --save-baseline before` on the old code"), the clones ("`name` is cloned twice per item"),
      the regex ("Clippy's `regex_creation_in_loops` lint, which is in the `perf` group, should
      catch this"), clippy ("run the skill's clippy command (`-D clippy::perf -W
      clippy::redundant_clone ...`)"), `with_capacity` in its rewrite. PASS.
- [x] R1 haiku: release, criterion ("`cargo bench --bench summarize -- --save-baseline before`"),
      the clones, the regex, clippy ("Clippy's `regex_creation_in_loops` (in the `perf` group)
      should flag this"). `with_capacity` dropped: its rewrite deletes the dead `v` and starts
      `out` with `String::new()`. PASS on four points, see the diff below for the fifth.
- [x] R2 opus: guard (quotes the table row "A `std::sync::Mutex` or `RwLock` guard alive across
      `.await`"), blocking I/O (quotes "Blocking calls in async code (`std::fs`,
      `std::thread::sleep`, heavy CPU)", uses `spawn_blocking`), unbounded read (quotes
      "`read_to_string`/`read_to_end` on a large input"). Adds a measurement plan (release,
      interleave, heaptrack, prove the change). PASS.
- [x] R2 haiku: guard, blocking I/O ("`tokio::fs`, `spawn_blocking`, or a thread pool such as
      rayon"), unbounded read. Adds a measurement plan. PASS.
- [x] Diff against RED, both directions. Gained: clippy (0 of 4 RED R1 cells, 2 of 2 GREEN R1);
      a measurement plan for R2 (0 of 2 RED, 2 of 2 GREEN). Lost: `with_capacity` in GREEN R1
      haiku; every RED R1 cell had it only inside a rewrite, not as a finding. The scenario's
      `Vec` is dead code, so deleting it (what every arm did) removes the pattern; the remaining
      `String` capacity is a guess the arms flag as such. Re-run of the same haiku cell on the
      final text (below) has it ("`String::new()` grows without a capacity hint. The skill
      suggests `with_capacity` when the length is known"), so the loss does not reproduce.

## REFACTOR

Gaps reported by the GREEN cells, and what was done with each:

- [x] CLOSED: the table row "String built with `+` or `format!` per iteration" implied that
      `out = out + &str` is costly. GREEN R1 opus: "in Rust, `String + &str` takes ownership of
      `out` and appends in place". Executed check above ("same buffer: true"). The row now reads
      "`format!` into a temporary on every iteration (`out = out + &format!(..)`)" with the fix
      "`write!` into one `String`; `String + &str` alone already appends in place". Same column
      widths, one row changed.
- [x] CLOSED: hyperfine against the generic method's interleaving, reported by GREEN R1 opus and
      haiku ("Swapping the order is not interleaving"). The paragraph now says hyperfine "is not
      the interleaving the generic method asks for: alternate `./old` and `./new` in a loop of
      your own for the verdict, and treat a hyperfine run (repeated with the order swapped) as a
      cross-check only." The hyperfine run-order fact is executed above.
- [x] DECLINED (judgement): the lock row's `tokio::sync::Mutex` alternative still serialises
      requests (GREEN R2 opus, both rounds). The row leads with "End the guard's scope before the
      await" and offers the tokio mutex only "if it must be held"; every arm chose an atomic for
      the counter, which ends the guard's scope. The generic checklist also flags "a lock held
      while waiting".
- [x] DECLINED (owned elsewhere): upstream timeouts, response-size caps, mutex poisoning and
      `unwrap()` panics (R2, both tiers): `bitranox:coding-resilience` and `bitranox:coding-rust`
      own them, and the haiku arm named the former itself.
- [x] DECLINED (out of scope): load-testing an HTTP handler under concurrency (R2, both tiers);
      the generic method's arm rules apply whatever the load tool, and choosing one is the
      reviewer's judgement.
- [x] DECLINED (out of scope): `LazyLock` minimum Rust version and `\d` Unicode semantics (R1,
      both tiers). `std::sync::LazyLock` is stable since Rust 1.80; a project's MSRV and a regex's
      meaning are correctness questions, not performance ones.
- [x] DECLINED (judgement): a recorded before figure that came from a debug build (R1 opus), and
      "no recorded before figure at all" (R1 haiku, R2 haiku). The generic step 2 applies when a
      figure exists; a debug-build figure fails "Never time a debug build" and is re-measured.
- [x] DECLINED (judgement): criterion's saved-baseline before/after runs the arms in sequence
      (re-run haiku). The skill already says "A criterion run is a micro-benchmark: confirm a win
      on the real workload too", which is where the interleaved arms run.
- [x] DECLINED (covered elsewhere): dead work such as the unused `Vec` (R1, both tiers); the
      generic checklist's "Eager work that is mostly thrown away" covers it, and every arm deleted
      it.
- [x] Width and fence check over the added lines: none over 100 columns, every fence closed, ASCII
      only. Paragraph after each insertion point read: the hyperfine paragraph is followed by the
      `## Profilers and allocations` heading; the table row has no back-reference.
- [x] Anchor of rule d-20261107-b46d031b unchanged; `skill_decisions.py check` 0 findings after the
      REFACTOR edits.

## Re-run on the final text (same prompts), 4 cells plus one repeat

- [x] R1 opus: quotes "`write!` into one `String`; `String + &str` alone already appends in place"
      and "Run `hyperfine --warmup 3 ./old ./new` in both orders as a cross-check only", with an
      interleaved `for arm in old new` loop for the verdict; clippy as step 1 ("run the clippy
      command from Skill 2"). All R1 points present except `with_capacity` (dead `v` deleted, no
      capacity on `out`). PASS.
- [x] R1 haiku: release, criterion, clones, regex, `with_capacity`, an interleaved loop; clippy
      only named in its gaps ("Clippy command not run"), not as a step. Repeated once: the repeat
      has every R1 point, clippy as a step ("Run `cargo clippy --all-targets -- -D clippy::perf`.
      It should flag `regex_creation_in_loops`") and `with_capacity`. The omission did not
      reproduce. New gap from the repeat (criterion runs arms in sequence) declined above.
- [x] R2 opus and haiku: all three R2 points, with quotes from the unchanged rows. The only new
      gap (`tokio::fs` alone keeps the 2 GB in memory, R2 opus) is answered by the adjacent
      `read_to_string` row, which both arms applied together with the blocking row.
- [x] No new undecided gap. Tiers: opus (effort medium) and haiku; 13 behavioural cells in all
      (4 RED, 4 GREEN, 4 final, 1 repeat).

## Other checks

- [x] Description: 530 characters (`len()` of the parsed field), under 1024; frontmatter parses
      with a YAML loader to `['description', 'name']`.
- [x] History-phrase finder and the address grep over the skill directory: no hits.
- [x] Body 926 words: a checklist plus tool recipes, no supporting files.
- [x] Trigger map and catalogue regenerated (`build_skill_triggers.py --check`: "in sync (85
      skills)"; `build_skill_docs.py --check`: "docs/skills.md in sync"); README and
      docs/installation.md counts set to 85.
