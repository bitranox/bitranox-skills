# skill-writer checklist - process-agents-subagent-driven-development (2026-10-16, opus tier)

- [x] Change: "Model Selection" and "Concrete tiers" now map to two working tiers, `haiku` for purely
      mechanical work and `opus` for everything else (`fable` above it unchanged), always passed as the
      alias so `opus` resolves to the latest Opus. A paragraph says `sonnet` is not a tier and why
      (more turns and reasoning tokens per job outweigh its lower per-token price). The effort table
      folds the old `sonnet` and `opus` rows into one `opus` row. The task-complexity signals lose the
      "standard model" middle. The description drops `sonnet` from its tier list.
- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED (text check of the artifact): `plugins/bitranox/hooks/tests/test_model_tiers.py`, written
      before the edit, failed with 45 plugin-wide `sonnet` tier lines, 4 of them in this skill. A
      behavioural RED was replaced on purpose: `redcheck.py --corpus-cascade` reported INHERITED
      COVERAGE (STRONG) - the always-loaded memory index on the authoring machine already says
      "never sonnet", so a behavioural arm answers `opus` with or without this text.
- [x] GREEN: the test passes; only the two EXPLANATIONS lines here name `sonnet`.
- [x] GREEN application probe (opus, text only, Skill gaps requested): 5 of 5 dispatches pinned as
      intended, each with the deciding line quoted (per-file layering reviewers `opus`, regex log
      scan `haiku`, complete-code implementer `haiku`, duplicate-deciding store reader `opus`,
      "sonnet is cheaper" refused with the turn-count line).
- [x] Gaps closed: "scanners" listed under both tiers (now: the judging decides the tier, not the
      fan-out); "complete code" vs "complete spec" (a prose spec is `opus`); "two working tiers"
      beside `fable` (now names `fable` as the exception); a single-file mechanical fix in prose got
      two answers (the complexity signal now names it `haiku` like the rule above it).
- [x] Each closing fix verified by quote-back: a second probe quoted the deciding line for a
      non-judging regex fan-out (`haiku`), a judging one (`opus`) and a prose 2-file spec (`opus`),
      and answered NONE for any line allowing `sonnet`.
- [x] Gaps declined: no tight-budget mode (the section's point is that a cheaper tier is not cheaper
      per job; scope cuts belong to planning); how effort is set and when the adversarial row applies
      (the effort paragraph, cut from the probe's excerpt, says it rides the agent type or a Workflow
      call; the row boundary predates this change); whether a regex job needs a model at all (owned by
      the design-time dispatch rule in meta-skill-writer); the description still listing `sonnet`
      (the probe read the installed listing; this change removes it).
- [x] Description measured: unchanged except the tier list; still trigger-first, under 1024
- [x] Security scan: prose edits only, no secrets, hostnames, paths or PII
