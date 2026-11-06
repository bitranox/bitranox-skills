# skill-writer checklist - coding-performance-review (2026-11-06, trigger words and claim line)

Two changes. The description is reworded so the keywords the router derives from its head are
performance words instead of general ones; the body is unchanged. The claim checker's closing
advice names the Method section of this skill instead of two tools that exist only in the Python
skill.

Decisions: d-20261106-66a56ec2

- [x] Receipt fresh (`skill_receipt.py check meta-skill-writer`). Step 0b: `show
      coding-performance-review --kind rejected,removed --full` lists one rejected entry
      (one-skill-per-language-refs), untouched by this change; no live `rule` anchor sits in the
      description, so no rule is superseded.
- [x] Mechanism read before the rewrite: `build_skill_triggers.py` keeps the first 14 distinct
      tokens of 4+ characters outside its stopword list, in description order, then appends only
      identifier-shaped tokens no other skill claims; `skill-router.py` `match()` nominates a skill
      at 2 distinct word-boundary hits. Words of 3 characters or fewer (N+1, I/O, A/B, Go, SQL)
      never become tokens.
- [x] RED (pre-change description, router `match()` with the shipped map): "fix the typo in the
      commit message" nominates this skill (2 hits), "reword the commit message for this change"
      (3), "which language should the docs be in, reviewing them now" (2); "the bash script loops
      over hosts and is slow", "profile why this endpoint got slow", "is this benchmark A/B result
      real or noise" and "review this Go service for N+1 queries" nominate nothing.
- [x] GREEN (new description, regenerated map): the three general prompts score 0 and nominate
      nothing for this skill; the bash, endpoint, benchmark-noise and N+1 prompts nominate it
      (2 hits each), as do "this commit claims a 3x speedup, is the benchmark believable" and
      "memory grows unbounded when the input file is large".
- [x] Control arm for over-triggering: prompts sharing a word with the new head stay at 1 hit and
      nominate nothing for this skill ("please review this change for correctness", "the build is
      slow, can you check the CI config", "benchmark the new laptop against the old one before
      buying", "profile this pytest suite for lru_cache candidates").
- [x] Replay over 1998 distinct typed prompts from local transcripts: the old head nominated this
      skill on 8, five of them unrelated (a permission-rule paste, a CI-version request, two harness
      probes, a deploy-routine request); the new head nominates it on 8, all about performance
      (five "performance review" requests, a slow bash loop scenario, an ODBC performance and
      memory-leak test request, one pasted review comment the old head also nominated).
- [x] Python prompt check: "profile this pytest suite for lru_cache candidates" gives this skill
      1 hit and coding-python-performance-review 0, so the router nominates neither; this skill
      does not outrank the Python one there.
- [x] Routing through the model-read skill listing is unverified: the old description is installed
      on this machine, so a live probe would answer from it. Text check instead: the description
      keeps every trigger the old one carried (optimising, speedup claim in a diff or commit, A/B
      win and no-difference result, timing versions, builds and configurations, algorithmic cost,
      N+1, per-item I/O, repeated work, blocking calls, unbounded memory, bash, JavaScript, Go,
      SQL) and the routing sentence for Python and Rust.
- [x] Front matter parses with a YAML loader (`['description', 'name']`); description length
      measured with `len()`: 603 characters, under the 1024 cap. ASCII only.
- [x] Derived artifacts regenerated: `build_skill_triggers.py` (only this skill's entry changed)
      and `build_skill_docs.py`; `build_skill_triggers.py --check` reports in sync.
- [x] Claim line: new test
      `test_cli_advice_names_no_language_specific_tool` reads the forbidden names from the Python
      skill's directory (asserting `find_hotspots` and `compare_performance` are among them) and
      requires the CLI output to name none of them and to name the Method section. RED: with the
      script reverted to its pre-fix text the test fails, `assert ['compare_performance',
      'find_hotspots'] == []`. GREEN: passes on the fixed line. The script's module docstring
      carries the decision in a `Decisions:` block pinned by that test.
- [x] Ledger: one `rejected` entry for the general-word head (`skill_decisions.py add`);
      `skill_decisions.py check` reports 0 findings.
