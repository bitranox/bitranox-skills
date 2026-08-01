# skill-writer checklist - coding-python-uv (2026-08-02, missing extra is a hard error)

Change: a gotcha section for `uv pip compile --extra dev` hard-erroring when the extra is absent,
where pip only warns. Ships with plugin 5.139.0.

- [x] Receipt held (`skill_receipt.py start meta-skill-writer`, issued for this batch).
- [x] Measured, with the exact text and exit code a reader will see: `error: Requested extra not
      found: dev`, exit 2. Found sweeping 25 repos where 24 declared a `dev` extra and one did not,
      so the failure looked repo-specific rather than like a uv-vs-pip behaviour difference.
- [x] States the confusing SHAPE, which is the useful part: install succeeds and a later compile in
      the SAME workflow dies, because `uv pip install -e .[dev]` tolerates what `uv pip compile
      --extra dev` refuses. A reader hitting only the second half would not suspect the first.
- [x] Gives the fix as code that handles BOTH declaration forms - an extra and a PEP 735 dependency
      group - rather than telling the reader to "check first" and leaving the mechanism implied.
- [x] Placed as a sibling `## Gotcha:` section matching the file's three existing ones, so it is
      discoverable by the same heading pattern.
- [x] Verified ABSENT before writing and PRESENT after with control-gated `claim_check`.
- [x] No session narrative, no private paths, no repo names from the sweep in the shipped text.
- [x] Suites green and `repo-gate.py --ci` clean with the CI dependency set.
