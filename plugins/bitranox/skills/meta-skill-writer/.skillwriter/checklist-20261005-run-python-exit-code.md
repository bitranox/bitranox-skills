# skill-writer checklist - meta-skill-writer (2026-10-05, run-python.sh exit-code line, D-11/DOCDELTAS)

A separate, later fix to the SAME file as checklist-20261005-exit-code-standard.md (that one
covered render-graphs.js/redcheck; this one covers the "Bundled scripts and hooks" paragraph
about `run-python.sh` itself): "it exits 3, so a hook registration must pass `--hook`" ->
"it exits 2, so...".

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. Test approach: retrieval - one question answered with a direct quote
      or NONE.
- [x] RED (pre-change text, pasted): "What exit code does a CLI call to `run-python.sh` give
      when it cannot run the script?" - direct quote of the OLD text: "it exits 3" (stale - D-8's
      run-python.sh change, commit 303fce9c, moved this to 2 plugin-wide).
- [x] Verified against `hooks/run-python.sh` source: "The shim could not run the script: always
      say so on stderr, then exit 2 for a CLI caller" - the file's own comment confirms 2, not 3.
- [x] GREEN (new text pasted): same question now answers with a direct quote of the NEW text:
      "it exits 2".
- [x] GREEN diffed against RED in both directions: nothing removed, the stale digit corrected.
- [x] Description unchanged - no routing keyword moved.
- [x] No address, MAC, hostname or machine path added.
- [x] Present tense, no session narrative, no private provenance.
