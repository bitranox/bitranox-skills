# Checklist 2026-11-08 - dhat out of timings and production

Change: the dhat recipe says `dhat::Alloc` slows every allocation by an amount the crate calls
"can be large", so no timing is read from a dhat build, and gates the allocator and profiler
behind a `dhat-heap` feature the way the crate documents. It notes that `dhat` itself stays a
plain dependency and that the pattern is read from the dhat 0.3.3 docs, not run. The description
keeps its words: a rewrite to avoid co-nomination was checked and rejected.

- [x] Decisions: d-20261108-7f1a2c02, d-20261108-c51412ee
- [x] Step 0b: `skill_decisions.py show coding-rust-performance-review` listed no-bundled-scripts,
      scripted-pipeline, description-trigger-words and lazylock-and-regex-semantics. None is
      touched: no script added, the description is unchanged.
- [x] Skill type: a tool recipe in a reference skill.

## RED

- [x] The old text is the RED: it gave the two dhat lines with no warning, so a teammate could
      merge them and quote the run's wall-clock time. `redcheck --corpus-cascade` matched only
      ordinary words.
- [x] Description: replayed skill-router `match()` over 8,341 typed prompts with the committed
      skill_triggers.json. The skill was nominated 0 times.

## GREEN (new text, text-only probe agent)

- [x] Opus and haiku: refused the timing as a baseline and asked for the feature-gated form
      before merging.

## Skill gaps and their disposition

- [x] Closed: whether `dhat` still compiles into a build without the feature (first probe);
      added the plain-dependency sentence.
- [x] Declined, unmeasured: how large the slowdown is; the crate gives no figure and none was
      run here, which the text says.

## Mechanical checks

- [x] No non-ASCII added, no line over 100 columns.
- [x] Description unchanged; derived artifacts not regenerated.
- [x] No version-history wording, no private paths or hosts added.
