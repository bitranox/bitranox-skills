# skill-writer checklist - docs-md-table-formatting (2026-10-16, fold23)

- [x] Change: pipe-in-code-span paragraph extended - a RENDERED cell count cannot detect it, because
      GFM drops the surplus and the rendered count equals the header's in exactly the broken case.
- [x] Change (withdrawn after verification): the drafted "unbalanced code span" paragraph was
      removed; GFM renders it correctly, see GREEN.
- [x] Claim checked by running the tool: a 3-column table with the row `` | x | it`s | z | `` through
      `reformat_tables.py --strict` exits 0 with no ragged warning, while the row
      `` | x | `p | q` | z | `` exits 1 with "ragged table row - 4 cells under a 3-column header".
- [x] Receipt held (coordinator ran skill_receipt.py start meta-skill-writer); this agent loaded
      the skill
- [x] RED (text check of the artifact): before this edit the skill covered only the pipe inside a
      code span; the verifier found nothing on an UNBALANCED span, no even-backtick check, and no
      note that the pipe count reads correct in both cases. Behavioural RED replaced on purpose
      because the rule is in the always-loaded memory index of the authoring machine (inherited
      coverage)
- [x] GREEN quote-back (fresh-context verifier): pipe in a code span -> SKILL.md:116 "Do not check it by
      counting RENDERED cells: GFM drops the surplus"; confirmed by rendering `| x | `p | q` | z |`
      with cmarkgfm (x / `p / q`, z dropped). The unbalanced-span paragraph was REMOVED: rendered with
      cmarkgfm and markdown-it-py, `| x | it`s | z |` gives three cells (x / it`s / z), because GFM
      splits cells before it parses code spans, so a stray backtick cannot swallow a separator.
- [x] Gaps closed or declined: the unbalanced-span half of the rule is declined as false on GFM
      (measured above); only the rendered-count warning ships.
- [x] Description measured: unchanged (165 characters)
- [x] Security scan: prose only, no secrets, hostnames, paths or PII
