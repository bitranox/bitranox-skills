# skill-writer checklist - process-test-design (20261109, queued test-design rules)

Queue entries: A32, A33, A34, A35, A36, A37, A38.

- [x] Decisions: none - additive rules from queued items; no ledger rule was reversed or removed

- [x] Step 0b: `show --kind rejected,removed --full` read for this skill; no entry touched.
- [x] RED by text check against the pre-edit text (`git show HEAD:`): every distinctive phrase of
      the added rules was absent there (listed below). No behavioural RED: the session's always-
      loaded memory index states several of these lessons, so a probe could not fail honestly; the
      coverage check against the skill file is the evidence.
- [x] Phrases checked: "depth-limit", "OS-agnostic", "version-specific", "planted file",
      "randbelow", "call count", "cancel-point".
- [x] GREEN: quote-back probe over the pasted new text, 27 scenarios covering every added rule,
      `opus` at effort `medium` and `haiku`, 2 cells. Both tiers answered every scenario with a
      direct quote of the governing sentence, none NONE. Two scope controls (a different defect
      class; a child process that needs no version-specific dependency) were both correctly outside
      the new rules, so the rules do not over-trigger.
- [x] Executed: `json.loads` of 100000 nested brackets on CPython 3.14 raised `RecursionError` under
      an 8 MiB stack and decoded under `ulimit -s unlimited`; 3.13 raised in both, confirming the
      sentence.
- [x] A37 extends the existing below-the-floor bullet to a port the code BINDS; A33 adds a capped
      fake to the bounded-loop entry; A38 is a new silent-defeaters entry with both trigger lists
      extended.
- [x] Gaps declined: a module using `from json import loads` (the stand-in names the module
      attribute, the general seam rule covers the rest); a marker family where none exists (the 'two
      families' paragraph covers it).
- [x] Width and fence check over the added lines printed nothing new beyond this file's own long
      lines; ASCII only; frontmatter parses with a YAML loader and its description is under 1024.
