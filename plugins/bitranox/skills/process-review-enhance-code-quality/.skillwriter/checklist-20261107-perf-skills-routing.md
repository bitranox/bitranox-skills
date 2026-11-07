# skill-writer checklist - process-review-enhance-code-quality (2026-11-07, perf skills routing)

The paragraph "**The cost rows are read, never measured.**" routed the measured performance pass
to `bitranox:coding-python-performance-review` on a Python project only. It now names
`bitranox:coding-rust-performance-review` for a Rust project and
`bitranox:coding-performance-review` for any other language, and says to start from the language
skill, which tells the reader to load the generic one alongside it for the measurement method
(both language skills say "load it alongside this skill": coding-rust-performance-review
SKILL.md:10, coding-python-performance-review SKILL.md:33).

Decisions: none - routing extended to the new performance skills; no rule changed.

- [x] Step 0b: `skill_decisions.py show process-review-enhance-code-quality` with and without
      `--kind rejected,removed --full` printed nothing (no ledger).
- [x] RED, pre-edit paragraph from `git show HEAD:`, opus and haiku. Scenario: the read-only sweep
      finished on a Rust CLI crate whose parser users call slow and on a Go service; which skill
      runs the measured part? Both tiers answered NONE for both projects, quoting "run
      `bitranox:coding-python-performance-review` on a Python project as a pass of its own".
- [x] GREEN round 1, opus and haiku: both quoted the Rust skill for the crate and the generic
      skill for Go. Both reported a gap the edit opened: "for the method and for any other
      language" read two ways (also run the generic skill beside the Rust one, or only take the
      method from it). Closed with "Start from the language skill where there is one: it tells you
      to load the generic skill alongside it for the measurement method."
- [x] GREEN round 2 on the final text, opus and haiku, with an added question on where the Rust
      crate's method comes from: both quoted the Rust skill, the generic skill for Go, and the
      sentence above for the method. 2 tiers, 6 cells in all (RED x2, GREEN x2 x2 rounds).
- [x] Remaining gaps, declined:
      - whether the measured pass is mandatory, what "did not run" covers, and using a reported
        slowdown to aim the pass: pre-existing wording outside this change, a judgement the skill
        leaves to the reviewer;
      - a project in several languages: no rule exists and none is invented here;
      - the parenthetical's examples (test suite, caching candidates) lean toward Python: they are
        examples, and each language skill states its own tools;
      - haiku could not find the two new skills in its own skill listing: they are not installed
        until this change ships, a property of the probe machine, not of the text.
- [x] Added lines: none over 100 columns, no fence. ASCII only.
