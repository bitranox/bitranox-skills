# Checklist 2026-11-08 - regex severity

Change: step 5 moves "uncompiled regex in a hot function" from SEVERE to MEDIUM and "in a
non-hot function" from MEDIUM to MINOR, matching the generic scale in coding-performance-review
(SEVERE = can exhaust memory or time). Step 4b no longer says the call "avoids recompilation on
every call": the `re` module caches compiled patterns, so the call pays a cache lookup. Step 5
adds that more patterns than the cache holds stays MEDIUM with the recompile named, and that a
pattern built from untrusted input is one SEVERE unsafe-input finding. The finder script's
docstring and `--help` text say the same.

- [x] Decisions: d-20261108-0833bd76
- [x] Step 0b: `skill_decisions.py show coding-python-performance-review` listed one rule
      (method-lives-in-generic). The change keeps the method in the generic skill and only
      re-aligns this skill's severity list with its scale.
- [x] Skill type: a reference correction inside a technique skill.

## RED

- [x] `redcheck --corpus-cascade` (exit 1) matched the cascade only on ordinary words (patterns,
      distinct, merge, regex in other senses); no named document states a regex severity. The old
      text is the RED: it said SEVERE for a hot uncompiled regex and claimed a recompile on every
      call. Measured 2026-11-08 on Python 3.14.4: `re.match(literal)` 240 ns against 130 ns
      compiled, `re._MAXCACHE` 512, so the old claim was false.

## GREEN (new text, text-only probe agent)

- [x] Opus and haiku: a hot `parse_line()` regex over a 2 GB log is MEDIUM, citing the cache.
- [x] Haiku re-probe on the cache-thrash sentence: 3,000 fixed patterns MEDIUM with the
      recompile named; patterns from a public web form SEVERE as unsafe input.

## Skill gaps and their disposition

- [x] Closed: "thousands of patterns" and "patterns from user input" were unclassified (first
      probe); added the cache-thrash and untrusted-pattern sentence.
- [x] Closed: one finding or two for an untrusted pattern, and the cache size (re-probe); the
      sentence now says ONE SEVERE finding with the recompile named inside it, and gives 512.
- [x] Declined, excerpt artefact: "hot function" is defined by step 4 (both regex scan and
      profiler hotspots), which the probe excerpt omitted.
- [x] Declined, outside the change: a search box that only picks among fixed patterns by index
      is not "built from untrusted input"; the wording already says built.

## Mechanical checks

- [x] No non-ASCII added (scan of the added diff lines). Long lines match the unwrapped
      paragraphs around them in this file.
- [x] Description unchanged; `build_skill_triggers.py` and `build_skill_docs.py` not needed.
- [x] `ruff check` passes on find_uncompiled_regex.py; its tests pass with the CI dependency set.
- [x] No version-history wording, no private paths or hosts added.
