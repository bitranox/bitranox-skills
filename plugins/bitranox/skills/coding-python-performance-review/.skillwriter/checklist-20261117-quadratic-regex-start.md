# skill-writer checklist - coding-python-performance-review (20261117, quadratic regex start)

Change: one rule in Step 4b, after the uncompiled-regex paragraph: a compiled pattern whose match
can start at many positions of one run is quadratic under `finditer`/`search`/`sub`/`findall`.
Two shapes as examples of the one cause (CLASS+ before a required suffix; a newline start
alternative followed by `\s*`), their fixes (a same-class negative lookbehind; `[^\S\n]*` after
the anchor), and the proof pair (growth ratio at N and 8N, one run per character kind; an old/new
replay over real inputs comparing what the caller uses, not the raw spans).

- [x] Step 0b: `show --kind rejected,removed --full` printed nothing; the live rules
      (method-lives-in-generic, regex-severity) are kept: the generic skill names catastrophic
      backtracking and quadratic work, this skill adds only the Python `re` remedies.
- [x] Premises checked by measurement, not taken from the queue entry:
      shape 1 `[\w./-]+\.(?:py|sh)\b` 3.47 ms at 2,000 chars, 222.8 ms at 16,000 (64.3x);
      anchored 0.022 and 0.162 ms (7.5x); spans identical on 7 samples.
      Shape 2 `(?:^|(?<=[;&|\n]))\s*echo\b` 0.42 ms at 500 blank lines, 25.7 ms at 4,000 (60.5x);
      with `[^\S\n]*` 7.9x; spans move on 2 of 6 samples (blank lines before the command), which
      is why the text compares what the caller uses rather than spans.
- [x] Claims in the new text executed: a narrower lookbehind `(?<![\w])` stays 61.3x on a `./`
      run (7.6x on letters only, so a letters-only growth test would pass it); a wider one
      `(?<![\w./+-])` drops `b.py` from `a+b.py`.
- [x] RED: the lesson is already in this machine's memory store (`redcheck --corpus-cascade`
      named a tree-top fact on anchoring and lookbehind run shapes), so a behavioural RED cannot
      fail honestly. Route taken: text check of the skill file. Pre-edit counts: `lookbehind` 0,
      `[^\S\n]*` 0, `growth-ratio` 0, `every position` 0.
- [x] GREEN: quote-back probe on opus and haiku (2 tiers, 4 regex questions each) over the
      edited 4b text plus Step 5 severity; see the GREEN section below.
- [x] Width and fence check over the added lines printed nothing; the paragraph after the
      insertion is the 4c heading.
- [x] Decided beyond the reported defect: the finding is filed under the existing Unsafe Input
      type, SEVERE when the scanned text can grow without bound or real input already costs
      seconds per run, MEDIUM when it only costs measurably on a hot path. Stated in the text; no
      new finding type added.
- [x] GREEN round 1 (opus and haiku, 4 regex questions each): both changed the pattern to the
      same-class lookbehind, rejected a `(?<![\w])` lookbehind quoting the narrower-class sentence,
      replaced `\s*` with `[^\S\n]*`, and read moved spans as expected. Gaps both tiers raised and
      closed: "one scan takes seconds" was ambiguous against a per-run figure and against Step 5's
      "grow unbounded" (severity sentence rewritten as above); "one run per kind of character" was
      not spelled out (now names the four runs for `[\w./-]`). Declined: the `^` alternative of
      the second shape (the text names the newline alternative as the shape; `^` matches once).
- [x] GREEN round 2 (haiku, final text, the touched questions): quoted the four-run list and the
      SEVERE/MEDIUM sentence verbatim; SEVERE for a transcript scan, MEDIUM for a bounded
      40-character input on a hot path. Its remaining gaps are excerpt limits (run sizes, the
      Step 6 finding format), covered outside the excerpt.
- [x] Proposed, not built: a static check in `find_uncompiled_regex.py` (it scans only uncompiled
      calls today, so it would need to read compiled patterns too and add a finding type Step 5
      parses).

Decisions: d-20261117-c546f20d
