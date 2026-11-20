# skill-writer checklist - coding-python-performance-review (20261120, quadratic regex shapes)

Change: `find_uncompiled_regex.py` gains two quadratic-start shapes (`group-run-before-suffix`,
`repeat-after-optional-prefix`), reports how many call sites it examined, and exits 2 when that
number is 0. Step 4b now names four shapes with their fixes, explains the `Examined` line and the
zero-site exit, and adds a lookaround or backreference inside a repeated group to the hand-review
list; the Step 4 exit-2 paragraph and the Step 5 format line name the new output.

- [x] Step 0b: `show --kind rejected,removed --full` printed nothing. The live rule
      d-20261119-a189b19d is superseded by d-20261119-1b8203f4, which keeps its four anchors and
      adds three; its reopen condition (a further shape the finder misses) is what this change
      answers.
- [x] Premises checked by measurement: the old harness script-path pattern
      `(?:[\w.-]+/)+[\w.-]+\.(?:py|sh)\b` (found with `git log -S`) timed 63x on `a` and 64x on
      `a/` for 8x the input, and the old finder returned None for it; `(?m)^[^\S\n]*(?:then\s+)*git`
      timed 37x and returned None; `(?:ab)*c` 73x and None. The fixes `[\w.-]/[\w.-]+\.(?:py|sh)\b`
      (8.2x) and `(?:then[^\S\n]+)*` (7.75x) are linear and not reported.
- [x] Claims in the new text executed: `then\ngit` matches at (0, 8) under the old pattern and at
      (5, 8) under the fix, the same match count; `(?<!\d)v?\d+\.\d+` is not reported; the
      `Examined ... in 1 file` line and the zero-site exit 2 are pinned by CLI tests.
- [x] RED (opus, pre-edit excerpt, 4 questions): for both new shapes it answered "NONE" for a
      rewrite and guessed one; it named the `Examined` line and the zero-site exit 2 as
      undocumented.
- [x] GREEN round 1 (opus and haiku, the same 4 questions, the edited excerpt): both quoted the
      group-shape and optional-prefix sentences for the rewrites, the `M and R patterns were NOT
      checked` sentence for Q3 and the `S = 0` sentence for Q4. Gaps raised and closed: the Step 4
      paragraph read as a complete list of exit-2 causes (a 4b sentence added), and the fourth
      shape's fix moves a span without saying so (sentence added, measured above). Declined: a
      mapping from each unchecked category to one hand-review item (the list already names both),
      and the third-party `regex` module (out of the finder's scope).
- [x] GREEN round 2 (haiku, the two changed sentences): listed all three exit-2 causes from the
      first paragraph and answered that `then\ngit` still matches on the `git` line, quoting the new
      sentence; its remaining gaps came from the excerpt (the replay paragraph and the first shape's
      lookbehind were not in it).
- [x] Width and non-ASCII check over the added lines printed nothing; no private host or path.

Superseded: d-20261119-a189b19d.

Decisions: d-20261119-1b8203f4
