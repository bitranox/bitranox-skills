# skill-writer checklist - coding-python-uv (memory rules folded in)

- [x] Change: ## Dependency Cooldowns, new paragraph directly after the 'A project's cooldown
      belongs in pyproject.toml, never on uv add' paragraph - coding-python-uv/05-resolution.md. RED
      on the pre-edit snapshot: NONE. Verified: Probed read-only in a scratchpad project with uv
      0.13.0 (`uv lock --offline`): (1) [tool.uv] exclude-newer = "7 days" + exclude-newer-package =
      { setuptools = false } -> rc=0, uv.lock has [options] with exclude-newer =
      "0001-01-01T00:00:00Z" (comment: no effect, backwards compat) and exclude-newer-span = "P7D",
      plus [options.exclude-newer-package] setuptools = false. (2) Same with "7 dayz" -> stderr
      'warning: Failed to parse `pyproject.toml` during settings discovery:' + TOML parse error,
      rc=0, uv.lock has NO [options] table (the valid exclude-newer-package was dropped too = whole
      table ignored). (3) Valid exclude-newer = "7 days" beside resolution = "bogus" -> same warning
      ('unknown variant `bogus`'), rc=0, zero 'options' lines in uv.lock (a bad value in ANOTHER key
      kills the cooldown). (4) resolution = "lowest" + managed = true -> [options] carries
      resolution-mode = "lowest" only, managed absent (confirms skeptic's caveat that [options]
      holds only resolution settings).
- [x] Dropped as stale or unverified: Dropped the fact body's/hint's 'require the expected keys' as
      a general check for any [tool.uv] key (skeptic caveat, confirmed by probe 4): narrowed to
      resolution settings, other keys verified by their own effect. Dropped the skeptic's '(Observed
      on an unrecorded uv version; re-check on yours.)': replaced by the version actually measured
      (0.13.0). Reconciled with the existing paragraph above, which tells readers to verify a
      cooldown with `grep exclude-newer pyproject.toml`: the new text states that grep only proves
      the line is present, not that uv parsed it (the existing line was left intact).
- [x] Change: 06-python-versions.md: ## Viewing Available Python Versions, new paragraph right after
      the first `uv python list` block. SKILL.md: Command-to-Document Quick Reference, `uv self
      update` row - coding-python-uv/06-python-versions.md (plus one table cell in SKILL.md). RED on
      the pre-edit snapshot: NONE. Verified: Baked-in list: `uv python list 3.13 --all-versions
      --offline` (uv 0.13.0) prints `<download available>` rows (e.g. cpython-3.13.15 ... <download
      available>) with no network, so the download list is local to the binary. `--mirror`
      semantics: `uv help python install` -> '--mirror <MIRROR> Set the URL to use as the source for
      downloading Python installations. The provided URL will replace ...' (host only). Other
      install channels: 01-getting-started.md 'Upgrading uv' section ('When another installation
      method is used, self-updates are disabled. Use the package manager's upgrade method instead').
      The 0.11.15 / 3.15.0b1 measurement is from the fact body and not re-measurable; kept as an
      explicitly 'observed' measurement with its version. Exact install error text not verified, so
      worded generically ('finds no matching download'). Table: reformat_tables.py --check --strict
      SKILL.md -> 'Unchanged: SKILL.md'; row length 181 = header length.
- [x] Dropped as stale or unverified: Did not use a numbered gotcha (skeptic: 06-python-versions.md
      numbers items only inside the 'install does not upgrade' gotcha); placed as a bold paragraph
      at the `uv python list` trigger point instead. Did not mention --python-downloads-json-url (a
      custom list the user supplies) to keep the rule focused; nothing stale in the body.
- [x] Review B fixed: the lock records a duration cooldown as exclude-newer-span beside an
      exclude-newer placeholder 0001-01-01T00:00:00Z that has no effect, which the text now says
      explicitly next to the upstream paragraph describing a computed timestamp (measured on uv
      0.13.0: uv lock writes that placeholder with its own comment "This has no effect").
- [x] Gaps declined: how a per-package value is written (documented by the upstream paragraph right
      after); uv self update when uv is externally managed (covered in 01-getting-started.md,
      UV_UNMANAGED_INSTALL).
- [x] Receipt held (the coordinator ran skill_receipt.py start meta-skill-writer); every editing
      agent loaded the skill through the Skill tool before its first edit.
- [x] RED as a text check: an opus quote-back against a pre-edit snapshot of the skill. Only a
      verbatim quote from the snapshot counts, so context inherited from this machine cannot
      satisfy it; redcheck --corpus-cascade was not run.
- [x] GREEN quote-back on haiku and opus against the edited files: every scenario after the edit,
      then the scenarios each review fix touched (6 after the first review, 1 after the second).
      Every answer was a quote from the new text on both tiers in every round; no NONE. Quotes
      were checked against the files; misses traced to line wraps and the arm's own commentary.
- [x] GREEN diffed against RED both ways: every partial RED quote is still in the edited text.
- [x] Tiers haiku and opus, one cell per scenario per tier per round.
- [x] Independent review of the full diff in three slices, then a review of each fix delta alone;
      every finding fixed or declined above. Each GREEN reply's Skill gaps list was read; gaps
      not listed here asked for detail the rule does not need or were answered elsewhere in the
      skill.
- [x] Description measured: unchanged (frontmatter not edited).
- [x] ASCII only, present tense (history wording absent from the added lines), tables canonical
      (reformat_tables.py --check --strict), every fence closes, added prose wrapped at 100
      columns, no code span split across lines.
- [x] Security scan: prose only; no secrets, hostnames, private paths or PII; values added are
      option names, commands, source file paths or reserved examples.
