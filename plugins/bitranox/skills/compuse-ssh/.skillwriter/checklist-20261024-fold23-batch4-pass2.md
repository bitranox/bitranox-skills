# skill-writer checklist - compuse-ssh (memory rules folded in)

- [x] Change: ## Quick reference table, new last row after '`scp` to a DIFFERENT remote user'
      (padded to the existing column widths, 2 cells; reformat_tables.py --check --strict rc=0) -
      compuse-ssh/SKILL.md. RED on the pre-edit snapshot: partial. Verified: Not in the skill before
      (only the upload example `scp ./job.ps1 user@host:C:/Windows/Temp/job.ps1`,
      compuse-ssh/SKILL.md ~line 172): CONFIRMED by grep. Backslash-download failure and
      forward-slash success: UNVERIFIABLE here (needs a Windows OpenSSH host; no ssh run), so
      carried only as observed behaviour with the body's recorded error signature. Row fits column
      widths (col2 width 776, content shorter); table canonical per
      docs-md-table-formatting/reformat_tables.py --check --strict rc=0.
- [x] Dropped as stale or unverified: Dropped the private provenance (the snapshot tool name, the
      private VM fact link, the 21 MB interpreter figure and date) - kept as the generic 'whatever
      the job downloaded'. Placed in the pitfall table instead of the hint's Hook/script section,
      per skeptic.
- [x] Review C fixed: a backslash path is accepted as an upload destination and fails as a download
      source; the upload example gained a step 3 that fetches with a forward-slash source and tidies
      only after `test -s`; the cleanup is `cmd /c del a b`, measured on a Windows OpenSSH host with
      cmd and with PowerShell running it (both files deleted).
- [x] Receipt held (the coordinator ran skill_receipt.py start meta-skill-writer); every editing
      agent loaded the skill through the Skill tool before its first edit.
- [x] RED as a text check: an opus quote-back against a pre-edit snapshot of the skill. Only a
      verbatim quote from the snapshot counts, so context inherited from this machine cannot
      satisfy it; redcheck --corpus-cascade was not run.
- [x] GREEN quote-back on haiku and opus against the edited files: every scenario after the edit,
      every scenario again after the first review's fixes, then the scenarios each later fix
      touched. Every answer was a quote from the new text on both tiers in every round; no NONE.
      Quotes were checked against the files (6-word windows; misses traced to line wraps,
      markup and line-number prefixes).
- [x] GREEN diffed against RED both ways: every partial RED quote is still in the edited text.
- [x] Tiers haiku and opus, one cell per scenario per tier per round.
- [x] Independent review of the full diff, then a review of each fix delta alone; every finding
      fixed or declined above. Each GREEN reply's Skill gaps list was read; gaps not listed
      here asked for detail the rule does not need (out of scope) or were answered elsewhere in
      the skill.
- [x] Description measured: unchanged (frontmatter not edited).
- [x] ASCII only, present tense (history finder clean on the added lines), tables canonical
      (reformat_tables.py --check --strict), every fence closes, added prose wrapped at 100
      columns except where the file keeps one line per paragraph or list item.
- [x] Security scan: prose only; no secrets, hostnames, private paths or PII; values added are
      option names, commands, source file paths or reserved examples.
