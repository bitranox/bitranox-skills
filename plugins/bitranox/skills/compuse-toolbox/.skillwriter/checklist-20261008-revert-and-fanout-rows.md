# skill-writer checklist - compuse-toolbox (2026-10-08)

Change: two `## Tools` rows, `mutation_arm --revert` and `fanout_crosscheck`, for the two jigs
shipped in 8.1.0 and 8.2.0. Skill type: reference (retrieval test).

- [x] Receipt held (`skill_receipt.py start meta-skill-writer`).
- [x] RED (haiku, `bitranox:baseline-probe`, the table without the two rows, NONE allowed), run
      BEFORE the memory fact naming both jigs was written. Situation 1 (prove a new test fails
      against the committed `src/parser.py` and keep the uncommitted fix): answered with a
      hand-rolled `git show HEAD:src/parser.py > src/parser.py.buggy` plus a whole-file
      `--mutate`. Situation 2 (three parallel agents, one per repo, did any write a sibling's
      text): answered `grep_all "alpha_lib|beta-tool|gamma" /work` and listed "no tool directly
      detects misdirected content" as a gap.
- [x] Inherited context checked with `redcheck --corpus-cascade`: both scenarios are now INHERITED
      (STRONG), because the always-loaded index carries the fact
      `feedback-a-parallel-write-agent-can-clobber-a-sibling-target-and-report-success`, whose hook
      names both jigs. A behavioural RED run now would pass on that line, not on the table. Route
      taken: the RED above stands, and GREEN is a text check of the rows plus a quote-back
      retrieval run, whose quotes must come from the pasted table text (the inherited hook carries
      neither row's wording nor its arguments).
- [x] GREEN (same tier, same two situations, the use-when column of the edited table, NONE
      allowed): situation 1 chose `mutation_arm --revert` and quoted "`--revert FILE REV` swaps
      FILE for its text at REV for one arm and restores your work tree from a copy taken first";
      situation 2 chose `fanout_crosscheck`. Both quotes are verbatim in the row text.
- [x] GREEN diffed against RED both ways: the hand-rolled `git show ... > f` and the "no tool"
      gap are gone; no baseline result was lost.
- [x] Skill gaps from GREEN, each decided: `--test` syntax not stated - declined, the probe was
      given the use-when column only and the shipped Invoke column names `--test`; repo paths
      guessed - declined, inherent to the scenario; git context implied - declined, the row
      states the refusal outside a git work tree.
- [x] Every behaviour claimed in the rows checked against the scripts: refusal cases from
      `resolve_revert`, exit codes from each module docstring, untracked files counted as gained.
- [x] CSO description: unchanged. It is 1009 of 1024 characters, so a new trigger would need a
      rewrite with its own routing test; the two jigs are reached through the toolbox-nudge rule,
      the dispatching-parallel Verification item and this table.
- [x] Table canonical per `reformat_tables --check`.
- [x] Security scan: prose only; example paths are relative placeholders.
