# skill-writer checklist - coding-python-enforce-data-architecture-strict (2026-10-29, STEP D Jev shadow removed)

The `data-arch-dict` Jev shadow site is removed from the tool (`meta-self-improve/jev_sites/
data-arch-dict.json` deleted, `jev_shadow_sites.AGENT_BUILT` entry dropped, its
`references/jev-shadow.md` row deleted), so the STEP D bullet that ran it is removed. The edit is
one pure-deletion hunk of 11 lines; STEP D's own grep-and-judge bullet before it and the
"If a real violation is found: GOTO STEP A" line after it are unchanged.

- [x] Receipt checked fresh (`skill_receipt.py check meta-skill-writer`: fresh).
- [x] Skill type: technique; the test is whether a reader following STEP D is sent to a command
      that cannot succeed.
- [x] RED by text check against the pre-change file: STEP D told the reader to run
      `jev_shadow.py run --site data-arch-dict`, a site `run` now refuses (exit 2, pinned by
      `test_a_retired_site_is_an_unknown_site[data-arch-dict]`). With the site file deleted and
      this SKILL.md not yet edited, `test_every_site_a_shipped_doc_runs_has_a_site_file` failed
      with `{'data-arch-dict': ['coding-python-enforce-data-architecture-strict']} == {}`.
- [x] GREEN: the same test passes on the edited file; `grep -n -i 'jev\|data-arch-dict'
      SKILL.md` finds nothing; `git diff` shows only deleted lines, no reflow of the neighbours.
- [x] STEP D still complete without the bullet: it reads the violations file, greps for
      candidates, judges each hit against the Exceptions rule, and branches on the result; none
      of those referred to the shadow's files or verdicts.
- [x] Table/format: `reformat_tables.py --check` reports Unchanged for this SKILL.md and for
      `meta-self-improve/references/jev-shadow.md`.
- [x] Gaps, each decided:
      - quote-back probes (opus + haiku) - DECLINED for this change: a pure deletion adds no text
        to quote back; the regression a reader could hit (a dangling `--site`) is pinned by the
        doc-scan test above, which covers every shipped skill doc.
- [x] Not mirrored (`repo-gate.py --mirrors` lists no twin for this skill).
- [x] Description unchanged - no routing keyword moved.
- [x] No address, hostname or machine path added; ASCII only; no version-history phrasing.
