# meta-claude-hooks review - 2026-08-23

Change under review: `references/io-contract.md` gains a `classifierContext` subsection and a
decision-control row; `references/upstream-stamp.json` is re-stamped; `SKILL.md` line 8 carries the
refreshed baseline (`17e8aaf586b4` -> `70c05a3733e6`, fetched date). No behavioural rule changed.

## Skill type and test approach

Reference skill. Tested by retrieval and by gate behaviour, not by pressure scenario: the edit adds
a field to a lookup table, so the question is whether a reader can find it and whether the tooling
that certifies this file can tell the difference.

## RED

- [x] RED ran and did NOT fire, which is the reportable result. Deleting the `classifierContext`
      subsection and its table row and re-running `hookdoc_stamp.py coverage` gave
      `coverage: complete (31 events, 65 required names)` and exit 0 - the same verdict as with the
      content present. The field moved only the advisory line, `12 of 96` -> `13 of 96`.
- [x] Conclusion recorded rather than worked around: `coverage` does NOT gate this field. Its
      blocking tier covers events, contract names, environment variables and handler types;
      per-tool example keys are advisory by design, because a gate that can never go green gets
      switched off. The detector that caught this was `check`, not `coverage`.
- [x] The advisory delta is the evidence the addition landed where the stamp looks: 13 with the
      section removed, 12 with it present.

## GREEN

- [x] `hookdoc_stamp.py check --json` returns `CURRENT` for both sources
      (hooks-reference `70c05a3733e6`, hooks-guide `ec9b5840cf98`), where it returned `STRUCTURAL`
      before the edit, naming exactly `H4:Annotate a result for the auto mode classifier` and the
      `classifierContext` json_field and table_key.
- [x] `hookdoc_stamp.py selftest` returns `COSMETIC`, `STRUCTURAL` and `BROKEN` on its three
      samples, so the `CURRENT` above is a verdict the detector was capable of withholding.
- [x] Content verified against the upstream text, not paraphrased from the field name: the
      subsection states the audience (the auto mode classifier, which never receives tool results),
      the version floor (v2.1.236), the trust split between Claude-Code-configured hooks and
      in-process SDK callbacks, and all four delivery limits (2,000 chars shared per call;
      synchronous responses only; recorded calls only; return with the rewrite or be dropped).
- [x] `cli_ahead_of_docs` remains `true` (CLI 2.1.240, docs cover to 2.1.234). Unchanged by this
      edit and still reported, because it is a separate signal from the verdict.

## REFACTOR

- [x] Gap: a reader wanting to tell the classifier something previously found only
      `additionalContext`, whose audience is Claude. Closed by placing `classifierContext` directly
      after the `additionalContext` subsection, so the two are adjacent where the choice is made,
      and by stating in the first line that it does not go to Claude.
- [x] Gap declined: `coverage` not gating advisory field names is left as designed. Promoting every
      example key to the blocking tier would fail on upstream detail this skill does not own.
- [x] Both directions checked. The edit adds one subsection and one table row; no existing row,
      heading or rule was removed or reworded. `git diff --stat` shows references/io-contract.md at
      31 insertions and 0 deletions.

## Quality checks

- [x] Present tense, no session narrative, no operator instructions, no scratch paths.
- [x] No machine-specific values added: `grep -nE '([0-9]{1,3}\.){3}[0-9]{1,3}|([0-9a-f]{2}:){5}[0-9a-f]{2}|/home/|/Users/|/tmp/'`
      over the changed reference returns nothing.
- [x] Frontmatter untouched; `name` and `description` unchanged, so no CSO impact and no
      description-length risk.
- [x] Hub routing table unaffected: the change is inside an already-routed reference file, and its
      row in the SKILL.md table ("I/O contract - ... `additionalContext`, decision control per
      event ...") already covers this content.
- [x] No scripts added or changed, so the shipped-tests requirement is unchanged; the skill's
      existing `scripts/` tests still pass (`coverage`, `selftest` both exit 0).
- [x] Security: the diff adds documentation prose only. It carries the upstream warning against
      copying untrusted tool output into the field, which is the security-relevant part.
