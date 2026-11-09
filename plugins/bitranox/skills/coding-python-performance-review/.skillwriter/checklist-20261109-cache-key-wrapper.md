# skill-writer checklist - coding-python-performance-review (2026-11-09, cache-key wrapper)

"On accept - Cache Candidate" gains a step 1: when an error names a caller-only value, split the
function so the value stays out of the cache key, before the measurement.

Decisions: none - additive rule; the skill's ledger holds no rejected or removed entry

- [x] Step 0b `skill_decisions.py show coding-python-performance-review --kind rejected,removed --full` read before the first edit; it printed nothing.
- [x] RED, text check against the pre-edit file and every skill's Markdown: no wording for a value-free refusal or an uncached wrapper around `lru_cache`.
- [x] Placement: the recipe sits before the measurement, not beside the mutable-args step. Argued, not measured: with the path in the key, calls under different paths share no entry, so the step-2 measurement cannot show the hits and a recipe placed after a REJECT would not be reached.
- [x] The added command was executed in a small probe: two valid calls under two paths gave 1 hit and 1 miss; two refused calls under two paths each carried their own path, kept the original cause, and left nothing in the cache (`currsize` stayed 1, the body ran each time).
- [x] GREEN: no subagent probe ran on this change; the evidence is the text check of the final file and the executed probe. The description is unchanged.
- [x] Added lines checked: ASCII only, no history wording, prose lines within 100 columns, fence balance unchanged.
- [x] Deployment: committed with one version bump, pushed with CI watched.
