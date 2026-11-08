# skill-writer checklist - coding-performance-review (2026-11-07, early-return advice)

Method item 2 ("Reproduce the recorded BEFORE figure first") gains the remedy for a BEFORE figure
that comes out far too fast: "count calls into the hot function to find the guard that returns
early, change the input so it reaches the slow path, repeat this check, and leave a comment in the
test saying why its input has that shape". coding-python-performance-review carried the first and
last parts and now points here for the method, so without this they were in neither skill.

Decisions: none - restores advice the Python skill carried before it pointed here; no rule changes.

- [x] Receipt fresh; Step 0b: `show coding-performance-review --kind rejected,removed --full`
      printed two rejected entries (one-skill-per-language-refs, description-trigger-words);
      neither is touched (no description, no structure change).
- [x] RED (text check): `grep -i "count calls"` over both skills' SKILL.md found nothing; the
      Python skill's pre-edit text (`git show HEAD:`) had it at line 111.
- [x] GREEN quote-back, opus (effort medium) and haiku, 2 cells. Q: backlog 40 s, probe on the
      unfixed code 0.2 s, what next. Both quoted "count calls into the hot function to find the
      guard that returns early". Both arms of the first round reported that the text does not say
      to change the input and re-run the check; the clause "change the input so it reaches the
      slow path, repeat this check" closes it. Re-run on the final text: both quoted that clause
      and read "this check" as the order-of-magnitude BEFORE check.
- [x] Remaining gaps (both tiers), declined:
      - how to count calls (profiler, counter, tracer): left to the reader, the skill is
        language-neutral and each language skill names its tools;
      - "order of magnitude" and "far too fast" thresholds: a factor of 10 either way is the
        plain reading, and the item gates trust, not a fine boundary;
      - a 200x gap could be different settings rather than a guard: item 3 ("Identical settings
        on both sides") directly follows and covers it;
      - reshaping the input versus item 1's real workload: the reshaped input exists to reach the
        slow path the real workload hit, which is what item 1 asks for;
      - no exit when no input reaches the slow path: then the recorded figure cannot be trusted
        either, a judgement left to the reader.
- [x] Added lines: none over 100 columns, no fence. ASCII only.
