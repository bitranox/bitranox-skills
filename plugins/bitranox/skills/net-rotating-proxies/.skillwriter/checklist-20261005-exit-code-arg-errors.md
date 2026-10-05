# skill-writer checklist - net-rotating-proxies (2026-10-05, exit-code arg-error cases, D-13/D-11)

Exit-codes paragraph extended: `run` also gives 2 when an argument cannot be used (an unsplittable
`--cmd`, an invalid `--dead-regex`, a non-UTF-8 `--worklist`); `validate` is a report and gives 0
even when no candidate turned out live.

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. Test approach: retrieval - two questions, each answered with a
      direct quote or NONE.
- [x] RED (pre-change text, pasted): "What does `run` exit when `--dead-regex` is not a valid
      regex?" - NONE (old text only names the binary-missing and no-usable-proxy cases). "Does
      `validate` ever exit non-zero when no proxy turned out live?" - NONE (old text says nothing
      about `validate`'s own exit code).
- [x] Verified against `proxy_pool.py` source: `_parse_run_inputs` raises `BadInput` on an
      unsplittable `--cmd` (shlex `ValueError`), an invalid `--dead-regex` (`re.error`), and a
      non-UTF-8 `--worklist` (`UnicodeDecodeError`), all mapped to exit 2; the `validate` CLI
      branch always `return 0` after its own could-not-run check.
- [x] GREEN (new text pasted): both questions now answer with a direct quote ("or an argument
      cannot be used (a `--cmd` that cannot be split...)", "`validate` is a report and gives 0
      even when no candidate turned out live").
- [x] GREEN diffed against RED in both directions: nothing removed, two gaps closed.
- [x] Description unchanged - no routing keyword moved.
- [x] No address, MAC, hostname or machine path added.
- [x] Present tense, no session narrative, no private provenance.
