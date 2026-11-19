# skill-writer checklist - process-test-design (2026-11-19, duplicate module-level defs, growth-ratio clock and measurable work)

- [x] Change 1: references/silent-test-defeaters.md, new entry "A second module-level `def` of a
      helper replaces the first for every caller", in "Python patch and import mechanics": the
      later def wins for every caller; F811 skips names matching `dummy-variable-rgx` (default:
      any `_` name) and a redefinition used at module level in between; close the shape with an
      ast repo test over `tree.body` that skips module-level if/try and overload stubs and fails
      on zero files examined; it points at `hooks/tests/test_no_duplicate_module_defs.py`.
- [x] Change 2: same reference, "A growth-ratio check": a fourth requirement, never divide by an
      arm that did no measurable work (keep the cheap negative case's input, return both arm
      times, pass a large arm under a floor without a ratio, guard with `small > 0`, RED the floor
      with a known super-linear case). Matches the shipped test fix (`_arm_times`, `_is_linear`,
      `_is_quadratic` in coding-python-performance-review's test_find_uncompiled_regex.py).
- [x] Change 3: same entry, requirement 1: the recommended clock was `os.times().user`, which
      steps in whole clock ticks (10 ms on Linux); it now names
      `resource.getrusage(RUSAGE_THREAD).ru_utime` (RUSAGE_SELF without RUSAGE_THREAD, which then
      counts every thread), keeps `os.times().user` for Windows, and says to measure the step of
      the clock. This matches the form the plugin's own hooks/tests/test_secret_patterns.py uses.
- [x] Change 4: the routing paragraphs (SKILL.md and the reference's intro) gain "adds a
      module-level helper to a test module".
- [x] Decisions: d-20261119-07f19503, d-20261119-c53688a1, d-20261119-326aca14
- [x] Step 0b: no rejected or removed entries for this skill; no live rule's anchor touched.
- [x] Commands executed: ruff 0.15.0, 0.16.0 and 0.17.5 `--isolated --select F811` on scratch
      files: plain `helper` redefinition reported, `_helper` not, a module-level use between the
      defs not reported; the two real underscore pairs reported only with
      `dummy-variable-rgx = "^_$"`. Clock steps measured on Linux: os.times().user 0.01 s,
      getrusage ru_utime about 3 us.
- [x] RED as a text check against the pre-edit SKILL.md and reference (`git show HEAD:`): no
      match for F811, redefinition of a def, dummy-variable-rgx, ZeroDivision, clock resolution or
      measurable work. The cascade check (`redcheck --corpus-cascade`) named a memory fact about
      module-level CONSTANTS rebound (an assignment, not a def) and a fact on user time / equal
      windows / fresh pages; neither states either new rule, so the text check is the RED.
- [x] GREEN quote-back on opus (effort medium) and haiku against the edited entries: both tiers
      quoted the new sentences for which helper runs, why F811 is silent, the platform-branch
      exemption and zero-file refusal, the four changes for the cheap negative case, and the
      getrusage call.
- [x] GREEN gaps closed: "measurable work" read as "change the input" against the remedy that
      keeps it (the lead now says never divide, and the text says keep the input and change the
      check); "count as linear" now "pass the linearity check"; how the test tells a module-level
      `if` (count only `tree.body`); RUSAGE_SELF counts every thread.
- [x] Declined gaps: the floor's number and Windows clock step depend on the case and host (the
      text says to measure them); which clock a test that must cause page faults reads predates
      this edit and depends on whether the faults are the cost under test.
- [x] Re-probe of the touched questions on the final text, opus and haiku: both quoted the
      governing sentences and answered keep-the-input-change-the-check; no new undecided gap.
- [x] Width and fence check over the added lines printed nothing; the paragraph after each
      insertion point was read.
- [x] ASCII only, present tense, no private paths or hosts.
