# skill-writer checklist - process-test-design (a validator inherits its own parser's blind spots)

Change: one standalone paragraph after the codec/serializer-equivalence note, before
`## Quick checklist`. No bullet-list edit, no frontmatter change.

## PLAN

- [x] Skill type: reference (test-design guidance). Test approach: text check of the artifact, plus
      a demonstrated malformation, since the claim is prose guidance rather than a script.
- [x] Verified the motivating incident against live code instead of trusting it. The specific case
      on record - four SKILL.md files whose closing delimiter was glued onto the description - is
      ALREADY FIXED by `frontmatter_unterminated`, wired into `frontmatter_problems`. Writing the
      paragraph around that case would have documented a closed gap.
- [x] The still-open case is a different malformation: a second, later frontmatter-shaped block.
      `frontmatter_description` and `frontmatter_name` read via `text.split("---", 2)[1]`, and
      `maxsplit=2` buckets everything past the second delimiter into one string nothing inspects
      again.

## RED

- [x] Demonstrated the open gap rather than asserting it: a throwaway SKILL.md with a well-formed
      first block and a second, smuggled frontmatter-shaped block carrying a divergent description.
      `frontmatter_problems()` returned an empty list, and both readers returned the first block's
      values, so the file reads fully clean.
- [x] Confirmed the same parser shape recurs in this plugin's own memory tooling, so the lesson is
      not one module's accident: `reconcile_memory_index.py`'s `parse_frontmatter` also scans to the
      first bare delimiter and returns everything past it as an unexamined body.
- [x] Coverage checked with `claim_check.py` over all 100 `skills/*/SKILL.md` and
      `skills/*/references/*.md`: ABSENT, control matched 703 times across 100 files. Narrower
      checks on `process-test-driven-development` (SKILL.md and `testing-anti-patterns.md`) were
      also ABSENT with matched controls. The two hits in `coding-input-sanitization` are about a
      parser as an output SINK, which is the opposite direction from a validator reading input.
- [x] Read the target section in full. Its four existing mechanics are pytest and mocking idioms
      (import-copy binding, index-usage proof, basename collision, doctest teardown leak); none of
      them tells a reader to ask what a validator's own parser tolerates before trusting its silence.

## GREEN

- [x] Quote-back of the governing sentence: "Before trusting such a check, enumerate concretely what
      its own parser forgives (a duplicated block, a glued-on closing delimiter, a duplicate key a
      dict-based loader overwrites), then verify each one STRUCTURALLY against the raw text - a
      delimiter count, a line scan - rather than through the same parser, which by construction
      cannot see what it already swallowed."
- [x] Applied to the demonstrated case, the paragraph surfaces exactly the malformation the four
      pre-existing mechanics do not reach.
- [x] `old_string` verified unique by exact substring count before applying, and verified disjoint
      from the other edit landing in this file in the same change.

## REFACTOR

- [x] Considered folding this into the "Four mechanics" list and declined: those four are
      pytest-specific idioms, while this is a general validator principle that applies to a shell
      gate or a config loader just as much, and renumbering the list would blur its frame.
- [x] Considered the adversarial-inputs table's Structure row as a possible duplicate and declined:
      that row is about which malformed inputs to feed AT a boundary; this is about auditing the
      VALIDATOR's own parser before trusting its silence.
- [x] Kept the examples generic (a duplicated block, a glued delimiter, a duplicate key) rather than
      naming this repo's own files, so the paragraph states the language-neutral principle.

## Quality

- [x] ASCII only, present tense, no session narrative, no machine paths.

## Deliverables

- [x] One paragraph in `SKILL.md`, applied.
- [x] The code gap the demonstration exposed - no check anywhere detects a second frontmatter block
      in a SKILL.md or a fact body - is NOT fixed here. It needs its own change with tests, and it
      needs care that a legitimate `---` horizontal rule in a body does not become a false positive.
      Recorded as a queued contribution rather than left implicit in this artifact.
