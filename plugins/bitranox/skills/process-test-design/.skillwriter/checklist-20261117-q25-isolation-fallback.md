# skill-writer checklist - process-test-design (an isolation fixture sets the fallback knob)

- [x] Change: references/silent-test-defeaters.md, new entry after "Port a template's autouse
      fixtures along with its tests" - an autouse isolation fixture for an override-plus-fallback
      lookup points every platform's fallback knob under the temp dir and removes the override
      with `setenv` then `delenv`; a file it plants to stop an upward search is expected by, or
      bypassed by name in, every test that counts that search's results; the root-conftest rule
      for `src/` doctests is pointed at, not repeated. The trigger lists at the top of the
      reference and in SKILL.md gained "isolates the suite in an autouse fixture".
- [x] Decisions: d-20261117-4e1d130b
- [x] Already covered, not added: a fixture that must reach `src/` doctests belongs in a root
      `conftest.py` ("`tests/conftest.py` fixtures never reach a `src/` doctest").
- [x] Step 0b: no rejected or removed entries; no live rule's anchor touched.
- [x] Mechanism executed: a pytest probe with `config_root() = LIB_X_ROOT or APPDATA` and a test
      setting `APPDATA` failed (1 failed) under an autouse fixture setting the override and passed
      (1 passed) under one setting the fallback and removing the override with setenv then delenv.
- [x] RED as a text check: an opus quote-back (effort medium) against the pre-edit text answered
      NONE for which knob to set and for the planted-sentinel count.
- [x] GREEN quote-back on opus (effort medium) and haiku against the edited text: both quoted the
      new entry. Round 2 after the fixes below re-asked the touched questions on both tiers.
- [x] GREEN gaps closed: which platform's fallback to set (now every one the lookup reads); the
      sentinel line told the reader to plant it "only where no counting test searches", which
      conflicts with its purpose (now: expect it, or assert on planted files by name); the entry
      prescribed `delenv(..., raising=False)`, which the same file's Determinism section shows
      records nothing to undo for an absent variable (now setenv then delenv, with a pointer).
- [x] Declined gaps: macOS or HOME redirection (the entry names the knobs the lookup reads, the
      reader lists them for their lookup); how to write the expected count (project-specific).
      Round 3 (opus and haiku, the delenv question alone) quoted the setenv-then-delenv text and
      found no two passages disagreeing; its remaining gaps (whether the rich-click entry's
      "delenv loop" needs the setenv form, line 82's `setenv` / `delenv` pair without a pointer)
      sit in pre-existing entries about other traps and are left for an edit of those entries.
- [x] Width and fence check over the added lines printed nothing; tables canonical.
- [x] Description measured: unchanged (frontmatter not edited).
- [x] Present tense, no history lines, no private hosts, paths or personal data.
