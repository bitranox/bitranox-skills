# skill-writer checklist - coding-python-performance-review (2026-11-07, single-run delta)

The `compare_performance.py` bullet presented the tool's delta as "the measured delta as
before/after evidence", while the tool times each arm once (`_compare()` in
compare_performance.py: one `_time_before`, one `_time_pytest_ms`), and the generic method
(coding-performance-review SKILL.md:34-36) calls an unrepeated, non-interleaved pair noise. The
bullet now says the tool times each arm once, one after the other, and to repeat it until each arm
has at least three runs, alternating, before quoting a delta.

Decisions: none - aligns this bullet with the generic method's rule; no new rule.

- [x] Step 0b: `skill_decisions.py show coding-python-performance-review` lists only
      d-20261106-4e9b9bbf (method lives in the generic skill); this change follows it.
- [x] RED, pre-edit bullet from `git show HEAD:`, opus and haiku. Q: one run printed BEFORE 41.2 s,
      AFTER 30.1 s; may "27% faster" go in the PR? Both said not yet, citing only the general
      "Before trusting an AFTER figure ... interleave the arms" line; opus reported "the text says
      to 'interleave the arms' but gives no flag or loop to do that".
- [x] GREEN, edited bullet, opus and haiku: both quoted "It times each arm once, one after the
      other, so one run is a single sample, not evidence: repeat it until each arm has at least
      three runs, alternating, before quoting a delta" and answered "run it again until each arm
      has at least three runs". 2 tiers, 4 cells (RED and GREEN on each).
- [x] Gaps, declined:
      - each run times BEFORE first: successive runs still give B, A, B, A, which is the
        alternation asked for;
      - how to combine the runs: the generic method item 4 ("Report the median and the spread per
        arm"), which this bullet points at;
      - no command for pinning the core: generic method item 5 names `taskset -c N`.
- [x] Added lines: none over 100 columns, no fence. ASCII only.
