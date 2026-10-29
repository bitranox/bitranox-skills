# skill-writer checklist - process-test-design (memory rules folded in, batch 10)

- [x] Change: SKILL.md: ## Prefer real over mocked; mock only at the true edge (new bullet after 'Default to integration / e2e', lines 30-37)
- [x] Change: SKILL.md: ## Reproducing a flake: starve it, or slow the clock it races (race-between-tasks bullet REPLACED, lines 447-461)
- [x] Change: SKILL.md: ## Wait on whatever lands LAST (appended paragraph, lines 436-441)
- [x] Change: SKILL.md: ## Adversarial inputs at the boundary (new paragraph after 'The branch rule governs the axis table above', lines 292-300)
- [x] Change: SKILL.md: ## Deterministic and order-independent (new bullet after the zero-deadline bullet, lines 409-419)
- [x] Change: SKILL.md: ## Prefer real over mocked - 'Never patch the clock function itself' bullet (appended sentences, lines 59-64)
- [x] Change: SKILL.md: ## Scrub a captured artifact fully before it becomes a fixture (new paragraph at section end, lines 332-339)
- [x] Change: silent-test-defeaters.md: ## Python patch and import mechanics - new ### after 'Harvest a pytest.raises(match=...) pattern per parametrized arm' (lines 346-353); routing lines 
- [x] Change: silent-test-defeaters.md: ## Determinism and environment - new ### after 'A blocking stub must exec its blocker' (lines 153-170); routing lines in SKILL.md and the reference he
- [x] Change: silent-test-defeaters.md: ## Determinism and environment - new ### after 'Bound every loop in a test by something the subject does not control' (lines 33-56); routing lines in 
- [x] Change: SKILL.md: ## Injecting a callable as a seam: four traps a green suite cannot show (heading and 'Three things' -> 'Four things'; new fourth trap at section end, 
- [x] Change: SKILL.md: Mechanics list before '## Quick checklist' ('Nine mechanics' -> 'Ten mechanics', line 662; new bullet after 'from m import X binds a COPY', lines 670-
- [x] Review fixes: the slow-upstream double releases its body on a test-set event (no timed knob outside the integration tier); only a monotonic patch freezes asyncio timers; the four-traps intro covers any injected callable.
- [x] Receipt held (the coordinator ran skill_receipt.py start meta-skill-writer); every editing
      agent loaded the skill through the Skill tool before its first edit.
- [x] RED as a text check: a quote-back against a pre-edit snapshot of each skill (43 rows). The
      rules under test are recorded in this machine's memory store, so a behavioural arm would
      be contaminated; only a verbatim quote counts. RED: 21 NONE, 13 PARTIAL, 9 full.
- [x] GREEN quote-back round 1: opus 42/43 full (1 PARTIAL, a row that routes to provmm-build by
      design), haiku 39/43. Round 2 on the 10 rows the review fixes touched: 10/10 on both tiers, quotes substring-checked with quotecheck (10 OK) and a planted false quote as the negative control (MISMATCH).
- [x] Independent opus review of both diffs: no factual error (pydantic, re, prctl, asyncio, bmk,
      PyPI, workflow claims probed), no public leak, no lost content; 8 findings fixed.
- [x] Mirror twins regenerated from the marketplace text; repo-gate --mirrors: 0 of 12 drifted.
- [x] Description measured: unchanged (frontmatter not edited).
- [x] ASCII only, present tense, tables canonical, added prose wrapped to the file's width.
- [x] Security scan: prose only; no secrets; marketplace text carries no private host, path or name.
