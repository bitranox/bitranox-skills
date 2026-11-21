# skill-writer checklist - process-test-design (race-test stress workers; worker stderr)

- [x] Change: references/silent-test-defeaters.md gains "A multi-process race test's cause is in
      the crashed worker's stderr" and "A stress worker must leave a gap after each write that
      took the lock"; the SKILL.md "No timer in a test" bullet says a stress worker's pause is not
      a timer it forbids and points at the entry; both trigger lists name the two new cases.
- [x] Decisions: d-20261121-8509332b, d-20261121-60bce682
- [x] Mechanism claims checked against the source: the race-test fix the stress-worker entry
      describes (workers pause up to 5 ms after each write, a fixed rename count, a stop file)
      and its measured result are in the commit that paced the memory-engine writer-race tests;
      the worker-stderr entry's Errno 13 body-head read is in the release that fixed the Windows
      rename race. `mutation_arm.py --help` lists `--revert FILE REV` (home
      `skills/compuse-toolbox/scripts/`).
- [x] Not applied, already covered: equal-work windows for a growth-ratio test are item 2 of
      references/silent-test-defeaters.md "A growth-ratio check: user CPU time, equal windows,
      fresh pages, measurable work" ("Give both arms EQUAL windows before taking the minimum of
      N: time the n arm as k back-to-back scans and divide by k.").
- [x] Step 0b: `skill_decisions.py show process-test-design --kind rejected,removed --full`
      printed nothing; no live rule's anchor touched.
- [x] RED as a text check, opus and haiku, on the pre-edit text (SKILL.md "No timer" bullet and
      "Reproducing a flake", the reference's loop-bound, shared-append and tool-reason entries):
      both answered NONE for what to change about the stress workers and for reading worker
      stderr first; opus proposed removing the waiter's 50 ms poll as "a timer" and stretched the
      tool-reason entry onto worker stderr as "my own stretch".
- [x] GREEN quote-back, opus and haiku, on the edited text: every answer for the workers' pause,
      the count-ended loop and stop file, the proof recipe, the pause-is-not-a-timer question,
      reading worker stderr first and the per-worker stderr file was quoted from the new text;
      a checker found each quote in the edited text and none in the pre-edit text (10 of 10).
- [x] Gaps from GREEN, closed and re-probed on the final text (opus and haiku, all quotes from
      the new text): what bounds a worker loop and what happens to workers left running (closed:
      an iteration cap that never binds while the stop file works, every worker killed in a
      `finally`); whether to inject a clock into the code under test's lock wait (closed: it
      keeps its real wait, across processes there is no clock to inject).
- [x] Gaps declined: the pause and cap sizes (judgement; the measured values are the example);
      the starvation recipe's competitor count and slowdown (covered in SKILL.md "Reproducing a
      flake", "Raise the count until the starved arm runs about 1.6x to 2.3x as long"); the
      product fix behind the stderr example (a retry) is the code's, not the test's; a test
      process killed before its `finally` (outside what a test can handle); SKILL.md's
      inject-the-clock sentence carrying no carve-out of its own (the next sentence routes to the
      reference entry, which states it).
- [x] Width and fence check over the added lines printed nothing; the paragraph after each
      insertion point read ("such a timer" re-bound to the injected clock, reworded to "a timer
      this rule forbids"); no list introduction carries a count.
- [x] Description measured: unchanged (frontmatter not edited).
- [x] Present tense, no history lines (finder over the added lines: no hit), no private hosts,
      paths or personal data (address scan over the added lines: no hit), ASCII only.
