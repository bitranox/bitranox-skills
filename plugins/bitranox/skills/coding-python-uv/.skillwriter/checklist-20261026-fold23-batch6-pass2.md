# skill-writer checklist - coding-python-uv (memory rules folded in)

- [x] Rule: Put --exclude-newer before the package spec (uvx --exclude-newer "14 days"
      pkg@latest), because anything after the spec goes to the tool and runs unprotected. @latest
      then resolves to the newest release the cutoff allows, transitive deps included.
      UV_EXCLUDE_NEWER or the user uv.toml also apply. A 'uv tool install --force pkg@latest'
      without the flag drops the cutoff stored in the receipt. Verify by comparing the resolved
      tool version with PyPI's newest release and with the newest one the cutoff admits.
      Where: SKILL.md), 07-tools-and-scripts.md new '### A Supply-Chain Cooldown for `uvx` and `uv tool`'
      after 'Requesting Specific Versions'; SKILL.md task-routing table row after 'Project
      dependency cooldown (exclude-newer)'
- [x] Rule: Recognise that the uvx-launched daemon holds uv's cache lock, so a plain clean waits
      on it forever without saying so; uv is not hung. Do not kill uv, restart the daemon or
      delete cache dirs by hand. Run 'uv cache clean --force <pkg>' (the daemon keeps running),
      knowing it leaves uvx's ephemeral archive/environment dirs behind, and list the cache
      afterwards to see what was actually removed.
      Where: 10-configuration.md (+ SKILL.md routing row, + 07-tools-and-scripts.md Tool Environments
      reconcile), 10-configuration.md '### Dependency caching' new bold paragraph after the escape
      hatches; SKILL.md task-routing row after 'Cache problems / disk space'; 07 '### Tool
      Environments' parenthetical
- [x] Receipt held (the coordinator ran skill_receipt.py start meta-skill-writer); every editing
      agent loaded the skill through the Skill tool before its first edit.
- [x] RED as a text check: an opus quote-back against a pre-edit snapshot of the skill. The rules
      under test are recorded in this machine's memory store, so a behavioural arm would be
      contaminated; only a verbatim quote from the snapshot counts.
- [x] GREEN quote-back on haiku and opus against the edited files (6 questions), again after the
      review fixes for every question, and a third time for the 1 questions the fix-delta fixes
      touched: every answer quoted the edited text, no NONE. Quotes were substring-checked against
      the files; the pre-edit snapshots fail the same check.
- [x] GREEN diffed against RED both ways: every partial RED quote is still in the edited text.
- [x] Tiers haiku and opus, one cell per question per tier per round.
- [x] Independent review of the full diff, then of the fix delta alone; every finding fixed or
      declined with evidence by the fixer, and the fix delta re-reviewed.
- [x] Each GREEN Skill gaps list triaged: 6 closed in the text, 11 declined with a reason (covered
      elsewhere with file:line, out of scope, owned by another skill, or a judgement the skill
      leaves open).
- [x] Description measured: unchanged (frontmatter not edited).
- [x] ASCII only, present tense, tables canonical (reformat_tables.py --check --strict), added
      prose wrapped like the surrounding text, no code span split across lines.
- [x] Security scan: prose only; no secrets, hostnames, private paths or PII; addresses are
      documentation ranges or placeholders.
