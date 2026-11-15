# skill-writer checklist - coding-python-performance-review (2026-11-15, queued lessons)

Five additions: a profiled wait is timed without the profiler before it is reported (4c); a
record built around a container the function made is not a cache candidate as is, and the finder
now skips it (4a, `find_cache_candidates.py`); a one-slot identity cache for repeated decoding of
one immutable node (4a); a copy-per-call arm when a cached run fails because a caller edits the
result (Step 6); and where a decline goes when the instructions file cannot be written (Step 6).
The peak-memory method queued for this skill went to `coding-performance-review` Method step 13,
because the measurement method lives there (rule d-20261106-4e9b9bbf).

Decisions: d-20261115-3c68312e, d-20261115-d414eb39, d-20261115-fd389612, d-20261115-70736ca8, d-20261115-aeb6b855

- [x] Receipt fresh (`skill_receipt.py check meta-skill-writer`). Step 0b: `show
      coding-python-performance-review --kind rejected,removed --full` prints nothing; the two
      live rules (method-lives-in-generic, regex-severity) are untouched, and the peak-memory
      lesson was placed in the generic skill to keep the first one.
- [x] RED by text check of the pre-edit file (`git show HEAD:...`): `perf_counter`, `deepcopy`,
      `object identity`, `NamedTuple` and `worktree` each occur 0 times; none of the five rules is
      stated. Text check chosen over a behavioural arm because these lessons are recorded in this
      machine's memory store, so a dispatched probe could answer them from inherited context.
- [x] Script change test-first: `test_a_record_built_around_a_new_mutable_container_is_not_a_candidate`
      failed on the unchanged finder (it reported `walk_positional`, `walk_keyword`,
      `walk_dotted`), passes after the fix; the lower-case controls (`tuple(...)`, `",".join`,
      `max`) stay candidates. The skill's whole suite: 188 passed. The heuristic choice is in the
      script's docstring `Decisions:` block.
- [x] GREEN quote-back, opus and haiku, 5 questions on this skill (of 15 across four skills):
      every answer quoted the new text verbatim and answered correctly on both tiers.
- [x] Gaps from GREEN, closed: step 3's "if only the cached run failed ... report that instead"
      read as conflicting with the copy arm (opus) - reworded to "report that behaviour change AND
      measure a second cached arm"; whether `_Walk` counts as capitalised (opus, haiku) - now
      "capitalised after any leading underscores (`_Walk`, `Result`)". Re-probe on haiku of both
      questions on the final text: both quoted and answered correctly, no new gap.
- [x] Gaps declined: the finder's "skips" vs "not reported" wording (haiku) - the paragraph
      opens "is never reported" for the same rule; elided steps in the excerpt - excerpt artifact,
      the full file holds them.
- [x] Width and fence check over the added lines: no output. Paragraph after each insertion read:
      no back-reference re-bound. ASCII only; no private names, hosts or paths.
- [x] Present tense, no version history; no example address or path added.
